"""M3 PR 3b-2: the question routes (D-11, D-12; tests T27 and T11 for these routes).

Create, read by id and by code, and the list. Autosave, checkpoints and archive come later.
"""

import copy
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from qbank.core.config import AppEnv, Settings
from qbank.core.db import Database
from qbank.main import create_app
from tests.integration.conftest import (
    Member,
    MigratedDatabase,
    make_member,
    platform_admin,
    sign_in,
)
from tests.integration.question_support import Catalogue, ready_for, seed_catalogue
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
        "admin": make_member(owner_db, "ADMIN", org_id=owner.org_id),
        "author": make_member(owner_db, "FACULTY", org_id=owner.org_id),
        "other": make_member(owner_db, "FACULTY", org_id=owner.org_id),
        "editor": make_member(owner_db, "FACULTY", org_id=owner.org_id, grants=["EDIT_OTHERS"]),
    }


@pytest.fixture
def catalogue(owner_db: Database, team: dict[str, Member]) -> Catalogue:
    return seed_catalogue(owner_db, team["owner"].org_id)


def as_member(client: TestClient, member: Member) -> dict[str, str]:
    """Sign in as ``member`` (the client keeps the session cookie of the latest sign-in)."""
    return sign_in(client, member.email)


def create(
    client: TestClient, headers: dict[str, str], content: dict[str, Any], **extra: str
) -> dict[str, Any]:
    response = client.post(PATH, json={"content": content}, headers={**headers, **extra})
    assert response.status_code == 201, response.text
    return response.json()


# --- create --------------------------------------------------------------------------------------


def test_creating_returns_the_question_its_code_and_the_findings(
    client: TestClient, team: dict[str, Member]
) -> None:
    headers = as_member(client, team["author"])
    response = client.post(PATH, json={"content": copy.deepcopy(DRAFT)}, headers=headers)
    assert response.status_code == 201
    body = response.json()
    assert len(body["code"]) == 8
    assert body["version_number"] == 1
    assert body["revision"] == 1
    assert body["archived"] is False
    assert body["created_by"] == str(team["author"].user_id)
    assert body["content"] == DRAFT
    assert [f["code"] for f in body["findings"]] == [
        "METADATA_MISSING",
        "OPTIONS_MISSING",
        "ANSWER_MISSING",
    ]
    assert body["findings"][0] == {
        "path": "metadata",
        "code": "METADATA_MISSING",
        "level": "incomplete",
        "message": body["findings"][0]["message"],
    }
    assert response.headers["Location"] == f"{PATH}/{body['id']}"
    assert response.headers["ETag"] == '"rev-1"'


