"""M2 PR 6a: change a member's role, remove a member (B-08, B-09, B-10; T14, T17)."""

import secrets
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
    MEMBER_PASSWORD,
    ORIGIN,
    Member,
    MigratedDatabase,
    make_member,
    sign_in,
)

MEMBERS = "/api/v1/members"
REDEEM = "/api/v1/auth/links/redeem"


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
        "faculty": make_member(owner_db, "FACULTY", org_id=owner.org_id, grants=["QC", "PUBLISH"]),
    }


def etag_of(client: TestClient, member: Member) -> str:
    response = client.get(f"{MEMBERS}/{member.membership_id}")
    assert response.status_code == 200, response.text
    return response.headers["ETag"]


def change_role(
    client: TestClient,
    headers: dict[str, str],
    member: Member,
    expected: str,
    new: str,
    etag: str | None = None,
) -> Any:
    return client.post(
        f"{MEMBERS}/{member.membership_id}/change-role",
        json={"expected_role": expected, "new_role": new},
        headers={**headers, "If-Match": etag or etag_of(client, member)},
    )


def remove(
    client: TestClient,
    headers: dict[str, str],
    member: Member,
    expected: str,
    etag: str | None = None,
) -> Any:
    return client.post(
        f"{MEMBERS}/{member.membership_id}/remove",
        json={"expected_role": expected},
        headers={**headers, "If-Match": etag or etag_of(client, member)},
    )


def code_of(response: Any) -> tuple[int, str]:
    return response.status_code, response.json()["error"]["code"]


def events(owner_db: Database, org_id: UUID, action: str) -> list[AuditEvent]:
    with owner_db.transaction(TenantContext(organization_id=org_id)) as session:
        return list(
            session.scalars(
                select(AuditEvent).where(
                    AuditEvent.organization_id == org_id, AuditEvent.action == action
                )
            )
        )


# --- Changing a role -----------------------------------------------------------------------------


def test_owner_promotes_faculty_and_demotes_admins_and_it_applies_at_once(
    client: TestClient, settings: Settings, owner_db: Database, team: dict[str, Member]
) -> None:
    faculty = team["faculty"]
    with TestClient(create_app(settings)) as faculty_browser:
        sign_in(faculty_browser, faculty.email)
        headers = sign_in(client, team["owner"].email)

        promoted = change_role(client, headers, faculty, "FACULTY", "ADMIN")

        assert promoted.status_code == 200, promoted.text
        assert (promoted.json()["role"], promoted.json()["grants"]) == ("ADMIN", [])
        assert promoted.headers["ETag"] == '"rev-2"'
        # The open session of the promoted person sees the new role on its next request.
        assert faculty_browser.get("/api/v1/me").json()["organization"]["role"] == "ADMIN"
        demoted = change_role(client, headers, faculty, "ADMIN", "FACULTY")
        assert demoted.status_code == 200
        assert faculty_browser.get("/api/v1/me").json()["organization"]["role"] == "FACULTY"
        assert faculty_browser.get("/api/v1/me").json()["organization"]["grants"] == []
    first, second = sorted(
        events(owner_db, faculty.org_id, "MEMBER_ROLE_CHANGED"), key=lambda e: e.created_at
    )
    assert first.before == {"role": "FACULTY", "grants": ["PUBLISH", "QC"]}  # grants cleared
    assert first.after == {"role": "ADMIN", "grants": []}
    assert (second.before, second.after) == (
        {"role": "ADMIN", "grants": []},
        {"role": "FACULTY", "grants": []},
    )
    assert first.actor_user_id == team["owner"].user_id


@pytest.mark.parametrize("who", ["admin", "faculty"])
def test_only_the_owner_changes_roles(
    client: TestClient, team: dict[str, Member], who: str
) -> None:
    owner_headers = sign_in(client, team["owner"].email)
    etag = etag_of(client, team["faculty"])
    headers = sign_in(client, team[who].email)

    response = change_role(client, headers, team["faculty"], "FACULTY", "ADMIN", etag)

    assert response.status_code == 403
    assert owner_headers  # (the Owner could have)


