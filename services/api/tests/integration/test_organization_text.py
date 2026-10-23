"""Names of coachings and members refuse control characters; a NUL would crash the database."""

import secrets
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
    new_coaching,
    platform_admin,
    sign_in,
)

COACHINGS = "/api/v1/platform/organizations"
MEMBERS = "/api/v1/members"

BAD = ["\x00", "a\x00b", "line one\nline two", "tab\there", "bell\x07", "\x7f"]


@pytest.fixture
def client(migrated_database: MigratedDatabase) -> Iterator[TestClient]:
    settings = Settings(
        app_env=AppEnv.TEST,
        database_url=migrated_database.app_url,
        session_cookie_secure=False,
    )
    with TestClient(create_app(settings)) as test_client:
        yield test_client


@pytest.fixture
def platform_headers(client: TestClient, owner_db: Database) -> dict[str, str]:
    return sign_in(client, platform_admin(owner_db))


@pytest.fixture
def owner(owner_db: Database) -> Member:
    return make_member(owner_db, "OWNER")


def refused(response: Any) -> tuple[int, str]:
    return response.status_code, response.json()["error"]["code"]


@pytest.mark.parametrize("bad", BAD, ids=["nul", "nul-inside", "newline", "tab", "bell", "delete"])
def test_coaching_and_owner_names_with_control_characters_are_a_400_not_a_500(
    client: TestClient, platform_headers: dict[str, str], bad: str
) -> None:
    owner = {"email": f"owner-{secrets.token_hex(5)}@example.com", "display_name": bad}
    bodies = [
        new_coaching(name=bad),
        {**new_coaching(), "owner": owner},
    ]

    for body in bodies:
        response = client.post(COACHINGS, json=body, headers=platform_headers)
        assert refused(response) == (400, "MALFORMED_REQUEST"), body


@pytest.mark.parametrize("bad", BAD, ids=["nul", "nul-inside", "newline", "tab", "bell", "delete"])
def test_renaming_a_coaching_with_control_characters_is_a_400_not_a_500(
    client: TestClient, platform_headers: dict[str, str], bad: str
) -> None:
    created = client.post(COACHINGS, json=new_coaching(), headers=platform_headers).json()
    url = f"{COACHINGS}/{created['organization']['id']}"

    response = client.patch(
        url, json={"display_name": bad}, headers={**platform_headers, "If-Match": '"rev-1"'}
    )

    assert refused(response) == (400, "MALFORMED_REQUEST")


@pytest.mark.parametrize("bad", BAD, ids=["nul", "nul-inside", "newline", "tab", "bell", "delete"])
def test_inviting_a_member_with_control_characters_in_the_name_is_a_400_not_a_500(
    client: TestClient, owner: Member, bad: str
) -> None:
    headers = sign_in(client, owner.email)
    email = f"invitee-{secrets.token_hex(5)}@example.com"
    body = {"email": email, "display_name": bad, "role": "FACULTY"}

    response = client.post(f"{MEMBERS}/invitations", json=body, headers=headers)

    assert refused(response) == (400, "MALFORMED_REQUEST")


def test_ordinary_names_in_any_script_are_still_accepted(
    client: TestClient, platform_headers: dict[str, str]
) -> None:
    names = ["Sharma Classes", "शर्मा क्लासेस", "Résumé — naïve", "質量とエネルギー", "a\u200db"]

    for name in names:
        response = client.post(COACHINGS, json=new_coaching(name=name), headers=platform_headers)
        assert response.status_code == 201, name
        assert response.json()["organization"]["display_name"] == name
