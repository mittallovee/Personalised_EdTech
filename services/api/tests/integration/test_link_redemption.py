"""M2 PR 4: activating an account or resetting a password with a one-time link (B-05, B-06, T16)."""

from collections.abc import Iterator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from qbank.core.config import AppEnv, Settings
from qbank.core.db import Database
from qbank.core.tenancy import TenantContext
from qbank.main import create_app
from qbank.modules.audit.models import AuditEvent
from qbank.modules.identity.public import LinkPurpose, issue_account_link
from tests.integration.conftest import (
    MEMBER_PASSWORD,
    ORIGIN,
    Member,
    MigratedDatabase,
    make_member,
    new_coaching,
    platform_admin,
    sign_in,
)

REDEEM = "/api/v1/auth/links/redeem"
NEW_PASSWORD = "a brand new passphrase"


@pytest.fixture
def settings(migrated_database: MigratedDatabase) -> Settings:
    return Settings(
        app_env=AppEnv.TEST, database_url=migrated_database.app_url, session_cookie_secure=False
    )


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings)) as test_client:
        yield test_client


def invite_owner(client: TestClient, owner_db: Database) -> dict[str, object]:
    """Create a coaching through the API; return its response (with the Owner's activation)."""
    with TestClient(client.app) as admin:
        headers = sign_in(admin, platform_admin(owner_db))
        response = admin.post(
            "/api/v1/platform/organizations", json=new_coaching(), headers=headers
        )
    assert response.status_code == 201, response.text
    created: dict[str, object] = response.json()
    return created


def token_of(created: dict[str, object]) -> str:
    token: str = created["activation"]["token"]  # type: ignore[index]
    return token


def redeem(client: TestClient, token: str, password: str = NEW_PASSWORD) -> tuple[int, str]:
    response = client.post(REDEEM, json={"token": token, "password": password}, headers=ORIGIN)
    code = response.json()["error"]["code"] if response.status_code >= 400 else ""
    return response.status_code, code


def reset_link(owner_db: Database, member: Member) -> str:
    context = TenantContext(organization_id=member.org_id, user_id=member.user_id)
    with owner_db.transaction(context) as session:
        link = issue_account_link(
            session,
            organization_id=member.org_id,
            membership_id=member.membership_id,
            user_id=member.user_id,
            purpose=LinkPurpose.RESET,
            created_by=member.user_id,
        )
    return link.token


def test_owner_activates_with_the_link_and_is_signed_in(
    client: TestClient, owner_db: Database
) -> None:
    created = invite_owner(client, owner_db)

    response = client.post(
        REDEEM, json={"token": token_of(created), "password": NEW_PASSWORD}, headers=ORIGIN
    )

    assert response.status_code == 200, response.text
    assert response.json()["user"]["organization"]["role"] == "OWNER"
    me = client.get("/api/v1/me").json()
    assert me["organization"]["display_name"] == "Sharma Classes"
    # From now on the normal sign-in works with the new password.
    email: str = created["owner"]["email"]  # type: ignore[index]
    signed_in = client.post(
        "/api/v1/auth/login", json={"email": email, "password": NEW_PASSWORD}, headers=ORIGIN
    )
    assert signed_in.status_code == 200
    org_id = UUID(created["organization"]["id"])  # type: ignore[index]
    with owner_db.transaction(TenantContext(organization_id=org_id)) as session:
        actions = session.scalars(
            select(AuditEvent.action).where(AuditEvent.organization_id == org_id)
        ).all()
    assert "ACCOUNT_ACTIVATED" in actions


def test_a_link_works_only_once(client: TestClient, owner_db: Database) -> None:
    token = token_of(invite_owner(client, owner_db))

    assert redeem(client, token)[0] == 200
    assert redeem(client, token, "another passphrase!") == (401, "LINK_INVALID")


