"""M3 PR 3b-3: autosave, checkpoints and history (D-12, E-04; test T27).

Autosave updates the working revision in place, guarded by ``If-Match``. A checkpoint freezes it
(with a content hash) and starts a new working revision. Frozen revisions never change.
"""

import copy
import hashlib
import json
from collections.abc import Iterator
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from qbank.core.config import AppEnv, Settings
from qbank.core.db import Database
from qbank.main import create_app
from qbank.modules.audit.models import AuditEvent
from tests.integration.conftest import (
    PLATFORM,
    Member,
    MigratedDatabase,
    make_member,
    sign_in,
)
from tests.unit.test_question_content import FIXTURES

DRAFT = FIXTURES["SCQ"]["draft"]
READY = FIXTURES["SCQ"]["ready"]
PATH = "/api/v1/questions"


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
        "author": make_member(owner_db, "FACULTY", org_id=owner.org_id),
        "other": make_member(owner_db, "FACULTY", org_id=owner.org_id),
        "editor": make_member(owner_db, "FACULTY", org_id=owner.org_id, grants=["EDIT_OTHERS"]),
    }


@pytest.fixture
def started(client: TestClient, team: dict[str, Member]) -> tuple[dict[str, Any], dict[str, str]]:
    """A draft started by the author, who is signed in; returns the question and the headers."""
    headers = sign_in(client, team["author"].email)
    response = client.post(PATH, json={"content": copy.deepcopy(DRAFT)}, headers=headers)
    assert response.status_code == 201, response.text
    return response.json(), headers


def tag(question: dict[str, Any]) -> dict[str, str]:
    return {"If-Match": f'"rev-{question["revision"]}"'}


def save(
    client: TestClient,
    headers: dict[str, str],
    question: dict[str, Any],
    content: dict[str, Any],
    **extra: str,
) -> Any:
    return client.put(
        f"{PATH}/{question['id']}/working-revision",
        json={"content": content},
        headers={**headers, **(extra or tag(question))},
    )


def checkpoint(
    client: TestClient, headers: dict[str, str], question: dict[str, Any], **extra: str
) -> Any:
    return client.post(
        f"{PATH}/{question['id']}/checkpoints", headers={**headers, **(extra or tag(question))}
    )


# --- autosave ------------------------------------------------------------------------------------


def test_autosave_replaces_the_working_content_and_moves_the_etag(
    client: TestClient, started: tuple[dict[str, Any], dict[str, str]]
) -> None:
    question, headers = started
    response = save(client, headers, question, copy.deepcopy(READY))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["content"] == READY
    assert body["findings"] == []  # the new content has no gaps
    assert body["revision"] == question["revision"] + 1
    assert response.headers["ETag"] == f'"rev-{body["revision"]}"'
    assert body["version_number"] == 1
    assert body["updated_at"] >= question["updated_at"]
    assert client.get(f"{PATH}/{question['id']}").json() == body


def test_autosave_accepts_a_draft_full_of_gaps_and_mistakes(
    client: TestClient, started: tuple[dict[str, Any], dict[str, str]]
) -> None:
    question, headers = started
    assert save(client, headers, question, {}).status_code == 200
    assert save(
        client, headers, question, {"stem": "not blocks"}, **{"If-Match": '"rev-2"'}
    ).json()["findings"]


def test_a_second_tab_with_an_old_etag_is_refused_and_overwrites_nothing(
    client: TestClient, started: tuple[dict[str, Any], dict[str, str]]
) -> None:
    question, headers = started
    assert save(client, headers, question, copy.deepcopy(READY)).status_code == 200
    stale = save(client, headers, question, {"language": "hi"})  # still holds the first ETag
    assert stale.status_code == 412
    assert stale.json()["error"]["code"] == "REVISION_STALE"
    assert client.get(f"{PATH}/{question['id']}").json()["content"] == READY


def test_autosave_needs_an_if_match(
    client: TestClient, started: tuple[dict[str, Any], dict[str, str]]
) -> None:
    question, headers = started
    response = client.put(
        f"{PATH}/{question['id']}/working-revision", json={"content": {}}, headers=headers
    )
    assert response.status_code == 428
    assert response.json()["error"]["code"] == "IF_MATCH_REQUIRED"


def test_autosave_refuses_oversize_content_and_extra_fields(
    client: TestClient, started: tuple[dict[str, Any], dict[str, str]]
) -> None:
    question, headers = started
    huge = {"stem": [{"kind": "paragraph", "text": "x" * 270_000}]}
    response = save(client, headers, question, huge)
    assert (response.status_code, response.json()["error"]["code"]) == (422, "CONTENT_TOO_LARGE")
    odd = client.put(
        f"{PATH}/{question['id']}/working-revision",
        json={"content": {}, "extra": 1},
        headers={**headers, **tag(question)},
    )
    assert odd.status_code == 400


def test_autosave_is_not_audited(
    client: TestClient,
    owner_db: Database,
    started: tuple[dict[str, Any], dict[str, str]],
) -> None:
    question, headers = started
    save(client, headers, question, copy.deepcopy(READY))
    assert actions(owner_db, question) == ["QUESTION_CREATED"]


def actions(owner_db: Database, question: dict[str, Any]) -> list[str]:
    with owner_db.transaction(PLATFORM) as session:
        rows = session.scalars(
            select(AuditEvent)
            .where(AuditEvent.entity_id == UUID(question["id"]))
            .order_by(AuditEvent.created_at)
        )
        return [row.action for row in rows]


