"""Shared by the Google sign-in tests: a stand-in for Google, and the steps of a flow."""

from dataclasses import dataclass, field
from urllib.parse import parse_qs, urlencode, urlparse
from uuid import UUID

from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy import text

from qbank.core.db import Database
from qbank.modules.identity.google import GoogleError, GoogleIdentity
from tests.integration.conftest import ORIGIN, PLATFORM

START = "/api/v1/auth/google/start"
CALLBACK = "/api/v1/auth/google/callback"
FAILED = "/login?google=failed"


@dataclass
class StandInGoogle:
    """Plays Google: hands out an address, and turns codes into Google accounts."""

    accounts: dict[str, GoogleIdentity] = field(default_factory=dict)
    asked: list[dict[str, str]] = field(default_factory=list)

    def authorization_url(
        self, *, redirect_uri: str, state: str, nonce: str, code_challenge: str
    ) -> str:
        query = {
            "redirect_uri": redirect_uri,
            "state": state,
            "nonce": nonce,
            "code_challenge": code_challenge,
        }
        return "https://google.test/auth?" + urlencode(query)

    def identify(
        self, *, code: str, redirect_uri: str, code_verifier: str, nonce: str
    ) -> GoogleIdentity:
        self.asked.append(
            {
                "code": code,
                "redirect_uri": redirect_uri,
                "code_verifier": code_verifier,
                "nonce": nonce,
            }
        )
        if code not in self.accounts:
            raise GoogleError("Google refused the code")
        return self.accounts[code]


def link_google(owner_db: Database, user_id: UUID, subject: str, email: str | None = None) -> None:
    with owner_db.transaction(PLATFORM) as session:
        session.execute(
            text(
                "INSERT INTO external_identities (user_id, provider, subject, email_at_link)"
                " VALUES (:user_id, 'google', :subject, :email)"
            ),
            {"user_id": user_id, "subject": subject, "email": email},
        )


def identity(subject: str, email: str = "someone@example.com") -> GoogleIdentity:
    return GoogleIdentity(subject=subject, email=email, email_verified=True)


def start(client: TestClient) -> str:
    """Start a flow; return the ``state`` Google would send back. The pending cookie is kept."""
    response = client.post(
        START, json={"purpose": "SIGN_IN", "return_origin": ORIGIN["Origin"]}, headers=ORIGIN
    )
    assert response.status_code == 200, response.text
    query = parse_qs(urlparse(response.json()["authorization_url"]).query)
    return query["state"][0]


def call_back(client: TestClient, state: str, code: str | None = "code-1") -> str:
    """Google sends the browser back; return where the browser is redirected to."""
    params = {"state": state, **({"code": code} if code else {})}
    response = client.get(CALLBACK, params=params, follow_redirects=False)
    assert response.status_code == 303
    return response.headers["location"]


def assert_signed_out_after_failure(client: TestClient, location: str) -> None:
    assert location == FAILED  # one answer for every failure
    assert "qb_session" not in client.cookies
    assert client.get("/api/v1/me").status_code == 401


def start_activation(client: TestClient, link_token: str | None) -> Response:
    """Start a flow that activates an invited account with Google. The pending cookie is kept."""
    body = {"purpose": "ACTIVATE", "return_origin": ORIGIN["Origin"], "link_token": link_token}
    return client.post(START, json=body, headers=ORIGIN)


def state_of(response: Response) -> str:
    return parse_qs(urlparse(response.json()["authorization_url"]).query)["state"][0]
