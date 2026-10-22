"""M2 PR 8c: linking and unlinking a Google account while signed in (B-02, B-04, T19)."""

import threading
from collections.abc import Callable, Iterator
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from qbank.core.config import AppEnv, Settings
from qbank.core.db import Database
from qbank.core.tenancy import NO_CONTEXT, TenantContext
from qbank.main import create_app
from qbank.modules.audit.models import AuditEvent
from tests.integration.conftest import (
    MEMBER_PASSWORD,
    ORIGIN,
    PLATFORM,
    Member,
    MigratedDatabase,
    make_member,
    platform_admin,
    sign_in,
)
from tests.integration.google_support import (
    StandInGoogle,
    call_back,
    identity,
    link_google,
    start,
    start_activation,
    state_of,
)
from tests.integration.test_link_redemption import invite_owner, token_of

START_LINK = "/api/v1/auth/google/start-link"
UNLINK = "/api/v1/auth/google/unlink"
LINK_FAILED = "/profile?google=failed"
LINKED = "/profile?google=linked"
SIGN_IN_FAILED = "/login?google=failed"

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
def app_client(settings: Settings, google: StandInGoogle) -> Iterator[TestClient]:
    app = create_app(settings)
    app.state.google = google
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def client(app_client: TestClient) -> TestClient:
    return app_client


def new_browser(client: TestClient) -> TestClient:
    return TestClient(client.app)


def start_link(client: TestClient, headers: dict[str, str], password: str = MEMBER_PASSWORD):  # type: ignore[no-untyped-def]
    body = {"return_origin": ORIGIN["Origin"], "password": password}
    return client.post(START_LINK, json=body, headers=headers)


def linked_subjects(owner_db: Database, user_id: UUID) -> list[str]:
    with owner_db.transaction(PLATFORM) as session:
        rows = session.scalars(
            text("SELECT subject FROM external_identities WHERE user_id = :u"), {"u": user_id}
        ).all()
    return list(rows)


def audit_actions(owner_db: Database, user_id: UUID) -> list[str]:
    with owner_db.transaction(PLATFORM) as session:
        return list(
            session.scalars(select(AuditEvent.action).where(AuditEvent.entity_id == user_id)).all()
        )


def signed_in_member(
    client: TestClient, owner_db: Database, role: str = "ADMIN"
) -> tuple[Member, dict[str, str]]:
    member = make_member(owner_db, role)
    return member, sign_in(client, member.email)


def test_linking_needs_a_session_and_the_csrf_token(client: TestClient, owner_db: Database) -> None:
    body = {"return_origin": ORIGIN["Origin"], "password": MEMBER_PASSWORD}
    assert client.post(START_LINK, json=body, headers=ORIGIN).status_code == 401

    member = make_member(owner_db, "ADMIN")
    sign_in(client, member.email)
    without_csrf = client.post(START_LINK, json=body, headers=ORIGIN)

    assert without_csrf.status_code == 403
    assert without_csrf.json()["error"]["code"] == "CSRF_TOKEN_INVALID"


def test_the_password_must_come_with_the_request(client: TestClient, owner_db: Database) -> None:
    _, headers = signed_in_member(client, owner_db)

    response = client.post(START_LINK, json={"return_origin": ORIGIN["Origin"]}, headers=headers)

    assert response.status_code == 400  # a fresh session alone is not proof
    assert "qb_google_flow" not in client.cookies


def test_a_wrong_password_is_refused_and_counts_towards_the_lockout(
    client: TestClient, owner_db: Database, settings: Settings
) -> None:
    member, headers = signed_in_member(client, owner_db)

    for _ in range(settings.login_max_failures):
        response = start_link(client, headers, "not the password")
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "PASSWORD_INCORRECT"

    # Locked now: even the right password is refused, here and at the ordinary sign-in.
    assert start_link(client, headers).status_code == 403
    login = new_browser(client).post(
        "/api/v1/auth/login",
        json={"email": member.email, "password": MEMBER_PASSWORD},
        headers=ORIGIN,
    )
    assert login.status_code == 401
    assert "qb_google_flow" not in client.cookies


