"""M2 PR 5a: members list, invitations, new links (A-01, A-06, B-05..B-09; T13, T16, T22)."""

import secrets
from collections.abc import Iterator
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text

from qbank.core.config import AppEnv, Settings
from qbank.core.db import Database
from qbank.core.tenancy import TenantContext
from qbank.main import create_app
from qbank.modules.audit.models import AuditEvent
from qbank.modules.organizations.models import Membership
from tests.integration.conftest import (
    MEMBER_PASSWORD,
    ORIGIN,
    Member,
    MigratedDatabase,
    make_member,
    platform_admin,
    sign_in,
)

MEMBERS = "/api/v1/members"
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


@pytest.fixture
def team(owner_db: Database) -> dict[str, Member]:
    """One coaching with an Owner, an admin and a faculty member (with the QC grant)."""
    owner = make_member(owner_db, "OWNER")
    return {
        "owner": owner,
        "admin": make_member(owner_db, "ADMIN", org_id=owner.org_id),
        "faculty": make_member(owner_db, "FACULTY", org_id=owner.org_id, grants=["QC"]),
    }


def invitation(role: str = "FACULTY", email: str | None = None) -> dict[str, str]:
    email = email or f"invitee-{secrets.token_hex(5)}@example.com"
    return {"email": email, "display_name": "Anita Rao", "role": role}


def redeem(settings: Settings, token: str, password: str = NEW_PASSWORD) -> int:
    """Use a link in a browser that is not signed in; return the status code."""
    with TestClient(create_app(settings)) as browser:
        response = browser.post(REDEEM, json={"token": token, "password": password}, headers=ORIGIN)
    return response.status_code


def events(owner_db: Database, org_id: UUID, action: str) -> list[AuditEvent]:
    with owner_db.transaction(TenantContext(organization_id=org_id)) as session:
        return list(
            session.scalars(
                select(AuditEvent).where(
                    AuditEvent.organization_id == org_id, AuditEvent.action == action
                )
            )
        )


# --- Listing -------------------------------------------------------------------------------------


def test_admin_sees_each_member_with_email_role_grants_and_allowed_actions(
    client: TestClient, team: dict[str, Member]
) -> None:
    sign_in(client, team["admin"].email)

    response = client.get(MEMBERS)

    assert response.status_code == 200, response.text
    by_email = {m["email"]: m for m in response.json()["data"]}
    assert set(by_email) == {member.email for member in team.values()}
    faculty = by_email[team["faculty"].email]
    assert faculty["role"] == "FACULTY"
    assert faculty["grants"] == ["QC"]
    assert faculty["account_status"] == "ACTIVE"
    assert faculty["actions"] == ["NEW_RESET_LINK"]  # admins manage faculty...
    assert by_email[team["admin"].email]["actions"] == []  # ...but not admins (themselves too)
    assert by_email[team["owner"].email]["actions"] == []


def test_faculty_cannot_see_the_member_list(client: TestClient, team: dict[str, Member]) -> None:
    sign_in(client, team["faculty"].email)

    assert client.get(MEMBERS).status_code == 403
    assert client.get(f"{MEMBERS}/{team['admin'].membership_id}").status_code == 403


def test_another_coachings_members_are_invisible(
    client: TestClient, owner_db: Database, team: dict[str, Member]
) -> None:
    stranger = make_member(owner_db, "FACULTY")  # in a coaching of its own
    sign_in(client, team["owner"].email)

    listed = {m["membership_id"] for m in client.get(MEMBERS).json()["data"]}
    assert str(stranger.membership_id) not in listed
    assert client.get(f"{MEMBERS}/{stranger.membership_id}").status_code == 404
    reset = client.post(
        f"{MEMBERS}/{stranger.membership_id}/reset-link",
        headers=sign_in(client, team["owner"].email),
    )
    assert reset.status_code == 404


