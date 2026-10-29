"""Nothing forbidden may reach the logs (ADR-0019 decision 3): secrets, tokens, personal data and
coaching content are blanked by the log pipeline even when code logs them by mistake."""

import io
import json
import logging
import secrets
from collections.abc import Iterator
from typing import Any

import pytest
import structlog

from qbank.core.logging import (
    add_log_context,
    begin_log_context,
    configure_logging,
    end_log_context,
)

TOKEN = secrets.token_urlsafe(32)  # 43 characters, like our real tokens; made fresh per run
BAITS = {
    "password": "hunter2-correct-horse",
    "csrf_token": "csrf-bait-value",
    "session_token": TOKEN,
    "authorization": "Bearer abcdefghij0123456789",
    "cookie": "qb_session=cookiebait12345",
    "activation_link": "http://localhost:3000/activate#" + TOKEN,
    "api_key": "sk-live-bait-key",
    "email": "ann.bait@example.com",
    "stem": "Find the bait integral of x squared",
    "options": ["bait option A", "bait option B"],
    "solution": "bait worked solution",
    "payload": {"stem": "bait payload stem"},
    "headers": {"x-bait": "bait header"},
}


@pytest.fixture
def stream() -> Iterator[io.StringIO]:
    out = io.StringIO()
    configure_logging("DEBUG", service="api", environment="test", stream=out)
    yield out
    root = logging.getLogger()
    root.handlers = [h for h in root.handlers if h.get_name() != "qbank-json"]


def lines(stream: io.StringIO) -> list[dict[str, Any]]:
    return [json.loads(line) for line in stream.getvalue().splitlines()]


def test_forbidden_fields_are_blanked(stream: io.StringIO) -> None:
    structlog.get_logger("test").info("something_happened", **BAITS, harmless="visible")

    output = stream.getvalue()
    for value in BAITS.values():
        assert json.dumps(value) not in output
    for bait in ("hunter2", "cookiebait", "bait option", "bait header", "ann.bait", TOKEN):
        assert bait not in output
    line = lines(stream)[0]
    assert line["harmless"] == "visible"
    assert line["event"] == "something_happened"


def test_secrets_inside_free_text_are_blanked(stream: io.StringIO) -> None:
    log = structlog.get_logger("test")
    log.warning("callback https://x.test/cb?code=oauthbait&state=statebait failed")
    log.warning("sent Authorization: Bearer abcdefghij0123456789")
    log.warning("login with password=hunter2bait for user")
    log.warning("duplicate: Key (email)=(ann.bait@example.com) already exists.")
    log.warning("token", detail=f"link was http://localhost/activate#{TOKEN}")

    output = stream.getvalue()
    for bait in ("oauthbait", "statebait", "abcdefghij", "hunter2bait", "ann.bait", TOKEN):
        assert bait not in output


def test_exception_text_is_scrubbed_but_still_reported(stream: io.StringIO) -> None:
    try:
        raise ValueError(f"bad token {TOKEN} for Key (email)=(ann.bait@example.com)")
    except ValueError:
        structlog.get_logger("test").exception("handler_crashed")

    output = stream.getvalue()
    assert TOKEN not in output
    assert "ann.bait" not in output
    assert "ValueError" in lines(stream)[0]["exception"]


def test_library_logs_use_the_same_json_shape_and_are_scrubbed(stream: io.StringIO) -> None:
    logging.getLogger("sqlalchemy.engine").warning("INSERT failed, password=hunter2bait")
    logging.getLogger("uvicorn.error").warning("worker note")

    first, second = lines(stream)
    assert first["event"] == "INSERT failed, password=[redacted]"
    for line in (first, second):
        assert line["service"] == "api" and line["env"] == "test"
        assert {"timestamp", "level", "logger"} <= line.keys()


def test_request_ids_are_not_rewritten(stream: io.StringIO) -> None:
    begin_log_context(request_id="client-supplied-id-" + "x" * 45)
    structlog.get_logger("test").info("with_id")
    end_log_context()

    assert lines(stream)[0]["request_id"] == "client-supplied-id-" + "x" * 45


def test_ids_added_later_reach_every_later_line(stream: io.StringIO) -> None:
    begin_log_context(request_id="req_1")
    add_log_context(user_id="u-1", organization_id="o-1", ignored=None)
    structlog.get_logger("test").info("later")
    end_log_context()
    structlog.get_logger("test").info("outside")

    inside, outside = lines(stream)
    assert (inside["request_id"], inside["user_id"], inside["organization_id"]) == (
        "req_1",
        "u-1",
        "o-1",
    )
    assert "ignored" not in inside
    assert "request_id" not in outside
