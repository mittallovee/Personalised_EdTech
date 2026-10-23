"""An Idempotency-Key with control characters is a 400, not a database crash (NUL has no text)."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from qbank.core.config import AppEnv, Settings
from qbank.core.db import Database
from qbank.main import create_app
from tests.integration.conftest import Member, MigratedDatabase, make_member, sign_in

INVITATIONS = "/api/v1/members/invitations"

BAD = ["k\x00k", "\x00", "line\nbreak", "tab\there", "bell\x07", "\x7f", "c1\x85"]


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
def owner(owner_db: Database) -> Member:
    return make_member(owner_db, "OWNER")


@pytest.mark.parametrize("bad", BAD, ids=["nul", "only-nul", "newline", "tab", "bell", "del", "c1"])
def test_a_key_with_control_characters_is_a_400_not_a_500(
    client: TestClient, owner: Member, bad: str
) -> None:
    # Sent as bytes: HTTP header text is latin-1, which is how the server reads it back.
    headers = {**sign_in(client, owner.email), "Idempotency-Key": bad.encode("latin-1")}
    body = {"email": "invitee@example.com", "display_name": "Anita", "role": "FACULTY"}

    response = client.post(INVITATIONS, json=body, headers=headers)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "MALFORMED_REQUEST"


def test_keys_in_ordinary_forms_are_still_accepted(client: TestClient, owner: Member) -> None:
    keys = ["invite-anita-1", "7c9e6679-7425-40de-944b-e07fc1f90ae7", "a b", "x" * 200]

    for number, key in enumerate(keys):
        headers = {**sign_in(client, owner.email), "Idempotency-Key": key}
        body = {"email": f"invitee{number}@example.com", "display_name": "Anita", "role": "FACULTY"}
        response = client.post(INVITATIONS, json=body, headers=headers)
        assert response.status_code == 201, key