def test_a_ready_question_has_no_findings(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    body = create(client, as_member(client, team["author"]), ready_for(catalogue))
    assert body["findings"] == []


def test_a_retry_with_the_same_key_gives_the_same_question(
    client: TestClient, team: dict[str, Member]
) -> None:
    headers = as_member(client, team["author"])
    first = create(client, headers, copy.deepcopy(READY), **{"Idempotency-Key": "abc"})
    again = create(client, headers, copy.deepcopy(READY), **{"Idempotency-Key": "abc"})
    assert again["id"] == first["id"]
    assert again["code"] == first["code"]
    reused = client.post(
        PATH,
        json={"content": copy.deepcopy(DRAFT)},
        headers={**headers, "Idempotency-Key": "abc"},
    )
    assert reused.status_code == 409
    assert reused.json()["error"]["code"] == "IDEMPOTENCY_KEY_REUSED"


def test_content_must_be_an_object_and_nothing_else_is_accepted(
    client: TestClient, team: dict[str, Member]
) -> None:
    headers = as_member(client, team["author"])
    for body in ({}, {"content": "text"}, {"content": [1]}, {"content": {}, "extra": 1}):
        response = client.post(PATH, json=body, headers=headers)
        assert response.status_code == 400, body


def test_oversize_content_is_refused_with_its_own_code(
    client: TestClient, team: dict[str, Member]
) -> None:
    headers = as_member(client, team["author"])
    huge = {"stem": [{"kind": "paragraph", "text": "x" * 270_000}]}
    response = client.post(PATH, json={"content": huge}, headers=headers)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "CONTENT_TOO_LARGE"


def test_you_must_be_signed_in_and_in_a_coaching(
    client: TestClient, team: dict[str, Member], owner_db: Database
) -> None:
    assert client.get(PATH).status_code == 401
    admin = platform_admin(owner_db)
    headers = sign_in(client, admin)
    response = client.post(PATH, json={"content": {}}, headers=headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"


# --- read ----------------------------------------------------------------------------------------


def test_reading_by_id_and_by_code_gives_the_same_question(
    client: TestClient, team: dict[str, Member]
) -> None:
    headers = as_member(client, team["author"])
    made = create(client, headers, copy.deepcopy(DRAFT))
    by_id = client.get(f"{PATH}/{made['id']}")
    assert by_id.status_code == 200
    assert by_id.headers["ETag"] == '"rev-1"'
    assert by_id.json() == made
    typed = f"{made['code'][:4].lower()}-{made['code'][4:].lower()}"
    assert client.get(f"{PATH}/by-code/{typed}").json() == made


def test_unknown_and_malformed_codes_and_ids(client: TestClient, team: dict[str, Member]) -> None:
    as_member(client, team["author"])
    assert client.get(f"{PATH}/by-code/00000000").status_code == 404
    short = client.get(f"{PATH}/by-code/short")
    assert (short.status_code, short.json()["error"]["code"]) == (422, "INVALID_CODE")
    assert client.get(f"{PATH}/00000000-0000-4000-8000-000000000000").status_code == 404
    assert client.get(f"{PATH}/not-a-uuid").status_code == 400


@pytest.mark.parametrize(
    ("who", "status"),
    [("author", 200), ("admin", 200), ("owner", 200), ("editor", 200), ("other", 404)],
)
def test_who_may_open_a_draft(
    client: TestClient, team: dict[str, Member], who: str, status: int
) -> None:
    made = create(client, as_member(client, team["author"]), copy.deepcopy(READY))
    as_member(client, team[who])
    assert client.get(f"{PATH}/{made['id']}").status_code == status
    assert client.get(f"{PATH}/by-code/{made['code']}").status_code == status


def test_another_coaching_cannot_open_it(
    client: TestClient, team: dict[str, Member], owner_db: Database
) -> None:
    made = create(client, as_member(client, team["author"]), copy.deepcopy(READY))
    stranger = make_member(owner_db, "ADMIN", coaching_name="Other Coaching")
    as_member(client, stranger)
    assert client.get(f"{PATH}/{made['id']}").status_code == 404
    assert client.get(f"{PATH}/by-code/{made['code']}").status_code == 404
    assert client.get(PATH).json()["data"] == []


# --- list ----------------------------------------------------------------------------------------


def test_the_list_shows_your_own_questions_newest_first(
    client: TestClient, team: dict[str, Member]
) -> None:
    mine = as_member(client, team["author"])
    first = create(client, mine, copy.deepcopy(DRAFT))
    second = create(client, mine, copy.deepcopy(READY))
    create(client, as_member(client, team["other"]), copy.deepcopy(READY))
    as_member(client, team["author"])
    page = client.get(PATH).json()
    assert [row["id"] for row in page["data"]] == [second["id"], first["id"]]
    assert page["page"] == {"next_cursor": None, "has_more": False}
    row = page["data"][1]
    assert row["code"] == first["code"]
    assert row["question_type"] == "SCQ"
    assert row["finding_counts"] == {"error": 0, "incomplete": 3, "warning": 0}
    assert "content" not in row


def test_admins_and_editors_see_everyones_and_can_ask_for_their_own(
    client: TestClient, team: dict[str, Member]
) -> None:
    create(client, as_member(client, team["author"]), copy.deepcopy(READY))
    create(client, as_member(client, team["other"]), copy.deepcopy(READY))
    as_member(client, team["admin"])
    assert len(client.get(PATH).json()["data"]) == 2
    assert client.get(PATH, params={"mine": "true"}).json()["data"] == []
    as_member(client, team["editor"])
    assert len(client.get(PATH).json()["data"]) == 2


def test_the_list_pages_with_a_cursor(client: TestClient, team: dict[str, Member]) -> None:
    headers = as_member(client, team["author"])
    made = [create(client, headers, copy.deepcopy(READY))["id"] for _ in range(3)]
    first = client.get(PATH, params={"limit": 2}).json()
    assert [row["id"] for row in first["data"]] == [made[2], made[1]]
    assert first["page"]["has_more"] is True
    second = client.get(PATH, params={"limit": 2, "cursor": first["page"]["next_cursor"]}).json()
    assert [row["id"] for row in second["data"]] == [made[0]]
    assert second["page"] == {"next_cursor": None, "has_more": False}
    assert client.get(PATH, params={"cursor": "garbage"}).status_code == 400
    assert client.get(PATH, params={"limit": 0}).status_code == 400
