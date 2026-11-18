"""M4 PR 4e: the bank index, and the bank list, filters, total and code lookup on top of it
(F-01, F-02; tests T37 and T38 part 1).

``bank_index`` is derived data: one row per question, written by the questions module in the same
transaction as every change, and rebuilt from the revisions by ``qbank reindex-bank``. What a person
may see is decided in the query, so a private draft is never listed, counted or found by its code.
"""

import copy
import itertools
import threading
import time
from collections.abc import Iterator
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from qbank import cli
from qbank.core.config import AppEnv, Settings
from qbank.core.db import Database
from qbank.core.ids import new_id
from qbank.core.tenancy import TenantContext
from qbank.main import create_app
from qbank.modules.questions.public import reindex_bank
from qbank.modules.search import api as bank_api
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
NOTE = "The answer key disagrees with the worked solution."
RETURN = {"reasons": ["ANSWER_WRONG"], "note": NOTE}
CHAIN = [("pass-qc", "qc"), ("approve", "approver"), ("publish", "publisher")]


@pytest.fixture
def settings(migrated_database: MigratedDatabase) -> Settings:
    # These tests sign in as many people many times; the sign-in limits are not what they test.
    return Settings(
        app_env=AppEnv.TEST,
        database_url=migrated_database.app_url,
        session_cookie_secure=False,
        login_attempts_per_ip=10_000,
        login_attempts_per_email=10_000,
    )


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings)) as test_client:
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


def start(
    client: TestClient, team: dict[str, Member], content: dict[str, Any], who: str = "author"
) -> dict[str, Any]:
    return ok(client.post(QUESTIONS, json={"content": content}, headers=as_(client, team, who)))


