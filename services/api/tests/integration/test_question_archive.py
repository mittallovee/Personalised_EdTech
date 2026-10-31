"""M3 PR 3b-4: archive and restore (design note section 6; test T27).

Questions are never deleted. Archiving hides a draft from the default list and stops edits, and its
code stays reserved and still resolves. The author or an admin may archive; holding the
edit-others grant is not enough.
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
        "admin": make_member(owner_db, "ADMIN", org_id=owner.org_id),
        "author": make_member(owner_db, "FACULTY", org_id=owner.org_id),
        "other": make_member(owner_db, "FACULTY", org_id=owner.org_id),
        "editor": make_member(owner_db, "FACULTY", org_id=owner.org_id, grants=["EDIT_OTHERS"]),
    }


@pytest.fixture
def started(client: TestClient, team: dict[str, Member]) -> tuple[dict[str, Any], dict[str, str]]:
    headers = sign_in(client, team["author"].email)
    response = client.post(PATH, json={"content": copy.deepcopy(READY)}, headers=headers)
    assert response.status_code == 201, response.text
    return response.json(), headers


def archive(client: TestClient, headers: dict[str, str], question: dict[str, Any]) -> Any:
    return client.post(f"{PATH}/{question['id']}/archive", headers=headers)


def restore(client: TestClient, headers: dict[str, str], question: dict[str, Any]) -> Any:
    return client.post(f"{PATH}/{question['id']}/restore", headers=headers)


def actions(owner_db: Database, question: dict[str, Any]) -> list[str]:
    with owner_db.transaction(PLATFORM) as session:
        rows = session.scalars(
            select(AuditEvent)
            .where(AuditEvent.entity_id == UUID(question["id"]))
            .order_by(AuditEvent.created_at)
        )
        return [row.action for row in rows]


def test_archiving_hides_the_draft_from_the_list_but_keeps_it_readable(
    client: TestClient,
    owner_db: Database,
    started: tuple[dict[str, Any], dict[str, str]],
) -> None:
    question, headers = started
    response = archive(client, headers, question)
    assert response.status_code == 200, response.text
    assert response.json()["archived"] is True
    assert response.json()["code"] == question["code"]
    assert client.get(PATH).json()["data"] == []
    listed = client.get(PATH, params={"archived": "true"}).json()["data"]
    assert [row["id"] for row in listed] == [question["id"]]
    assert listed[0]["archived"] is True
    assert client.get(f"{PATH}/{question['id']}").json()["archived"] is True
    assert client.get(f"{PATH}/by-code/{question['code']}").status_code == 200
    assert actions(owner_db, question) == ["QUESTION_CREATED", "QUESTION_ARCHIVED"]


def test_an_archived_question_cannot_be_edited_until_it_is_restored(
    client: TestClient, started: tuple[dict[str, Any], dict[str, str]]
) -> None:
    question, headers = started
    archive(client, headers, question)
    save = client.put(
        f"{PATH}/{question['id']}/working-revision",
        json={"content": {}},
        headers={**headers, "If-Match": '"rev-1"'},
    )
    assert (save.status_code, save.json()["error"]["code"]) == (409, "QUESTION_ARCHIVED")
    back = restore(client, headers, question)
    assert back.status_code == 200
    assert back.json()["archived"] is False
    assert [row["id"] for row in client.get(PATH).json()["data"]] == [question["id"]]
    assert client.get(PATH, params={"archived": "true"}).json()["data"] == []
    again = client.put(
        f"{PATH}/{question['id']}/working-revision",
        json={"content": {}},
        headers={**headers, "If-Match": '"rev-1"'},
    )
    assert again.status_code == 200


def test_archiving_twice_changes_nothing_and_is_audited_once(
    client: TestClient,
    owner_db: Database,
    started: tuple[dict[str, Any], dict[str, str]],
) -> None:
    question, headers = started
    assert archive(client, headers, question).status_code == 200
    assert archive(client, headers, question).status_code == 200
    assert restore(client, headers, question).status_code == 200
    assert restore(client, headers, question).status_code == 200
    assert actions(owner_db, question) == [
        "QUESTION_CREATED",
        "QUESTION_ARCHIVED",
        "QUESTION_RESTORED",
    ]


@pytest.mark.parametrize(
    ("who", "status"),
    [("author", 200), ("admin", 200), ("owner", 200), ("editor", 403), ("other", 404)],
)
def test_who_may_archive_and_restore(
    client: TestClient,
    team: dict[str, Member],
    started: tuple[dict[str, Any], dict[str, str]],
    who: str,
    status: int,
) -> None:
    question, _ = started
    headers = sign_in(client, team[who].email)
    assert archive(client, headers, question).status_code == status
    assert restore(client, headers, question).status_code == status


def test_another_coaching_cannot_archive(
    client: TestClient,
    owner_db: Database,
    started: tuple[dict[str, Any], dict[str, str]],
) -> None:
    question, _ = started
    stranger = make_member(owner_db, "ADMIN", coaching_name="Other Coaching")
    headers = sign_in(client, stranger.email)
    assert archive(client, headers, question).status_code == 404
    assert restore(client, headers, question).status_code == 404


def test_the_archived_list_follows_the_same_visibility_rules(
    client: TestClient,
    team: dict[str, Member],
    started: tuple[dict[str, Any], dict[str, str]],
) -> None:
    question, headers = started
    archive(client, headers, question)
    sign_in(client, team["other"].email)
    assert client.get(PATH, params={"archived": "true"}).json()["data"] == []
    sign_in(client, team["admin"].email)
    assert len(client.get(PATH, params={"archived": "true"}).json()["data"]) == 1
