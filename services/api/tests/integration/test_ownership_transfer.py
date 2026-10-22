"""M2 PR 6b: transfer ownership to another admin (B-08; T15, T17)."""

import threading
from collections.abc import Iterator
from contextlib import ExitStack
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from qbank.core.config import AppEnv, Settings
from qbank.core.db import Database
from qbank.core.tenancy import TenantContext
from qbank.main import create_app
from qbank.modules.audit.models import AuditEvent
from qbank.modules.organizations.models import Membership
from tests.integration.conftest import (
    ORIGIN,
    Member,
    MigratedDatabase,
    make_member,
    platform_admin,
    sign_in,
)

MEMBERS = "/api/v1/members"
TRANSFER = "/api/v1/organization/transfer-ownership"


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
        "other_admin": make_member(owner_db, "ADMIN", org_id=owner.org_id),
        "faculty": make_member(owner_db, "FACULTY", org_id=owner.org_id),
    }


def etag_of(client: TestClient, member: Member) -> str:
    response = client.get(f"{MEMBERS}/{member.membership_id}")
    assert response.status_code == 200, response.text
    return response.headers["ETag"]


def transfer(
    client: TestClient,
    headers: dict[str, str],
    owner: Member,
    heir: Member,
    etag: str | None = None,
) -> Any:
    return client.post(
        TRANSFER,
        json={
            "expected_owner_membership_id": str(owner.membership_id),
            "new_owner_membership_id": str(heir.membership_id),
        },
        headers={**headers, "If-Match": etag or etag_of(client, owner)},
    )


def code_of(response: Any) -> tuple[int, str]:
    return response.status_code, response.json()["error"]["code"]


def roles(owner_db: Database, org_id: UUID) -> dict[UUID, tuple[str, str]]:
    with owner_db.transaction(TenantContext(organization_id=org_id)) as session:
        rows = session.scalars(select(Membership).where(Membership.organization_id == org_id))
        return {row.id: (row.role, row.status) for row in rows}


def test_owner_hands_the_coaching_to_an_admin(
    client: TestClient, settings: Settings, owner_db: Database, team: dict[str, Member]
) -> None:
    with TestClient(create_app(settings)) as admin_browser:
        sign_in(admin_browser, team["admin"].email)
        headers = sign_in(client, team["owner"].email)

        response = transfer(client, headers, team["owner"], team["admin"])

        assert response.status_code == 200, response.text
        body = response.json()
        assert (body["previous_owner"]["role"], body["new_owner"]["role"]) == ("ADMIN", "OWNER")
        assert body["new_owner"]["membership_id"] == str(team["admin"].membership_id)
        # Both people's open sessions see their new roles on the next request.
        assert admin_browser.get("/api/v1/me").json()["organization"]["role"] == "OWNER"
        assert client.get("/api/v1/me").json()["organization"]["role"] == "ADMIN"
    held = roles(owner_db, team["owner"].org_id)
    assert sorted(role for role, _ in held.values() if role == "OWNER") == ["OWNER"]
    assert held[team["owner"].membership_id] == ("ADMIN", "ACTIVE")
    with owner_db.transaction(TenantContext(organization_id=team["owner"].org_id)) as session:
        [event] = session.scalars(
            select(AuditEvent).where(
                AuditEvent.organization_id == team["owner"].org_id,
                AuditEvent.action == "OWNERSHIP_TRANSFERRED",
            )
        )
    assert event.actor_user_id == team["owner"].user_id
    assert event.before == {
        "owner_membership_id": str(team["owner"].membership_id),
        "owner_user_id": str(team["owner"].user_id),
    }
    assert event.after == {
        "owner_membership_id": str(team["admin"].membership_id),
        "owner_user_id": str(team["admin"].user_id),
    }


