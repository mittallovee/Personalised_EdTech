"""M4 PR 4f: free-text and typo search of the bank (F-03; test T38 part 2).

The search reads the same ``bank_index`` rows as the list, through the same visibility and
filters, so a private draft is never a hit. Exact words come first, close words (typos) after them.
"""

from collections.abc import Iterator
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from qbank import cli
from qbank.core.config import AppEnv, Settings
from qbank.core.db import Database
from qbank.core.tenancy import TenantContext
from qbank.main import create_app
from qbank.modules.search import service
from tests.integration.conftest import (
    Member,
    MigratedDatabase,
    make_member,
    platform_admin,
    sign_in,
)
from tests.integration.question_support import Catalogue, ready_for, seed_catalogue

QUESTIONS = "/api/v1/questions"
BANK = "/api/v1/bank/questions"
CHAIN = [("pass-qc", "qc"), ("approve", "approver"), ("publish", "publisher")]


def make_settings(migrated_database: MigratedDatabase, **more: Any) -> Settings:
    return Settings(
        app_env=AppEnv.TEST,
        database_url=migrated_database.app_url,
        session_cookie_secure=False,
        login_attempts_per_ip=10_000,
        login_attempts_per_email=10_000,
        **more,
    )


@pytest.fixture
def client(migrated_database: MigratedDatabase) -> Iterator[TestClient]:
    with TestClient(create_app(make_settings(migrated_database))) as test_client:
        yield test_client


@pytest.fixture
def team(owner_db: Database) -> dict[str, Member]:
    owner = make_member(owner_db, "OWNER")
    org = owner.org_id
    return {
        "owner": owner,
        "admin": make_member(owner_db, "ADMIN", org_id=org),
        "author": make_member(owner_db, "FACULTY", org_id=org),
        "other": make_member(owner_db, "FACULTY", org_id=org),
        "qc": make_member(owner_db, "FACULTY", org_id=org, grants=["QC"]),
        "approver": make_member(owner_db, "FACULTY", org_id=org, grants=["APPROVE"]),
        "publisher": make_member(owner_db, "FACULTY", org_id=org, grants=["PUBLISH"]),
        "editor": make_member(owner_db, "FACULTY", org_id=org, grants=["EDIT_OTHERS"]),
    }


@pytest.fixture
def catalogue(owner_db: Database, team: dict[str, Member]) -> Catalogue:
    return seed_catalogue(owner_db, team["owner"].org_id)


def as_(client: TestClient, team: dict[str, Member], who: str) -> dict[str, str]:
    return sign_in(client, team[who].email)


def ok(response: Any) -> dict[str, Any]:
    assert response.status_code in (200, 201), response.text
    return dict(response.json())


def para(words: str) -> list[dict[str, str]]:
    return [{"kind": "paragraph", "text": words}]


def content_of(
    catalogue: Catalogue,
    stem: str,
    *,
    options: list[str] | None = None,
    solution: str | None = None,
    **meta: Any,
) -> dict[str, Any]:
    content = ready_for(catalogue)
    content["stem"] = para(stem)
    if options is not None:
        for option, words in zip(content["options"], options, strict=True):
            option["content"] = para(words)
    if solution is not None:
        content["solution"] = para(solution)
    content["metadata"].update(meta)
    return content


def start(
    client: TestClient, team: dict[str, Member], content: dict[str, Any], who: str = "author"
) -> dict[str, Any]:
    return ok(client.post(QUESTIONS, json={"content": content}, headers=as_(client, team, who)))


def act(
    client: TestClient, team: dict[str, Member], who: str, question: dict[str, Any], step: str
) -> dict[str, Any]:
    tag = f'"rev-{question["revision"]}"' if step == "submit" else question["flow_etag"]
    headers = {**as_(client, team, who), "If-Match": tag}
    return ok(client.post(f"{QUESTIONS}/{question['id']}/{step}", headers=headers))


def publish_through(
    client: TestClient, team: dict[str, Member], question: dict[str, Any]
) -> dict[str, Any]:
    question = act(client, team, "author", question, "submit")
    for step, who in CHAIN:
        question = act(client, team, who, question, step)
    return question