def test_emails_are_returned_only_for_members_of_the_current_coaching(
    db: Database, team: dict[str, Member], owner_db: Database
) -> None:
    stranger = make_member(owner_db, "FACULTY")
    ids = [team["faculty"].user_id, stranger.user_id]
    with db.transaction(TenantContext(organization_id=team["owner"].org_id)) as session:
        rows = session.execute(
            text("SELECT user_id, email FROM auth_member_emails(:ids)"), {"ids": ids}
        ).all()
    assert [(row.user_id, row.email) for row in rows] == [
        (team["faculty"].user_id, team["faculty"].email)
    ]
    with db.transaction(TenantContext()) as session:  # no coaching: nothing at all
        assert (
            session.execute(text("SELECT * FROM auth_member_emails(:ids)"), {"ids": ids}).all()
            == []
        )


def test_members_page_by_page(client: TestClient, team: dict[str, Member]) -> None:
    sign_in(client, team["owner"].email)

    first = client.get(MEMBERS, params={"limit": 2}).json()
    second = client.get(MEMBERS, params={"limit": 2, "cursor": first["page"]["next_cursor"]}).json()

    assert first["page"]["has_more"] is True
    assert second["page"] == {"next_cursor": None, "has_more": False}
    seen = [m["membership_id"] for m in first["data"] + second["data"]]
    assert sorted(seen) == sorted(str(m.membership_id) for m in team.values())


def test_one_member_carries_its_revision_as_etag(
    client: TestClient, team: dict[str, Member]
) -> None:
    sign_in(client, team["owner"].email)

    response = client.get(f"{MEMBERS}/{team['faculty'].membership_id}")

    assert response.status_code == 200
    assert response.headers["ETag"] == '"rev-1"'
    assert response.json()["actions"] == ["NEW_RESET_LINK"]


def test_platform_admin_sees_members_only_while_acting_in_the_coaching(
    client: TestClient, owner_db: Database, team: dict[str, Member]
) -> None:
    headers = sign_in(client, platform_admin(owner_db))
    assert client.get(MEMBERS).status_code == 403

    acting = client.post(
        "/api/v1/platform/acting-organization",
        json={"organization_id": str(team["owner"].org_id)},
        headers=headers,
    )
    assert acting.status_code == 204
    members = {m["role"]: m for m in client.get(MEMBERS).json()["data"]}
    assert members["OWNER"]["actions"] == ["NEW_RESET_LINK"]  # only the platform resets the Owner


# --- Inviting ------------------------------------------------------------------------------------


def test_admin_invites_faculty_who_activates_with_the_link(
    client: TestClient, settings: Settings, owner_db: Database, team: dict[str, Member]
) -> None:
    headers = sign_in(client, team["admin"].email)
    body = invitation(email=f"  Anita.{secrets.token_hex(3)}@Example.COM ")

    response = client.post(f"{MEMBERS}/invitations", json=body, headers=headers)

    assert response.status_code == 201, response.text
    assert response.headers["Cache-Control"] == "no-store"
    created = response.json()
    member = created["member"]
    assert member["email"] == body["email"].strip().lower()
    assert (member["role"], member["account_status"]) == ("FACULTY", "INVITED")
    assert member["actions"] == ["NEW_ACTIVATION_LINK"]
    assert response.headers["Location"] == f"{MEMBERS}/{member['membership_id']}"
    assert redeem(settings, created["activation"]["token"]) == 200
    activated = client.get(f"{MEMBERS}/{member['membership_id']}").json()
    assert activated["account_status"] == "ACTIVE"
    [event] = events(owner_db, team["owner"].org_id, "MEMBER_INVITED")
    assert event.actor_user_id == team["admin"].user_id
    assert event.after == {
        "user_id": member["user_id"],
        "display_name": "Anita Rao",
        "email": member["email"],
        "role": "FACULTY",
    }


