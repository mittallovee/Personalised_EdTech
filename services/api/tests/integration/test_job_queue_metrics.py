"""The job queue gauges (ADR-0019): counts per type and state, readable only by the worker."""

import pytest
from prometheus_client import REGISTRY
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from qbank.core import metrics
from qbank.core.db import Database
from qbank.core.jobs import enqueue
from qbank.core.tenancy import TenantContext
from tests.integration.conftest import Coaching


def sample(name: str, **labels: str) -> float | None:
    return REGISTRY.get_sample_value(name, labels)


@pytest.fixture(autouse=True)
def empty_queue(owner_db: Database) -> None:
    with owner_db.transaction(TenantContext(is_platform=True)) as session:
        session.execute(
            text("UPDATE jobs SET state = 'FAILED' WHERE state IN ('QUEUED', 'RUNNING')")
        )


def test_waiting_jobs_are_counted_per_type_across_coachings(
    db: Database, worker_db: Database, coaching_a: Coaching, coaching_b: Coaching
) -> None:
    for coaching in (coaching_a, coaching_b):
        with db.transaction(coaching.context) as session:
            enqueue(session, "queue.metrics", {}, context=coaching.context)
    with db.transaction(coaching_a.context) as session:
        enqueue(session, "queue.metrics", {}, context=coaching_a.context)
    metrics.watch_job_queue(worker_db)

    labels = {"job_type": "queue.metrics", "state": "QUEUED"}
    assert sample("qbank_jobs_queue_depth", **labels) == 3  # both coachings, the worker sees all
    age = sample("qbank_jobs_oldest_ready_age_seconds", job_type="queue.metrics")
    assert age is not None and age >= 0


def test_the_age_is_how_long_the_oldest_ready_job_has_waited(
    db: Database, owner_db: Database, worker_db: Database, coaching_a: Coaching
) -> None:
    with db.transaction(coaching_a.context) as session:
        job = enqueue(session, "queue.age", {}, context=coaching_a.context)
    with owner_db.transaction(TenantContext(is_platform=True)) as session:
        session.execute(
            text("UPDATE jobs SET run_after = now() - interval '10 minutes' WHERE id = :id"),
            {"id": job},
        )
    metrics.watch_job_queue(worker_db)

    age = sample("qbank_jobs_oldest_ready_age_seconds", job_type="queue.age")
    assert age is not None and 595 <= age <= 700


def test_the_api_role_cannot_ask_for_the_stats(db: Database) -> None:
    with (
        pytest.raises(DBAPIError, match="permission denied"),
        db.transaction(TenantContext()) as session,
    ):
        session.execute(text("SELECT * FROM jobs_stats()"))
