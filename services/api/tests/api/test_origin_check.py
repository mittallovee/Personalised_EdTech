"""Owner decision (19 Oct, Codex review on #4): changes must come from our own web app's address.

Browsers always send ``Origin`` (or at least ``Referer``) with a cross-site POST, so a request a
malicious site makes a victim's browser send is refused before any handler runs. Requests with
neither header come from non-browser clients, which carry no victim's cookies, and are let through
to the normal authentication and CSRF checks.
"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from qbank.core.config import AppEnv, Settings
from qbank.main import create_app
from tests.conftest import UNREACHABLE_DB

WEB_APP = "http://localhost:3000"
MALFORMED_LOGIN = {"email": "not-an-email"}  # fails validation (400) once past the origin check


@pytest.fixture
def client() -> Iterator[TestClient]:
    settings = Settings(app_env=AppEnv.TEST, database_url=UNREACHABLE_DB, allowed_origins=[WEB_APP])
    with TestClient(create_app(settings), raise_server_exceptions=False) as test_client:
        yield test_client


def login(client: TestClient, headers: dict[str, str]) -> int:
    response = client.post("/api/v1/auth/login", json=MALFORMED_LOGIN, headers=headers)
    return response.status_code


@pytest.mark.parametrize(
    "headers",
    [
        {"Origin": "https://evil.example"},
        {"Origin": "http://localhost:3001"},  # same host, different port: a different origin
        {"Origin": "null"},  # sandboxed frames and some redirects send this
        {"Referer": "https://evil.example/page"},
        {"Origin": "https://evil.example", "Referer": "http://localhost:3000/login"},
    ],
)
def test_change_from_another_site_is_refused(client: TestClient, headers: dict[str, str]) -> None:
    response = client.post("/api/v1/auth/login", json=MALFORMED_LOGIN, headers=headers)

    assert response.status_code == 403
    body = response.json()["error"]
    assert body["code"] == "ORIGIN_NOT_ALLOWED"
    assert body["request_id"] == response.headers["X-Request-ID"]
    assert "set-cookie" not in response.headers


@pytest.mark.parametrize(
    "headers",
    [
        {"Origin": WEB_APP},
        {"Origin": "HTTP://LOCALHOST:3000"},  # scheme and host are case-insensitive
        {"Referer": "http://localhost:3000/login?next=/home"},
        {},  # no browser involved (scripts, server-to-server, tests)
    ],
)
def test_change_from_the_web_app_or_a_non_browser_client_passes(
    client: TestClient, headers: dict[str, str]
) -> None:
    assert login(client, headers) == 400  # reached request validation


def test_reading_is_never_blocked_by_origin(client: TestClient) -> None:
    response = client.get("/health/live", headers={"Origin": "https://evil.example"})

    assert response.status_code == 200


@pytest.mark.parametrize(
    "origins",
    [
        ["http://localhost:3000/"],  # trailing slash: not an origin
        ["http://localhost:3000/login"],  # has a path
        ["localhost:3000"],  # no scheme
        ["*"],
    ],
)
def test_allowed_origins_must_be_plain_origins(origins: list[str]) -> None:
    with pytest.raises(ValidationError, match="ALLOWED_ORIGINS"):
        Settings(app_env=AppEnv.TEST, database_url=UNREACHABLE_DB, allowed_origins=origins)


def test_hosted_environments_require_https_origins() -> None:
    with pytest.raises(ValidationError, match="https"):
        Settings(
            app_env=AppEnv.PRODUCTION,
            database_url=UNREACHABLE_DB,
            allowed_origins=["http://app.example.com"],
        )


def test_default_ports_are_canonicalised_like_browsers_do() -> None:
    settings = Settings(
        app_env=AppEnv.TEST,
        database_url=UNREACHABLE_DB,
        allowed_origins=["https://app.example.com:443", "http://localhost:80"],
    )
    assert settings.allowed_origins == ["https://app.example.com", "http://localhost"]

    with TestClient(create_app(settings), raise_server_exceptions=False) as client:
        browser_origin = {"Origin": "https://app.example.com"}  # browsers omit default ports
        explicit_referer = {"Referer": "https://app.example.com:443/login"}

        assert login(client, browser_origin) == 400  # reached request validation
        assert login(client, explicit_referer) == 400