def act(
    client: TestClient,
    team: dict[str, Member],
    who: str,
    question: dict[str, Any],
    step: str,
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    tag = f'"rev-{question["revision"]}"' if step == "submit" else question["flow_etag"]
    headers = {**as_(client, team, who), "If-Match": tag}
    return ok(client.post(f"{QUESTIONS}/{question['id']}/{step}", json=body, headers=headers))


def edit(
    client: TestClient,
    team: dict[str, Member],
    question: dict[str, Any],
    who: str = "author",
    **changes: Any,
) -> dict[str, Any]:
    """Save the working copy with ``changes`` replacing top-level fields of the content."""
    content = {**question["content"], **changes}
    headers = {**as_(client, team, who), "If-Match": f'"rev-{question["revision"]}"'}
    return ok(
        client.put(
            f"{QUESTIONS}/{question['id']}/working-revision",
            json={"content": content},
            headers=headers,
        )
    )


def publish_through(
    client: TestClient, team: dict[str, Member], question: dict[str, Any]
) -> dict[str, Any]:
    question = act(client, team, "author", question, "submit")
    for step, who in CHAIN:
        question = act(client, team, who, question, step)
    return question


def bank(client: TestClient, team: dict[str, Member], who: str, **params: Any) -> dict[str, Any]:
    response = client.get(BANK, params=params, headers=as_(client, team, who))
    assert response.status_code == 200, response.text
    return dict(response.json())


def codes(page: dict[str, Any]) -> list[str]:
    return [row["code"] for row in page["data"]]


def row_of(page: dict[str, Any], question: dict[str, Any]) -> dict[str, Any]:
    return next(row for row in page["data"] if row["question_id"] == question["id"])


def with_meta(catalogue: Catalogue, kind: str = "SCQ", **meta: Any) -> dict[str, Any]:
    content = ready_for(catalogue, kind)
    content["metadata"].update(meta)
    return content


_NUMBERS = itertools.count(1)


def distinct(catalogue: Catalogue) -> dict[str, Any]:
    """The ready fixture with a stem of its own: two identical questions would correctly wait at
    Pass QC as exact duplicates (D-16), which is not what these tests are about."""
    content = ready_for(catalogue)
    content["stem"] = [{"kind": "paragraph", "text": f"What is 2 + {next(_NUMBERS)}?"}]
    return content


def snapshot(owner_db: Database, org_id: UUID) -> list[dict[str, Any]]:
    """Every row of the bank index of a coaching, exactly as stored, in code order."""
    with owner_db.transaction(TenantContext(organization_id=org_id)) as session:
        rows = (
            session.execute(
                text("SELECT * FROM bank_index WHERE organization_id = :org ORDER BY code"),
                {"org": org_id},
            )
            .mappings()
            .all()
        )
    return [dict(row) for row in rows]


# ---- what the index holds ---------------------------------------------------------------------


def test_a_new_question_is_in_the_bank_with_its_labels(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    content = with_meta(catalogue, difficulty=7, bloom_level="APPLY")
    question = start(client, team, content)

    page = bank(client, team, "author")

    assert page["total"] == 1
    assert page["page"] == {"next_cursor": None, "has_more": False}
    row = row_of(page, question)
    assert row == {
        "question_id": question["id"],
        "code": question["code"],
        "author_id": str(team["author"].user_id),
        "state": "DRAFT",
        "version_number": 1,
        "archived": False,
        "has_published": False,
        "has_open_correction": False,
        "question_type": "SCQ",
        "language": content["language"],
        "class_id": str(catalogue.class_id),
        "subject_id": str(catalogue.subject_id),
        "chapter_id": str(catalogue.chapter_id),
        "topic_id": str(catalogue.topic_id),
        "primary_concept_id": str(catalogue.concept_id),
        "concept_ids": [str(catalogue.concept_id)],
        "difficulty": 7,
        "bloom_level": "APPLY",
        "is_pyq": False,
        "exam_id": None,
        "exam_year": None,
        "has_solution": row["has_solution"],
        "has_video": False,
        "preview": "What is 2 + 3?",
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }
    assert row["has_solution"] is False  # the spec-v1 "ready" fixture has no worked solution


def test_saving_a_draft_changes_its_row_at_once(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    question = start(client, team, with_meta(catalogue, difficulty=3))
    before = row_of(bank(client, team, "author"), question)

    changed = copy.deepcopy(question["content"])
    changed["metadata"]["difficulty"] = 9
    changed["language"] = "hi"
    edit(client, team, question, **{"metadata": changed["metadata"], "language": "hi"})

    after = row_of(bank(client, team, "author"), question)
    assert (after["difficulty"], after["language"]) == (9, "hi")
    assert after["updated_at"] > before["updated_at"]


def test_labels_that_are_not_valid_are_left_out_not_trusted(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    """A draft may hold anything; the index keeps only what it can read."""
    junk = with_meta(
        catalogue,
        difficulty=99,
        bloom_level="WIZARD",
        exam_year="soon",
        subject_id="not-an-id",
        secondary_concept_ids=["nope", str(catalogue.concept_id), 5],
    )
    junk["language"] = "not a language"
    question = start(client, team, junk)

    row = row_of(bank(client, team, "author"), question)

    assert (row["difficulty"], row["bloom_level"], row["exam_year"], row["language"]) == (
        None,
        None,
        None,
        None,
    )
    assert row["subject_id"] is None
    assert row["concept_ids"] == [str(catalogue.concept_id)]


# ---- every step keeps the row right -----------------------------------------------------------


def test_the_row_follows_each_step_of_the_workflow(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    question = start(client, team, ready_for(catalogue))
    seen = []
    question = act(client, team, "author", question, "submit")
    seen.append(row_of(bank(client, team, "other"), question)["state"])
    for step, who in CHAIN:
        question = act(client, team, who, question, step)
        seen.append(row_of(bank(client, team, "other"), question)["state"])

    assert seen == ["IN_REVIEW", "QC_PASSED", "APPROVED", "PUBLISHED"]
    published = row_of(bank(client, team, "other"), question)
    assert published["has_published"] is True
    assert published["has_open_correction"] is False


def test_a_correction_shows_the_published_labels_until_it_is_published(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    published = publish_through(
        client, team, start(client, team, with_meta(catalogue, difficulty=4))
    )
    correction = act(client, team, "author", published, "start-correction")
    changed = copy.deepcopy(correction["content"])
    changed["metadata"]["difficulty"] = 9
    edit(client, team, correction, metadata=changed["metadata"])

    # Everyone reads version 1: the bank shows its labels, not the correction's.
    for who in ("other", "qc", "author", "admin"):
        row = row_of(bank(client, team, who), published)
        assert (row["version_number"], row["state"], row["difficulty"]) == (1, "PUBLISHED", 4), who
        assert (row["has_published"], row["has_open_correction"]) == (True, True), who

    # Once the correction is published, the row follows it.
    saved = ok(client.get(f"{QUESTIONS}/{published['id']}", headers=as_(client, team, "author")))
    corrected = act(client, team, "author", saved, "submit")
    for step, who in CHAIN:
        corrected = act(client, team, who, corrected, step)
    row = row_of(bank(client, team, "other"), published)
    assert (row["version_number"], row["difficulty"], row["has_open_correction"]) == (2, 9, False)


def test_withdrawing_or_returning_makes_a_question_private_again(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    question = act(client, team, "author", start(client, team, ready_for(catalogue)), "submit")
    assert question["code"] in codes(bank(client, team, "other"))

    withdrawn = act(client, team, "author", question, "withdraw")
    assert withdrawn["code"] not in codes(bank(client, team, "other"))
    assert withdrawn["code"] in codes(bank(client, team, "author"))

    again = act(client, team, "author", withdrawn, "submit")
    returned = act(client, team, "qc", again, "return", RETURN)
    assert returned["code"] not in codes(bank(client, team, "other"))
    assert returned["code"] not in codes(bank(client, team, "qc"))
    assert returned["code"] in codes(bank(client, team, "author"))


def test_archive_and_restore_move_a_question_out_of_and_back_into_the_bank(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    question = start(client, team, ready_for(catalogue))
    assert ok(
        client.post(f"{QUESTIONS}/{question['id']}/archive", headers=as_(client, team, "author"))
    )
    assert bank(client, team, "author")["total"] == 0
    archive = bank(client, team, "author", archived=True)
    assert codes(archive) == [question["code"]] and archive["total"] == 1
    assert row_of(archive, question)["archived"] is True
    # A person pasting a code still finds it.
    found = client.get(f"{BANK}/by-code/{question['code']}", headers=as_(client, team, "author"))
    assert found.status_code == 200 and found.json()["archived"] is True

    assert ok(
        client.post(f"{QUESTIONS}/{question['id']}/restore", headers=as_(client, team, "author"))
    )
    assert codes(bank(client, team, "author")) == [question["code"]]
    assert bank(client, team, "author", archived=True)["total"] == 0


# ---- who may see what -------------------------------------------------------------------------


def test_a_draft_is_listed_counted_and_found_only_for_those_who_may_open_it(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    draft = start(client, team, ready_for(catalogue))

    for who in ("author", "editor", "admin", "owner"):
        assert bank(client, team, who)["total"] == 1, who
        found = client.get(f"{BANK}/by-code/{draft['code']}", headers=as_(client, team, who))
        assert found.status_code == 200, who
    for who in ("other", "qc", "approver", "publisher"):
        page = bank(client, team, who)
        assert (page["total"], page["data"]) == (0, []), who  # not even in the count
        found = client.get(f"{BANK}/by-code/{draft['code']}", headers=as_(client, team, who))
        assert found.status_code == 404, who


def test_the_bank_agrees_with_what_each_person_may_open(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    """The bank applies the questions module's rule over its own columns. For a question in each
    state and each kind of person, the bank lists it exactly when opening it answers 200."""
    drafts = start(client, team, distinct(catalogue))
    in_review = act(client, team, "author", start(client, team, distinct(catalogue)), "submit")
    returned = act(
        client,
        team,
        "qc",
        act(client, team, "author", start(client, team, distinct(catalogue)), "submit"),
        "return",
        RETURN,
    )
    passed = act(
        client,
        team,
        "qc",
        act(client, team, "author", start(client, team, distinct(catalogue)), "submit"),
        "pass-qc",
    )
    published = publish_through(client, team, start(client, team, distinct(catalogue)))
    questions = [drafts, in_review, returned, passed, published]

    for who in ("author", "other", "editor", "admin", "owner", "qc", "approver", "publisher"):
        headers = as_(client, team, who)
        listed = {row["question_id"] for row in bank(client, team, who)["data"]}
        can_open = {
            q["id"]
            for q in questions
            if client.get(f"{QUESTIONS}/{q['id']}", headers=headers).status_code == 200
        }
        assert listed == can_open, who


def test_a_person_with_no_role_cannot_use_the_bank(
    client: TestClient, owner_db: Database, team: dict[str, Member]
) -> None:
    headers = sign_in(client, platform_admin(owner_db))  # not acting in any coaching
    assert client.get(BANK, headers=headers).status_code == 403
    assert client.get(f"{BANK}/by-code/7K2M9PQX", headers=headers).status_code == 403


def test_another_coaching_sees_nothing_and_a_code_from_elsewhere_is_not_found(
    client: TestClient, owner_db: Database, team: dict[str, Member], catalogue: Catalogue
) -> None:
    question = publish_through(client, team, start(client, team, ready_for(catalogue)))
    stranger = make_member(owner_db, "OWNER")
    headers = sign_in(client, stranger.email)

    page = client.get(BANK, headers=headers).json()
    assert (page["total"], page["data"]) == (0, [])
    assert client.get(f"{BANK}/by-code/{question['code']}", headers=headers).status_code == 404
    mine = bank(client, team, "other")
    assert codes(mine) == [question["code"]]


# ---- filters, total, order and pages ----------------------------------------------------------


def labelled_bank(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue, owner_db: Database
) -> dict[str, dict[str, Any]]:
    """Questions of the author with different labels, to filter."""
    other_concept = seed_second_concept(owner_db, team["owner"].org_id, catalogue)
    exam = new_id()
    return {
        "easy_en": start(client, team, with_meta(catalogue, difficulty=2, bloom_level="REMEMBER")),
        "hard_hi": start(
            client,
            team,
            {**with_meta(catalogue, difficulty=9, bloom_level="APPLY"), "language": "hi"},
        ),
        "with_video": start(
            client,
            team,
            {
                **with_meta(catalogue, difficulty=4),
                "solution": [{"kind": "paragraph", "text": "Use the formula for speed."}],
                "video_solution_url": "https://example.com/video",
            },
        ),
        "pyq": start(
            client,
            team,
            with_meta(catalogue, difficulty=5, is_pyq=True, exam_year=2023, exam_id=str(exam)),
        ),
        "two_concepts": start(
            client,
            team,
            with_meta(catalogue, difficulty=5, secondary_concept_ids=[str(other_concept)]),
        ),
    }


def seed_second_concept(owner_db: Database, org_id: UUID, catalogue: Catalogue) -> UUID:
    from qbank.modules.taxonomy.models import Concept

    concept_id = new_id()
    with owner_db.transaction(TenantContext(organization_id=org_id)) as session:
        session.add(
            Concept(
                id=concept_id,
                organization_id=org_id,
                subject_id=catalogue.subject_id,
                name="Speed",
                name_key="speed",
            )
        )
    return concept_id


def test_each_filter_narrows_and_the_total_counts_every_match(
    client: TestClient, owner_db: Database, team: dict[str, Member], catalogue: Catalogue
) -> None:
    made = labelled_bank(client, team, catalogue, owner_db)
    ids = {name: q["id"] for name, q in made.items()}

    def found(**params: Any) -> set[str]:
        page = bank(client, team, "author", **params)
        assert page["total"] == len(page["data"])
        return {row["question_id"] for row in page["data"]}

    assert found() == set(ids.values())
    assert found(language="hi") == {ids["hard_hi"]}
    assert found(language="HI") == {ids["hard_hi"]}  # a code typed in any case
    assert found(difficulty=9) == {ids["hard_hi"]}
    assert found(bloom_level="REMEMBER") == {ids["easy_en"]}
    assert found(is_pyq="true") == {ids["pyq"]}
    assert found(is_pyq="false") == set(ids.values()) - {ids["pyq"]}
    assert found(exam_year=2023) == {ids["pyq"]}
    assert found(question_type="SCQ") == set(ids.values())
    assert found(question_type="INTEGER") == set()
    assert found(state="DRAFT") == set(ids.values())
    assert found(state="PUBLISHED") == set()
    assert found(subject_id=str(catalogue.subject_id)) == set(ids.values())
    assert found(subject_id=str(new_id())) == set()
    assert found(author_id=str(team["author"].user_id)) == set(ids.values())
    assert found(author_id=str(team["other"].user_id)) == set()
    assert found(has_video="true") == {ids["with_video"]}
    assert found(has_solution="true") == {ids["with_video"]}
    assert found(has_solution="false") == set(ids.values()) - {ids["with_video"]}


def test_several_values_of_one_filter_match_any_and_different_filters_must_all_match(
    client: TestClient, owner_db: Database, team: dict[str, Member], catalogue: Catalogue
) -> None:
    made = labelled_bank(client, team, catalogue, owner_db)
    ids = {name: q["id"] for name, q in made.items()}

    def found(**params: Any) -> set[str]:
        return {row["question_id"] for row in bank(client, team, "author", **params)["data"]}

    assert found(difficulty=[2, 9]) == {ids["easy_en"], ids["hard_hi"]}
    assert found(difficulty=[2, 9], language="hi") == {ids["hard_hi"]}
    assert found(difficulty=[2, 9], language="hi", bloom_level="REMEMBER") == set()


def test_a_concept_filter_matches_the_main_concept_or_any_other(
    client: TestClient, owner_db: Database, team: dict[str, Member], catalogue: Catalogue
) -> None:
    made = labelled_bank(client, team, catalogue, owner_db)
    second = made["two_concepts"]["content"]["metadata"]["secondary_concept_ids"][0]

    main = bank(client, team, "author", concept_id=str(catalogue.concept_id))
    assert main["total"] == 5  # every question has the main concept
    only = bank(client, team, "author", concept_id=second)
    assert [row["question_id"] for row in only["data"]] == [made["two_concepts"]["id"]]


def test_the_list_is_newest_change_first_and_pages_do_not_repeat_or_skip(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    made = [start(client, team, ready_for(catalogue)) for _ in range(5)]
    edit(client, team, made[0], language="hi")  # the oldest question changes last

    everything = bank(client, team, "author")
    assert codes(everything)[0] == made[0]["code"]
    assert everything["total"] == 5

    collected: list[str] = []
    cursor: str | None = None
    while True:
        params = {"limit": 2, **({"cursor": cursor} if cursor else {})}
        page = bank(client, team, "author", **params)
        assert page["total"] == 5  # the total is not the page size
        collected += codes(page)
        if not page["page"]["has_more"]:
            break
        cursor = page["page"]["next_cursor"]
    assert collected == codes(everything)
    assert len(set(collected)) == 5


@pytest.mark.parametrize(
    "params",
    [
        {"subject_id": "not-an-id"},
        {"difficulty": 11},
        {"difficulty": 0},
        {"bloom_level": "wizard!"},
        {"language": "not a language"},
        {"limit": 0},
        {"limit": 101},
        {"cursor": "garbage"},
        {"is_pyq": "maybe"},
        {"exam_year": 1800},
    ],
)
def test_a_malformed_filter_is_a_400_not_a_500(
    client: TestClient, team: dict[str, Member], params: dict[str, Any]
) -> None:
    response = client.get(BANK, params=params, headers=as_(client, team, "author"))
    assert response.status_code == 400, response.text


def test_text_in_a_filter_is_checked_for_shape_and_is_never_query_syntax(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    start(client, team, ready_for(catalogue))
    headers = as_(client, team, "author")
    for hostile in ("DRAFT' OR '1'='1", "DRAFT; DROP TABLE bank_index;--", "%"):
        for name in ("state", "bloom_level", "question_type", "language"):
            response = client.get(BANK, params={name: hostile}, headers=headers)
            assert response.status_code == 400, (name, hostile)
    # A well-formed value that matches nothing is just an empty answer; a LIKE wildcard is a letter.
    assert bank(client, team, "author", state="NO_SUCH_STATE")["total"] == 0
    assert bank(client, team, "author", state="DRAFT_")["total"] == 0
    assert bank(client, team, "author", state="_")["total"] == 0  # not a wildcard
    assert bank(client, team, "author")["total"] == 1  # nothing was dropped or loosened


def test_filters_and_the_total_agree_with_a_plain_count_of_the_questions(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    """T38: for every combination of a few filters, the bank answers what counting the saved
    questions by hand answers, in both the rows and the total."""
    made = []
    for n in range(16):
        kind = ("SCQ", "INTEGER")[n % 2]
        content = with_meta(
            catalogue,
            kind,
            difficulty=1 + n % 4,
            bloom_level=("REMEMBER", "APPLY", "ANALYZE")[n % 3],
            is_pyq=n % 5 == 0,
        )
        content["language"] = ("en", "hi", "gu")[n % 3 if n % 4 else 0]
        made.append(start(client, team, content))

    def expected(**wanted: Any) -> set[str]:
        keep = set()
        for q in made:
            c, meta = q["content"], q["content"]["metadata"]
            fields = {
                "language": c["language"],
                "question_type": c["question_type"],
                "difficulty": meta["difficulty"],
                "bloom_level": meta["bloom_level"],
                "is_pyq": meta["is_pyq"],
            }
            if all(fields[name] in values for name, values in wanted.items()):
                keep.add(q["id"])
        return keep

    choices: dict[str, list[list[Any]]] = {
        "language": [[], ["en"], ["hi", "gu"]],
        "question_type": [[], ["INTEGER"]],
        "difficulty": [[], [2], [1, 4]],
        "bloom_level": [[], ["APPLY"], ["REMEMBER", "ANALYZE"]],
        "is_pyq": [[], [True], [False]],
    }
    names = list(choices)
    combinations = 0
    for picks in itertools.product(*choices.values()):
        wanted = {name: values for name, values in zip(names, picks, strict=True) if values}
        params = {name: values for name, values in wanted.items()}
        page = bank(client, team, "author", limit=100, **params)
        got = {row["question_id"] for row in page["data"]}
        assert got == expected(**wanted), wanted
        assert page["total"] == len(got), wanted
        combinations += 1
    assert combinations == 3 * 2 * 3 * 3 * 3


def test_a_member_who_was_removed_can_no_longer_read_the_bank(
    client: TestClient, owner_db: Database, team: dict[str, Member], catalogue: Catalogue
) -> None:
    question = publish_through(client, team, start(client, team, ready_for(catalogue)))
    headers = as_(client, team, "other")
    assert client.get(BANK, headers=headers).json()["total"] == 1

    with owner_db.transaction(TenantContext(organization_id=team["other"].org_id)) as session:
        session.execute(
            text("DELETE FROM memberships WHERE id = :id"), {"id": team["other"].membership_id}
        )

    # Signed out or refused, depending on how the session ends: never an answer.
    for path in (BANK, f"{BANK}/by-code/{question['code']}"):
        assert client.get(path, headers=headers).status_code in (401, 403), path


# ---- by code ----------------------------------------------------------------------------------


def test_a_code_is_found_however_it_was_typed(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    question = start(client, team, ready_for(catalogue))
    headers = as_(client, team, "author")
    code = question["code"]
    typed = f"{code[:4].lower()}-{code[4:].lower()}"

    response = client.get(f"{BANK}/by-code/{typed}", headers=headers)

    assert response.status_code == 200, response.text
    assert response.json()["question_id"] == question["id"]
    assert client.get(f"{BANK}/by-code/short", headers=headers).status_code == 422
    assert client.get(f"{BANK}/by-code/{'0' * 8}", headers=headers).status_code == 404


# ---- derived data: the incremental rows equal a rebuild --------------------------------------


@pytest.fixture
def worked_bank(
    client: TestClient, owner_db: Database, team: dict[str, Member], catalogue: Catalogue
) -> list[dict[str, Any]]:
    """Questions taken through every kind of change, so each write path has touched a row."""
    saved = start(client, team, with_meta(catalogue, difficulty=3))
    edit(client, team, saved, language="hi")
    checkpointed = start(client, team, distinct(catalogue))
    ok(
        client.post(
            f"{QUESTIONS}/{checkpointed['id']}/checkpoints",
            headers={
                **as_(client, team, "author"),
                "If-Match": f'"rev-{checkpointed["revision"]}"',
            },
        )
    )
    in_review = act(client, team, "author", start(client, team, distinct(catalogue)), "submit")
    returned = act(
        client,
        team,
        "qc",
        act(client, team, "author", start(client, team, distinct(catalogue)), "submit"),
        "return",
        RETURN,
    )
    withdrawn = act(
        client,
        team,
        "author",
        act(client, team, "author", start(client, team, distinct(catalogue)), "submit"),
        "withdraw",
    )
    published = publish_through(client, team, start(client, team, distinct(catalogue)))
    corrected = act(
        client,
        team,
        "author",
        publish_through(client, team, start(client, team, distinct(catalogue))),
        "start-correction",
    )
    archived = start(client, team, distinct(catalogue))
    ok(client.post(f"{QUESTIONS}/{archived['id']}/archive", headers=as_(client, team, "author")))
    restored = start(client, team, distinct(catalogue))
    for path in ("archive", "restore"):
        ok(client.post(f"{QUESTIONS}/{restored['id']}/{path}", headers=as_(client, team, "author")))
    return [
        saved,
        checkpointed,
        in_review,
        returned,
        withdrawn,
        published,
        corrected,
        archived,
        restored,
    ]


def test_every_kind_of_change_leaves_the_row_a_rebuild_would_write(
    owner_db: Database,
    monkeypatch: pytest.MonkeyPatch,
    migrated_database: MigratedDatabase,
    team: dict[str, Member],
    worked_bank: list[dict[str, Any]],
) -> None:
    org = team["owner"].org_id
    written = snapshot(owner_db, org)
    assert len(written) == len(worked_bank)

    monkeypatch.setenv("MIGRATION_DATABASE_URL", migrated_database.owner_url)
    assert cli.main(["reindex-bank", "--organization", str(org)]) == 0

    assert snapshot(owner_db, org) == written


def test_the_reindex_repairs_rows_that_are_missing_or_wrong(
    owner_db: Database,
    monkeypatch: pytest.MonkeyPatch,
    migrated_database: MigratedDatabase,
    team: dict[str, Member],
    worked_bank: list[dict[str, Any]],
    capsys: pytest.CaptureFixture[str],
) -> None:
    org = team["owner"].org_id
    written = snapshot(owner_db, org)
    with owner_db.transaction(TenantContext(organization_id=org)) as session:
        session.execute(
            text(
                "UPDATE bank_index SET state = 'WRONG', difficulty = 10, is_private = false"
                " WHERE organization_id = :org"
            ),
            {"org": org},
        )
        session.execute(
            text("DELETE FROM bank_index WHERE organization_id = :org AND code = :code"),
            {"org": org, "code": written[0]["code"]},
        )
    assert snapshot(owner_db, org) != written

    monkeypatch.setenv("MIGRATION_DATABASE_URL", migrated_database.owner_url)
    assert cli.main(["reindex-bank"]) == 0  # every coaching, so also the others in this database

    assert snapshot(owner_db, org) == written
    assert f"Coaching {org}: {len(worked_bank)} questions indexed" in capsys.readouterr().out


def test_the_reindex_command_needs_the_owner_connection_and_a_real_id(
    monkeypatch: pytest.MonkeyPatch, migrated_database: MigratedDatabase
) -> None:
    monkeypatch.delenv("MIGRATION_DATABASE_URL", raising=False)
    assert cli.main(["reindex-bank"]) == 2
    monkeypatch.setenv("MIGRATION_DATABASE_URL", migrated_database.owner_url)
    assert cli.main(["reindex-bank", "--organization", "not-an-id"]) == 2


def test_a_change_that_is_rolled_back_leaves_no_row_behind(
    client: TestClient, owner_db: Database, team: dict[str, Member], catalogue: Catalogue
) -> None:
    """The row is written in the same transaction as the change: a refused change leaves the
    index as it was."""
    question = start(client, team, with_meta(catalogue, difficulty=3))
    stale = client.put(
        f"{QUESTIONS}/{question['id']}/working-revision",
        json={"content": {**question["content"], "language": "hi"}},
        headers={**as_(client, team, "author"), "If-Match": '"rev-999"'},
    )
    assert stale.status_code == 412
    row = row_of(bank(client, team, "author"), question)
    assert row["language"] == question["content"]["language"]


# ---- races -------------------------------------------------------------------------------------


def test_the_rebuild_waits_for_a_change_in_progress_instead_of_overwriting_it(
    client: TestClient, owner_db: Database, team: dict[str, Member], catalogue: Catalogue
) -> None:
    """Every writer locks the question first. A rebuild that read a question without that lock
    could write back a row worked out before a change that commits meanwhile (a withdrawal making
    the question private), and the bank would list it to people who may not read it."""
    question = act(client, team, "author", start(client, team, ready_for(catalogue)), "submit")
    org = team["owner"].org_id
    finished = threading.Event()
    failures: list[BaseException] = []

    def rebuild() -> None:
        try:
            with owner_db.transaction(TenantContext(organization_id=org)) as session:
                reindex_bank(session, org)
        except BaseException as error:  # reported on the main thread
            failures.append(error)
        finally:
            finished.set()

    with owner_db.transaction(TenantContext(organization_id=org)) as writer:
        writer.execute(
            text("SELECT id FROM question_masters WHERE id = :id FOR UPDATE"),
            {"id": question["id"]},
        )
        threading.Thread(target=rebuild, daemon=True).start()
        time.sleep(1.5)
        assert not finished.is_set(), "the rebuild did not wait for the question's lock"
    assert finished.wait(30)
    assert failures == []


def test_the_list_and_its_total_are_read_from_one_snapshot(
    client: TestClient,
    team: dict[str, Member],
    catalogue: Catalogue,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Otherwise a change committed between the count and the page could give a page with
    ``total`` 0, which the exact-total contract forbids."""
    start(client, team, ready_for(catalogue))
    seen: list[str] = []
    real = bank_api.service.list_bank

    def spy(session: Any, *args: Any, **kwargs: Any) -> Any:
        seen.append(str(session.scalar(text("SHOW transaction_isolation"))))
        return real(session, *args, **kwargs)

    monkeypatch.setattr(bank_api.service, "list_bank", spy)
    bank(client, team, "author")
    assert seen == ["repeatable read"]
