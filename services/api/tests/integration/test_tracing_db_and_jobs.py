"""A job continues the trace of the request that created it, and SQL spans hold no values."""

from collections.abc import Iterator

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from sqlalchemy import text
from sqlalchemy.orm import Session

from qbank.core import telemetry
from qbank.core.db import Database
from qbank.core.jobs import Job, JobRegistry, Worker, enqueue
from qbank.core.tenancy import TenantContext
from tests.integration.conftest import Coaching, MigratedDatabase


@pytest.fixture
def spans() -> Iterator[InMemorySpanExporter]:
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    telemetry.use_provider(provider)
    yield exporter
    telemetry.use_provider(None)


def test_sql_spans_hold_the_statement_but_never_the_values(
    migrated_database: MigratedDatabase, spans: InMemorySpanExporter
) -> None:
    database = Database(migrated_database.app_url)
    telemetry.instrument_database(database.engine)
    try:
        with (
            telemetry.tracer().start_as_current_span("request"),
            database.transaction(TenantContext()) as session,
        ):
            session.execute(text("SELECT CAST(:v AS text)"), {"v": "bait-value-123"})
    finally:
        database.dispose()

    finished = spans.get_finished_spans()
    sql = [s for s in finished if s.name.startswith("db ")]
    assert any(s.name == "db SELECT" for s in sql)
    assert "bait-value-123" not in str([dict(s.attributes or {}) for s in sql])
    request = next(s for s in finished if s.name == "request")
    assert all(s.parent is not None and s.parent.span_id == request.context.span_id for s in sql)


def test_a_job_runs_inside_the_trace_of_the_request_that_enqueued_it(
    db: Database,
    worker_db: Database,
    owner_db: Database,
    coaching_a: Coaching,
    spans: InMemorySpanExporter,
) -> None:
    with owner_db.transaction(TenantContext(is_platform=True)) as session:
        session.execute(
            text("UPDATE jobs SET state = 'FAILED' WHERE state IN ('QUEUED', 'RUNNING')")
        )
    seen: list[str | None] = []

    def handler(_session: Session, job: Job) -> None:
        seen.append(job.traceparent)

    registry = JobRegistry()
    registry.register("trace.test", handler)
    with (
        telemetry.tracer().start_as_current_span("request") as request_span,
        db.transaction(coaching_a.context) as session,
    ):
        enqueue(session, "trace.test", {}, context=coaching_a.context)

    assert Worker(worker_db, registry).run_until_idle() == 1

    job_span = next(s for s in spans.get_finished_spans() if s.name == "job trace.test")
    request_context = request_span.get_span_context()
    assert job_span.context.trace_id == request_context.trace_id
    assert job_span.parent is not None and job_span.parent.span_id == request_context.span_id
    assert job_span.attributes is not None and job_span.attributes["job.type"] == "trace.test"
    assert seen[0] is not None and seen[0].startswith("00-")
    assert trace.get_current_span().get_span_context().is_valid is False


def test_an_error_that_escapes_a_job_records_its_type_but_never_its_text(
    db: Database,
    worker_db: Database,
    owner_db: Database,
    coaching_a: Coaching,
    spans: InMemorySpanExporter,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # SQLAlchemy errors quote the statement and its bound values, which can hold job payloads or
    # coaching content: they must not reach a trace through the span's exception capture.
    with owner_db.transaction(TenantContext(is_platform=True)) as session:
        session.execute(
            text("UPDATE jobs SET state = 'FAILED' WHERE state IN ('QUEUED', 'RUNNING')")
        )
    registry = JobRegistry()
    registry.register("trace.leak", lambda _session, _job: None)

    def exploding_complete(_self: Worker, _job: Job, _error: str, *, retry: bool) -> None:
        raise RuntimeError("INSERT ... parameters: {'stem': 'bait-question-text'}")

    worker = Worker(worker_db, registry)
    with db.transaction(coaching_a.context) as session:
        enqueue(session, "trace.leak", {}, context=coaching_a.context)
    monkeypatch.setattr(worker, "_run", lambda job: exploding_complete(worker, job, "", retry=True))

    with pytest.raises(RuntimeError):
        worker.run_next()

    job_span = next(s for s in spans.get_finished_spans() if s.name == "job trace.leak")
    assert job_span.events == ()  # no recorded exception message or traceback
    assert job_span.status.description is None
    assert job_span.status.status_code.name == "ERROR"
    assert job_span.attributes is not None and job_span.attributes["error.type"] == "RuntimeError"
    assert "bait-question-text" not in str(job_span.to_json())
