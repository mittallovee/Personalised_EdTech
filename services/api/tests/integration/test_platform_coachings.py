"""M2 PR 3: platform admins create coachings with their first Owner (A-04, B-05, B-07, ADR-0015)."""

import hashlib
import secrets
import threading
from collections.abc import Iterator
from contextlib import ExitStack
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from qbank.core.config import AppEnv, Settings
from qbank.core.db import Database
from qbank.core.tenancy import TenantContext
from qbank.main import create_app
from qbank.modules.audit.models import AuditEvent
from qbank.modules.identity.models import User
from qbank.modules.identity.service import create_platform_admin
from qbank.modules.organizations.models import Membership, Organization
from tests.integration.conftest import MEMBER_PASSWORD, PLATFORM, MigratedDatabase, make_member

ORIGIN = {"Origin": "http://localhost:3000"}


@pytest.fixture
def settings(migrated_database: MigratedDatabase) -> Settings:
    return Settings(
        app_env=AppEnv.TEST, database_url=migrated_database.app_url, session_cookie_secure=False
    )


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings)) as test_client:
        yield test_client


def sign_in(client: TestClient, email: str) -> dict[str, str]:
    """Sign in; return the headers a change needs (CSRF token and our web app's Origin)."""
    response = client.post(
        "/api/v1/auth/login", json={"email": email, "password": MEMBER_PASSWORD}, headers=ORIGIN
    )
    assert response.status_code == 200, response.text
    return {**ORIGIN, "X-CSRF-Token": response.json()["csrf_token"]}


def platform_admin(owner_db: Database) -> str:
    email = f"platform-{secrets.token_hex(5)}@example.com"
    create_platform_admin(owner_db, email, "Platform Admin", MEMBER_PASSWORD)
    return email


def new_coaching(name: str = "Sharma Classes", email: str | None = None) -> dict[str, Any]:
    email = email or f"owner-{secrets.token_hex(5)}@example.com"
    return {
        "display_name": name,
        "timezone": "Asia/Kolkata",
        "owner": {"email": email, "display_name": "Priya Sharma"},
    }


def test_platform_admin_creates_a_coaching_with_an_invited_owner(
    client: TestClient, owner_db: Database
) -> None:
    headers = sign_in(client, platform_admin(owner_db))
    local = f"Priya.{secrets.token_hex(4)}"
    body = new_coaching(email=f"  {local}@Example.com ")

    response = client.post("/api/v1/platform/organizations", json=body, headers=headers)

    assert response.status_code == 201, response.text
    created = response.json()
    org_id = created["organization"]["id"]
    assert response.headers["Location"] == f"/api/v1/platform/organizations/{org_id}"
    assert response.headers["Cache-Control"] == "no-store"
    assert created["organization"]["display_name"] == "Sharma Classes"
    assert created["organization"]["status"] == "ACTIVE"
    email = f"{local}@example.com".lower()  # stored and shown in one normal form
    assert created["owner"]["email"] == email
    token = created["activation"]["token"]
    expires_at = datetime.fromisoformat(created["activation"]["expires_at"])
    assert timedelta(hours=23) < expires_at - datetime.now(UTC) <= timedelta(hours=24)

    with owner_db.transaction(TenantContext(organization_id=org_id)) as session:
        owner = session.get(User, created["owner"]["user_id"])
        membership = session.get(Membership, created["owner"]["membership_id"])
        links = session.execute(
            text("SELECT token_hash, purpose, used_at FROM account_links WHERE user_id = :u"),
            {"u": created["owner"]["user_id"]},
        ).all()
        reserved = session.scalar(
            text("SELECT user_id FROM account_emails WHERE email = :e"),
            {"e": email},
        )
        events = session.scalars(select(AuditEvent).where(AuditEvent.entity_id == org_id)).all()
    assert owner is not None and owner.status == "INVITED"
    assert membership is not None and (membership.role, membership.status) == ("OWNER", "ACTIVE")
    assert str(reserved) == created["owner"]["user_id"]
    # Only the hash of the token is stored.
    assert [(row.purpose, row.used_at) for row in links] == [("ACTIVATION", None)]
    assert links[0].token_hash == hashlib.sha256(token.encode()).hexdigest()
    assert [(event.action, event.actor_is_platform) for event in events] == [
        ("COACHING_CREATED", True)
    ]
    assert token not in str(events[0].after)


