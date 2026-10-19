"""Codex review on #4: login must be throttled before any database lookup or password hashing."""

from fastapi.testclient import TestClient

from qbank.core.config import AppEnv, Settings
from qbank.main import create_app
from tests.conftest import UNREACHABLE_DB


def make_client(per_ip: int, per_email: int) -> TestClient:
    settings = Settings(
        app_env=AppEnv.TEST,
        database_url=UNREACHABLE_DB,
        login_attempts_per_ip=per_ip,
        login_attempts_per_email=per_email,
    )
    return TestClient(create_app(settings), raise_server_exceptions=False)


def attempt(client: TestClient, email: str = "someone@example.com") -> int:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": "x"})
    return response.status_code


def test_too_many_attempts_from_one_address_get_429_without_touching_the_database() -> None:
    client = make_client(per_ip=2, per_email=100)

    # The database is unreachable, so attempts that pass the limiter fail with 500 —
    # the third one must be stopped before it gets that far.
    assert [attempt(client, f"user{i}@example.com") for i in range(3)] == [500, 500, 429]


def test_too_many_attempts_for_one_email_get_429() -> None:
    client = make_client(per_ip=100, per_email=2)

    assert [attempt(client) for _ in range(3)] == [500, 500, 429]
    assert attempt(client, "other@example.com") == 500  # a different account is not blocked


def test_rate_limited_response_says_when_to_retry() -> None:
    client = make_client(per_ip=1, per_email=100)
    attempt(client)

    response = client.post("/api/v1/auth/login", json={"email": "a@example.com", "password": "x"})

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "RATE_LIMITED"
    assert int(response.headers["Retry-After"]) > 0