def published(client: TestClient, team: dict[str, Member], content: dict[str, Any]) -> str:
    """Start a question and publish it, so every member reads it; returns its code."""
    return str(publish_through(client, team, start(client, team, content))["code"])


def search(
    client: TestClient, team: dict[str, Member], who: str, q: str, **params: Any
) -> dict[str, Any]:
    response = client.get(BANK, params={"q": q, **params}, headers=as_(client, team, who))
    assert response.status_code == 200, response.text
    return dict(response.json())


def codes(page: dict[str, Any]) -> list[str]:
    return [row["code"] for row in page["data"]]


# ---- what is searched --------------------------------------------------------------------------


def test_the_stem_each_option_and_the_solution_are_searched(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    in_stem = published(client, team, content_of(catalogue, "A pendulum swings."))
    in_option = published(
        client,
        team,
        content_of(catalogue, "Pick one.", options=["gravity", "spring", "tension", "drag"]),
    )
    in_solution = published(
        client,
        team,
        content_of(catalogue, "Pick another.", solution="Use conservation of momentum."),
    )

    assert codes(search(client, team, "other", "pendulum")) == [in_stem]
    assert codes(search(client, team, "other", "tension")) == [in_option]
    assert codes(search(client, team, "other", "momentum")) == [in_solution]
    assert search(client, team, "other", "unrelatedword")["data"] == []


def test_an_equation_is_found_by_its_latex(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    content = content_of(catalogue, "Find the energy.")
    content["stem"].append(
        {"kind": "equation", "format": "latex", "source": r"E = \frac{1}{2} m v^2"}
    )
    code = published(client, team, content)

    assert codes(search(client, team, "other", "frac")) == [code]
    assert codes(search(client, team, "other", "energy frac")) == [code]


def test_several_words_must_all_match_and_a_quoted_phrase_must_match_together(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    both = published(client, team, content_of(catalogue, "The net force on the block is zero."))
    apart = published(
        client, team, content_of(catalogue, "The force is large and the net is wide.")
    )

    assert sorted(codes(search(client, team, "other", "net force"))) == sorted([both, apart])
    assert codes(search(client, team, "other", '"net force"')) == [both]
    assert codes(search(client, team, "other", "force -zero")) == [apart]


def test_the_same_word_in_two_forms_of_unicode_is_the_same_word(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    decomposed = "Café problem"  # an e and a separate accent
    code = published(client, team, content_of(catalogue, decomposed))

    assert codes(search(client, team, "other", "café")) == [code]  # one composed letter
    # Typed decomposed too. Quoted, so that only an exact match (not a close word) can find it.
    assert codes(search(client, team, "other", '"café"')) == [code]


def test_words_in_hindi_are_searched(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    code = published(
        client, team, {**content_of(catalogue, "त्वरण का मात्रक क्या है?"), "language": "hi"}
    )
    published(client, team, content_of(catalogue, "The unit of acceleration."))

    assert codes(search(client, team, "other", "त्वरण")) == [code]
    assert codes(search(client, team, "other", "मात्रक", language="hi")) == [code]


# ---- typos --------------------------------------------------------------------------------------


def test_a_typo_still_finds_the_question(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    code = published(client, team, content_of(catalogue, "Find the acceleration of the cart."))
    published(client, team, content_of(catalogue, "A rope hangs from a ceiling."))

    assert codes(search(client, team, "other", "acceleratoin")) == [code]
    assert codes(search(client, team, "other", "acceleraton")) == [code]  # a letter missing
    assert codes(search(client, team, "other", "velocty")) == []  # a word that is not in the bank


def test_exact_words_come_before_close_words(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    exact = published(client, team, content_of(catalogue, "Find the acceleration."))
    close = published(client, team, content_of(catalogue, "The acceleratoin of a cart is steady."))

    # The close match is the more recent one, so recency alone would put it first.
    assert codes(search(client, team, "other", "acceleration")) == [exact, close]


def test_the_better_match_comes_first_not_the_most_recent(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    many = published(client, team, content_of(catalogue, "Heron heron heron: a heron and a heron."))
    once = published(client, team, content_of(catalogue, "A heron wades by the river bank today."))

    assert codes(search(client, team, "other", "heron")) == [many, once]


def test_every_word_of_a_long_search_must_still_match_when_typos_are_forgiven(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    # Only the first words get close alternatives; the others must still be there exactly.
    words = "acceleration block cart disc energy force gravity mass"
    without = published(client, team, content_of(catalogue, f"Words: {words}."))
    with_it = published(client, team, content_of(catalogue, f"Words: {words} zebra."))

    found = codes(search(client, team, "other", f"acceleratoin {words[13:]} zebra"))

    assert with_it in found
    assert without not in found


def test_an_unrelated_word_is_not_a_typo(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    published(client, team, content_of(catalogue, "A rope hangs from a ceiling."))

    assert search(client, team, "other", "acceleration")["data"] == []
    assert search(client, team, "other", "pendulum")["data"] == []


def test_a_quoted_phrase_or_a_left_out_word_gets_no_close_matches(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    published(client, team, content_of(catalogue, "The acceleration of a cart."))

    # Typed loosely, the typo is forgiven; asked for exactly, it is not.
    assert len(search(client, team, "other", "acceleratoin")["data"]) == 1
    assert search(client, team, "other", '"acceleratoin"')["data"] == []
    assert search(client, team, "other", "acceleratoin -ramp")["data"] == []


def test_close_words_are_added_only_when_few_questions_match_exactly(
    client: TestClient,
    team: dict[str, Member],
    catalogue: Catalogue,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    exact = [
        published(client, team, content_of(catalogue, f"Find the velocity {n}.")) for n in range(2)
    ]
    close = published(
        client, team, content_of(catalogue, "The velocty is shown.")
    )  # a letter missing

    monkeypatch.setattr(service, "FALLBACK_BELOW", 2)  # two exact matches are enough
    assert sorted(codes(search(client, team, "other", "velocity"))) == sorted(exact)

    monkeypatch.setattr(service, "FALLBACK_BELOW", 3)  # two are too few: close words follow
    assert codes(search(client, team, "other", "velocity"))[2:] == [close]


# ---- who may find what --------------------------------------------------------------------------


def test_a_private_draft_is_found_only_by_those_who_may_open_it(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    draft = start(client, team, content_of(catalogue, "The zebra crosses the road."))

    for who in ("author", "admin", "owner", "editor"):
        assert codes(search(client, team, who, "zebra")) == [draft["code"]], who
        assert codes(search(client, team, who, "zebraa")) == [draft["code"]], who  # typo too
    for who in ("other", "qc", "approver", "publisher"):
        assert search(client, team, who, "zebra")["data"] == [], who
        assert search(client, team, who, "zebraa")["data"] == [], who


def test_a_withdrawn_question_leaves_the_search_of_others(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    question = act(
        client,
        team,
        "author",
        start(client, team, content_of(catalogue, "A lemur sleeps.")),
        "submit",
    )
    assert len(search(client, team, "other", "lemur")["data"]) == 1

    act(client, team, "author", question, "withdraw")

    assert search(client, team, "other", "lemur")["data"] == []
    assert len(search(client, team, "author", "lemur")["data"]) == 1


def test_another_coaching_is_never_searched(
    client: TestClient, owner_db: Database, team: dict[str, Member], catalogue: Catalogue
) -> None:
    mine = published(client, team, content_of(catalogue, "A meteor falls."))
    stranger = make_member(owner_db, "OWNER")
    headers = sign_in(client, stranger.email)

    for words in ("meteor", "meteoor"):
        found = client.get(BANK, params={"q": words}, headers=headers).json()
        assert (found["data"], found["total"]) == ([], 0)
    assert codes(search(client, team, "other", "meteor")) == [mine]


def test_a_person_with_no_role_cannot_search(
    client: TestClient, owner_db: Database, team: dict[str, Member]
) -> None:
    headers = sign_in(client, platform_admin(owner_db))
    assert client.get(BANK, params={"q": "anything"}, headers=headers).status_code == 403


def test_the_archive_is_searched_only_when_asked_for(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    question = start(client, team, content_of(catalogue, "An otter swims."))
    ok(client.post(f"{QUESTIONS}/{question['id']}/archive", headers=as_(client, team, "author")))

    assert search(client, team, "author", "otter")["data"] == []
    assert codes(search(client, team, "author", "otter", archived=True)) == [question["code"]]


# ---- with filters, and what comes back ----------------------------------------------------------


def test_the_words_and_the_filters_must_both_match(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    easy = published(client, team, content_of(catalogue, "A heron wades.", difficulty=2))
    published(client, team, content_of(catalogue, "A heron flies.", difficulty=8))

    assert codes(search(client, team, "other", "heron", difficulty=2)) == [easy]
    assert len(search(client, team, "other", "heron")["data"]) == 2
    assert search(client, team, "other", "heron", difficulty=5)["data"] == []


def test_a_search_shows_the_beginning_of_the_text_and_says_when_more_matched(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    long_stem = "marmot " + "word " * 100
    published(client, team, content_of(catalogue, long_stem))
    for n in range(2):
        published(client, team, content_of(catalogue, f"A marmot digs {n}."))

    everything = search(client, team, "other", "marmot", limit=3)
    assert (everything["total"], everything["truncated"]) == (3, False)
    assert everything["page"] == {"next_cursor": None, "has_more": False}
    previews = [row["preview"] for row in everything["data"]]
    assert long_stem[:200] in previews and len(long_stem[:200]) == 200

    some = search(client, team, "other", "marmot", limit=2)
    assert (len(some["data"]), some["total"], some["truncated"]) == (2, 2, True)
    assert some["page"] == {"next_cursor": None, "has_more": False}


def test_the_plain_list_shows_the_preview_too(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    published(client, team, content_of(catalogue, "A stem to preview."))

    page = ok(client.get(BANK, headers=as_(client, team, "other")))

    assert [row["preview"] for row in page["data"]] == ["A stem to preview."]
    assert page["truncated"] is False


def test_a_search_cannot_be_paged_or_empty_or_long(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    headers = as_(client, team, "author")
    for params in (
        {"q": "word", "cursor": "abc"},
        {"q": ""},
        {"q": "   "},
        {"q": "x" * 201},
    ):
        response = client.get(BANK, params=params, headers=headers)
        assert response.status_code == 400, params
        assert response.json()["error"]["code"] in ("MALFORMED_REQUEST", "VALIDATION_FAILED"), (
            params
        )


@pytest.mark.parametrize(
    "words",
    [
        "'; DROP TABLE bank_index; --",
        "a & b | !c (d) :* <-> e",
        '"unbalanced quote',
        "\\",
        "%_%",
        "!!!",
        "- - -",
        "a\x00b",
        "x" * 200,
        "💥🔥",
        "or or or",
    ],
)
def test_what_is_typed_never_becomes_query_syntax(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue, words: str
) -> None:
    code = published(client, team, content_of(catalogue, "A safe question about drop and table."))

    response = client.get(BANK, params={"q": words}, headers=as_(client, team, "other"))

    assert response.status_code == 200, response.text
    assert len(response.json()["data"]) <= 1
    assert codes(search(client, team, "other", "safe")) == [code]  # the table is still there


# ---- limits -----------------------------------------------------------------------------------


def test_searches_are_limited_per_person_but_the_list_is_not(
    migrated_database: MigratedDatabase, team: dict[str, Member]
) -> None:
    app = create_app(
        make_settings(migrated_database, searches_per_user=2, search_window_seconds=60)
    )
    with TestClient(app) as limited:
        headers = as_(limited, team, "author")
        assert limited.get(BANK, params={"q": "one"}, headers=headers).status_code == 200
        assert limited.get(BANK, params={"q": "two"}, headers=headers).status_code == 200
        refused = limited.get(BANK, params={"q": "three"}, headers=headers)

        assert refused.status_code == 429
        assert refused.json()["error"]["code"] == "RATE_LIMITED"
        assert int(refused.headers["Retry-After"]) >= 1
        assert (
            limited.get(BANK, headers=headers).status_code == 200
        )  # the plain list is not a search
        other = as_(limited, team, "other")  # somebody else has their own allowance
        assert limited.get(BANK, params={"q": "one"}, headers=other).status_code == 200


def test_a_search_that_runs_too_long_is_stopped_and_answered_plainly(
    migrated_database: MigratedDatabase,
    team: dict[str, Member],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def slow(session: Any, where: Any, words: str, count: int) -> list[Any]:
        session.execute(text("SELECT pg_sleep(5)"))  # the database must stop this, not us
        return []

    monkeypatch.setattr(service, "_exact_matches", slow)
    app = create_app(make_settings(migrated_database, search_timeout_ms=200))
    with TestClient(app) as limited:
        response = limited.get(BANK, params={"q": "slow"}, headers=as_(limited, team, "author"))
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "SEARCH_TIMED_OUT"
        # The connection is clean afterwards: the next request works.
        assert limited.get(BANK, headers=as_(limited, team, "author")).status_code == 200


# ---- the index --------------------------------------------------------------------------------


def test_editing_a_draft_changes_what_finds_it_at_once(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    question = start(client, team, content_of(catalogue, "A gecko climbs."))
    assert len(search(client, team, "author", "gecko")["data"]) == 1

    content = {**question["content"], "stem": para("A newt swims.")}
    headers = {**as_(client, team, "author"), "If-Match": f'"rev-{question["revision"]}"'}
    ok(
        client.put(
            f"{QUESTIONS}/{question['id']}/working-revision",
            json={"content": content},
            headers=headers,
        )
    )

    assert search(client, team, "author", "gecko")["data"] == []
    assert codes(search(client, team, "author", "newt")) == [question["code"]]


def test_the_reindex_fills_the_text_of_rows_that_have_none(
    client: TestClient,
    owner_db: Database,
    migrated_database: MigratedDatabase,
    monkeypatch: pytest.MonkeyPatch,
    team: dict[str, Member],
    catalogue: Catalogue,
) -> None:
    org: UUID = team["owner"].org_id
    code = published(client, team, content_of(catalogue, "A badger digs."))
    with owner_db.transaction(TenantContext(organization_id=org)) as session:
        session.execute(  # the state of a row made before the text columns existed
            text("UPDATE bank_index SET stem_text = '', preview = '' WHERE organization_id = :org"),
            {"org": org},
        )
    assert search(client, team, "other", "badger")["data"] == []  # the word index follows the text

    monkeypatch.setenv("MIGRATION_DATABASE_URL", migrated_database.owner_url)
    assert cli.main(["reindex-bank", "--organization", str(org)]) == 0

    found = search(client, team, "other", "badger")
    assert codes(found) == [code] and found["data"][0]["preview"] == "A badger digs."


def test_the_words_of_the_bank_are_kept_per_coaching_by_the_database(
    client: TestClient, owner_db: Database, team: dict[str, Member], catalogue: Catalogue
) -> None:
    # Typos are matched against the coaching's own list of words, which a trigger keeps.
    start(client, team, content_of(catalogue, "A quokka smiles."))
    stranger = make_member(owner_db, "OWNER")
    stranger_catalogue = seed_catalogue(owner_db, stranger.org_id)
    headers = sign_in(client, stranger.email)
    ok(
        client.post(
            QUESTIONS,
            json={"content": content_of(stranger_catalogue, "A wombat digs.")},
            headers=headers,
        )
    )

    def words_of(org: UUID) -> set[str]:
        with owner_db.transaction(TenantContext(organization_id=org)) as session:
            return set(
                session.scalars(
                    text("SELECT word FROM bank_words WHERE organization_id = :org"), {"org": org}
                )
            )

    mine, theirs = words_of(team["owner"].org_id), words_of(stranger.org_id)
    assert "quokka" in mine and "quokka" not in theirs
    assert "wombat" in theirs and "wombat" not in mine
    assert all(3 <= len(word) <= 40 for word in mine | theirs)
