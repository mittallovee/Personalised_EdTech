"""M4 PR 4a-2: submit and withdraw, and the read-only editor (E-01, E-04; tests T34 part, T37 part).

Submit freezes the working revision as the one under review; while a question is in review the
server refuses every save; only an explicit withdraw makes it editable again. Every step after
submit carries the workflow ETag (``flow-N``).
"""

import copy
from collections.abc import Iterator
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from qbank.core.config import AppEnv, Settings
from qbank.core.db import Database
from qbank.core.tenancy import TenantContext
from qbank.main import create_app
from qbank.modules.audit.models import AuditEvent
from qbank.modules.questions.models import ReviewDecision
from tests.integration.conftest import (
    PLATFORM,
    Member,
    MigratedDatabase,
    make_member,
    sign_in,
)
from tests.integration.question_support import Catalogue, ready_for, seed_catalogue
from tests.unit.test_question_content import FIXTURES

PATH = "/api/v1/questions"
DRAFT = FIXTURES["SCQ"]["draft"]


@pytest.fixture
def settings(migrated_database: MigratedDatabase) -> Settings:
    return Settings(
        app_env=AppEnv.TEST, database_url=migrated_database.app_url, session_cookie_secure=False
    )


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings)) as test_client:
        yield test_client


@pytest.fixture
def team(owner_db: Database) -> dict[str, Member]:
    owner = make_member(owner_db, "OWNER")
    return {
        "owner": owner,
        "admin": make_member(owner_db, "ADMIN", org_id=owner.org_id),
        "author": make_member(owner_db, "FACULTY", org_id=owner.org_id),
        "other": make_member(owner_db, "FACULTY", org_id=owner.org_id),
        "editor": make_member(owner_db, "FACULTY", org_id=owner.org_id, grants=["EDIT_OTHERS"]),
        "qc": make_member(owner_db, "FACULTY", org_id=owner.org_id, grants=["QC"]),
    }


@pytest.fixture
def catalogue(owner_db: Database, team: dict[str, Member]) -> Catalogue:
    return seed_catalogue(owner_db, team["owner"].org_id)