def test_linking_google_keeps_the_session_and_signs_in_later(
    client: TestClient, google: StandInGoogle, owner_db: Database
) -> None:
    member, headers = signed_in_member(client, owner_db)
    google.accounts["code-1"] = identity("sub-mine", email="me@gmail.example")
    response = start_link(client, headers)
    assert response.status_code == 200, response.text

    assert call_back(client, state_of(response)) == LINKED

    assert client.get("/api/v1/me").status_code == 200  # still signed in
    assert linked_subjects(owner_db, member.user_id) == ["sub-mine"]
    assert "GOOGLE_LINKED" in audit_actions(owner_db, member.user_id)
    methods = client.get("/api/v1/me/login-methods").json()
    assert methods == {"password": True, "google": {"linked": True, "email": "me@gmail.example"}}
    # From another browser, Google now signs in as this person.
    other = new_browser(client)
    assert call_back(other, start(other)) == "/"
    assert other.get("/api/v1/me").json()["id"] == str(member.user_id)


def test_a_platform_admin_without_a_coaching_can_link_google_and_sign_in_with_it(
    client: TestClient, google: StandInGoogle, owner_db: Database
) -> None:
    email = platform_admin(owner_db)
    headers = sign_in(client, email)
    google.accounts["code-1"] = identity("sub-admin")

    assert call_back(client, state_of(start_link(client, headers))) == LINKED

    other = new_browser(client)
    assert call_back(other, start(other)) == "/"
    assert other.get("/api/v1/me").json()["is_platform_admin"] is True


def test_a_second_google_account_cannot_be_linked(
    client: TestClient, google: StandInGoogle, owner_db: Database
) -> None:
    member, headers = signed_in_member(client, owner_db)
    google.accounts["code-1"] = identity("sub-first")
    assert call_back(client, state_of(start_link(client, headers))) == LINKED

    second = start_link(client, headers)

    assert second.status_code == 409
    assert second.json()["error"]["code"] == "ALREADY_LINKED"
    assert linked_subjects(owner_db, member.user_id) == ["sub-first"]


def test_two_links_racing_leave_exactly_one(
    client: TestClient, google: StandInGoogle, owner_db: Database
) -> None:
    member = make_member(owner_db, "ADMIN")
    first, second = client, new_browser(client)
    first_headers, second_headers = sign_in(first, member.email), sign_in(second, member.email)
    google.accounts["code-1"] = identity("sub-one")
    # Both flows start before either finishes, so neither is refused at the start.
    state_one = state_of(start_link(first, first_headers))
    state_two = state_of(start_link(second, second_headers))
    google.accounts["code-1"] = identity("sub-one")

    assert call_back(first, state_one) == LINKED
    google.accounts["code-1"] = identity("sub-two")
    assert call_back(second, state_two) == LINK_FAILED

    assert linked_subjects(owner_db, member.user_id) == ["sub-one"]


def test_a_google_account_that_belongs_to_someone_else_cannot_be_linked(
    client: TestClient, google: StandInGoogle, owner_db: Database
) -> None:
    other = make_member(owner_db, "FACULTY")
    link_google(owner_db, other.user_id, "sub-taken")
    member, headers = signed_in_member(client, owner_db)
    google.accounts["code-1"] = identity("sub-taken")

    assert call_back(client, state_of(start_link(client, headers))) == LINK_FAILED

    assert linked_subjects(owner_db, member.user_id) == []


def _sign_out(client: TestClient, headers: dict[str, str], member: Member, db: Database) -> None:
    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 204


def _expire(client: TestClient, headers: dict[str, str], member: Member, db: Database) -> None:
    with db.transaction(PLATFORM) as session:
        session.execute(text("UPDATE sessions SET idle_expires_at = now() - interval '1 second'"))


def _revoke(client: TestClient, headers: dict[str, str], member: Member, db: Database) -> None:
    with db.transaction(PLATFORM) as session:
        session.execute(text("UPDATE sessions SET revoked_at = now()"))


def _remove(client: TestClient, headers: dict[str, str], member: Member, db: Database) -> None:
    with db.transaction(PLATFORM) as session:
        session.execute(
            text("UPDATE memberships SET status = 'REMOVED' WHERE user_id = :u"),
            {"u": member.user_id},
        )


def _suspend(client: TestClient, headers: dict[str, str], member: Member, db: Database) -> None:
    with db.transaction(PLATFORM) as session:
        session.execute(
            text("UPDATE organizations SET status = 'SUSPENDED' WHERE id = :o"),
            {"o": member.org_id},
        )