def test_coaching_list_and_detail(client: TestClient, owner_db: Database) -> None:
    headers = sign_in(client, platform_admin(owner_db))
    ids = [
        client.post(
            "/api/v1/platform/organizations", json=new_coaching(f"Coaching {n}"), headers=headers
        ).json()["organization"]["id"]
        for n in range(3)
    ]

    first = client.get("/api/v1/platform/organizations", params={"limit": 2}).json()
    rest = client.get(
        "/api/v1/platform/organizations", params={"cursor": first["page"]["next_cursor"]}
    ).json()
    listed = [org["id"] for org in first["data"] + rest["data"]]

    assert listed.index(ids[2]) < listed.index(ids[1]) < listed.index(ids[0])  # newest first
    assert len(listed) == len(set(listed))
    detail = client.get(f"/api/v1/platform/organizations/{ids[0]}")
    assert detail.json()["display_name"] == "Coaching 0"
    missing = client.get("/api/v1/platform/organizations/019a0000-0000-7000-8000-000000000000")
    assert missing.status_code == 404


@pytest.mark.parametrize("role", ["OWNER", "ADMIN", "FACULTY"])
def test_coaching_members_cannot_use_the_platform_api(
    client: TestClient, owner_db: Database, role: str
) -> None:
    headers = sign_in(client, make_member(owner_db, role).email)

    created = client.post("/api/v1/platform/organizations", json=new_coaching(), headers=headers)
    listed = client.get("/api/v1/platform/organizations")

    assert (created.status_code, listed.status_code) == (403, 403)
    assert created.json()["error"]["code"] == "PERMISSION_DENIED"


def test_signed_out_caller_gets_401(client: TestClient) -> None:
    assert client.get("/api/v1/platform/organizations").status_code == 401


