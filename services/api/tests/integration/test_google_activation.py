"""M2 PR 8b: activating an invited account with Google instead of a password (B-02, B-04, T19)."""

from collections.abc import Callable, Iterator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from qbank.core.config import AppEnv, Settings
from qbank.core.db import Database
from qbank.core.tenancy import NO_CONTEXT, TenantContext
from qbank.main import create_app
from qbank.modules.audit.models import AuditEvent
from qbank.modules.identity.public import LinkPurpose, issue_account_link
from tests.integration.conftest import (
    MEMBER_PASSWORD,
    ORIGIN,
    PLATFORM,
    MigratedDatabase,
    make_member,
)
from tests.integration.google_support import (
    StandInGoogle,
    assert_signed_out_after_failure,
    call_back,
    identity,
    link_google,
    start,
    start_activation,
    state_of,
)
from tests.integration.test_link_redemption import invite_owner, redeem, reset_link, token_of

pytestmark = pytest.mark.usefixtures("empty_google_tables")


@pytest.fixture
def settings(migrated_database: MigratedDatabase) -> Settings:
    return Settings(
        app_env=AppEnv.TEST,
        database_url=migrated_database.app_url,
        session_cookie_secure=False,
        login_attempts_per_ip=1000,
        login_attempts_per_email=1000,
    )


@pytest.fixture(autouse=True)
def empty_google_tables(owner_db: Database) -> None:
    with owner_db.transaction(PLATFORM) as session:
        session.execute(text("DELETE FROM oauth_flows"))
        session.execute(text("DELETE FROM external_identities"))


@pytest.fixture
def google() -> StandInGoogle:
    return StandInGoogle()


@pytest.fixture
def client(settings: Settings, google: StandInGoogle) -> Iterator[TestClient]:
    app = create_app(settings)
    app.state.google = google
    with TestClient(app) as test_client:
        yield test_client


def org_of(created: dict[str, object]) -> UUID:
    return UUID(created["organization"]["id"])  # type: ignore[index]


def owner_of(created: dict[str, object]) -> UUID:
    return UUID(created["owner"]["user_id"])  # type: ignore[index]


def change(owner_db: Database, org_id: UUID, statement: str) -> None:
    """Change the coaching's rows behind the app's back, as the table owner."""
    with owner_db.transaction(TenantContext(organization_id=org_id, is_platform=True)) as session:
        session.execute(text(statement), {"org": org_id})


def user_status(owner_db: Database, user_id: UUID) -> str:
    with owner_db.transaction(PLATFORM) as session:
        status = session.scalar(text("SELECT status FROM users WHERE id = :id"), {"id": user_id})
    assert status is not None
    return str(status)


def linked_accounts(owner_db: Database) -> int:
    with owner_db.transaction(PLATFORM) as session:
        return int(session.scalar(text("SELECT count(*) FROM external_identities")) or 0)


def open_flows(owner_db: Database) -> int:
    with owner_db.transaction(PLATFORM) as session:
        return int(session.scalar(text("SELECT count(*) FROM oauth_flows")) or 0)


