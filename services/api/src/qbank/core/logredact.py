"""Safety net that keeps secrets, personal data and coaching content out of logs (ADR-0019).

The first defence is that code logs identifiers, never content. This is the second: every log line
passes through ``redact_event`` just before it is written, so a mistake does not reach the logs, the
log store or a trace. It blanks fields whose names say they hold something forbidden, and rewrites
text that looks like a token, a password, a bearer header, a sign-in cookie or a database error
detail (which can quote the row's values).
"""

import re
from collections.abc import Mapping, MutableMapping
from typing import Any

REDACTED = "[redacted]"
_MAX_DEPTH = 6

# Field names (lower case, "-" as "_") that never carry a value into a log.
# fmt: off
_FORBIDDEN_KEYS = frozenset({
    # secrets and credentials
    "password", "passwd", "password_hash", "secret", "client_secret", "token", "authorization",
    "cookie", "cookies", "set_cookie", "headers", "api_key", "apikey", "code_verifier", "nonce",
    "link", "activation_link", "reset_link", "dsn",
    # personal data (people appear as user_id)
    "email", "email_address", "phone", "mobile", "display_name", "full_name", "first_name",
    "last_name", "filename",
    # coaching and question content, and anything that can hold it
    "body", "request_body", "response_body", "content", "blocks", "stem", "option", "options",
    "solution", "explanation", "answer", "answers", "question_text", "payload", "file_content",
})
# fmt: on
_FORBIDDEN_SUFFIXES = ("_token", "_secret", "_password", "_link", "_cookie", "_api_key")
# Identifiers we generate or validate ourselves: never rewritten, so a log line still matches the
# ID the person sees (the response header, the error screen).
_ID_KEYS = frozenset({"request_id", "trace_id", "span_id", "job_id", "timestamp"})

_TEXT_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(?i)\b(bearer|basic)\s+[A-Za-z0-9._~+/=-]{8,}"), rf"\1 {REDACTED}"),
    (
        re.compile(
            r"(?i)\b(qb_session|csrf_token|x-csrf-token|password|passwd|secret|api_key|token)"
            r"([=:]\s*)[^\s&;,\"']+"
        ),
        rf"\1\2{REDACTED}",
    ),
    (re.compile(r"(?i)([?&](?:code|state|token|key)=)[^\s&\"']+"), rf"\1{REDACTED}"),
    # PostgreSQL error detail such as: Key (email)=(a@b.c) already exists.
    (re.compile(r"\bKey \([^)]*\)=\([^)]*\)"), f"Key {REDACTED}"),
    # Anything shaped like a random token (secrets.token_urlsafe gives 43+ characters).
    (re.compile(r"[A-Za-z0-9_-]{40,}"), REDACTED),
)


def scrub_text(text: str) -> str:
    for pattern, replacement in _TEXT_RULES:
        text = pattern.sub(replacement, text)
    return text


def _is_forbidden_key(key: str) -> bool:
    name = key.lower().replace("-", "_")
    return name in _FORBIDDEN_KEYS or name.endswith(_FORBIDDEN_SUFFIXES)


def _clean(key: str, value: Any, depth: int) -> Any:
    if _is_forbidden_key(key):
        return REDACTED
    if value is None or isinstance(value, bool | int | float) or key in _ID_KEYS:
        return value
    if isinstance(value, str):
        return scrub_text(value)
    if depth >= _MAX_DEPTH:
        return REDACTED
    if isinstance(value, Mapping):
        return {str(k): _clean(str(k), v, depth + 1) for k, v in value.items()}
    if isinstance(value, list | tuple | set | frozenset):
        return [_clean(key, item, depth + 1) for item in value]
    return scrub_text(str(value))  # UUIDs, datetimes, exceptions, anything else


def redact_event(
    _logger: Any, _method: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    """A structlog processor: the last step before a line is rendered."""
    return {key: _clean(key, value, 0) for key, value in event_dict.items()}
