"""M1 exit tests T5-T7: sign-in, sessions, CSRF and sign-out (B-01, B-10, B-11)."""

import secrets
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update

from qbank.core.config import AppEnv, Settings
from qbank.core.db import Database
from qbank.core.ids import new_id
from qbank.core.security import hash_password
from qbank.core.tenancy import TenantContext
from qbank.main import create_app
from qbank.modules.audit.models import AuditEvent
from qbank.modules.identity.models import PasswordCredential, User, UserSession
from qbank.modules.identity.service import create_platform_admin
from qbank.modules.organizations.models import Membership, Organization
from tests.integration.conftest import MigratedDatabase

PASSWORD = "correct horse battery staple"
PLATFORM = TenantContext(is_platform=True)


@pytest.fixture
def client(migrated_database: MigratedDatabase) -> Iterator[TestClient]:
    settings = Settings(
        app_env=AppEnv.TEST,
        database_url=migrated_database.app_url,
        session_cookie_secure=False,  # TestClient talks plain http
        login_max_failures=3,
    )
    with TestClient(create_app(settings)) as test_client:
        yield test_client


def unique_email(prefix: str) -> str:
    return f"{prefix}-{secrets.token_hex(5)}@example.com"


@dataclass(frozen=True)
class Faculty:
    email: str
    user_id: UUID
    org_id: UUID
    membership_id: UUID


def make_faculty(owner_db: Database) -> Faculty:
    email, user_id, org_id, membership_id = unique_email("faculty"), new_id(), new_id(), new_id()
    with owner_db.transaction(PLATFORM) as session:
        session.add(Organization(id=org_id, display_name="Test Coaching"))
        session.add(User(id=user_id, display_name="Test Faculty"))
        session.flush()
        session.add(
            PasswordCredential(user_id=user_id, email=email, password_hash=hash_password(PASSWORD))
        )
    with owner_db.transaction(TenantContext(organization_id=org_id)) as session:
        session.add(
            Membership(id=membership_id, organization_id=org_id, user_id=user_id, role="FACULTY")
        )
    return Faculty(email, user_id, org_id, membership_id)


def sign_in(client: TestClient, email: str, password: str = PASSWORD) -> str:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    csrf: str = response.json()["csrf_token"]
    return csrf


def test_platform_admin_signs_in_and_sees_themselves(
    client: TestClient, owner_db: Database
) -> None:
    email = unique_email("admin")
    user_id = create_platform_admin(owner_db, email, "Platform Admin", PASSWORD)

    sign_in(client, email.upper())  # email is case-insensitive
    response = client.get("/api/v1/me")

    assert response.status_code == 200
    assert response.json() == {
        "id": str(user_id),
        "display_name": "Platform Admin",
        "is_platform_admin": True,
        "organization": None,
        "acting_organization_id": None,
    }


def test_session_cookie_is_http_only(client: TestClient, owner_db: Database) -> None:
    email = unique_email("admin")
    create_platform_admin(owner_db, email, "Admin", PASSWORD)

    response = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})

    cookies = response.headers.get_list("set-cookie")
    session_cookie = next(c for c in cookies if c.startswith("qb_session="))
    csrf_cookie = next(c for c in cookies if c.startswith("qb_csrf="))
    assert "HttpOnly" in session_cookie
    assert "SameSite=lax" in session_cookie
    assert "HttpOnly" not in csrf_cookie


def test_wrong_password_and_unknown_email_look_identical(
    client: TestClient, owner_db: Database
) -> None:
    email = unique_email("admin")
    create_platform_admin(owner_db, email, "Admin", PASSWORD)

    wrong = client.post("/api/v1/auth/login", json={"email": email, "password": "nope"})
    unknown = client.post(
        "/api/v1/auth/login", json={"email": unique_email("ghost"), "password": "nope"}
    )

    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json()["error"]["message"] == unknown.json()["error"]["message"]
    assert "qb_session" not in client.cookies


def test_account_locks_after_repeated_failures(client: TestClient, owner_db: Database) -> None:
    email = unique_email("admin")
    user_id = create_platform_admin(owner_db, email, "Admin", PASSWORD)

    for _ in range(3):  # login_max_failures=3 in this test app
        client.post("/api/v1/auth/login", json={"email": email, "password": "wrong"})
    locked = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert locked.status_code == 401

    with owner_db.transaction(PLATFORM) as session:  # time passes: lock expires
        session.execute(
            update(PasswordCredential)
            .where(PasswordCredential.user_id == user_id)
            .values(locked_until=datetime.now(UTC) - timedelta(seconds=1))
        )
    sign_in(client, email)
    with owner_db.transaction(PLATFORM) as session:
        assert session.get(PasswordCredential, user_id).failed_attempts == 0  # type: ignore[union-attr]


