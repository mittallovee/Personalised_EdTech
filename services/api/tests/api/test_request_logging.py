"""What the API writes per request: one line, the response's request ID, no forbidden data."""

import io
import json
import logging
from collections.abc import Iterator
from typing import Any
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from qbank.core.logging import configure_logging

TRACE_ID = "4bf92f3577b34da6a3ce929d0e0e4736"
TRACEPARENT = f"00-{TRACE_ID}-00f067aa0ba902b7-01"


@pytest.fixture
def stream() -> Iterator[io.StringIO]:
    out = io.StringIO()
    configure_logging("INFO", service="api", environment="test", stream=out)
    yield out
    root = logging.getLogger()
    root.handlers = [h for h in root.handlers if h.get_name() != "qbank-json"]


@pytest.fixture
def test_client(app: FastAPI) -> TestClient:
    @app.get("/_test/typed/{item_id}")
    def typed(item_id: UUID) -> dict[str, str]:
        return {"id": str(item_id)}

    @app.get("/_test/crash")
    def crash() -> None:
        raise RuntimeError("internal detail")

    return TestClient(app, raise_server_exceptions=False)


def completed(stream: io.StringIO) -> list[dict[str, Any]]:
    lines = [json.loads(line) for line in stream.getvalue().splitlines()]
    return [line for line in lines if line["event"] == "request_completed"]


def test_one_line_per_request_with_the_response_request_id(
    test_client: TestClient, stream: io.StringIO
) -> None:
    response = test_client.get("/_test/typed/" + "0" * 8 + "-0000-0000-0000-" + "0" * 12)

    (line,) = completed(stream)
    assert line["request_id"] == response.headers["X-Request-ID"]
    assert (line["method"], line["status"], line["outcome"]) == ("GET", 200, "ok")
    assert line["service"] == "api" and line["level"] == "info"


def test_the_route_template_is_logged_never_the_raw_path_or_query(
    test_client: TestClient, stream: io.StringIO
) -> None:
    item = "12345678-0000-0000-0000-000000000000"
    test_client.get(f"/_test/typed/{item}?token=QUERYSECRET")
    test_client.get("/no/such/route")

    typed, unknown = completed(stream)
    assert typed["route"] == "/_test/typed/{item_id}"
    assert unknown["route"] == "unmatched"
    assert item not in stream.getvalue() and "QUERYSECRET" not in stream.getvalue()


def test_a_valid_traceparent_gives_the_trace_id_and_a_bad_one_is_ignored(
    test_client: TestClient, stream: io.StringIO
) -> None:
    test_client.get("/_test/typed/" + str(UUID(int=1)), headers={"traceparent": TRACEPARENT})
    zeros = f"00-{'0' * 32}-00f067aa0ba902b7-01"
    test_client.get("/_test/typed/" + str(UUID(int=1)), headers={"traceparent": zeros})
    test_client.get("/_test/typed/" + str(UUID(int=1)), headers={"traceparent": "garbage"})

    good, zero, bad = completed(stream)
    assert good["trace_id"] == TRACE_ID
    assert "trace_id" not in zero and "trace_id" not in bad


def test_server_errors_are_logged_at_error_level_with_the_traceback(
    test_client: TestClient, stream: io.StringIO
) -> None:
    response = test_client.get("/_test/crash")

    lines = [json.loads(line) for line in stream.getvalue().splitlines()]
    crashed = next(line for line in lines if line["event"] == "unhandled_error")
    assert "RuntimeError" in crashed["exception"]
    assert crashed["request_id"] == response.headers["X-Request-ID"]
    (done,) = completed(stream)
    assert (done["level"], done["status"], done["outcome"]) == ("error", 500, "server_error")


def test_health_checks_are_not_logged_when_they_succeed(
    test_client: TestClient, stream: io.StringIO
) -> None:
    test_client.get("/health/live")

    assert completed(stream) == []


def test_credentials_in_a_request_never_reach_the_logs(
    test_client: TestClient, stream: io.StringIO
) -> None:
    # The database is unreachable in this test, so the sign-in fails; the failure is logged.
    credentials = {"email": "ann.bait@example.com", "password": "hunter2-bait-pw"}  # gitleaks:allow
    test_client.post(
        "/api/v1/auth/login?token=QUERYSECRET",
        json=credentials,
        headers={
            "Authorization": "Bearer headerbait0123456789",
            "Cookie": "qb_session=cookiebait0123456789",
            "X-CSRF-Token": "csrfbait",
        },
    )

    output = stream.getvalue()
    assert output  # something was logged, so the checks below mean something
    for bait in ("ann.bait", "hunter2", "headerbait", "cookiebait", "csrfbait", "QUERYSECRET"):
        assert bait not in output