@pytest.mark.parametrize(
    "change",
    [
        {"timezone": "Mars/Olympus"},
        {"display_name": "   "},
        {"owner": {"email": "not-an-email", "display_name": "X"}},
    ],
)
def test_invalid_input_is_400(
    client: TestClient, owner_db: Database, change: dict[str, Any]
) -> None:
    headers = sign_in(client, platform_admin(owner_db))

    response = client.post(
        "/api/v1/platform/organizations", json={**new_coaching(), **change}, headers=headers
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "MALFORMED_REQUEST"


def test_email_of_an_existing_account_is_refused_and_nothing_is_left_behind(
    client: TestClient, owner_db: Database
) -> None:
    existing = make_member(owner_db, "FACULTY")
    headers = sign_in(client, platform_admin(owner_db))
    name = f"Duplicate {secrets.token_hex(4)}"

    response = client.post(
        "/api/v1/platform/organizations",
        json=new_coaching(name, email=f"  {existing.email.upper()} "),
        headers=headers,
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EMAIL_TAKEN"
    with owner_db.transaction(PLATFORM) as session:
        assert (
            session.scalars(select(Organization).where(Organization.display_name == name)).all()
            == []
        )


def test_concurrent_invitations_of_one_email_create_one_account(
    settings: Settings, owner_db: Database
) -> None:
    """T16: two coachings inviting the same person at the same moment: exactly one succeeds."""
    admin_email = platform_admin(owner_db)
    email = f"race-{secrets.token_hex(5)}@example.com"
    statuses: list[int] = []
    start = threading.Barrier(2)

    with ExitStack() as stack:  # two separate apps, like two API processes
        clients = [stack.enter_context(TestClient(create_app(settings))) for _ in range(2)]
        headers = [sign_in(each, admin_email) for each in clients]
        # FastAPI prepares routes lazily on first use, which is not thread-safe across apps that
        # share routers (the server matches routes on one thread, so only this test can race).
        for each in clients:
            assert each.get("/api/v1/platform/organizations").status_code == 200

        def create(index: int) -> None:
            start.wait()
            response = clients[index].post(
                "/api/v1/platform/organizations",
                json=new_coaching(f"Race {index}", email=email.upper() if index else email),
                headers=headers[index],
            )
            statuses.append(response.status_code)

        threads = [threading.Thread(target=create, args=(i,)) for i in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

    assert sorted(statuses) == [201, 409]
    with owner_db.transaction(PLATFORM) as session:
        owners = session.scalar(
            text("SELECT count(*) FROM account_emails WHERE email = :e"), {"e": email}
        )
    assert owners == 1


def test_retry_with_the_same_key_returns_the_same_coaching_with_a_fresh_link(
    client: TestClient, owner_db: Database
) -> None:
    """T22: a lost response costs nothing: no second coaching, no EMAIL_TAKEN."""
    headers = {**sign_in(client, platform_admin(owner_db)), "Idempotency-Key": secrets.token_hex(8)}
    body = new_coaching(f"Retry {secrets.token_hex(4)}")

    first = client.post("/api/v1/platform/organizations", json=body, headers=headers).json()
    second = client.post("/api/v1/platform/organizations", json=body, headers=headers)

    assert second.status_code == 201
    retried = second.json()
    assert retried["organization"]["id"] == first["organization"]["id"]
    assert retried["owner"]["user_id"] == first["owner"]["user_id"]
    assert retried["activation"]["token"] != first["activation"]["token"]
    org_id = first["organization"]["id"]
    with owner_db.transaction(TenantContext(organization_id=org_id)) as session:
        links = session.execute(
            text(
                "SELECT token_hash, revoked_at FROM account_links"
                " WHERE organization_id = :org ORDER BY created_at"
            ),
            {"org": org_id},
        ).all()
        actions = session.scalars(
            select(AuditEvent.action).where(AuditEvent.organization_id == org_id)
        ).all()
        named = session.scalars(
            select(Organization.id).where(Organization.display_name == body["display_name"])
        ).all()
    digest = hashlib.sha256(retried["activation"]["token"].encode()).hexdigest()
    assert [(link.token_hash == digest, link.revoked_at is None) for link in links] == [
        (False, False),  # the first, never-seen link no longer works
        (True, True),
    ]
    assert sorted(actions) == ["ACTIVATION_LINK_REISSUED", "COACHING_CREATED"]
    assert len(named) == 1


def test_same_key_with_a_different_body_is_409(client: TestClient, owner_db: Database) -> None:
    headers = {**sign_in(client, platform_admin(owner_db)), "Idempotency-Key": secrets.token_hex(8)}
    client.post("/api/v1/platform/organizations", json=new_coaching("One"), headers=headers)

    response = client.post(
        "/api/v1/platform/organizations", json=new_coaching("Another"), headers=headers
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "IDEMPOTENCY_KEY_REUSED"


def test_platform_admin_email_is_reserved_too(client: TestClient, owner_db: Database) -> None:
    taken = platform_admin(owner_db)
    headers = sign_in(client, platform_admin(owner_db))

    response = client.post(
        "/api/v1/platform/organizations", json=new_coaching(email=taken), headers=headers
    )

    assert response.json()["error"]["code"] == "EMAIL_TAKEN"


# --- Database guarantees behind the endpoint (ADR-0005, ADR-0015) -------------------------------


def test_runtime_role_cannot_read_token_hashes_or_emails(db: Database) -> None:
    for query in ("SELECT token_hash FROM account_links", "SELECT email FROM account_emails"):
        with pytest.raises(DBAPIError, match="permission denied"), db.transaction(PLATFORM) as s:
            s.execute(text(query))


def test_email_can_only_be_reserved_for_a_new_invited_account(
    db: Database, owner_db: Database
) -> None:
    active = make_member(owner_db, "FACULTY")
    with (
        pytest.raises(DBAPIError, match="only for a new invited account"),
        db.transaction(TenantContext(organization_id=active.org_id, user_id=active.user_id)) as s,
    ):
        s.execute(
            text("SELECT auth_reserve_email('someone-else@example.com', :u)"),
            {"u": active.user_id},
        )


def test_email_cannot_be_reserved_without_a_coaching_or_platform_context(db: Database) -> None:
    with (
        pytest.raises(DBAPIError, match="needs a coaching or platform context"),
        db.transaction(TenantContext()) as session,
    ):
        session.execute(text("SELECT auth_reserve_email('x@example.com', gen_random_uuid())"))