# --- who may save --------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("who", "saved", "checkpointed"),
    [("editor", 200, 201), ("owner", 200, 201), ("other", 404, 404)],
)
def test_who_may_save_and_checkpoint_someone_elses_draft(
    client: TestClient,
    team: dict[str, Member],
    started: tuple[dict[str, Any], dict[str, str]],
    who: str,
    saved: int,
    checkpointed: int,
) -> None:
    question, _ = started
    headers = sign_in(client, team[who].email)
    response = save(client, headers, question, copy.deepcopy(READY))
    assert response.status_code == saved
    current = response.json() if saved == 200 else question
    assert checkpoint(client, headers, current).status_code == checkpointed


def test_another_coaching_cannot_save(
    client: TestClient,
    owner_db: Database,
    started: tuple[dict[str, Any], dict[str, str]],
) -> None:
    question, _ = started
    stranger = make_member(owner_db, "ADMIN", coaching_name="Other Coaching")
    headers = sign_in(client, stranger.email)
    assert save(client, headers, question, {}).status_code == 404
    assert checkpoint(client, headers, question).status_code == 404


def test_an_archived_question_cannot_be_changed(
    client: TestClient,
    owner_db: Database,
    team: dict[str, Member],
    started: tuple[dict[str, Any], dict[str, str]],
) -> None:
    question, headers = started
    with owner_db.transaction(PLATFORM) as session:
        session.execute(
            text("UPDATE question_masters SET archived_at = now() WHERE id = :id"),
            {"id": question["id"]},
        )
    for response in (save(client, headers, question, {}), checkpoint(client, headers, question)):
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "QUESTION_ARCHIVED"


# --- checkpoints ---------------------------------------------------------------------------------


def test_a_checkpoint_freezes_the_content_and_starts_a_new_working_revision(
    client: TestClient,
    owner_db: Database,
    started: tuple[dict[str, Any], dict[str, str]],
) -> None:
    question, headers = started
    saved = save(client, headers, question, copy.deepcopy(READY)).json()
    response = checkpoint(client, headers, saved)
    assert response.status_code == 201, response.text
    working = response.json()
    assert working["content"] == READY  # the new working revision starts as a copy
    assert working["revision"] == saved["revision"] + 1  # a stale tab can never match again
    assert response.headers["Location"] == f"{PATH}/{question['id']}/revisions/1"
    assert response.headers["ETag"] == f'"rev-{working["revision"]}"'

    history = client.get(f"{PATH}/{question['id']}/revisions").json()["data"]
    assert [(row["number"], row["working"]) for row in history] == [(2, True), (1, False)]
    frozen = history[1]
    expected = hashlib.sha256(
        json.dumps(READY, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()
    assert frozen["content_hash"] == expected
    assert frozen["frozen_at"] is not None
    assert history[0]["content_hash"] is None
    assert actions(owner_db, question) == ["QUESTION_CREATED", "QUESTION_CHECKPOINTED"]


def test_a_frozen_revision_keeps_its_content_while_work_goes_on(
    client: TestClient, started: tuple[dict[str, Any], dict[str, str]]
) -> None:
    question, headers = started
    saved = save(client, headers, question, copy.deepcopy(READY)).json()
    working = checkpoint(client, headers, saved).json()
    save(client, headers, working, copy.deepcopy(DRAFT))
    old = client.get(f"{PATH}/{question['id']}/revisions/1")
    assert old.status_code == 200
    assert old.json()["content"] == READY
    assert old.json()["findings"] == []
    assert old.json()["working"] is False
    now = client.get(f"{PATH}/{question['id']}/revisions/2").json()
    assert now["content"] == DRAFT
    assert now["working"] is True


def test_an_old_tab_cannot_save_after_a_checkpoint(
    client: TestClient, started: tuple[dict[str, Any], dict[str, str]]
) -> None:
    question, headers = started  # a tab holding the first ETag
    assert checkpoint(client, headers, question).status_code == 201
    assert save(client, headers, question, {}).status_code == 412
    assert checkpoint(client, headers, question).status_code == 412


def test_a_checkpoint_needs_an_if_match(
    client: TestClient, started: tuple[dict[str, Any], dict[str, str]]
) -> None:
    question, headers = started
    response = client.post(f"{PATH}/{question['id']}/checkpoints", headers=headers)
    assert response.status_code == 428


def test_unknown_revisions_are_not_found(
    client: TestClient, started: tuple[dict[str, Any], dict[str, str]]
) -> None:
    question, _ = started
    assert client.get(f"{PATH}/{question['id']}/revisions/9").status_code == 404
    assert client.get(f"{PATH}/{question['id']}/revisions/0").status_code == 400


def test_history_is_private_like_the_draft(
    client: TestClient, team: dict[str, Member], started: tuple[dict[str, Any], dict[str, str]]
) -> None:
    question, _ = started
    sign_in(client, team["other"].email)
    assert client.get(f"{PATH}/{question['id']}/revisions").status_code == 404
    assert client.get(f"{PATH}/{question['id']}/revisions/1").status_code == 404
    sign_in(client, team["editor"].email)
    assert client.get(f"{PATH}/{question['id']}/revisions").status_code == 200
