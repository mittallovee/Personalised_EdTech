"""Traces: follow one request through the API, the database and the worker (ADR-0019).

A *trace* is the story of one request; a *span* is one step in it (the request, one SQL statement,
one job run). The spans here are written by hand, not by an automatic instrumentation library, so
nothing is recorded that we did not choose: attributes are identifiers, route templates and SQL
text with placeholders. Never a URL with its query string, a header, a body or a bind value.

Log lines travel the same way: when the endpoint is set, each finished (already redacted) JSON line
is also sent to the Collector, so Loki can search it and link it to its trace.

Everything is off, and almost free, until ``OTEL_EXPORTER_OTLP_ENDPOINT`` is set.
"""

import logging
import time
from collections.abc import Awaitable, Callable, Iterator
from contextlib import contextmanager
from typing import Any

from fastapi import FastAPI, Request, Response
from opentelemetry import trace
from opentelemetry._logs import LogRecord, SeverityNumber
from opentelemetry.context import Context, get_current
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased
from opentelemetry.trace import Span, SpanKind, Status, StatusCode
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from sqlalchemy import Connection, Engine, event
from sqlalchemy.engine import ExceptionContext
from sqlalchemy.engine.interfaces import DBAPICursor, ExecutionContext

from qbank.core.config import Settings
from qbank.core.logredact import scrub_text

_propagator = TraceContextTextMapPropagator()
_provider: TracerProvider | None = None
_MAX_STATEMENT = 500


def use_provider(provider: TracerProvider | None) -> None:
    """Choose where spans go (tests pass an in-memory one). None turns tracing off."""
    global _provider
    _provider = provider


def setup_tracing(settings: Settings, service: str) -> None:
    """Send spans to the OTLP endpoint when one is configured; otherwise do nothing."""
    if not settings.otel_exporter_otlp_endpoint:
        return
    endpoint = settings.otel_exporter_otlp_endpoint.rstrip("/") + "/v1/traces"
    provider = TracerProvider(
        resource=Resource.create(
            {"service.name": f"qbank-{service}", "deployment.environment": settings.app_env.value}
        ),
        sampler=ParentBased(TraceIdRatioBased(settings.otel_traces_sample_ratio)),
    )
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
    use_provider(provider)
    logs = LoggerProvider(resource=provider.resource)
    logs.add_log_record_processor(
        BatchLogRecordProcessor(
            OTLPLogExporter(endpoint=settings.otel_exporter_otlp_endpoint.rstrip("/") + "/v1/logs")
        )
    )
    attach_log_shipper(logs)


_SHIPPER = "qbank-otlp"
# Records about the exporting itself must not be exported (they would feed on each other).
_NOT_SHIPPED = ("opentelemetry", "urllib3", "requests", "httpcore", "httpx")
_SEVERITY = {
    logging.DEBUG: SeverityNumber.DEBUG,
    logging.INFO: SeverityNumber.INFO,
    logging.WARNING: SeverityNumber.WARN,
    logging.ERROR: SeverityNumber.ERROR,
    logging.CRITICAL: SeverityNumber.FATAL,
}


class _LogShipper(logging.Handler):
    """Sends each log line to the OTLP endpoint as the body of one log record.

    The body is the line our own formatter wrote, after redaction. Nothing else is attached: the
    standard OpenTelemetry handler would add the raw exception message and stack trace as
    attributes, bypassing the redaction.
    """

    def __init__(self, provider: LoggerProvider) -> None:
        super().__init__()
        self.set_name(_SHIPPER)
        self._logger = provider.get_logger("qbank")
        self.addFilter(lambda record: not record.name.startswith(_NOT_SHIPPED))

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._logger.emit(
                LogRecord(
                    timestamp=int(record.created * 1e9),
                    observed_timestamp=time.time_ns(),
                    context=get_current(),  # carries the trace and span IDs
                    severity_text=record.levelname,
                    severity_number=_SEVERITY.get(record.levelno, SeverityNumber.INFO),
                    body=self.format(record),
                )
            )
        except Exception:
            self.handleError(record)


def attach_log_shipper(provider: LoggerProvider) -> None:
    """Add the shipper to the root logger, reusing the JSON formatter of the stdout handler."""
    root = logging.getLogger()
    shipper = _LogShipper(provider)
    for existing in list(root.handlers):
        if existing.get_name() == _SHIPPER:
            root.removeHandler(existing)
        elif existing.formatter is not None and existing.get_name() == "qbank-json":
            shipper.setFormatter(existing.formatter)
    root.addHandler(shipper)


def tracer() -> trace.Tracer:
    return (_provider or trace.get_tracer_provider()).get_tracer("qbank")