def test_the_owner_activates_with_google_and_needs_no_password(
    client: TestClient, google: StandInGoogle, owner_db: Database
) -> None:
    created = invite_owner(client, owner_db)
    token = token_of(created)
    # The Google account's own email is not the invited one: the link, not the email, is the proof.
    google.accounts["code-1"] = identity("sub-owner", email="priya.personal@gmail.example")

    response = start_activation(client, token)
    assert response.status_code == 200, response.text
    assert call_back(client, state_of(response)) == "/"

    me = client.get("/api/v1/me").json()
    assert me["organization"]["role"] == "OWNER"
    assert user_status(owner_db, owner_of(created)) == "ACTIVE"
    # The link is spent, and there is no password to sign in with.
    assert redeem(client, token) == (401, "LINK_INVALID")
    email: str = created["owner"]["email"]  # type: ignore[index]
    with TestClient(client.app) as other:
        password_login = other.post(
            "/api/v1/auth/login", json={"email": email, "password": MEMBER_PASSWORD}, headers=ORIGIN
        )
        assert password_login.status_code == 401
        # But Google works from now on.
        assert call_back(other, start(other)) == "/"
    with owner_db.transaction(TenantContext(organization_id=org_of(created))) as session:
        events = session.scalars(
            select(AuditEvent).where(
                AuditEvent.organization_id == org_of(created),
                AuditEvent.action == "ACCOUNT_ACTIVATED",
            )
        ).all()
    assert [event.after for event in events] == [{"method": "google"}]
    with owner_db.transaction(TenantContext(organization_id=org_of(created))) as session:
        used = session.scalar(
            text("SELECT used_at FROM account_links WHERE organization_id = :org"),
            {"org": org_of(created)},
        )
    assert used is not None  # the link is marked spent, not only the account activated
    with owner_db.transaction(PLATFORM) as session:
        row = session.execute(text("SELECT subject, email_at_link FROM external_identities")).one()
    assert (row.subject, row.email_at_link) == ("sub-owner", "priya.personal@gmail.example")


def test_starting_needs_the_activation_link(client: TestClient) -> None:
    response = start_activation(client, None)

    assert response.status_code == 400  # MALFORMED_REQUEST: link_token is missing
    assert "qb_google_flow" not in client.cookies


def _expire(owner_db: Database, org: UUID) -> None:
    change(owner_db, org, "UPDATE account_links SET expires_at = now() - interval '1 second'")


def _revoke(owner_db: Database, org: UUID) -> None:
    change(owner_db, org, "UPDATE account_links SET revoked_at = now()")


def _remove(owner_db: Database, org: UUID) -> None:
    change(owner_db, org, "UPDATE memberships SET status = 'REMOVED'")


def _suspend(owner_db: Database, org: UUID) -> None:
    change(owner_db, org, "UPDATE organizations SET status = 'SUSPENDED' WHERE id = :org")


def _use(owner_db: Database, org: UUID) -> None:
    change(owner_db, org, "UPDATE account_links SET used_at = now()")


Spoil = Callable[[Database, UUID], None]

SPOILERS = pytest.mark.parametrize(
    "spoil",
    [_expire, _revoke, _remove, _suspend, _use],
    ids=["expired", "replaced", "member-removed", "coaching-suspended", "used"],
)


@SPOILERS
def test_a_link_that_is_no_longer_good_cannot_start_a_flow(
    client: TestClient, owner_db: Database, spoil: Spoil
) -> None:
    created = invite_owner(client, owner_db)
    spoil(owner_db, org_of(created))

    response = start_activation(client, token_of(created))

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "LINK_INVALID"
    assert "qb_google_flow" not in client.cookies
    assert open_flows(owner_db) == 0


def test_a_reset_link_for_a_not_yet_activated_person_cannot_start_a_flow(
    client: TestClient, owner_db: Database
) -> None:
    created = invite_owner(client, owner_db)
    with owner_db.transaction(TenantContext(organization_id=org_of(created))) as session:
        membership_id = session.scalar(
            text("SELECT id FROM memberships WHERE organization_id = :org"),
            {"org": org_of(created)},
        )
        token = issue_account_link(
            session,
            organization_id=org_of(created),
            membership_id=membership_id,
            user_id=owner_of(created),
            purpose=LinkPurpose.RESET,
            created_by=owner_of(created),
        ).token

    response = start_activation(client, token)

    assert response.status_code == 401
    assert open_flows(owner_db) == 0


def test_an_unknown_link_cannot_start_a_flow(client: TestClient, owner_db: Database) -> None:
    response = start_activation(client, "x" * 43)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "LINK_INVALID"
    assert open_flows(owner_db) == 0