def test_after_the_transfer_the_new_owner_holds_the_owner_rules(
    client: TestClient, settings: Settings, team: dict[str, Member]
) -> None:
    old_headers = sign_in(client, team["owner"].email)
    assert transfer(client, old_headers, team["owner"], team["admin"]).status_code == 200

    # The old Owner is now an admin: no more owner-only actions, and can be demoted or removed.
    refused = client.post(
        f"{MEMBERS}/{team['faculty'].membership_id}/change-role",
        json={"expected_role": "FACULTY", "new_role": "ADMIN"},
        headers={**old_headers, "If-Match": etag_of(client, team["faculty"])},
    )
    assert refused.status_code == 403
    with TestClient(create_app(settings)) as new_owner:
        headers = sign_in(new_owner, team["admin"].email)
        old = new_owner.get(f"{MEMBERS}/{team['owner'].membership_id}")
        assert old.json()["actions"] == [
            "NEW_RESET_LINK",
            "CHANGE_ROLE",
            "REMOVE",
            "TRANSFER_OWNERSHIP",
        ]
        removed = new_owner.post(
            f"{MEMBERS}/{team['owner'].membership_id}/remove",
            json={"expected_role": "ADMIN"},
            headers={**headers, "If-Match": old.headers["ETag"]},
        )
        assert removed.status_code == 200  # the former Owner can be removed like any admin


def test_only_the_owner_may_transfer(client: TestClient, team: dict[str, Member]) -> None:
    sign_in(client, team["owner"].email)
    etag = etag_of(client, team["owner"])
    for who in ("admin", "faculty"):
        headers = sign_in(client, team[who].email)

        response = transfer(client, headers, team["owner"], team["other_admin"], etag)

        assert response.status_code == 403


@pytest.mark.parametrize("heir", ["faculty", "owner"])
def test_ownership_goes_only_to_another_admin(
    client: TestClient, team: dict[str, Member], heir: str
) -> None:
    headers = sign_in(client, team["owner"].email)

    response = transfer(client, headers, team["owner"], team[heir])

    assert code_of(response) == (409, "INVALID_NEW_OWNER")


def test_not_to_a_removed_or_never_activated_admin_or_another_coachings(
    client: TestClient, owner_db: Database, team: dict[str, Member]
) -> None:
    headers = sign_in(client, team["owner"].email)
    invited = client.post(
        f"{MEMBERS}/invitations",
        json={"email": "newadmin@example.com", "display_name": "New", "role": "ADMIN"},
        headers=headers,
    ).json()["member"]
    invited_admin = Member(
        "newadmin@example.com",
        UUID(invited["user_id"]),
        team["owner"].org_id,
        UUID(invited["membership_id"]),
    )
    removed = team["other_admin"]
    with owner_db.transaction(TenantContext(organization_id=removed.org_id)) as session:
        session.execute(
            text("UPDATE memberships SET status = 'REMOVED' WHERE id = :id"),
            {"id": removed.membership_id},
        )
    stranger = make_member(owner_db, "ADMIN")  # an admin of a coaching of its own
    etag = etag_of(client, team["owner"])

    assert code_of(transfer(client, headers, team["owner"], invited_admin, etag)) == (
        409,
        "INVALID_NEW_OWNER",
    )
    assert code_of(transfer(client, headers, team["owner"], removed, etag)) == (
        409,
        "INVALID_NEW_OWNER",
    )
    assert transfer(client, headers, team["owner"], stranger, etag).status_code == 404


def test_transfers_need_the_current_owner_and_revision(
    client: TestClient, team: dict[str, Member]
) -> None:
    headers = sign_in(client, team["owner"].email)
    body = {
        "expected_owner_membership_id": str(team["owner"].membership_id),
        "new_owner_membership_id": str(team["admin"].membership_id),
    }

    missing = client.post(TRANSFER, json=body, headers=headers)
    stale = client.post(TRANSFER, json=body, headers={**headers, "If-Match": '"rev-9"'})
    wrong_owner = client.post(
        TRANSFER,
        json={**body, "expected_owner_membership_id": str(team["admin"].membership_id)},
        headers={**headers, "If-Match": etag_of(client, team["owner"])},
    )

    assert code_of(missing) == (428, "IF_MATCH_REQUIRED")
    assert code_of(stale) == (412, "REVISION_STALE")
    assert code_of(wrong_owner) == (409, "OWNER_CHANGED")
    assert transfer(client, headers, team["owner"], team["admin"]).status_code == 200


