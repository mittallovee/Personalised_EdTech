"""M4 PR 4g-2: deciding about possible duplicates, and Pass QC waiting for it (D-16; T39 part 2).

An exact copy in the shared bank blocks Pass QC until a person records that it is not a duplicate;
a "duplicate of" decision blocks it too; a near copy, a private draft and an archived question never
block. Decisions are about one text, append-only, audited, and only the author, editors and quality
control make them.
"""

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from qbank.core.db import Database
from qbank.core.tenancy import TenantContext
from qbank.main import create_app
from tests.integration.conftest import Member, MigratedDatabase, make_member, sign_in
from tests.integration.question_support import Catalogue, seed_catalogue
from tests.integration.test_bank_search import QUESTIONS, act, as_, make_settings, ok, start
from tests.integration.test_duplicates import STEM, block_question, duplicates, publish_as


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


@pytest.fixture
def original(client: TestClient, team: dict[str, Member], catalogue: Catalogue) -> dict[str, Any]:
    """A question already in the shared bank, published by "other"."""
    return publish_as(
        client, team, start(client, team, block_question(catalogue), "other"), "other"
    )


@pytest.fixture
def copy_in_review(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue, original: dict[str, Any]
) -> dict[str, Any]:
    """The author's exact copy of it, submitted for review."""
    return act(client, team, "author", start(client, team, block_question(catalogue)), "submit")


def decide(
    client: TestClient,
    team: dict[str, Member],
    who: str,
    question: dict[str, Any],
    other: dict[str, Any],
    decision: str = "NOT_DUPLICATE",
    note: str = "Checked side by side.",
) -> Any:
    return client.post(
        f"{QUESTIONS}/{question['id']}/duplicates/decisions",
        json={"other_question_id": other["id"], "decision": decision, "note": note},
        headers=as_(client, team, who),
    )


def pass_qc(client: TestClient, team: dict[str, Member], question: dict[str, Any]) -> Any:
    headers = {**as_(client, team, "qc"), "If-Match": question["flow_etag"]}
    return client.post(f"{QUESTIONS}/{question['id']}/pass-qc", headers=headers)


# ---- Pass QC waits for a decision --------------------------------------------------------------


def test_an_undecided_exact_copy_blocks_pass_qc_and_a_decision_unblocks_it(
    client: TestClient,
    team: dict[str, Member],
    original: dict[str, Any],
    copy_in_review: dict[str, Any],
) -> None:
    refused = pass_qc(client, team, copy_in_review)
    assert refused.status_code == 409
    assert refused.json()["error"]["code"] == "QC_BLOCKED_DUPLICATE"
    assert refused.json()["error"]["details"]["duplicates"] == [
        {"question_id": original["id"], "code": original["code"]}
    ]
    check = duplicates(client, team, "qc", copy_in_review)
    assert check["qc_blocked_by"] == [{"question_id": original["id"], "code": original["code"]}]

    made = decide(client, team, "qc", copy_in_review, original)
    assert made.status_code == 201, made.text
    assert made.json()["decision"] == "NOT_DUPLICATE"

    after = duplicates(client, team, "qc", copy_in_review)
    assert after["qc_blocked_by"] == []
    assert after["data"][0]["decision"]["note"] == "Checked side by side."
    assert pass_qc(client, team, copy_in_review).status_code == 200


def test_a_duplicate_of_decision_blocks_and_the_newest_decision_counts(
    client: TestClient,
    team: dict[str, Member],
    original: dict[str, Any],
    copy_in_review: dict[str, Any],
) -> None:
    assert decide(client, team, "qc", copy_in_review, original, "DUPLICATE_OF").status_code == 201
    assert pass_qc(client, team, copy_in_review).json()["error"]["code"] == "QC_BLOCKED_DUPLICATE"

    assert decide(client, team, "qc", copy_in_review, original, "NOT_DUPLICATE").status_code == 201
    assert pass_qc(client, team, copy_in_review).status_code == 200


def test_marking_a_near_copy_as_a_duplicate_blocks_too(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue, original: dict[str, Any]
) -> None:
    near = act(
        client,
        team,
        "author",
        start(client, team, block_question(catalogue, stem=STEM.replace("Find its", "Find the"))),
        "submit",
    )
    assert pass_qc(client, team, near).status_code == 200  # a near copy only informs

    another = act(
        client,
        team,
        "author",
        start(client, team, block_question(catalogue, stem=STEM.replace("slides", "glides"))),
        "submit",
    )
    assert decide(client, team, "author", another, original, "DUPLICATE_OF").status_code == 201
    assert pass_qc(client, team, another).json()["error"]["code"] == "QC_BLOCKED_DUPLICATE"


def test_a_decision_made_on_the_draft_still_counts_once_it_is_submitted(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue, original: dict[str, Any]
) -> None:
    draft = start(client, team, block_question(catalogue))
    assert decide(client, team, "author", draft, original).status_code == 201

    submitted = act(client, team, "author", draft, "submit")

    assert pass_qc(client, team, submitted).status_code == 200