def test_a_password_reset_link_cannot_be_used_to_activate_with_google(
    client: TestClient, owner_db: Database
) -> None:
    member = make_member(owner_db, "FACULTY")

    response = start_activation(client, reset_link(owner_db, member))

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "LINK_INVALID"


@SPOILERS
def test_a_link_spoiled_while_at_google_stops_the_activation(
    client: TestClient, google: StandInGoogle, owner_db: Database, spoil: Spoil
) -> None:
    created = invite_owner(client, owner_db)
    google.accounts["code-1"] = identity("sub-owner")
    state = state_of(start_activation(client, token_of(created)))  # the person leaves for Google...
    spoil(owner_db, org_of(created))  # ...and meanwhile the link or their place is taken away

    assert_signed_out_after_failure(client, call_back(client, state))

    assert linked_accounts(owner_db) == 0
    assert user_status(owner_db, owner_of(created)) == "INVITED"


def test_the_link_used_with_a_password_while_at_google_stops_the_activation(
    client: TestClient, google: StandInGoogle, owner_db: Database
) -> None:
    created = invite_owner(client, owner_db)
    google.accounts["code-1"] = identity("sub-owner")
    state = state_of(start_activation(client, token_of(created)))
    with TestClient(client.app) as elsewhere:  # the same link is redeemed with a password first
        assert redeem(elsewhere, token_of(created)) == (200, "")

    assert_signed_out_after_failure(client, call_back(client, state))
    assert linked_accounts(owner_db) == 0


def test_a_google_account_linked_to_someone_else_cannot_activate_another_person(
    client: TestClient, google: StandInGoogle, owner_db: Database
) -> None:
    existing = make_member(owner_db, "ADMIN")
    link_google(owner_db, existing.user_id, "sub-taken")
    created = invite_owner(client, owner_db)
    google.accounts["code-1"] = identity("sub-taken")
    state = state_of(start_activation(client, token_of(created)))

    assert_signed_out_after_failure(client, call_back(client, state))

    assert linked_accounts(owner_db) == 1  # still only the existing person's
    assert user_status(owner_db, owner_of(created)) == "INVITED"
    assert (
        redeem(client, token_of(created))[0] == 200
    )  # the link is untouched: a password still works


def test_a_flow_that_was_never_taken_cannot_activate(
    client: TestClient, owner_db: Database, db: Database
) -> None:
    created = invite_owner(client, owner_db)
    assert start_activation(client, token_of(created)).status_code == 200
    with owner_db.transaction(PLATFORM) as session:
        flow_id = session.scalar(text("SELECT id FROM oauth_flows"))

    with db.transaction(NO_CONTEXT) as session:
        row = session.execute(
            text("SELECT * FROM auth_google_activate(:flow, 'sub-x', NULL)"), {"flow": flow_id}
        ).first()

    assert row is None
    assert user_status(owner_db, owner_of(created)) == "INVITED"


def test_a_sign_in_flow_cannot_activate_anyone(
    client: TestClient, owner_db: Database, db: Database
) -> None:
    created = invite_owner(client, owner_db)
    start(client)
    with owner_db.transaction(PLATFORM) as session:
        session.execute(text("UPDATE oauth_flows SET used_at = now()"))
        flow_id = session.scalar(text("SELECT id FROM oauth_flows"))

    with db.transaction(NO_CONTEXT) as session:
        row = session.execute(
            text("SELECT * FROM auth_google_activate(:flow, 'sub-x', NULL)"), {"flow": flow_id}
        ).first()

    assert row is None
    assert user_status(owner_db, owner_of(created)) == "INVITED"


def test_guessing_at_one_link_is_slowed_down(
    settings: Settings, google: StandInGoogle, owner_db: Database
) -> None:
    strict = settings.model_copy(update={"login_attempts_per_email": 3})
    app = create_app(strict)
    app.state.google = google
    with TestClient(app) as client:
        codes = [start_activation(client, "y" * 43).status_code for _ in range(4)]

    assert codes == [401, 401, 401, 429]