def test_replaying_a_transfer_does_nothing(client: TestClient, team: dict[str, Member]) -> None:
    headers = sign_in(client, team["owner"].email)
    etag = etag_of(client, team["owner"])
    assert transfer(client, headers, team["owner"], team["admin"], etag).status_code == 200

    # The same request again (a retry or a second tab): the old Owner is an admin now.
    again = transfer(client, headers, team["owner"], team["admin"], etag)

    assert again.status_code == 403  # no longer the Owner, so no longer allowed to transfer


def test_a_platform_admin_acting_in_the_coaching_can_transfer(
    client: TestClient, owner_db: Database, team: dict[str, Member]
) -> None:
    headers = sign_in(client, platform_admin(owner_db))
    etag = '"rev-1"'
    refused = transfer(client, headers, team["owner"], team["admin"], etag)
    assert refused.status_code == 403  # not acting in a coaching yet
    acted = client.post(
        "/api/v1/platform/acting-organization",
        json={"organization_id": str(team["owner"].org_id)},
        headers=headers,
    )
    assert acted.status_code == 204

    response = transfer(client, headers, team["owner"], team["admin"])

    assert response.status_code == 200, response.text
    with owner_db.transaction(TenantContext(organization_id=team["owner"].org_id)) as session:
        [event] = session.scalars(
            select(AuditEvent).where(
                AuditEvent.organization_id == team["owner"].org_id,
                AuditEvent.action == "OWNERSHIP_TRANSFERRED",
            )
        )
    assert event.actor_is_platform is True


def test_actions_offer_the_transfer_only_to_the_owner_and_only_for_admins(
    client: TestClient, team: dict[str, Member]
) -> None:
    sign_in(client, team["owner"].email)
    listed = {m["membership_id"]: m["actions"] for m in client.get(MEMBERS).json()["data"]}

    assert "TRANSFER_OWNERSHIP" in listed[str(team["admin"].membership_id)]
    assert "TRANSFER_OWNERSHIP" not in listed[str(team["faculty"].membership_id)]
    assert "TRANSFER_OWNERSHIP" not in listed[str(team["owner"].membership_id)]
    sign_in(client, team["admin"].email)
    for actions in client.get(MEMBERS).json()["data"]:
        assert "TRANSFER_OWNERSHIP" not in actions["actions"]


def test_simultaneous_transfers_leave_exactly_one_owner(
    settings: Settings, owner_db: Database, team: dict[str, Member]
) -> None:
    """T15: two transfers sent at the same moment, to different admins, from the same screen."""
    statuses: list[int] = []
    start = threading.Barrier(2)
    heirs = [team["admin"], team["other_admin"]]

    with ExitStack() as stack:  # two separate apps, like two API processes
        clients = [stack.enter_context(TestClient(create_app(settings))) for _ in range(2)]
        headers = [sign_in(each, team["owner"].email) for each in clients]
        etag = etag_of(clients[0], team["owner"])
        # FastAPI prepares routes lazily on first use, which is not thread-safe across apps that
        # share routers (the server matches routes on one thread, so only this test can race).
        for each in clients:
            assert each.get(MEMBERS).status_code == 200

        def send(index: int) -> None:
            start.wait()
            response = clients[index].post(
                TRANSFER,
                json={
                    "expected_owner_membership_id": str(team["owner"].membership_id),
                    "new_owner_membership_id": str(heirs[index].membership_id),
                },
                headers={**headers[index], "If-Match": etag},
            )
            statuses.append(response.status_code)

        threads = [threading.Thread(target=send, args=(i,)) for i in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

    assert sorted(statuses) == [200, 412]
    held = roles(owner_db, team["owner"].org_id)
    owners = [member for member, (role, status) in held.items() if role == "OWNER"]
    assert len(owners) == 1
    assert owners[0] in {team["admin"].membership_id, team["other_admin"].membership_id}
    assert held[team["owner"].membership_id] == ("ADMIN", "ACTIVE")


def test_changes_need_a_session_and_the_csrf_token(
    client: TestClient, team: dict[str, Member]
) -> None:
    body = {
        "expected_owner_membership_id": str(team["owner"].membership_id),
        "new_owner_membership_id": str(team["admin"].membership_id),
    }

    assert client.post(TRANSFER, json=body, headers=ORIGIN).status_code == 401
    sign_in(client, team["owner"].email)
    assert client.post(TRANSFER, json=body, headers=ORIGIN).status_code == 403
