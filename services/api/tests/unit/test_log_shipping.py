"""Log lines sent to the Collector (ADR-0019): redacted, linked to their trace, nothing extra."""

import io
import json
import logging
from collections.abc import Iterator
from typing import Any

import pytest
import structlog
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import InMemoryLogRecordExporter, SimpleLogRecordProcessor
from opentelemetry.sdk.trace import TracerProvider

from qbank.core import telemetry
from qbank.core.logging import configure_logging


@pytest.fixture
def shipped() -> Iterator[InMemoryLogRecordExporter]:
    exporter = InMemoryLogRecordExporter()
    provider = LoggerProvider()
    provider.add_log_record_processor(SimpleLogRecordProcessor(exporter))
    configure_logging("INFO", service="api", environment="test", stream=io.StringIO())
    telemetry.attach_log_shipper(provider)
    telemetry.use_provider(TracerProvider())
    yield exporter
    telemetry.use_provider(None)
    root = logging.getLogger()
    root.handlers = [h for h in root.handlers if h.get_name() not in ("qbank-json", "qbank-otlp")]


def records(exporter: InMemoryLogRecordExporter) -> list[Any]:
    return [r.log_record for r in exporter.get_finished_logs()]


def test_a_line_is_shipped_as_its_redacted_json_with_the_trace_ids(
    shipped: InMemoryLogRecordExporter,
) -> None:
    with telemetry.tracer().start_as_current_span("request") as span:
        structlog.get_logger("test").info(
            "something_happened", password="hunter2-bait", email="ann.bait@example.com", job="x"
        )

    (record,) = records(shipped)
    line = json.loads(record.body)
    assert line["event"] == "something_happened" and line["job"] == "x"
    assert line["password"] == line["email"] == "[redacted]"
    context = span.get_span_context()
    assert line["trace_id"] == format(context.trace_id, "032x")
    assert record.trace_id == context.trace_id and record.span_id == context.span_id
    assert record.severity_text == "INFO"


def test_nothing_but_the_line_is_attached_so_exception_text_cannot_bypass_redaction(
    shipped: InMemoryLogRecordExporter,
) -> None:
    try:
        raise ValueError("Key (email)=(ann.bait@example.com) already exists")
    except ValueError:
        structlog.get_logger("test").exception("handler_crashed")

    (record,) = records(shipped)
    assert not record.attributes  # the standard OpenTelemetry handler would add the raw message
    assert "ann.bait" not in str(record.body)
    assert "ValueError" in json.loads(record.body)["exception"]


def test_library_lines_are_shipped_but_the_exporters_own_noise_is_not(
    shipped: InMemoryLogRecordExporter,
) -> None:
    logging.getLogger("sqlalchemy.engine").warning("slow statement")
    logging.getLogger("opentelemetry.exporter.otlp").warning("could not export")
    logging.getLogger("urllib3.connectionpool").warning("retrying")

    (record,) = records(shipped)
    assert json.loads(record.body)["event"] == "slow statement"
    assert record.severity_text == "WARNING"
