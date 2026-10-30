"""Structured JSON logging with request, trace, organization and user IDs (ADR-0010, ADR-0019).

Every line, from our code and from libraries (uvicorn, SQLAlchemy, Alembic), is one JSON object with
the same fields. IDs for the current request or job are kept in a small dictionary that all code
running for it shares, even code that FastAPI runs in a worker thread, and are added to every line.
Nothing reaches the output without passing ``redact_event``.
"""

import logging
import re
import sys
import time
from collections.abc import Awaitable, Callable, MutableMapping
from contextvars import ContextVar
from typing import Any, TextIO

import structlog
from fastapi import FastAPI, Request, Response

from qbank.core.errors import internal_error_response
from qbank.core.ids import new_id
from qbank.core.logredact import redact_event
from qbank.core.telemetry import add_trace_ids

REQUEST_ID_HEADER = "X-Request-ID"
TRACEPARENT_HEADER = "traceparent"
# Accept a caller's request ID only if it is short and harmless; otherwise generate our own.
_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
# W3C Trace Context: version-traceid-spanid-flags. All-zero IDs are invalid.
_TRACEPARENT = re.compile(r"^00-(?!0{32})([0-9a-f]{32})-(?!0{16})[0-9a-f]{16}-[0-9a-f]{2}$")
_OUR_HANDLER = "qbank-json"

log = structlog.get_logger("qbank.http")

_event_context: ContextVar[dict[str, Any] | None] = ContextVar("log_event_context", default=None)


def begin_log_context(**fields: Any) -> None:
    """Start the IDs for one request or job. Later ``add_log_context`` calls, from any thread
    started by that request, add to the same dictionary."""
    _event_context.set({k: v for k, v in fields.items() if v is not None})


def add_log_context(**fields: Any) -> None:
    """Add IDs once they are known (e.g. the signed-in user). No effect outside a request or job."""
    current = _event_context.get()
    if current is not None:
        current.update({k: v for k, v in fields.items() if v is not None})


def end_log_context() -> None:
    _event_context.set(None)


def trace_id_from(traceparent: str | None) -> str | None:
    """The trace ID of a valid W3C ``traceparent`` header, else None."""
    match = _TRACEPARENT.match(traceparent or "")
    return match.group(1) if match else None


def _merge_event_context(
    _logger: Any, _method: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    for key, value in (_event_context.get() or {}).items():
        event_dict.setdefault(key, value)
    return event_dict


def configure_logging(
    level: str,
    *,
    service: str = "api",
    environment: str = "local",
    stream: TextIO | None = None,
) -> None:
    """Log one JSON object per line to stdout (or ``stream``), from our code and libraries alike."""

    def add_service(
        _l: Any, _m: str, event_dict: MutableMapping[str, Any]
    ) -> MutableMapping[str, Any]:
        event_dict.setdefault("service", service)
        event_dict.setdefault("env", environment)
        return event_dict

    shared: list[Any] = [
        structlog.contextvars.merge_contextvars,
        _merge_event_context,
        add_trace_ids,
        add_service,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            *shared,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    handler = logging.StreamHandler(stream or sys.stdout)
    handler.set_name(_OUR_HANDLER)
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=shared,
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                redact_event,
                structlog.processors.JSONRenderer(),
            ],
        )
    )
    root = logging.getLogger()
    # Replace only our own handler, so repeated calls (tests) neither double the output nor remove
    # handlers that other tools attached.
    for existing in [h for h in root.handlers if h.get_name() == _OUR_HANDLER]:
        root.removeHandler(existing)
    root.addHandler(handler)
    root.setLevel(level.upper())
    # uvicorn installs its own plain-text handlers; hand its loggers to ours. Its access line is
    # replaced by the richer "request_completed" below.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = True
    logging.getLogger("uvicorn.access").disabled = True
    # HTTP client libraries log the full URL of every outgoing call, query string included.
    for name in ("httpx", "httpx2", "httpcore", "urllib3"):
        logging.getLogger(name).setLevel(logging.WARNING)


def _route_of(request: Request) -> str:
    """The route template (``/api/v1/questions/{id}``), never the raw path or the query string."""
    return str(getattr(request.scope.get("route"), "path", "unmatched"))


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
        begin_log_context(
            request_id=request_id, trace_id=trace_id_from(request.headers.get(TRACEPARENT_HEADER))
        )

        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            # Unexpected bug: log the traceback with the request ID, answer with a safe 500 that
            # still carries the ID header so the client can report it.
            log.exception("unhandled_error", method=request.method, route=_route_of(request))
            response = internal_error_response(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        status = response.status_code
        # Health checks run every few seconds: keep them out of the way unless something is wrong.
        quiet = request.url.path.startswith("/health/") and status < 400
        log.log(
            logging.DEBUG if quiet else logging.ERROR if status >= 500 else logging.INFO,
            "request_completed",
            method=request.method,
            route=_route_of(request),
            status=status,
            outcome="server_error" if status >= 500 else "client_error" if status >= 400 else "ok",
            duration_ms=round((time.perf_counter() - started) * 1000, 1),
        )
        end_log_context()
        return response
