"""M2 PR 8a: signing in with Google (B-02, B-04, T19). Google itself is a stand-in: no real call."""

from collections.abc import Iterator
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from qbank.core.config import AppEnv, Settings
from qbank.core.db import Database
from qbank.core.tenancy import NO_CONTEXT
from qbank.main import create_app
from qbank.modules.audit.models import AuditEvent
from qbank.modules.identity.google import code_challenge
from tests.integration.conftest import (
    ORIGIN,
    PLATFORM,
    Member,
    MigratedDatabase,
    make_member,
    platform_admin,
)
from tests.integration.google_support import (
    FAILED,
    START,
    StandInGoogle,
    assert_signed_out_after_failure,
    call_back,
    identity,
    link_google,
    start,
)


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
    """The test database is shared by the whole run: start each test without Google links/flows."""
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


def test_methods_say_google_is_available_only_when_set_up(client: TestClient) -> None:
    assert client.get("/api/v1/auth/methods").json() == {"password": True, "google": True}

    client.app.state.google = None  # type: ignore[attr-defined]
    assert client.get("/api/v1/auth/methods").json() == {"password": True, "google": False}


def test_starting_is_refused_while_google_is_not_set_up(client: TestClient) -> None:
    client.app.state.google = None  # type: ignore[attr-defined]

    response = client.post(
        START, json={"purpose": "SIGN_IN", "return_origin": ORIGIN["Origin"]}, headers=ORIGIN
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "GOOGLE_DISABLED"


def test_starting_is_refused_for_a_web_address_that_is_not_allowed(client: TestClient) -> None:
    response = client.post(
        START,
        json={"purpose": "SIGN_IN", "return_origin": "https://evil.example.com"},
        headers=ORIGIN,
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "RETURN_ORIGIN_NOT_ALLOWED"
    assert "qb_google_flow" not in client.cookies


def test_starting_gives_google_the_state_nonce_pkce_and_our_callback(
    client: TestClient,
) -> None:
    response = client.post(
        START, json={"purpose": "SIGN_IN", "return_origin": ORIGIN["Origin"]}, headers=ORIGIN
    )

    assert response.status_code == 200
    query = parse_qs(urlparse(response.json()["authorization_url"]).query)
    assert query["redirect_uri"] == ["http://localhost:3000/api/v1/auth/google/callback"]
    assert all(len(query[key][0]) >= 20 for key in ("state", "nonce", "code_challenge"))
    cookie = response.headers["set-cookie"].lower()
    assert "qb_google_flow=" in cookie
    assert "httponly" in cookie
    assert "samesite=lax" in cookie
    assert "path=/api/v1/auth/google" in cookie
    assert "max-age=600" in cookie


def test_a_linked_google_account_signs_in(
    client: TestClient, google: StandInGoogle, owner_db: Database
) -> None:
    member = make_member(owner_db, "OWNER")
    link_google(owner_db, member.user_id, "sub-1")
    google.accounts["code-1"] = identity("sub-1")
    state = start(client)

    location = call_back(client, state)

    assert location == "/"
    assert client.get("/api/v1/me").json()["id"] == str(member.user_id)
    assert "qb_google_flow" not in client.cookies  # the pending cookie is spent
    with owner_db.transaction(PLATFORM) as session:
        signed_in = session.scalars(
            select(AuditEvent).where(
                AuditEvent.action == "USER_SIGNED_IN", AuditEvent.entity_id == member.user_id
            )
        ).all()
    assert len(signed_in) == 1


def test_google_is_given_the_matching_pkce_verifier_and_nonce(
    client: TestClient, google: StandInGoogle, owner_db: Database
) -> None:
    member = make_member(owner_db, "ADMIN")
    link_google(owner_db, member.user_id, "sub-1")
    google.accounts["code-1"] = identity("sub-1")
    response = client.post(
        START, json={"purpose": "SIGN_IN", "return_origin": ORIGIN["Origin"]}, headers=ORIGIN
    )
    query = parse_qs(urlparse(response.json()["authorization_url"]).query)

    call_back(client, query["state"][0])

    [asked] = google.asked
    assert code_challenge(asked["code_verifier"]) == query["code_challenge"][0]
    assert asked["nonce"] == query["nonce"][0]
    assert asked["redirect_uri"] == query["redirect_uri"][0]


def test_a_platform_admin_without_a_coaching_signs_in_with_google(
    client: TestClient, google: StandInGoogle, owner_db: Database
) -> None:
    email = platform_admin(owner_db)
    with owner_db.transaction(PLATFORM) as session:
        user_id = session.scalar(
            text("SELECT user_id FROM account_emails WHERE email = :email"), {"email": email}
        )
    link_google(owner_db, user_id, "sub-admin")
    google.accounts["code-1"] = identity("sub-admin")

    assert call_back(client, start(client)) == "/"
    assert client.get("/api/v1/me").json()["is_platform_admin"] is True


def test_a_google_account_nobody_linked_fails_and_creates_nothing(
    client: TestClient, google: StandInGoogle, owner_db: Database
) -> None:
    google.accounts["code-1"] = identity("sub-stranger")
    with owner_db.transaction(PLATFORM) as session:
        users_before = session.scalar(text("SELECT count(*) FROM users"))

    assert_signed_out_after_failure(client, call_back(client, start(client)))

    with owner_db.transaction(PLATFORM) as session:
        assert session.scalar(text("SELECT count(*) FROM users")) == users_before
        assert session.scalar(text("SELECT count(*) FROM external_identities")) == 0


def test_the_same_email_with_another_google_account_gets_no_access(
    client: TestClient, google: StandInGoogle, owner_db: Database
) -> None:
    member = make_member(owner_db, "OWNER")
    link_google(owner_db, member.user_id, "sub-real", email=member.email)
    # Someone else's Google account that happens to carry the same, even verified, email.
    google.accounts["code-1"] = identity("sub-impostor", email=member.email)

    assert_signed_out_after_failure(client, call_back(client, start(client)))


def test_a_wrong_state_fails_and_the_flow_cannot_be_retried(
    client: TestClient, google: StandInGoogle, owner_db: Database
) -> None:
    member = make_member(owner_db, "OWNER")
    link_google(owner_db, member.user_id, "sub-1")
    google.accounts["code-1"] = identity("sub-1")
    state = start(client)
    cookie = client.cookies["qb_google_flow"]

    assert call_back(client, "not-the-state") == FAILED
    client.cookies.set("qb_google_flow", cookie, path="/api/v1/auth/google")  # try again
    assert call_back(client, state) == FAILED  # the real state is too late now
    assert google.asked == []  # Google was never asked
    assert client.get("/api/v1/me").status_code == 401


def test_the_state_without_the_browsers_cookie_fails(
    client: TestClient, google: StandInGoogle, owner_db: Database, settings: Settings
) -> None:
    member = make_member(owner_db, "OWNER")
    link_google(owner_db, member.user_id, "sub-1")
    google.accounts["code-1"] = identity("sub-1")
    state = start(client)

    # An attacker walks someone's browser into a callback; that browser has no cookie of this flow.
    with TestClient(client.app) as victim:
        assert_signed_out_after_failure(victim, call_back(victim, state))
    assert google.asked == []


def test_a_cookie_from_another_flow_fails(
    client: TestClient, google: StandInGoogle, owner_db: Database
) -> None:
    member = make_member(owner_db, "OWNER")
    link_google(owner_db, member.user_id, "sub-1")
    google.accounts["code-1"] = identity("sub-1")
    state_of_first = start(client)
    with TestClient(client.app) as other:
        start(other)  # a second flow, with its own cookie
        assert_signed_out_after_failure(other, call_back(other, state_of_first))


def test_a_flow_works_only_once(
    client: TestClient, google: StandInGoogle, owner_db: Database
) -> None:
    member = make_member(owner_db, "OWNER")
    link_google(owner_db, member.user_id, "sub-1")
    google.accounts["code-1"] = identity("sub-1")
    state = start(client)
    cookie = client.cookies["qb_google_flow"]
    assert call_back(client, state) == "/"

    with TestClient(client.app) as replay:
        replay.cookies.set("qb_google_flow", cookie, path="/api/v1/auth/google")
        assert_signed_out_after_failure(replay, call_back(replay, state))


def test_an_expired_flow_fails(
    client: TestClient, google: StandInGoogle, owner_db: Database
) -> None:
    member = make_member(owner_db, "OWNER")
    link_google(owner_db, member.user_id, "sub-1")
    google.accounts["code-1"] = identity("sub-1")
    state = start(client)
    with owner_db.transaction(PLATFORM) as session:
        session.execute(text("UPDATE oauth_flows SET expires_at = now() - interval '1 second'"))

    assert_signed_out_after_failure(client, call_back(client, state))
    assert google.asked == []


def test_cancelling_at_google_fails_and_uses_up_the_flow(
    client: TestClient, google: StandInGoogle, owner_db: Database
) -> None:
    member = make_member(owner_db, "OWNER")
    link_google(owner_db, member.user_id, "sub-1")
    google.accounts["code-1"] = identity("sub-1")
    state = start(client)
    cookie = client.cookies["qb_google_flow"]

    assert call_back(client, state, code=None) == FAILED  # Google sent an error, no code
    client.cookies.set("qb_google_flow", cookie, path="/api/v1/auth/google")  # try again
    assert call_back(client, state) == FAILED


def test_a_code_google_refuses_fails(client: TestClient, google: StandInGoogle) -> None:
    assert_signed_out_after_failure(client, call_back(client, start(client), code="forged"))


@pytest.mark.parametrize(
    "change",
    [
        "UPDATE memberships SET status = 'REMOVED' WHERE user_id = :user_id",
        "UPDATE organizations SET status = 'SUSPENDED' WHERE id = :org_id",
        "UPDATE users SET status = 'DISABLED' WHERE id = :user_id",
    ],
    ids=["member-removed", "coaching-suspended", "account-disabled"],
)
def test_losing_access_while_at_google_stops_the_sign_in(
    client: TestClient, google: StandInGoogle, owner_db: Database, change: str
) -> None:
    member: Member = make_member(owner_db, "FACULTY")
    link_google(owner_db, member.user_id, "sub-1")
    google.accounts["code-1"] = identity("sub-1")
    state = start(client)  # the person leaves for Google...
    with owner_db.transaction(PLATFORM) as session:  # ...and meanwhile loses access
        session.execute(text(change), {"user_id": member.user_id, "org_id": member.org_id})

    assert_signed_out_after_failure(client, call_back(client, state))


def test_the_runtime_role_cannot_touch_the_google_tables(db: Database) -> None:
    for table in ("external_identities", "oauth_flows"):
        with pytest.raises(DBAPIError, match="permission denied"), db.transaction(NO_CONTEXT) as s:
            s.execute(text(f"SELECT * FROM {table}"))  # noqa: S608  (fixed names)
        with pytest.raises(DBAPIError, match="permission denied"), db.transaction(NO_CONTEXT) as s:
            s.execute(text(f"DELETE FROM {table}"))  # noqa: S608


def test_starting_too_often_is_slowed_down(settings: Settings, google: StandInGoogle) -> None:
    strict = settings.model_copy(update={"login_attempts_per_ip": 3})
    app = create_app(strict)
    app.state.google = google
    with TestClient(app) as client:
        codes = [
            client.post(
                START,
                json={"purpose": "SIGN_IN", "return_origin": ORIGIN["Origin"]},
                headers=ORIGIN,
            ).status_code
            for _ in range(4)
        ]

    assert codes == [200, 200, 200, 429]
