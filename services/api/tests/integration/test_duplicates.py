"""M4 PR 4g-1: possible duplicates of a question (D-16; test T39 part 1, T37 for duplicates).

Exact (same content, case and spacing of the prose aside), near (very similar text), never a
changed equation or answer as exact, never another coaching's, an archived one or a private draft
the reader may not open.
"""

import copy
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from qbank.core.db import Database
from qbank.core.tenancy import TenantContext
from qbank.main import create_app
from qbank.modules.search import duplicates as search_duplicates
from qbank.modules.search.public import NEAR_SIMILARITY
from tests.integration.conftest import (
    Member,
    MigratedDatabase,
    make_member,
    platform_admin,
    sign_in,
)
from tests.integration.question_support import Catalogue, seed_catalogue
from tests.integration.test_bank_search import (
    CHAIN,
    QUESTIONS,
    act,
    as_,
    content_of,
    make_settings,
    ok,
    para,
    start,
)

SAMPLE = json.loads(
    (Path(__file__).parent.parent / "fixtures" / "duplicate_sample.json").read_text("utf-8")
)
STEM = (
    "A block of mass 2 kg slides down a smooth incline of angle 30 degrees. Find its acceleration."
)
OPTIONS = ["5 m/s^2", "10 m/s^2", "2.5 m/s^2", "0"]


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


def block_question(catalogue: Catalogue, stem: str = STEM, **more: Any) -> dict[str, Any]:
    return content_of(catalogue, stem, options=OPTIONS, **more)


def duplicates(
    client: TestClient, team: dict[str, Member], who: str, question: dict[str, Any]
) -> dict[str, Any]:
    response = client.get(
        f"{QUESTIONS}/{question['id']}/duplicates", headers=as_(client, team, who)
    )
    assert response.status_code == 200, response.text
    return dict(response.json())


def publish_as(
    client: TestClient, team: dict[str, Member], question: dict[str, Any], author: str
) -> dict[str, Any]:
    question = act(client, team, author, question, "submit")
    for step, who in CHAIN:
        question = act(client, team, who, question, step)
    return question


def matches(found: dict[str, Any]) -> list[tuple[str, str]]:
    return [(row["code"], row["match"]) for row in found["data"]]


@pytest.fixture
def published(client: TestClient, team: dict[str, Member], catalogue: Catalogue) -> dict[str, Any]:
    """The question already in the bank, published."""
    return publish_as(
        client, team, start(client, team, block_question(catalogue), "other"), "other"
    )


# ---- exact, near, not exact --------------------------------------------------------------------


def test_the_same_question_typed_again_is_an_exact_duplicate(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue, published: dict[str, Any]
) -> None:
    retyped = block_question(
        catalogue,
        stem="  a BLOCK of mass 2 kg slides down a SMOOTH incline"
        " of angle 30 degrees.   Find its acceleration. ",
    )
    retyped["solution"] = para("Another worked solution.")  # not part of the comparison
    retyped["metadata"]["difficulty"] = 9
    draft = start(client, team, retyped)

    found = duplicates(client, team, "author", draft)

    assert matches(found) == [(published["code"], "EXACT")]
    assert found["data"][0]["similarity_percent"] == 100
    assert found["data"][0]["state"] == "PUBLISHED"
    assert found["data"][0]["preview"].startswith("A block of mass 2 kg")


def test_a_small_change_of_the_words_is_a_near_duplicate(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue, published: dict[str, Any]
) -> None:
    draft = start(
        client,
        team,
        block_question(
            catalogue, stem=STEM.replace("Find its", "Find the").replace("slides", "slids")
        ),
    )

    found = duplicates(client, team, "author", draft)

    assert matches(found) == [(published["code"], "NEAR")]
    assert int(float(NEAR_SIMILARITY) * 100) <= found["data"][0]["similarity_percent"] < 100


def test_a_changed_equation_or_answer_is_not_an_exact_duplicate(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue, published: dict[str, Any]
) -> None:
    with_equation = block_question(catalogue)
    with_equation["stem"].append({"kind": "equation", "format": "latex", "source": "a = g"})
    capital = copy.deepcopy(with_equation)
    capital["stem"][1]["source"] = "a = G"
    publish_as(client, team, start(client, team, with_equation, "other"), "other")
    other_answer = block_question(catalogue)
    other_answer["answer"] = {"option_id": "C"}  # the fixture's answer is B

    for content in (capital, other_answer):
        found = duplicates(client, team, "author", start(client, team, content))
        assert [row["match"] for row in found["data"]] == ["NEAR"] * len(found["data"])
        assert published["code"] in [row["code"] for row in found["data"]]


def test_a_different_question_on_the_same_topic_is_not_a_duplicate(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue, published: dict[str, Any]
) -> None:
    draft = start(
        client,
        team,
        content_of(
            catalogue,
            "A block of mass 2 kg rests on a rough incline of angle 30 degrees. Find the friction"
            " force on it.",
            options=["10 N", "20 N", "5 N", "0"],
        ),
    )
    assert duplicates(client, team, "author", draft)["data"] == []