def test_the_owner_cannot_be_demoted_or_removed(
    client: TestClient, owner_db: Database, team: dict[str, Member]
) -> None:
    headers = sign_in(client, team["owner"].email)
    etag = etag_of(client, team["owner"])

    demote = change_role(client, headers, team["owner"], "OWNER", "ADMIN", etag)
    delete = remove(client, headers, team["owner"], "OWNER", etag)

    assert code_of(demote) == (409, "LAST_OWNER")
    assert code_of(delete) == (409, "LAST_OWNER")
    with owner_db.transaction(TenantContext(organization_id=team["owner"].org_id)) as session:
        owner = session.get(Membership, team["owner"].membership_id)
        assert (owner.role, owner.status) == ("OWNER", "ACTIVE")  # type: ignore[union-attr]


def test_role_changes_need_the_current_revision_and_the_role_the_screen_showed(
    client: TestClient, team: dict[str, Member]
) -> None:
    headers = sign_in(client, team["owner"].email)
    target = f"{MEMBERS}/{team['faculty'].membership_id}/change-role"
    body = {"expected_role": "FACULTY", "new_role": "ADMIN"}

    missing = client.post(target, json=body, headers=headers)
    assert code_of(missing) == (428, "IF_MATCH_REQUIRED")
    stale = client.post(target, json=body, headers={**headers, "If-Match": '"rev-9"'})
    assert code_of(stale) == (412, "REVISION_STALE")
    assert stale.json()["error"]["details"] == {"current_etag": '"rev-1"'}
    wrong_role = client.post(
        target,
        json={"expected_role": "ADMIN", "new_role": "FACULTY"},
        headers={**headers, "If-Match": '"rev-1"'},
    )
    assert code_of(wrong_role) == (409, "ROLE_CHANGED")
    assert wrong_role.json()["error"]["details"] == {"current_role": "FACULTY"}
    # Nothing changed on the way: the right request still works.
    assert change_role(client, headers, team["faculty"], "FACULTY", "ADMIN").status_code == 200


def test_asking_for_the_role_they_have_changes_nothing(
    client: TestClient, owner_db: Database, team: dict[str, Member]
) -> None:
    headers = sign_in(client, team["owner"].email)

    response = change_role(client, headers, team["faculty"], "FACULTY", "FACULTY")

    assert response.status_code == 200
    assert response.headers["ETag"] == '"rev-1"'
    assert events(owner_db, team["owner"].org_id, "MEMBER_ROLE_CHANGED") == []


def test_other_coachings_members_are_out_of_reach(
    client: TestClient, owner_db: Database, team: dict[str, Member]
) -> None:
    stranger = make_member(owner_db, "FACULTY")
    headers = sign_in(client, team["owner"].email)

    promote = change_role(client, headers, stranger, "FACULTY", "ADMIN", '"rev-1"')
    delete = remove(client, headers, stranger, "FACULTY", '"rev-1"')

    assert promote.status_code == 404
    assert delete.status_code == 404


# --- Removing ------------------------------------------------------------------------------------


