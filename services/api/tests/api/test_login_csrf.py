"""Codex review on #4: a malicious site must not sign a victim's browser in ("login CSRF").

A cross-site HTML form can only send form-encoded, multipart or text/plain bodies. The login
endpoint accepts JSON only (FastAPI does not parse a text/plain body as JSON), so such a form
fails before any lookup and no session cookie is set. A cross-site script sending real JSON
needs CORS approval, which this API does not grant.

These tests send no ``Origin`` header so they check this layer on its own; the Origin allow-list
in front of it is tested in ``test_origin_check.py``.
"""

from fastapi.testclient import TestClient

from qbank.core.config import AppEnv, Settings
from qbank.main import create_app
from tests.conftest import UNREACHABLE_DB

JSON_LOOKING_BODY = '{"email": "attacker@example.com", "password": "attackers-password"}'


def make_client() -> TestClient:
    settings = Settings(app_env=AppEnv.TEST, database_url=UNREACHABLE_DB)
    return TestClient(create_app(settings), raise_server_exceptions=False)


def test_text_plain_form_with_json_shaped_body_is_rejected() -> None:
    response = make_client().post(
        "/api/v1/auth/login",
        content=JSON_LOOKING_BODY,
        headers={"Content-Type": "text/plain"},
    )

    assert response.status_code == 400  # never reaches the database (which is unreachable here)
    assert "set-cookie" not in response.headers


def test_url_encoded_form_is_rejected() -> None:
    response = make_client().post(
        "/api/v1/auth/login",
        data={"email": "attacker@example.com", "password": "attackers-password"},
    )

    assert response.status_code == 400
    assert "set-cookie" not in response.headers


def test_cross_origin_requests_get_no_cors_permission() -> None:
    preflight = make_client().options(
        "/api/v1/auth/login",
        headers={
            "Origin": "https://evil.example",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert "access-control-allow-origin" not in preflight.headers