def test_only_the_owner_invites_admins(client: TestClient, team: dict[str, Member]) -> None:
    as_admin = sign_in(client, team["admin"].email)
    refused = client.post(f"{MEMBERS}/invitations", json=invitation("ADMIN"), headers=as_admin)
    assert refused.status_code == 403

    as_owner = sign_in(client, team["owner"].email)
    accepted = client.post(f"{MEMBERS}/invitations", json=invitation("ADMIN"), headers=as_owner)
    assert accepted.status_code == 201
    owner = client.post(f"{MEMBERS}/invitations", json=invitation("OWNER"), headers=as_owner)
    assert owner.status_code == 400  # an Owner is never invited: only a transfer makes one


def test_faculty_cannot_invite(client: TestClient, team: dict[str, Member]) -> None:
    headers = sign_in(client, team["faculty"].email)

    response = client.post(f"{MEMBERS}/invitations", json=invitation(), headers=headers)

    assert response.status_code == 403


def test_an_email_that_already_has_an_account_is_refused_and_nothing_is_left(
    client: TestClient, owner_db: Database, team: dict[str, Member]
) -> None:
    elsewhere = make_member(owner_db, "FACULTY")  # another coaching (B-07: one coaching each)
    headers = sign_in(client, team["owner"].email)

    response = client.post(
        f"{MEMBERS}/invitations",
        json=invitation(email=f" {elsewhere.email.upper()} "),
        headers=headers,
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EMAIL_TAKEN"
    with owner_db.transaction(TenantContext(organization_id=team["owner"].org_id)) as session:
        count = session.scalar(
            select(func.count())
            .select_from(Membership)
            .where(Membership.organization_id == team["owner"].org_id)
        )
    assert count == 3


def test_a_retried_invitation_returns_the_same_member_with_a_fresh_link(
    client: TestClient, settings: Settings, owner_db: Database, team: dict[str, Member]
) -> None:
    headers = {**sign_in(client, team["owner"].email), "Idempotency-Key": "invite-anita-1"}
    body = invitation()

    first = client.post(f"{MEMBERS}/invitations", json=body, headers=headers).json()
    again = client.post(f"{MEMBERS}/invitations", json=body, headers=headers)

    assert again.status_code == 201
    retried: dict[str, Any] = again.json()
    assert retried["member"]["membership_id"] == first["member"]["membership_id"]
    assert retried["activation"]["token"] != first["activation"]["token"]
    assert redeem(settings, first["activation"]["token"]) == 401  # the unseen first link is dead
    assert redeem(settings, retried["activation"]["token"]) == 200
    assert len(events(owner_db, team["owner"].org_id, "MEMBER_INVITED")) == 1
    changed = client.post(
        f"{MEMBERS}/invitations", json={**body, "display_name": "Someone Else"}, headers=headers
    )
    assert changed.status_code == 409
    assert changed.json()["error"]["code"] == "IDEMPOTENCY_KEY_REUSED"


# --- New links -----------------------------------------------------------------------------------


def invite(client: TestClient, headers: dict[str, str]) -> dict[str, Any]:
    response = client.post(f"{MEMBERS}/invitations", json=invitation(), headers=headers)
    assert response.status_code == 201, response.text
    created: dict[str, Any] = response.json()
    return created


def test_a_new_activation_link_replaces_the_old_one(
    client: TestClient, settings: Settings, team: dict[str, Member]
) -> None:
    headers = sign_in(client, team["admin"].email)
    created = invite(client, headers)
    membership_id = created["member"]["membership_id"]

    response = client.post(f"{MEMBERS}/{membership_id}/activation-link", headers=headers)

    assert response.status_code == 200, response.text
    assert response.headers["Cache-Control"] == "no-store"
    assert redeem(settings, created["activation"]["token"]) == 401
    assert redeem(settings, response.json()["token"]) == 200


def test_the_link_must_suit_the_account(client: TestClient, team: dict[str, Member]) -> None:
    headers = sign_in(client, team["admin"].email)
    invited = invite(client, headers)["member"]["membership_id"]
    active = team["faculty"].membership_id

    activation = client.post(f"{MEMBERS}/{active}/activation-link", headers=headers)
    reset = client.post(f"{MEMBERS}/{invited}/reset-link", headers=headers)

    assert (activation.status_code, activation.json()["error"]["code"]) == (
        409,
        "ALREADY_ACTIVATED",
    )
    assert (reset.status_code, reset.json()["error"]["code"]) == (409, "NOT_ACTIVATED")


def test_admin_makes_a_reset_link_that_sets_a_new_password(
    client: TestClient, settings: Settings, owner_db: Database, team: dict[str, Member]
) -> None:
    headers = sign_in(client, team["admin"].email)

    response = client.post(f"{MEMBERS}/{team['faculty'].membership_id}/reset-link", headers=headers)

    assert response.status_code == 200, response.text
    assert redeem(settings, response.json()["token"]) == 200
    old = client.post(
        "/api/v1/auth/login",
        json={"email": team["faculty"].email, "password": MEMBER_PASSWORD},
        headers=ORIGIN,
    )
    assert old.status_code == 401
    [event] = events(owner_db, team["owner"].org_id, "RESET_LINK_ISSUED")
    assert (event.actor_user_id, event.entity_id) == (
        team["admin"].user_id,
        team["faculty"].user_id,
    )
    assert event.after is None  # never the token


@pytest.mark.parametrize(
    ("who", "target", "allowed"),
    [
        ("admin", "admin", False),
        ("admin", "owner", False),
        ("owner", "admin", True),
        ("owner", "owner", False),  # the Owner's link comes from the platform
        ("faculty", "faculty", False),
    ],
)
def test_reset_links_follow_the_role_rules(
    client: TestClient, team: dict[str, Member], who: str, target: str, allowed: bool
) -> None:
    headers = sign_in(client, team[who].email)

    response = client.post(f"{MEMBERS}/{team[target].membership_id}/reset-link", headers=headers)

    assert response.status_code == (200 if allowed else 403)


def test_platform_admin_acting_in_the_coaching_makes_the_owners_reset_link(
    client: TestClient, owner_db: Database, team: dict[str, Member]
) -> None:
    headers = sign_in(client, platform_admin(owner_db))
    not_acting = client.post(f"{MEMBERS}/{team['owner'].membership_id}/reset-link", headers=headers)
    assert not_acting.status_code == 403
    client.post(
        "/api/v1/platform/acting-organization",
        json={"organization_id": str(team["owner"].org_id)},
        headers=headers,
    )

    response = client.post(f"{MEMBERS}/{team['owner'].membership_id}/reset-link", headers=headers)

    assert response.status_code == 200
    [event] = events(owner_db, team["owner"].org_id, "RESET_LINK_ISSUED")
    assert event.actor_is_platform is True


def test_no_link_for_someone_who_is_no_longer_a_member(
    client: TestClient, owner_db: Database, team: dict[str, Member]
) -> None:
    headers = sign_in(client, team["owner"].email)
    with owner_db.transaction(TenantContext(organization_id=team["owner"].org_id)) as session:
        session.execute(
            text("UPDATE memberships SET status = 'REMOVED' WHERE id = :id"),
            {"id": team["faculty"].membership_id},
        )

    response = client.post(f"{MEMBERS}/{team['faculty'].membership_id}/reset-link", headers=headers)

    assert (response.status_code, response.json()["error"]["code"]) == (409, "MEMBER_REMOVED")
    listed = {m["membership_id"] for m in client.get(MEMBERS).json()["data"]}
    assert str(team["faculty"].membership_id) not in listed


def test_changes_need_a_session_and_the_csrf_token(
    client: TestClient, team: dict[str, Member]
) -> None:
    signed_out = client.post(f"{MEMBERS}/invitations", json=invitation(), headers=ORIGIN)
    assert signed_out.status_code == 401
    sign_in(client, team["owner"].email)
    no_csrf = client.post(f"{MEMBERS}/invitations", json=invitation(), headers=ORIGIN)
    assert no_csrf.status_code == 403