def test_removed_member_loses_access_at_once_and_history_stays(
    client: TestClient, settings: Settings, owner_db: Database, team: dict[str, Member]
) -> None:
    """T14: the removed person's open session stops working on its very next request."""
    faculty = team["faculty"]
    with TestClient(create_app(settings)) as faculty_browser:
        sign_in(faculty_browser, faculty.email)
        assert faculty_browser.get("/api/v1/me").status_code == 200
        headers = sign_in(client, team["admin"].email)

        removed = remove(client, headers, faculty, "FACULTY")

        assert removed.status_code == 200, removed.text
        body = removed.json()
        assert (body["status"], body["actions"]) == ("REMOVED", [])
        assert faculty_browser.get("/api/v1/me").status_code == 401
    # They cannot come back in by signing in again, either.
    again = client.post(
        "/api/v1/auth/login",
        json={"email": faculty.email, "password": MEMBER_PASSWORD},
        headers=ORIGIN,
    )
    assert again.status_code == 401
    listed = {m["membership_id"] for m in client.get(MEMBERS).json()["data"]}
    assert str(faculty.membership_id) not in listed
    with owner_db.transaction(TenantContext(organization_id=faculty.org_id)) as session:
        row = session.get(Membership, faculty.membership_id)
        assert (row.status, row.role, row.revision) == ("REMOVED", "FACULTY", 2)  # type: ignore[union-attr]
        sessions = session.execute(
            text(
                "SELECT count(*) FILTER (WHERE revoked_at IS NULL) FROM sessions WHERE user_id=:u"
            ),
            {"u": faculty.user_id},
        ).scalar()
        assert sessions == 0
    [event] = events(owner_db, faculty.org_id, "MEMBER_REMOVED")
    assert event.actor_user_id == team["admin"].user_id
    assert event.before == {"role": "FACULTY", "status": "ACTIVE"}
    assert event.after == {"role": "FACULTY", "status": "REMOVED"}


def test_removing_an_invitee_frees_their_email_and_kills_their_link(
    client: TestClient, settings: Settings, owner_db: Database, team: dict[str, Member]
) -> None:
    headers = sign_in(client, team["owner"].email)
    email = f"typo-{secrets.token_hex(4)}@example.com"
    invite = {"email": email, "display_name": "Mistyped", "role": "FACULTY"}
    created = client.post(f"{MEMBERS}/invitations", json=invite, headers=headers).json()
    invitee = Member(
        email,
        UUID(created["member"]["user_id"]),
        team["owner"].org_id,
        UUID(created["member"]["membership_id"]),
    )

    removed = remove(client, headers, invitee, "FACULTY")

    assert removed.status_code == 200
    with TestClient(create_app(settings)) as browser:
        used = browser.post(
            REDEEM,
            json={"token": created["activation"]["token"], "password": "a long enough passphrase"},
            headers=ORIGIN,
        )
    assert used.status_code == 401  # the link no longer works
    redone = client.post(f"{MEMBERS}/invitations", json=invite, headers=headers)
    assert redone.status_code == 201  # the same email can be invited again
    assert redone.json()["member"]["membership_id"] != created["member"]["membership_id"]


def test_removing_an_activated_member_keeps_their_email_reserved(
    client: TestClient, team: dict[str, Member]
) -> None:
    headers = sign_in(client, team["owner"].email)
    assert remove(client, headers, team["faculty"], "FACULTY").status_code == 200

    again = client.post(
        f"{MEMBERS}/invitations",
        json={"email": team["faculty"].email, "display_name": "Back", "role": "FACULTY"},
        headers=headers,
    )

    assert code_of(again) == (409, "EMAIL_TAKEN")  # their history stays with the account


def test_a_removed_members_unused_reset_link_stops_working(
    client: TestClient, settings: Settings, team: dict[str, Member]
) -> None:
    headers = sign_in(client, team["owner"].email)
    link = client.post(f"{MEMBERS}/{team['faculty'].membership_id}/reset-link", headers=headers)
    token = link.json()["token"]

    assert remove(client, headers, team["faculty"], "FACULTY").status_code == 200

    with TestClient(create_app(settings)) as browser:
        used = browser.post(
            REDEEM, json={"token": token, "password": "a long enough passphrase"}, headers=ORIGIN
        )
    assert used.status_code == 401


@pytest.mark.parametrize(
    ("who", "target", "allowed"),
    [
        ("admin", "faculty", True),
        ("owner", "faculty", True),
        ("owner", "admin", True),
        ("admin", "admin", False),
        ("faculty", "faculty", False),
        ("faculty", "admin", False),
    ],
)
def test_who_may_remove_whom(
    client: TestClient, team: dict[str, Member], who: str, target: str, allowed: bool
) -> None:
    etag = sign_in(client, team["owner"].email) and etag_of(client, team[target])
    headers = sign_in(client, team[who].email)

    response = remove(client, headers, team[target], target.upper(), etag)

    assert response.status_code == (200 if allowed else 403)