def test_expired_link_is_refused(client: TestClient, owner_db: Database) -> None:
    created = invite_owner(client, owner_db)
    org_id = UUID(created["organization"]["id"])  # type: ignore[index]
    with owner_db.transaction(TenantContext(organization_id=org_id)) as session:
        session.execute(
            text(
                "UPDATE account_links SET expires_at = now() - interval '1 second'"
                " WHERE organization_id = :org"
            ),
            {"org": org_id},
        )

    assert redeem(client, token_of(created)) == (401, "LINK_INVALID")


def test_unknown_link_gets_the_same_answer(client: TestClient) -> None:
    assert redeem(client, "x" * 43) == (401, "LINK_INVALID")


def test_link_of_a_removed_member_is_refused(client: TestClient, owner_db: Database) -> None:
    created = invite_owner(client, owner_db)
    org_id = UUID(created["organization"]["id"])  # type: ignore[index]
    with owner_db.transaction(TenantContext(organization_id=org_id)) as session:
        session.execute(
            text("UPDATE memberships SET status = 'REMOVED' WHERE organization_id = :org"),
            {"org": org_id},
        )

    assert redeem(client, token_of(created)) == (401, "LINK_INVALID")


def test_link_does_not_work_while_the_coaching_is_suspended(
    client: TestClient, owner_db: Database
) -> None:
    created = invite_owner(client, owner_db)
    org_id = UUID(created["organization"]["id"])  # type: ignore[index]
    with owner_db.transaction(TenantContext(is_platform=True)) as session:
        session.execute(
            text("UPDATE organizations SET status = 'SUSPENDED' WHERE id = :org"), {"org": org_id}
        )

    assert redeem(client, token_of(created)) == (401, "LINK_INVALID")


def test_a_reset_sets_the_new_password_and_ends_other_sessions(
    settings: Settings, client: TestClient, owner_db: Database
) -> None:
    member = make_member(owner_db, "FACULTY")
    with TestClient(create_app(settings)) as other_device:
        sign_in(other_device, member.email)
        token = reset_link(owner_db, member)

        assert redeem(client, token)[0] == 200

        assert other_device.get("/api/v1/me").status_code == 401  # the old session ended
    assert client.get("/api/v1/me").status_code == 200  # the new one works
    old = client.post(
        "/api/v1/auth/login",
        json={"email": member.email, "password": MEMBER_PASSWORD},
        headers=ORIGIN,
    )
    assert old.status_code == 401


def test_reset_link_cannot_activate_an_invited_account(
    client: TestClient, owner_db: Database
) -> None:
    """Purpose matters: a reset link is only for an account that is already active."""
    member = make_member(owner_db, "FACULTY")
    token = reset_link(owner_db, member)
    with owner_db.transaction(TenantContext(organization_id=member.org_id)) as session:
        session.execute(
            text("UPDATE users SET status = 'INVITED' WHERE id = :u"), {"u": member.user_id}
        )

    assert redeem(client, token) == (401, "LINK_INVALID")


def test_short_password_is_400(client: TestClient, owner_db: Database) -> None:
    token = token_of(invite_owner(client, owner_db))

    status, code = redeem(client, token, "short")

    assert (status, code) == (400, "MALFORMED_REQUEST")
    assert redeem(client, token)[0] == 200  # the link was not used up


def test_redemption_from_another_website_is_refused(client: TestClient, owner_db: Database) -> None:
    token = token_of(invite_owner(client, owner_db))

    response = client.post(
        REDEEM,
        json={"token": token, "password": NEW_PASSWORD},
        headers={"Origin": "https://evil.example"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ORIGIN_NOT_ALLOWED"


def test_guessing_is_rate_limited(settings: Settings, owner_db: Database) -> None:
    limited = settings.model_copy(update={"login_attempts_per_ip": 3})
    with TestClient(create_app(limited)) as client:
        statuses = [redeem(client, f"guess-{n:040d}")[0] for n in range(4)]

    assert statuses == [401, 401, 401, 429]
