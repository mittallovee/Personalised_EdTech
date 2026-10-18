"""Structured JSON logging and per-request IDs (ADR-0010)."""

import logging
import re
import sys
import time
from collections.abc import Awaitable, Callable

import structlog
from fastapi import FastAPI, Request, Response

from qbank.core.errors import internal_error_response
from qbank.core.ids import new_id

REQUEST_ID_HEADER = "X-Request-ID"
# Accept a caller's request ID only if it is short and harmless; otherwise generate our own.
_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")

log = structlog.get_logger("qbank.http")


def configure_logging(level: str) -> None:
    """Log one JSON object per line to stdout, including any context bound for the request."""
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level.upper())
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(level.upper())),
        cache_logger_on_first_use=True,
    )


def install_request_logging(app: FastAPI) -> None:
    """Give every request an ID (echoed in the response) and log one line when it finishes.

    Middleware wraps the exception handlers, so error responses get the ID header too.
    """

    @app.middleware("http")
    async def request_context(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        incoming = request.headers.get(REQUEST_ID_HEADER, "")
        request_id = incoming if _SAFE_REQUEST_ID.match(incoming) else f"req_{new_id().hex}"
        request.state.request_id = request_id
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            # Unexpected bug: log the traceback with the request ID, answer with a safe 500 that
            # still carries the ID header so the client can report it.
            log.exception("unhandled_error", method=request.method, path=request.url.path)
            response = internal_error_response(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        log.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=round((time.perf_counter() - started) * 1000, 1),
        )
        return response