def test_removing_twice_or_with_a_stale_screen_is_refused(
    client: TestClient, team: dict[str, Member]
) -> None:
    headers = sign_in(client, team["owner"].email)
    stale_etag = etag_of(client, team["faculty"])
    assert remove(client, headers, team["faculty"], "FACULTY").status_code == 200

    again = remove(client, headers, team["faculty"], "FACULTY", stale_etag)
    missing = client.post(
        f"{MEMBERS}/{team['faculty'].membership_id}/remove",
        json={"expected_role": "FACULTY"},
        headers=headers,
    )

    assert code_of(again) == (412, "REVISION_STALE")
    assert code_of(missing) == (428, "IF_MATCH_REQUIRED")
    current = etag_of(client, team["faculty"])
    assert code_of(remove(client, headers, team["faculty"], "FACULTY", current)) == (
        409,
        "MEMBER_REMOVED",
    )


def test_a_screen_from_before_a_promotion_cannot_remove_the_new_admin(
    client: TestClient, team: dict[str, Member]
) -> None:
    """An admin's old screen shows "faculty"; the Owner promoted them meanwhile."""
    owner_headers = sign_in(client, team["owner"].email)
    old_etag = etag_of(client, team["faculty"])
    assert (
        change_role(client, owner_headers, team["faculty"], "FACULTY", "ADMIN").status_code == 200
    )
    admin_headers = sign_in(client, team["admin"].email)

    stale = remove(client, admin_headers, team["faculty"], "FACULTY", old_etag)
    fresh_but_wrong_role = remove(client, admin_headers, team["faculty"], "FACULTY")

    assert code_of(stale) == (412, "REVISION_STALE")
    assert code_of(fresh_but_wrong_role) == (409, "ROLE_CHANGED")
    assert client.get(f"{MEMBERS}/{team['faculty'].membership_id}").json()["status"] == "ACTIVE"


def test_simultaneous_changes_to_one_member_let_exactly_one_through(
    settings: Settings, team: dict[str, Member]
) -> None:
    """T17: a promotion and a removal sent at the same moment, both from the same screen."""
    statuses: list[int] = []
    start = threading.Barrier(2)

    with ExitStack() as stack:  # two separate apps, like two API processes
        clients = [stack.enter_context(TestClient(create_app(settings))) for _ in range(2)]
        headers = [sign_in(each, team["owner"].email) for each in clients]
        etag = etag_of(clients[0], team["faculty"])
        # FastAPI prepares routes lazily on first use, which is not thread-safe across apps that
        # share routers (the server matches routes on one thread, so only this test can race).
        for each in clients:
            assert each.get(MEMBERS).status_code == 200

        def promote() -> None:
            start.wait()
            response = clients[0].post(
                f"{MEMBERS}/{team['faculty'].membership_id}/change-role",
                json={"expected_role": "FACULTY", "new_role": "ADMIN"},
                headers={**headers[0], "If-Match": etag},
            )
            statuses.append(response.status_code)

        def delete() -> None:
            start.wait()
            response = clients[1].post(
                f"{MEMBERS}/{team['faculty'].membership_id}/remove",
                json={"expected_role": "FACULTY"},
                headers={**headers[1], "If-Match": etag},
            )
            statuses.append(response.status_code)

        threads = [threading.Thread(target=promote), threading.Thread(target=delete)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

    assert sorted(statuses) == [200, 412]


def test_changes_need_a_session_and_the_csrf_token(
    client: TestClient, team: dict[str, Member]
) -> None:
    target = f"{MEMBERS}/{team['faculty'].membership_id}/remove"
    body = {"expected_role": "FACULTY"}

    assert client.post(target, json=body, headers=ORIGIN).status_code == 401
    sign_in(client, team["owner"].email)
    assert client.post(target, json=body, headers=ORIGIN).status_code == 403