def test_me_requires_sign_in(client: TestClient) -> None:
    response = client.get("/api/v1/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


def test_logout_requires_csrf_token(client: TestClient, owner_db: Database) -> None:
    email = unique_email("admin")
    create_platform_admin(owner_db, email, "Admin", PASSWORD)
    sign_in(client, email)

    missing = client.post("/api/v1/auth/logout")
    forged = client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": "not-the-token"})

    assert missing.status_code == forged.status_code == 403
    assert missing.json()["error"]["code"] == "CSRF_TOKEN_INVALID"
    assert client.get("/api/v1/me").status_code == 200  # still signed in


def test_logout_revokes_the_session(client: TestClient, owner_db: Database) -> None:
    email = unique_email("admin")
    create_platform_admin(owner_db, email, "Admin", PASSWORD)
    csrf = sign_in(client, email)
    session_cookie = client.cookies["qb_session"]

    response = client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf})

    assert response.status_code == 204
    client.cookies.set("qb_session", session_cookie)  # replaying the old cookie must not work
    assert client.get("/api/v1/me").status_code == 401


def test_expired_session_is_rejected(client: TestClient, owner_db: Database) -> None:
    email = unique_email("admin")
    user_id = create_platform_admin(owner_db, email, "Admin", PASSWORD)
    sign_in(client, email)

    with owner_db.transaction(PLATFORM) as session:
        session.execute(
            update(UserSession)
            .where(UserSession.user_id == user_id)
            .values(idle_expires_at=datetime.now(UTC) - timedelta(seconds=1))
        )

    assert client.get("/api/v1/me").status_code == 401


def test_short_idle_window_is_refreshed_while_the_user_is_active(
    migrated_database: MigratedDatabase, owner_db: Database
) -> None:
    settings = Settings(
        app_env=AppEnv.TEST,
        database_url=migrated_database.app_url,
        session_cookie_secure=False,
        session_idle_minutes=5,  # the shortest allowed idle window
    )
    email = unique_email("admin")
    user_id = create_platform_admin(owner_db, email, "Admin", PASSWORD)
    with TestClient(create_app(settings)) as short_client:
        sign_in(short_client, email)
        # Pretend the sign-in was 4 minutes ago: 1 minute of the idle window is left.
        now = datetime.now(UTC)
        with owner_db.transaction(PLATFORM) as session:
            session.execute(
                update(UserSession)
                .where(UserSession.user_id == user_id)
                .values(
                    last_seen_at=now - timedelta(minutes=4),
                    idle_expires_at=now + timedelta(minutes=1),
                )
            )

        assert short_client.get("/api/v1/me").status_code == 200

    with owner_db.transaction(PLATFORM) as session:
        idle_expires_at = session.scalars(
            select(UserSession.idle_expires_at).where(UserSession.user_id == user_id)
        ).one()
    assert idle_expires_at > now + timedelta(minutes=4)  # activity restarted the 5-minute window


def test_faculty_sees_their_coaching(client: TestClient, owner_db: Database) -> None:
    faculty = make_faculty(owner_db)
    sign_in(client, faculty.email)

    me = client.get("/api/v1/me").json()

    assert me["is_platform_admin"] is False
    assert me["organization"] == {"id": str(faculty.org_id), "role": "FACULTY"}


def test_removed_member_loses_access_immediately(client: TestClient, owner_db: Database) -> None:
    """B-10: removal takes effect on the very next request, without waiting for expiry."""
    faculty = make_faculty(owner_db)
    sign_in(client, faculty.email)

    with owner_db.transaction(TenantContext(organization_id=faculty.org_id)) as session:
        session.execute(
            update(Membership)
            .where(Membership.id == faculty.membership_id)
            .values(status="REMOVED")
        )

    assert client.get("/api/v1/me").status_code == 401


def test_suspended_coaching_cannot_sign_in(client: TestClient, owner_db: Database) -> None:
    faculty = make_faculty(owner_db)
    with owner_db.transaction(PLATFORM) as session:
        session.execute(
            update(Organization).where(Organization.id == faculty.org_id).values(status="SUSPENDED")
        )

    response = client.post(
        "/api/v1/auth/login", json={"email": faculty.email, "password": PASSWORD}
    )

    assert response.status_code == 401


def test_sign_in_and_out_are_audited(client: TestClient, owner_db: Database) -> None:
    faculty = make_faculty(owner_db)
    csrf = sign_in(client, faculty.email)
    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf})

    with owner_db.transaction(TenantContext(organization_id=faculty.org_id)) as session:
        actions = session.scalars(
            select(AuditEvent.action)
            .where(AuditEvent.actor_user_id == faculty.user_id)
            .order_by(AuditEvent.created_at)
        ).all()

    assert actions == ["USER_SIGNED_IN", "USER_SIGNED_OUT"]


def test_users_see_only_their_own_sessions(
    client: TestClient, owner_db: Database, db: Database
) -> None:
    first, second = unique_email("admin"), unique_email("admin")
    first_id = create_platform_admin(owner_db, first, "First", PASSWORD)
    second_id = create_platform_admin(owner_db, second, "Second", PASSWORD)
    sign_in(client, first)
    sign_in(client, second)

    with db.transaction(TenantContext(user_id=second_id)) as session:  # runtime role
        visible = set(session.scalars(select(UserSession.user_id)))

    assert second_id in visible
    assert first_id not in visible
