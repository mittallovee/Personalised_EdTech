"""M2 PR 3b: rename with If-Match (T17), suspend/reactivate (A-07, T21), acting in (A-06)."""

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
from tests.integration.conftest import (
    MigratedDatabase,
    make_member,
    new_coaching,
    platform_admin,
    sign_in,
)

COACHINGS = "/api/v1/platform/organizations"


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
def admin_headers(client: TestClient, owner_db: Database) -> dict[str, str]:
    return sign_in(client, platform_admin(owner_db))


def create(client: TestClient, headers: dict[str, str], name: str = "Sharma Classes") -> str:
    response = client.post(COACHINGS, json=new_coaching(name), headers=headers)
    assert response.status_code == 201, response.text
    org_id: str = response.json()["organization"]["id"]
    return org_id


def actions(owner_db: Database, org_id: str) -> list[tuple[str, Any, Any]]:
    with owner_db.transaction(TenantContext(organization_id=UUID(org_id))) as session:
        events = session.scalars(
            select(AuditEvent)
            .where(AuditEvent.organization_id == org_id)
            .order_by(AuditEvent.created_at, AuditEvent.id)
        ).all()
        return [(event.action, event.before, event.after) for event in events]


# --- Rename / time zone with If-Match (style guide §6, T17) -------------------------------------


def test_rename_needs_the_current_etag(
    client: TestClient, admin_headers: dict[str, str], owner_db: Database
) -> None:
    org_id = create(client, admin_headers)
    read = client.get(f"{COACHINGS}/{org_id}")
    assert read.headers["ETag"] == '"rev-1"'

    missing = client.patch(
        f"{COACHINGS}/{org_id}", json={"display_name": "New"}, headers=admin_headers
    )
    renamed = client.patch(
        f"{COACHINGS}/{org_id}",
        json={"display_name": "Sharma Academy", "timezone": "Asia/Dubai"},
        headers={**admin_headers, "If-Match": read.headers["ETag"]},
    )
    stale = client.patch(
        f"{COACHINGS}/{org_id}",
        json={"display_name": "Overwrite"},
        headers={**admin_headers, "If-Match": read.headers["ETag"]},
    )

    assert (missing.status_code, missing.json()["error"]["code"]) == (428, "IF_MATCH_REQUIRED")
    assert renamed.status_code == 200
    assert renamed.headers["ETag"] == '"rev-2"'
    assert renamed.json()["display_name"] == "Sharma Academy"
    assert renamed.json()["timezone"] == "Asia/Dubai"
    assert (stale.status_code, stale.json()["error"]["code"]) == (412, "REVISION_STALE")
    assert stale.json()["error"]["details"] == {"current_etag": '"rev-2"'}
    assert client.get(f"{COACHINGS}/{org_id}").json()["display_name"] == "Sharma Academy"
    updates = [event for event in actions(owner_db, org_id) if event[0] == "COACHING_UPDATED"]
    assert len(updates) == 1
    _, before, after = updates[0]
    assert (before["display_name"], after["display_name"]) == ("Sharma Classes", "Sharma Academy")


def test_rename_to_the_same_values_changes_nothing(
    client: TestClient, admin_headers: dict[str, str], owner_db: Database
) -> None:
    org_id = create(client, admin_headers)

    response = client.patch(
        f"{COACHINGS}/{org_id}",
        json={"display_name": "Sharma Classes"},
        headers={**admin_headers, "If-Match": '"rev-1"'},
    )

    assert response.headers["ETag"] == '"rev-1"'
    assert "COACHING_UPDATED" not in [event[0] for event in actions(owner_db, org_id)]


@pytest.mark.parametrize(
    "body", [{}, {"timezone": "Mars/Olympus"}, {"display_name": " "}], ids=["empty", "tz", "name"]
)
def test_invalid_change_is_400(
    client: TestClient, admin_headers: dict[str, str], body: dict[str, str]
) -> None:
    org_id = create(client, admin_headers)

    response = client.patch(
        f"{COACHINGS}/{org_id}", json=body, headers={**admin_headers, "If-Match": '"rev-1"'}
    )

    assert response.status_code == 400


def test_unknown_coaching_is_404(client: TestClient, admin_headers: dict[str, str]) -> None:
    unknown = f"{COACHINGS}/019a0000-0000-7000-8000-000000000000"
    patched = client.patch(
        unknown, json={"display_name": "X"}, headers={**admin_headers, "If-Match": '"rev-1"'}
    )
    suspended = client.post(f"{unknown}/suspend", headers=admin_headers)
    assert (patched.status_code, suspended.status_code) == (404, 404)


@pytest.mark.parametrize("role", ["OWNER", "ADMIN", "FACULTY"])
def test_coaching_members_cannot_rename_or_suspend(
    client: TestClient, owner_db: Database, role: str
) -> None:
    member = make_member(owner_db, role)
    headers = sign_in(client, member.email)
    own = f"{COACHINGS}/{member.org_id}"

    responses = [
        client.patch(
            own, json={"display_name": "Mine"}, headers={**headers, "If-Match": '"rev-1"'}
        ),
        client.post(f"{own}/suspend", headers=headers),
        client.post(f"{own}/reactivate", headers=headers),
        client.post(
            "/api/v1/platform/acting-organization",
            json={"organization_id": str(member.org_id)},
            headers=headers,
        ),
    ]

    assert [response.status_code for response in responses] == [403, 403, 403, 403]