def add_trace_ids(_logger: Any, _method: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    """A log processor: put the current trace and span IDs on the line, so a log line leads to its
    trace and a trace leads to its log lines."""
    context = trace.get_current_span().get_span_context()
    if context.is_valid:
        event_dict["trace_id"] = format(context.trace_id, "032x")
        event_dict["span_id"] = format(context.span_id, "016x")
    return event_dict


def current_traceparent() -> str | None:
    """The W3C ``traceparent`` of the current span, to store with work that runs later."""
    carrier: dict[str, str] = {}
    _propagator.inject(carrier)
    return carrier.get("traceparent")


def _parent(traceparent: str | None) -> Context | None:
    return _propagator.extract({"traceparent": traceparent}) if traceparent else None


# Spans are opened with record_exception=False and set_status_on_exception=False: by default an
# exception that escapes a span is recorded with its message and traceback, and the message is
# copied into the status. Database errors quote the statement and its values, which can hold job
# payloads or coaching content. So we record the exception *type* only, with mark_error.
def mark_error(kind: str) -> None:
    """Mark the current span failed. Only the exception *type*: messages can hold content."""
    span = trace.get_current_span()
    span.set_attribute("error.type", kind)
    span.set_status(Status(StatusCode.ERROR))


def install_request_tracing(app: FastAPI) -> None:
    """One server span per request. Install after the request logging, so it is outermost and the
    log lines of the request carry its trace and span IDs."""

    @app.middleware("http")
    async def request_trace(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if request.url.path.startswith("/health/"):  # polled every few seconds: not worth a trace
            return await call_next(request)
        with tracer().start_as_current_span(
            request.method,
            context=_parent(request.headers.get("traceparent")),
            kind=SpanKind.SERVER,
            attributes={"http.request.method": request.method},
            record_exception=False,
            set_status_on_exception=False,
        ) as span:
            response = await call_next(request)
            route = str(getattr(request.scope.get("route"), "path", "unmatched"))
            span.update_name(f"{request.method} {route}")
            span.set_attribute("http.route", route)
            span.set_attribute("http.response.status_code", response.status_code)
            if (request_id := getattr(request.state, "request_id", None)) is not None:
                span.set_attribute("request.id", request_id)
            if (principal := getattr(request.state, "principal", None)) is not None:
                span.set_attribute("enduser.id", str(principal.user_id))
                org = principal.tenant_context.organization_id
                if org is not None:
                    span.set_attribute("organization.id", str(org))
            if response.status_code >= 500:
                span.set_status(Status(StatusCode.ERROR))
            return response


@contextmanager
def job_span(
    *,
    job_id: str,
    job_type: str,
    attempt: int,
    organization_id: str | None,
    request_id: str | None,
    traceparent: str | None,
) -> Iterator[Span]:
    """One span for a run of a job, a child of the request that created it when that was traced."""
    attributes: dict[str, str | int] = {
        "job.id": job_id,
        "job.type": job_type,
        "job.attempt": attempt,
    }
    if organization_id:
        attributes["organization.id"] = organization_id
    if request_id:
        attributes["request.id"] = request_id
    with tracer().start_as_current_span(
        f"job {job_type}",
        context=_parent(traceparent),
        kind=SpanKind.CONSUMER,
        attributes=attributes,
        record_exception=False,
        set_status_on_exception=False,
    ) as span:
        try:
            yield span
        except BaseException as exc:
            mark_error(type(exc).__name__)
            raise


def instrument_database(engine: Engine) -> None:
    """One span per SQL statement: the statement text with its placeholders, never the values."""

    @event.listens_for(engine, "before_cursor_execute")
    def start(
        conn: Connection,
        _cursor: DBAPICursor,
        statement: str,
        _parameters: Any,
        _context: ExecutionContext | None,
        _executemany: bool,
    ) -> None:
        if not trace.get_current_span().is_recording():
            return
        verb = statement.lstrip().split(None, 1)[0].upper() if statement.strip() else "SQL"
        span = tracer().start_span(
            f"db {verb}",
            kind=SpanKind.CLIENT,
            attributes={
                "db.system": "postgresql",
                "db.operation": verb,
                "db.statement": scrub_text(statement)[:_MAX_STATEMENT],
            },
        )
        open_spans: list[Span] = conn.info.setdefault("qbank_spans", [])
        open_spans.append(span)

    @event.listens_for(engine, "after_cursor_execute")
    def finish(
        conn: Connection,
        _cursor: DBAPICursor,
        _statement: str,
        _parameters: Any,
        _context: ExecutionContext | None,
        _executemany: bool,
    ) -> None:
        if conn.info.get("qbank_spans"):
            conn.info["qbank_spans"].pop().end()

    @event.listens_for(engine, "handle_error")
    def failed(context: ExceptionContext) -> None:
        conn = context.connection
        if conn is not None and conn.info.get("qbank_spans"):
            span = conn.info["qbank_spans"].pop()
            span.set_attribute("error.type", type(context.original_exception).__name__)
            span.set_status(Status(StatusCode.ERROR))
            span.end()