def _disable(client: TestClient, headers: dict[str, str], member: Member, db: Database) -> None:
    with db.transaction(PLATFORM) as session:
        session.execute(
            text("UPDATE users SET status = 'DISABLED' WHERE id = :u"), {"u": member.user_id}
        )


Spoil = Callable[[TestClient, dict[str, str], Member, Database], None]


@pytest.mark.parametrize(
    "spoil",
    [_sign_out, _expire, _revoke, _remove, _suspend, _disable],
    ids=["signed-out", "expired", "revoked", "member-removed", "coaching-suspended", "disabled"],
)
def test_losing_the_session_or_access_while_at_google_stops_the_link(
    client: TestClient, google: StandInGoogle, owner_db: Database, spoil: Spoil
) -> None:
    member, headers = signed_in_member(client, owner_db)
    google.accounts["code-1"] = identity("sub-mine")
    state = state_of(start_link(client, headers))  # the person leaves for Google...
    spoil(client, headers, member, owner_db)  # ...and meanwhile loses the session or access

    assert call_back(client, state) == LINK_FAILED

    assert linked_subjects(owner_db, member.user_id) == []


def test_the_browser_that_did_not_start_the_flow_cannot_finish_it(
    client: TestClient, google: StandInGoogle, owner_db: Database
) -> None:
    member, headers = signed_in_member(client, owner_db)
    google.accounts["code-1"] = identity("sub-mine")
    state = state_of(start_link(client, headers))
    victim = new_browser(client)
    sign_in(victim, make_member(owner_db, "ADMIN").email)

    assert call_back(victim, state) == SIGN_IN_FAILED  # no pending cookie of this flow

    assert linked_subjects(owner_db, member.user_id) == []


def test_unlinking_removes_google_but_not_the_password(
    client: TestClient, google: StandInGoogle, owner_db: Database
) -> None:
    member, headers = signed_in_member(client, owner_db)
    google.accounts["code-1"] = identity("sub-mine")
    assert call_back(client, state_of(start_link(client, headers))) == LINKED

    assert client.post(UNLINK, headers=headers).status_code == 204

    assert linked_subjects(owner_db, member.user_id) == []
    assert "GOOGLE_UNLINKED" in audit_actions(owner_db, member.user_id)
    other = new_browser(client)
    assert call_back(other, start(other)) == SIGN_IN_FAILED  # Google no longer signs in
    assert sign_in(new_browser(client), member.email)  # the password still does
    # And another Google account can be linked now.
    google.accounts["code-1"] = identity("sub-next")
    assert call_back(client, state_of(start_link(client, headers))) == LINKED


def test_unlinking_needs_a_session_and_the_csrf_token(
    client: TestClient, owner_db: Database
) -> None:
    assert client.post(UNLINK, headers=ORIGIN).status_code == 401
    member = make_member(owner_db, "ADMIN")
    sign_in(client, member.email)

    response = client.post(UNLINK, headers=ORIGIN)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "CSRF_TOKEN_INVALID"


def test_unlinking_when_nothing_is_linked_says_so(client: TestClient, owner_db: Database) -> None:
    _, headers = signed_in_member(client, owner_db)

    response = client.post(UNLINK, headers=headers)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "GOOGLE_NOT_LINKED"


def test_google_cannot_be_unlinked_when_it_is_the_only_way_in(
    client: TestClient, google: StandInGoogle, owner_db: Database
) -> None:
    created = invite_owner(client, owner_db)
    google.accounts["code-1"] = identity("sub-owner")
    assert call_back(client, state_of(start_activation(client, token_of(created)))) == "/"
    headers = {**ORIGIN, "X-CSRF-Token": client.cookies["qb_csrf"]}
    owner_id = UUID(created["owner"]["user_id"])  # type: ignore[index]

    response = client.post(UNLINK, headers=headers)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "NO_OTHER_LOGIN_METHOD"
    assert linked_subjects(owner_db, owner_id) == ["sub-owner"]
    methods = client.get("/api/v1/me/login-methods").json()
    assert methods["password"] is False
    assert methods["google"]["linked"] is True


def test_login_methods_for_a_password_only_account(client: TestClient, owner_db: Database) -> None:
    signed_in_member(client, owner_db)

    assert client.get("/api/v1/me/login-methods").json() == {
        "password": True,
        "google": {"linked": False, "email": None},
    }
    assert new_browser(client).get("/api/v1/me/login-methods").status_code == 401


