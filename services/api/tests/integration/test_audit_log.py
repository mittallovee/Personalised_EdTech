"""M2 PR 2: the audit log API (I-03), permission checks (T13) and isolation (T18)."""

from collections.abc import Iterator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from qbank.core.config import AppEnv, Settings
from qbank.core.db import Database
from qbank.core.ids import new_id
from qbank.core.tenancy import TenantContext
from qbank.main import create_app
from qbank.modules.audit.public import record_event
from qbank.modules.identity.service import create_platform_admin
from tests.integration.conftest import MEMBER_PASSWORD, PLATFORM, MigratedDatabase, make_member


@pytest.fixture
def client(migrated_database: MigratedDatabase) -> Iterator[TestClient]:
    settings = Settings(
        app_env=AppEnv.TEST, database_url=migrated_database.app_url, session_cookie_secure=False
    )
    with TestClient(create_app(settings)) as test_client:
        yield test_client


def sign_in(client: TestClient, email: str) -> None:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": MEMBER_PASSWORD})
    assert response.status_code == 200, response.text


def add_events(owner_db: Database, org_id: UUID, count: int) -> list[str]:
    """``count`` events in separate transactions (so each has its own time), oldest first."""
    ids = []
    for number in range(count):
        entity_id = new_id()
        with owner_db.transaction(TenantContext(organization_id=org_id)) as session:
            record_event(
                session,
                action="TEST_CHANGED",
                entity_type="test",
                entity_id=entity_id,
                organization_id=org_id,
                actor_user_id=None,
                after={"number": number},
            )
        ids.append(str(entity_id))
    return ids


def test_owner_sees_own_coaching_events_newest_first_with_actor_names(
    client: TestClient, owner_db: Database
) -> None:
    owner = make_member(owner_db, "OWNER")
    sign_in(client, owner.email)  # writes USER_SIGNED_IN for the owner

    response = client.get("/api/v1/audit-events")

    assert response.status_code == 200
    events = response.json()["data"]
    assert events[0]["action"] == "USER_SIGNED_IN"
    assert events[0]["actor"] == {
        "user_id": str(owner.user_id),
        "display_name": "Test Owner",
        "is_platform_admin": False,
    }
    times = [event["created_at"] for event in events]
    assert times == sorted(times, reverse=True)


def test_other_coachings_events_are_invisible(client: TestClient, owner_db: Database) -> None:
    admin = make_member(owner_db, "ADMIN")
    other = make_member(owner_db, "OWNER")
    other_ids = add_events(owner_db, other.org_id, 2)
    sign_in(client, admin.email)

    seen = {event["entity_id"] for event in client.get("/api/v1/audit-events").json()["data"]}

    assert seen.isdisjoint(other_ids)
    # Even asking for the other coaching's entity by ID finds nothing.
    response = client.get("/api/v1/audit-events", params={"entity_id": other_ids[0]})
    assert response.json()["data"] == []


@pytest.mark.parametrize("grants", [(), ("QC", "APPROVE", "PUBLISH", "EDIT_OTHERS")])
def test_faculty_may_not_read_the_audit_log(
    client: TestClient, owner_db: Database, grants: tuple[str, ...]
) -> None:
    faculty = make_member(owner_db, "FACULTY", grants=grants)
    sign_in(client, faculty.email)

    response = client.get("/api/v1/audit-events")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"


def test_signed_out_caller_gets_401(client: TestClient) -> None:
    assert client.get("/api/v1/audit-events").status_code == 401


def test_pages_follow_each_other_without_gaps_or_repeats(
    client: TestClient, owner_db: Database
) -> None:
    owner = make_member(owner_db, "OWNER")
    ids = add_events(owner_db, owner.org_id, 5)
    sign_in(client, owner.email)

    seen: list[str] = []
    params: dict[str, str | int] = {"entity_type": "test", "limit": 2}
    for _ in range(5):
        body = client.get("/api/v1/audit-events", params=params).json()
        seen += [event["entity_id"] for event in body["data"]]
        if not body["page"]["has_more"]:
            assert body["page"]["next_cursor"] is None
            break
        params["cursor"] = body["page"]["next_cursor"]

    assert seen == list(reversed(ids))


def test_damaged_cursor_is_400(client: TestClient, owner_db: Database) -> None:
    owner = make_member(owner_db, "OWNER")
    sign_in(client, owner.email)

    response = client.get("/api/v1/audit-events", params={"cursor": "garbage!"})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "MALFORMED_REQUEST"


def test_platform_admin_not_acting_sees_only_platform_level_events(
    client: TestClient, owner_db: Database
) -> None:
    coaching = make_member(owner_db, "OWNER")
    coaching_ids = add_events(owner_db, coaching.org_id, 1)
    platform_entity = new_id()
    with owner_db.transaction(PLATFORM) as session:
        record_event(
            session,
            action="TEST_PLATFORM_CHANGED",
            entity_type="test",
            entity_id=platform_entity,
            organization_id=None,
            actor_user_id=None,
        )
    email = f"platform-{new_id().hex[:8]}@example.com"
    create_platform_admin(owner_db, email, "Platform Admin", MEMBER_PASSWORD)
    sign_in(client, email)

    seen = {
        event["entity_id"]
        for event in client.get("/api/v1/audit-events", params={"entity_type": "test"}).json()[
            "data"
        ]
    }

    assert str(platform_entity) in seen
    assert seen.isdisjoint(coaching_ids)