def test_an_empty_draft_has_no_duplicates(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    empty = start(client, team, {"schema_version": 1, "question_type": "SCQ", "stem": []})
    start(client, team, {"schema_version": 1, "question_type": "SCQ", "stem": []})
    assert duplicates(client, team, "author", empty)["data"] == []


def test_exact_copies_beyond_the_exact_limit_are_never_shown_as_near(
    client: TestClient,
    team: dict[str, Member],
    catalogue: Catalogue,
    published: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    second = publish_as(
        client, team, start(client, team, block_question(catalogue), "other"), "other"
    )
    draft = start(client, team, block_question(catalogue))
    monkeypatch.setattr(search_duplicates, "MAX_CANDIDATES", 1)  # only one exact match is shown

    found = duplicates(client, team, "author", draft)

    assert [row["match"] for row in found["data"]] == ["EXACT"]
    assert found["data"][0]["code"] in (published["code"], second["code"])


# ---- which text, and whose questions -----------------------------------------------------------


def test_a_draft_is_checked_as_it_is_now_and_never_against_itself(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue, published: dict[str, Any]
) -> None:
    draft = start(client, team, content_of(catalogue, "Something else entirely about optics."))
    assert duplicates(client, team, "author", draft)["data"] == []

    headers = {**as_(client, team, "author"), "If-Match": f'"rev-{draft["revision"]}"'}
    ok(
        client.put(
            f"{QUESTIONS}/{draft['id']}/working-revision",
            json={"content": block_question(catalogue)},
            headers=headers,
        )
    )
    found = duplicates(client, team, "author", draft)
    assert matches(found) == [(published["code"], "EXACT")]
    # From the other side too, for someone who may open the draft.
    assert duplicates(client, team, "admin", published)["data"][0]["code"] == draft["code"]


def test_a_submitted_question_is_checked_as_submitted(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue, published: dict[str, Any]
) -> None:
    submitted = act(
        client, team, "author", start(client, team, block_question(catalogue)), "submit"
    )

    found = duplicates(client, team, "qc", submitted)

    assert found["checked_revision_id"] == submitted["review_revision_id"]
    assert matches(found) == [(published["code"], "EXACT")]


def test_a_private_draft_is_offered_only_to_those_who_may_open_it(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue, published: dict[str, Any]
) -> None:
    secret = start(client, team, block_question(catalogue), "author")  # a private draft

    for who in ("admin", "owner", "editor"):
        codes = [row["code"] for row in duplicates(client, team, who, published)["data"]]
        assert secret["code"] in codes, who
    for who in ("qc", "approver", "publisher"):
        codes = [row["code"] for row in duplicates(client, team, who, published)["data"]]
        assert secret["code"] not in codes, who
    # And the draft itself cannot be checked by someone who may not open it.
    response = client.get(f"{QUESTIONS}/{secret['id']}/duplicates", headers=as_(client, team, "qc"))
    assert response.status_code == 404


def test_another_coaching_is_never_offered_or_checked(
    client: TestClient,
    owner_db: Database,
    team: dict[str, Member],
    catalogue: Catalogue,
    published: dict[str, Any],
) -> None:
    stranger = make_member(owner_db, "OWNER")
    headers = sign_in(client, stranger.email)
    theirs = ok(
        client.post(
            QUESTIONS,
            json={"content": block_question(seed_catalogue(owner_db, stranger.org_id))},
            headers=headers,
        )
    )
    assert (
        client.get(f"{QUESTIONS}/{theirs['id']}/duplicates", headers=headers).json()["data"] == []
    )
    assert (
        client.get(f"{QUESTIONS}/{published['id']}/duplicates", headers=headers).status_code == 404
    )
    codes = [row["code"] for row in duplicates(client, team, "owner", published)["data"]]
    assert theirs["code"] not in codes


def test_an_archived_question_is_not_offered(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue, published: dict[str, Any]
) -> None:
    draft = start(client, team, block_question(catalogue))
    ok(client.post(f"{QUESTIONS}/{published['id']}/archive", headers=as_(client, team, "owner")))
    assert duplicates(client, team, "author", draft)["data"] == []


def test_a_person_with_no_role_cannot_check(
    client: TestClient, owner_db: Database, published: dict[str, Any]
) -> None:
    headers = sign_in(client, platform_admin(owner_db))
    assert client.get(f"{QUESTIONS}/{published['id']}/duplicates", headers=headers).status_code in (
        403,
        404,
    )


# ---- the threshold ------------------------------------------------------------------------------


def test_the_near_threshold_separates_the_labelled_sample(owner_db: Database) -> None:
    threshold = float(NEAR_SIMILARITY)
    with owner_db.transaction(TenantContext(is_platform=True)) as session:

        def score(a: str, b: str) -> float:
            return float(session.scalar(text("SELECT similarity(:a, :b)"), {"a": a, "b": b}))

        same = [score(a, b) for a, b in SAMPLE["same"]]
        different = [score(a, b) for a, b in SAMPLE["different"]]
    assert min(same) >= threshold, sorted(same)
    assert max(different) < threshold, sorted(different)