# --- Suspend / reactivate (A-07, T21) -----------------------------------------------------------


def test_suspension_signs_members_out_and_reactivation_lets_them_back(
    settings: Settings, client: TestClient, admin_headers: dict[str, str], owner_db: Database
) -> None:
    member = make_member(owner_db, "FACULTY")
    with TestClient(create_app(settings)) as faculty:
        sign_in(faculty, member.email)
        assert faculty.get("/api/v1/me").status_code == 200

        suspended = client.post(f"{COACHINGS}/{member.org_id}/suspend", headers=admin_headers)
        again = client.post(f"{COACHINGS}/{member.org_id}/suspend", headers=admin_headers)

        assert suspended.json()["status"] == "SUSPENDED"
        assert again.json()["revision"] == suspended.json()["revision"]  # no second change
        assert faculty.get("/api/v1/me").status_code == 401  # on the very next request
        login = faculty.post(
            "/api/v1/auth/login",
            json={"email": member.email, "password": "correct horse battery staple"},
            headers={"Origin": "http://localhost:3000"},
        )
        assert login.status_code == 401

        reactivated = client.post(f"{COACHINGS}/{member.org_id}/reactivate", headers=admin_headers)

        assert reactivated.json()["status"] == "ACTIVE"
        sign_in(faculty, member.email)
        assert faculty.get("/api/v1/me").status_code == 200
    status_events = [
        (name, before["status"], after["status"])
        for name, before, after in actions(owner_db, str(member.org_id))
        if name.startswith("COACHING_")
    ]
    assert status_events == [
        ("COACHING_SUSPENDED", "ACTIVE", "SUSPENDED"),
        ("COACHING_REACTIVATED", "SUSPENDED", "ACTIVE"),
    ]


# --- Acting in a coaching (A-06) ----------------------------------------------------------------


def test_platform_admin_acts_in_a_coaching_and_stops(
    client: TestClient, admin_headers: dict[str, str], owner_db: Database
) -> None:
    org_id = create(client, admin_headers, "Gupta Tutorials")

    started = client.post(
        "/api/v1/platform/acting-organization",
        json={"organization_id": org_id},
        headers=admin_headers,
    )
    me = client.get("/api/v1/me").json()
    log = client.get("/api/v1/audit-events").json()["data"]

    assert started.status_code == 204
    assert (me["acting_organization_id"], me["acting_organization_name"]) == (
        org_id,
        "Gupta Tutorials",
    )
    # While acting, the audit log is that coaching's (its creation and the acting itself).
    assert {"COACHING_CREATED", "PLATFORM_ACTING_STARTED"} <= {event["action"] for event in log}
    assert all(event["entity_id"] == org_id for event in log)

    stopped = client.delete("/api/v1/platform/acting-organization", headers=admin_headers)
    me = client.get("/api/v1/me").json()

    assert stopped.status_code == 204
    assert me["acting_organization_id"] is None
    assert [event[0] for event in actions(owner_db, org_id)][-2:] == [
        "PLATFORM_ACTING_STARTED",
        "PLATFORM_ACTING_STOPPED",
    ]


def test_switching_coachings_records_stop_and_start(
    client: TestClient, admin_headers: dict[str, str], owner_db: Database
) -> None:
    first, second = create(client, admin_headers, "First"), create(client, admin_headers, "Second")
    act = "/api/v1/platform/acting-organization"

    client.post(act, json={"organization_id": first}, headers=admin_headers)
    client.post(act, json={"organization_id": first}, headers=admin_headers)  # already there
    client.post(act, json={"organization_id": second}, headers=admin_headers)

    assert [event[0] for event in actions(owner_db, first)].count("PLATFORM_ACTING_STARTED") == 1
    assert [event[0] for event in actions(owner_db, first)][-1] == "PLATFORM_ACTING_STOPPED"
    assert [event[0] for event in actions(owner_db, second)][-1] == "PLATFORM_ACTING_STARTED"
    assert client.get("/api/v1/me").json()["acting_organization_id"] == second


def test_acting_applies_only_to_that_sign_in_session(
    settings: Settings, client: TestClient, owner_db: Database
) -> None:
    email = platform_admin(owner_db)
    headers = sign_in(client, email)
    org_id = create(client, headers)
    client.post(
        "/api/v1/platform/acting-organization", json={"organization_id": org_id}, headers=headers
    )

    with TestClient(create_app(settings)) as other_device:
        sign_in(other_device, email)
        assert other_device.get("/api/v1/me").json()["acting_organization_id"] is None


def test_acting_in_an_unknown_coaching_is_404(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    response = client.post(
        "/api/v1/platform/acting-organization",
        json={"organization_id": "019a0000-0000-7000-8000-000000000000"},
        headers=admin_headers,
    )

    assert response.status_code == 404
    assert client.get("/api/v1/me").json()["acting_organization_id"] is None
