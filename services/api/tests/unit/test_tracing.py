"""Traces (ADR-0019): a span per request, the caller's trace continued, nothing secret recorded."""

import io
import json
import logging
from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from qbank.core import telemetry
from qbank.core.logging import configure_logging

TRACE_ID = "4bf92f3577b34da6a3ce929d0e0e4736"
TRACEPARENT = f"00-{TRACE_ID}-00f067aa0ba902b7-01"


@pytest.fixture
def spans() -> Iterator[InMemorySpanExporter]:
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    telemetry.use_provider(provider)
    yield exporter
    telemetry.use_provider(None)


@pytest.fixture
def stream() -> Iterator[io.StringIO]:
    out = io.StringIO()
    configure_logging("INFO", service="api", environment="test", stream=out)
    yield out
    root = logging.getLogger()
    root.handlers = [h for h in root.handlers if h.get_name() != "qbank-json"]


@pytest.fixture
def test_client(app: FastAPI) -> TestClient:
    @app.get("/_test/item/{item_id}")
    def item(item_id: int) -> dict[str, int]:
        return {"id": item_id}

    @app.get("/_test/crash")
    def crash() -> None:
        raise RuntimeError("secret internal detail")

    return TestClient(app, raise_server_exceptions=False)


def finished(exporter: InMemorySpanExporter) -> list[ReadableSpan]:
    return list(exporter.get_finished_spans())


def test_a_request_is_one_server_span_named_by_its_route_template(
    test_client: TestClient, spans: InMemorySpanExporter
) -> None:
    response = test_client.get("/_test/item/7")

    (span,) = finished(spans)
    assert span.name == "GET /_test/item/{item_id}"
    assert span.attributes is not None
    assert span.attributes["http.route"] == "/_test/item/{item_id}"
    assert span.attributes["http.response.status_code"] == 200
    assert span.attributes["request.id"] == response.headers["X-Request-ID"]


def test_the_callers_trace_is_continued_and_its_ids_are_on_the_log_lines(
    test_client: TestClient, spans: InMemorySpanExporter, stream: io.StringIO
) -> None:
    test_client.get("/_test/item/7", headers={"traceparent": TRACEPARENT})

    (span,) = finished(spans)
    assert format(span.context.trace_id, "032x") == TRACE_ID
    assert span.parent is not None and format(span.parent.span_id, "016x") == "00f067aa0ba902b7"
    lines = [json.loads(x) for x in stream.getvalue().splitlines()]
    line = next(x for x in lines if x["event"] == "request_completed")
    assert line["trace_id"] == TRACE_ID
    assert line["span_id"] == format(span.context.span_id, "016x")


def test_errors_mark_the_span_and_health_checks_make_none(
    test_client: TestClient, spans: InMemorySpanExporter
) -> None:
    test_client.get("/health/live")
    test_client.get("/_test/crash")

    (span,) = finished(spans)
    assert span.status.status_code.name == "ERROR"
    assert span.attributes is not None and span.attributes["http.response.status_code"] == 500


def test_no_query_string_header_or_message_is_recorded(
    test_client: TestClient, spans: InMemorySpanExporter
) -> None:
    test_client.get(
        "/_test/crash?token=QUERYSECRET&code=OAUTHCODE",
        headers={"Authorization": "Bearer headerbait0123456789", "Cookie": "qb_session=cookiebait"},
    )

    recorded = json.dumps(
        [
            [dict(s.attributes or {}), [dict(e.attributes or {}) for e in s.events], s.name]
            for s in finished(spans)
        ],
        default=str,
    )
    for bait in ("QUERYSECRET", "OAUTHCODE", "headerbait", "cookiebait", "secret internal detail"):
        assert bait not in recorded


def test_nothing_happens_when_tracing_is_off(test_client: TestClient) -> None:
    telemetry.use_provider(None)

    assert test_client.get("/_test/item/1").status_code == 200
    assert telemetry.current_traceparent() is None