def test_a_decision_is_about_one_text_and_an_edit_needs_a_new_one(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue, original: dict[str, Any]
) -> None:
    draft = start(client, team, block_question(catalogue))
    assert decide(client, team, "author", draft, original).status_code == 201
    content = block_question(catalogue)
    content["answer"] = {"option_id": "C"}  # another answer: another question
    headers = {**as_(client, team, "author"), "If-Match": f'"rev-{draft["revision"]}"'}
    ok(
        client.put(
            f"{QUESTIONS}/{draft['id']}/working-revision",
            json={"content": content},
            headers=headers,
        )
    )

    check = duplicates(client, team, "author", draft)

    assert [row["decision"] for row in check["data"]] == [None]  # the old decision was another text


def test_a_private_draft_or_an_archived_copy_never_blocks(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    start(client, team, block_question(catalogue), "other")  # someone else's private draft
    archived = publish_as(
        client, team, start(client, team, block_question(catalogue), "editor"), "editor"
    )
    ok(client.post(f"{QUESTIONS}/{archived['id']}/archive", headers=as_(client, team, "owner")))
    mine = act(client, team, "author", start(client, team, block_question(catalogue)), "submit")

    assert pass_qc(client, team, mine).status_code == 200


# ---- who may decide, about what -----------------------------------------------------------------


def test_only_the_author_editors_and_quality_control_may_decide(
    client: TestClient,
    team: dict[str, Member],
    original: dict[str, Any],
    copy_in_review: dict[str, Any],
) -> None:
    for who in ("approver", "publisher"):  # they may read it, not decide it
        response = decide(client, team, who, copy_in_review, original)
        assert response.status_code == 403, who
    for who in ("author", "editor", "admin", "owner", "qc"):
        assert decide(client, team, who, copy_in_review, original).status_code == 201, who


def test_someone_elses_private_draft_cannot_be_named_as_the_other_question(
    client: TestClient,
    team: dict[str, Member],
    catalogue: Catalogue,
    copy_in_review: dict[str, Any],
) -> None:
    secret = start(client, team, block_question(catalogue), "other")
    response = decide(client, team, "qc", copy_in_review, secret)
    assert response.status_code == 404
    assert decide(client, team, "admin", copy_in_review, secret).status_code == 201  # may open it


def test_another_coaching_is_never_reachable(
    client: TestClient,
    owner_db: Database,
    team: dict[str, Member],
    original: dict[str, Any],
    copy_in_review: dict[str, Any],
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
    across = client.post(
        f"{QUESTIONS}/{theirs['id']}/duplicates/decisions",
        json={"other_question_id": original["id"], "decision": "NOT_DUPLICATE", "note": "x"},
        headers=headers,
    )
    assert across.status_code == 404
    assert decide(client, team, "qc", copy_in_review, theirs).status_code == 404


def test_a_decision_needs_another_question_a_note_and_an_unpublished_question(
    client: TestClient,
    team: dict[str, Member],
    original: dict[str, Any],
    copy_in_review: dict[str, Any],
) -> None:
    itself = decide(client, team, "qc", copy_in_review, copy_in_review)
    assert itself.status_code == 422 and itself.json()["error"]["code"] == "SAME_QUESTION"
    blank = decide(client, team, "qc", copy_in_review, original, note="   ")
    assert blank.status_code == 422 and blank.json()["error"]["code"] == "NOTE_REQUIRED"
    assert decide(client, team, "qc", copy_in_review, original, note="").status_code == 400
    closed = decide(client, team, "other", original, copy_in_review)
    assert closed.status_code == 409
    assert closed.json()["error"]["code"] == "DUPLICATE_DECISION_CLOSED"


# ---- kept for good ------------------------------------------------------------------------------


def test_decisions_are_audited_and_can_never_be_changed_or_deleted(
    client: TestClient,
    owner_db: Database,
    migrated_database: MigratedDatabase,
    team: dict[str, Member],
    original: dict[str, Any],
    copy_in_review: dict[str, Any],
) -> None:
    assert decide(client, team, "qc", copy_in_review, original).status_code == 201
    org = team["owner"].org_id
    with owner_db.transaction(TenantContext(organization_id=org)) as session:
        events = (
            session.execute(
                text(
                    "SELECT after FROM audit_events WHERE organization_id = :org"
                    " AND action = 'QUESTION_DUPLICATE_DECIDED'"
                ),
                {"org": org},
            )
            .scalars()
            .all()
        )
    assert len(events) == 1
    assert events[0]["other_code"] == original["code"]
    assert events[0]["decision"] == "NOT_DUPLICATE"

    for statement in (
        "UPDATE duplicate_decisions SET decision = 'DUPLICATE_OF'",
        "DELETE FROM duplicate_decisions",
    ):
        with (
            pytest.raises(DBAPIError),
            owner_db.transaction(TenantContext(organization_id=org)) as session,
        ):
            session.execute(text(statement))  # the table owner: the trigger refuses
        app_db = Database(migrated_database.app_url)
        try:
            with (
                pytest.raises(DBAPIError),
                app_db.transaction(TenantContext(organization_id=org)) as session,
            ):
                session.execute(text(statement))  # the app: no right to change or delete
        finally:
            app_db.dispose()