def test_starting_a_link_is_slowed_down(
    settings: Settings, google: StandInGoogle, owner_db: Database
) -> None:
    strict = settings.model_copy(update={"login_attempts_per_ip": 3})
    app = create_app(strict)
    app.state.google = google
    member = make_member(owner_db, "ADMIN")
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/login",
            json={"email": member.email, "password": MEMBER_PASSWORD},
            headers=ORIGIN,
        )
        headers = {**ORIGIN, "X-CSRF-Token": response.json()["csrf_token"]}
        codes = [start_link(client, headers).status_code for _ in range(4)]

    assert codes[:2] == [200, 200]
    assert 429 in codes


def test_the_database_functions_refuse_what_the_api_never_sends(
    client: TestClient, owner_db: Database, db: Database
) -> None:
    member, headers = signed_in_member(client, owner_db)
    other = new_browser(client)
    other_member, _ = signed_in_member(other, owner_db)
    assert start_link(client, headers).status_code == 200
    with owner_db.transaction(PLATFORM) as session:
        flow_id = session.scalar(text("SELECT id FROM oauth_flows"))
        other_session = session.scalar(
            text("SELECT id FROM sessions WHERE user_id = :u"), {"u": other_member.user_id}
        )

    with db.transaction(NO_CONTEXT) as session:
        # A flow that was never taken (so Google never called back) links nothing.
        untaken = session.scalar(
            text("SELECT auth_google_link(:flow, 'sub-x', NULL)"), {"flow": flow_id}
        )
    with owner_db.transaction(PLATFORM) as session:
        session.execute(text("UPDATE oauth_flows SET used_at = now(), purpose = 'SIGN_IN'"))
    with db.transaction(NO_CONTEXT) as session:
        # A taken flow of another purpose links nothing either.
        wrong_purpose = session.scalar(
            text("SELECT auth_google_link(:flow, 'sub-x', NULL)"), {"flow": flow_id}
        )
    # Someone else's session cannot be used to start a flow for this person.
    context = TenantContext(user_id=member.user_id)
    with db.transaction(context) as session:
        borrowed = session.scalar(
            text("SELECT auth_oauth_begin_link(:id, 'c', 's', 'v', 'n', :o, :sid)"),
            {"id": uuid4(), "o": ORIGIN["Origin"], "sid": other_session},
        )
    with db.transaction(NO_CONTEXT) as session:
        # With nobody signed in there is nobody to link for.
        anonymous = session.scalar(
            text("SELECT auth_oauth_begin_link(:id, 'c2', 's2', 'v', 'n', :o, :sid)"),
            {"id": uuid4(), "o": ORIGIN["Origin"], "sid": other_session},
        )

    assert untaken is None
    assert wrong_purpose is None
    assert borrowed == "NO_SESSION"
    assert anonymous == "NO_SESSION"
    assert linked_subjects(owner_db, member.user_id) == []


def test_a_link_waits_for_a_sign_out_in_progress(
    client: TestClient, owner_db: Database, db: Database
) -> None:
    """The callback locks the session that started the flow, as the activation locks the member."""
    member, headers = signed_in_member(client, owner_db)
    assert start_link(client, headers).status_code == 200
    with owner_db.transaction(PLATFORM) as session:
        flow_id = session.scalar(text("SELECT id FROM oauth_flows"))
        session.execute(text("UPDATE oauth_flows SET used_at = now()"))  # as if taken
    outcome: dict[str, object] = {}

    def link() -> None:
        with db.transaction(NO_CONTEXT) as session:
            outcome["user"] = session.scalar(
                text("SELECT auth_google_link(:flow, 'sub-race', NULL)"), {"flow": flow_id}
            )
        outcome["done"] = True

    with owner_db.transaction(PLATFORM) as session:
        session.execute(
            text("UPDATE sessions SET revoked_at = now() WHERE user_id = :u"), {"u": member.user_id}
        )  # the sign-out is mid-way
        worker = threading.Thread(target=link)
        worker.start()
        worker.join(timeout=1.0)
        assert "done" not in outcome  # waiting for the sign-out to finish
    worker.join(timeout=10.0)

    assert outcome.get("done") is True
    assert outcome["user"] is None  # it saw the revoked session and linked nothing
    assert linked_subjects(owner_db, member.user_id) == []