@pytest.fixture
def started(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> tuple[dict[str, Any], dict[str, str]]:
    """A complete question started by the author, who is signed in; returns it and the headers."""
    headers = sign_in(client, team["author"].email)
    response = client.post(PATH, json={"content": ready_for(catalogue)}, headers=headers)
    assert response.status_code == 201, response.text
    return response.json(), headers


def rev(question: dict[str, Any]) -> dict[str, str]:
    return {"If-Match": f'"rev-{question["revision"]}"'}


def flow(question: dict[str, Any]) -> dict[str, str]:
    return {"If-Match": question["flow_etag"]}


def submit(client: TestClient, headers: dict[str, str], question: dict[str, Any]) -> Any:
    return client.post(f"{PATH}/{question['id']}/submit", headers={**headers, **rev(question)})


def withdraw(client: TestClient, headers: dict[str, str], question: dict[str, Any]) -> Any:
    return client.post(f"{PATH}/{question['id']}/withdraw", headers={**headers, **flow(question)})


def submitted(client: TestClient, started: tuple[dict[str, Any], dict[str, str]]) -> dict[str, Any]:
    question, headers = started
    response = submit(client, headers, question)
    assert response.status_code == 200, response.text
    return response.json()


# ---- a new question starts as a draft ---------------------------------------------------------


def test_a_new_question_is_a_draft_that_can_be_submitted(
    started: tuple[dict[str, Any], dict[str, str]],
) -> None:
    question, _ = started
    assert question["state"] == "DRAFT"
    assert question["flow_etag"] == '"flow-1"'
    assert question["allowed_steps"] == ["SUBMIT"]
    assert question["review_revision_id"] is None


# ---- submit -----------------------------------------------------------------------------------


def test_submit_freezes_the_working_revision_as_the_one_under_review(
    client: TestClient,
    started: tuple[dict[str, Any], dict[str, str]],
    team: dict[str, Member],
    owner_db: Database,
) -> None:
    question, headers = started
    response = submit(client, headers, question)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["state"] == "IN_REVIEW"
    assert body["flow_etag"] == '"flow-2"'
    assert body["allowed_steps"] == ["WITHDRAW"]
    assert body["review_revision_id"] is not None
    assert body["content"] == question["content"]
    # The revision under review is frozen with a hash; a new working copy follows it.
    listing = client.get(f"{PATH}/{question['id']}/revisions", headers=headers).json()["data"]
    assert [(r["number"], r["working"]) for r in listing] == [(2, True), (1, False)]
    assert listing[1]["content_hash"] and listing[1]["frozen_at"]
    assert body["revision"] == question["revision"] + 1  # the ETag continues the count
    # The decision and the audit event were written with it.
    with owner_db.transaction(TenantContext(organization_id=team["author"].org_id)) as session:
        rows = session.scalars(
            select(ReviewDecision).where(ReviewDecision.organization_id == team["author"].org_id)
        ).all()
        assert [(r.step, r.from_state, r.to_state, r.flow_revision) for r in rows] == [
            ("SUBMIT", "DRAFT", "IN_REVIEW", 2)
        ]
        assert str(rows[0].revision_id) == body["review_revision_id"]
        assert rows[0].actor_id == team["author"].user_id
    with owner_db.transaction(PLATFORM) as session:
        events = session.scalars(
            select(AuditEvent).where(AuditEvent.entity_id == UUID(question["id"]))
        ).all()
    submitted_events = [e for e in events if e.action == "QUESTION_SUBMITTED"]
    assert len(submitted_events) == 1
    assert submitted_events[0].after is not None
    assert submitted_events[0].after["state"] == "IN_REVIEW"


def test_submit_needs_the_working_etag(
    client: TestClient, started: tuple[dict[str, Any], dict[str, str]]
) -> None:
    question, headers = started
    url = f"{PATH}/{question['id']}/submit"
    assert client.post(url, headers=headers).status_code == 428
    stale = client.post(url, headers={**headers, "If-Match": '"rev-99"'})
    assert stale.status_code == 412
    assert stale.json()["error"]["code"] == "REVISION_STALE"
    # A workflow ETag is another value space and is not accepted for a revision.
    mixed = client.post(url, headers={**headers, **flow(question)})
    assert mixed.status_code == 412
    assert client.get(f"{PATH}/{question['id']}", headers=headers).json()["state"] == "DRAFT"


def test_a_question_with_mistakes_is_not_submitted(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    headers = sign_in(client, team["author"].email)
    content = ready_for(catalogue)
    content["answer"] = {"option_id": "Z"}  # there is no option Z
    question = client.post(PATH, json={"content": content}, headers=headers).json()
    response = submit(client, headers, question)
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "QUESTION_HAS_ERRORS"
    assert {f["code"] for f in error["details"]["findings"]} == {"ANSWER_OPTION_UNKNOWN"}
    assert client.get(f"{PATH}/{question['id']}", headers=headers).json()["state"] == "DRAFT"


def test_things_still_to_do_do_not_stop_a_submit(
    client: TestClient, team: dict[str, Member]
) -> None:
    headers = sign_in(client, team["author"].email)
    question = client.post(PATH, json={"content": copy.deepcopy(DRAFT)}, headers=headers).json()
    assert any(f["level"] == "incomplete" for f in question["findings"])
    assert not any(f["level"] == "error" for f in question["findings"])
    assert submit(client, headers, question).status_code == 200


def test_a_submitted_question_cannot_be_submitted_again(
    client: TestClient, started: tuple[dict[str, Any], dict[str, str]]
) -> None:
    question = submitted(client, started)
    _, headers = started
    again = submit(client, headers, question)
    assert again.status_code == 409
    error = again.json()["error"]
    assert error["code"] == "WORKFLOW_STEP_INVALID"
    assert error["details"] == {"state": "IN_REVIEW", "allowed": ["RETURN", "PASS_QC", "WITHDRAW"]}


def test_an_archived_question_is_not_submitted(
    client: TestClient, started: tuple[dict[str, Any], dict[str, str]]
) -> None:
    question, headers = started
    assert client.post(f"{PATH}/{question['id']}/archive", headers=headers).status_code == 200
    response = submit(client, headers, question)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "QUESTION_ARCHIVED"


# ---- the editor is read-only during review ----------------------------------------------------


def test_a_question_in_review_cannot_be_saved_or_checkpointed(
    client: TestClient, started: tuple[dict[str, Any], dict[str, str]]
) -> None:
    question = submitted(client, started)
    _, headers = started
    changed = copy.deepcopy(question["content"])
    changed["stem"] = [{"kind": "paragraph", "text": "Changed after submit"}]
    saved = client.put(
        f"{PATH}/{question['id']}/working-revision",
        json={"content": changed},
        headers={**headers, **rev(question)},
    )
    assert saved.status_code == 409
    assert saved.json()["error"]["code"] == "QUESTION_NOT_EDITABLE"
    assert saved.json()["error"]["details"] == {"state": "IN_REVIEW"}
    checkpoint = client.post(
        f"{PATH}/{question['id']}/checkpoints", headers={**headers, **rev(question)}
    )
    assert checkpoint.status_code == 409
    assert checkpoint.json()["error"]["code"] == "QUESTION_NOT_EDITABLE"
    again = client.get(f"{PATH}/{question['id']}", headers=headers).json()
    assert again["content"] == question["content"]


# ---- withdraw ---------------------------------------------------------------------------------


def test_withdraw_makes_the_question_editable_again(
    client: TestClient,
    started: tuple[dict[str, Any], dict[str, str]],
    team: dict[str, Member],
    owner_db: Database,
) -> None:
    question = submitted(client, started)
    _, headers = started
    response = withdraw(client, headers, question)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["state"] == "DRAFT"
    assert body["flow_etag"] == '"flow-3"'
    assert body["review_revision_id"] is None
    assert body["allowed_steps"] == ["SUBMIT"]
    assert body["revision"] == question["revision"]  # the working copy carries on unchanged
    changed = copy.deepcopy(body["content"])
    changed["stem"] = [{"kind": "paragraph", "text": "Edited after the withdraw"}]
    saved = client.put(
        f"{PATH}/{question['id']}/working-revision",
        json={"content": changed},
        headers={**headers, **rev(body)},
    )
    assert saved.status_code == 200, saved.text
    with owner_db.transaction(TenantContext(organization_id=team["author"].org_id)) as session:
        rows = session.scalars(
            select(ReviewDecision)
            .where(ReviewDecision.organization_id == team["author"].org_id)
            .order_by(ReviewDecision.flow_revision)
        ).all()
        assert [(r.step, r.to_state) for r in rows] == [
            ("SUBMIT", "IN_REVIEW"),
            ("WITHDRAW", "DRAFT"),
        ]
        # The withdraw is recorded against the revision that had been under review.
        assert rows[0].revision_id == rows[1].revision_id


def test_a_new_submit_after_a_withdraw_freezes_a_new_revision(
    client: TestClient, started: tuple[dict[str, Any], dict[str, str]]
) -> None:
    first = submitted(client, started)
    _, headers = started
    back = withdraw(client, headers, first).json()
    second = submit(client, headers, back).json()
    assert second["state"] == "IN_REVIEW"
    assert second["flow_etag"] == '"flow-4"'
    assert second["review_revision_id"] != first["review_revision_id"]


def test_withdraw_needs_the_workflow_etag(
    client: TestClient, started: tuple[dict[str, Any], dict[str, str]]
) -> None:
    question = submitted(client, started)
    _, headers = started
    url = f"{PATH}/{question['id']}/withdraw"
    assert client.post(url, headers=headers).status_code == 428
    wrong = client.post(url, headers={**headers, **rev(question)})  # a "rev-N" is not a "flow-N"
    assert wrong.status_code == 412
    assert wrong.json()["error"]["details"]["current_etag"] == '"flow-2"'
    assert withdraw(client, headers, question).status_code == 200
    stale = withdraw(client, headers, question)  # the same request again, on the old state
    assert stale.status_code == 412
    assert stale.json()["error"]["details"]["current_etag"] == '"flow-3"'


def test_a_draft_cannot_be_withdrawn(
    client: TestClient, started: tuple[dict[str, Any], dict[str, str]]
) -> None:
    question, headers = started
    response = withdraw(client, headers, question)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "WORKFLOW_STEP_INVALID"
    assert response.json()["error"]["details"] == {"state": "DRAFT", "allowed": ["SUBMIT"]}


# ---- who may do what, and who may read --------------------------------------------------------


def test_someone_elses_draft_is_not_found_so_it_cannot_be_submitted(
    client: TestClient,
    started: tuple[dict[str, Any], dict[str, str]],
    team: dict[str, Member],
) -> None:
    question, _ = started
    other = sign_in(client, team["other"].email)
    assert client.get(f"{PATH}/{question['id']}", headers=other).status_code == 404
    assert submit(client, other, question).status_code == 404


def test_edit_others_and_admins_may_submit_and_withdraw_for_the_author(
    client: TestClient,
    started: tuple[dict[str, Any], dict[str, str]],
    team: dict[str, Member],
) -> None:
    question, _ = started
    editor = sign_in(client, team["editor"].email)
    sent = submit(client, editor, question)
    assert sent.status_code == 200, sent.text
    assert sent.json()["allowed_steps"] == ["WITHDRAW"]
    admin = sign_in(client, team["admin"].email)
    back = withdraw(client, admin, sent.json())
    assert back.status_code == 200, back.text
    assert back.json()["state"] == "DRAFT"


def test_every_member_may_read_a_submitted_question_but_not_withdraw_it(
    client: TestClient,
    started: tuple[dict[str, Any], dict[str, str]],
    team: dict[str, Member],
) -> None:
    question = submitted(client, started)
    for who in ("other", "qc"):
        headers = sign_in(client, team[who].email)
        read = client.get(f"{PATH}/{question['id']}", headers=headers)
        assert read.status_code == 200, who
        body = read.json()
        assert body["state"] == "IN_REVIEW"
        assert body["content"] == question["content"]
        assert "WITHDRAW" not in body["allowed_steps"]
        assert body["flow_etag"] == question["flow_etag"]
        found = client.get(f"{PATH}/by-code/{question['code']}", headers=headers)
        assert found.status_code == 200
        denied = withdraw(client, headers, question)
        assert denied.status_code == 403, who
    assert client.get(f"{PATH}/{question['id']}", headers=sign_in(client, team["qc"].email)).json()[
        "allowed_steps"
    ] == ["RETURN", "PASS_QC"]


def test_a_withdrawn_question_is_private_again(
    client: TestClient,
    started: tuple[dict[str, Any], dict[str, str]],
    team: dict[str, Member],
) -> None:
    question = submitted(client, started)
    _, headers = started
    assert withdraw(client, headers, question).status_code == 200
    other = sign_in(client, team["other"].email)
    assert client.get(f"{PATH}/{question['id']}", headers=other).status_code == 404


def test_another_coachings_question_is_not_found(
    client: TestClient,
    started: tuple[dict[str, Any], dict[str, str]],
    owner_db: Database,
) -> None:
    question = submitted(client, started)
    outsider = make_member(owner_db, "OWNER")
    headers = sign_in(client, outsider.email)
    assert client.get(f"{PATH}/{question['id']}", headers=headers).status_code == 404
    assert withdraw(client, headers, question).status_code == 404
    assert submit(client, headers, question).status_code == 404
