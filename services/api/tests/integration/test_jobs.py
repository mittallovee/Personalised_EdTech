"""M1 exit test T9: background jobs are durable, run once in their coaching, and retry safely."""

import time
from collections.abc import Iterator
from datetime import timedelta
from uuid import UUID

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.orm import Session

from qbank.core.db import Database
from qbank.core.errors import Conflict
from qbank.core.jobs import Job, JobRegistry, PermanentJobError, Worker, enqueue, retry_delay
from qbank.core.tenancy import TenantContext
from qbank.modules.audit.models import AuditEvent
from qbank.modules.audit.public import record_event
from tests.integration.conftest import Coaching


class Recorder:
    """Test handlers: write an audit row (so we can see committed work) and remember calls."""

    def __init__(self) -> None:
        self.calls: list[Job] = []
        self.seen_org: list[UUID | None] = []
        self.failures_left = 0
        self.permanent = False

    def handle(self, session: Session, job: Job) -> None:
        self.calls.append(job)
        self.seen_org.append(session.scalar(text("SELECT app_current_org()")))
        record_event(
            session,
            action="JOB_TEST",
            entity_type="job",
            entity_id=job.id,
            organization_id=job.organization_id,
            actor_user_id=None,
        )
        if self.permanent:
            raise PermanentJobError("input is invalid")
        if self.failures_left:
            self.failures_left -= 1
            raise RuntimeError("temporary outage")


@pytest.fixture(autouse=True)
def empty_queue(owner_db: Database) -> None:
    """Jobs left by other tests must not be picked up by this test's worker."""
    with owner_db.transaction(TenantContext(is_platform=True)) as session:
        session.execute(
            text("UPDATE jobs SET state = 'FAILED' WHERE state IN ('QUEUED', 'RUNNING')")
        )


@pytest.fixture
def recorder() -> Recorder:
    return Recorder()


@pytest.fixture
def worker(worker_db: Database, recorder: Recorder) -> Iterator[Worker]:
    registry = JobRegistry()
    registry.register("test.record", recorder.handle)
    yield Worker(worker_db, registry, worker_id="worker-a")


def add_job(
    db: Database, coaching: Coaching, *, idempotency_key: str | None = None, max_attempts: int = 3
) -> UUID:
    with db.transaction(coaching.context) as session:
        return enqueue(
            session,
            "test.record",
            {"n": 1},
            context=coaching.context,
            idempotency_key=idempotency_key,
            max_attempts=max_attempts,
        )


def job_row(owner_db: Database, job_id: UUID) -> dict[str, object]:
    with owner_db.transaction(TenantContext(is_platform=True)) as session:
        row = session.execute(text("SELECT * FROM jobs WHERE id = :id"), {"id": job_id}).one()
    return dict(row._mapping)


def make_ready_now(owner_db: Database, job_id: UUID) -> None:
    with owner_db.transaction(TenantContext(is_platform=True)) as session:
        session.execute(text("UPDATE jobs SET run_after = now() WHERE id = :id"), {"id": job_id})


def audit_rows(owner_db: Database, coaching: Coaching, job_id: UUID) -> int:
    with owner_db.transaction(coaching.context) as session:
        return len(
            session.scalars(select(AuditEvent.id).where(AuditEvent.entity_id == job_id)).all()
        )


def test_committed_job_runs_once_inside_its_coaching(
    db: Database, owner_db: Database, worker: Worker, recorder: Recorder, coaching_a: Coaching
) -> None:
    job_id = add_job(db, coaching_a)

    assert worker.run_until_idle() == 1
    assert worker.run_until_idle() == 0  # nothing runs twice
    assert recorder.seen_org == [coaching_a.org_id]
    assert job_row(owner_db, job_id)["state"] == "SUCCEEDED"
    assert audit_rows(owner_db, coaching_a, job_id) == 1


def test_job_enqueued_in_a_rolled_back_transaction_never_runs(
    db: Database, worker: Worker, recorder: Recorder, coaching_a: Coaching
) -> None:
    with pytest.raises(RuntimeError), db.transaction(coaching_a.context) as session:
        enqueue(session, "test.record", {}, context=coaching_a.context)
        raise RuntimeError("the request failed after enqueueing")

    assert worker.run_until_idle() == 0
    assert recorder.calls == []


def test_temporary_failure_is_retried_later_and_partial_work_is_undone(
    db: Database, owner_db: Database, worker: Worker, recorder: Recorder, coaching_a: Coaching
) -> None:
    recorder.failures_left = 1
    job_id = add_job(db, coaching_a)

    worker.run_until_idle()
    after_failure = job_row(owner_db, job_id)
    assert after_failure["state"] == "QUEUED"
    assert after_failure["attempts"] == 1
    assert after_failure["last_error"] == "RuntimeError: temporary outage"
    assert audit_rows(owner_db, coaching_a, job_id) == 0  # the failed attempt's writes rolled back
    assert worker.run_until_idle() == 0  # backoff: not ready yet

    make_ready_now(owner_db, job_id)
    worker.run_until_idle()
    assert job_row(owner_db, job_id)["state"] == "SUCCEEDED"
    assert job_row(owner_db, job_id)["attempts"] == 2
    assert audit_rows(owner_db, coaching_a, job_id) == 1


def test_job_fails_for_good_after_its_last_attempt(
    db: Database, owner_db: Database, worker: Worker, recorder: Recorder, coaching_a: Coaching
) -> None:
    recorder.failures_left = 5
    job_id = add_job(db, coaching_a, max_attempts=2)

    worker.run_until_idle()
    make_ready_now(owner_db, job_id)
    worker.run_until_idle()

    row = job_row(owner_db, job_id)
    assert row["state"] == "FAILED"
    assert row["attempts"] == 2
    assert row["finished_at"] is not None


def test_permanent_error_is_not_retried(
    db: Database, owner_db: Database, worker: Worker, recorder: Recorder, coaching_a: Coaching
) -> None:
    recorder.permanent = True
    job_id = add_job(db, coaching_a)

    worker.run_until_idle()

    row = job_row(owner_db, job_id)
    assert (row["state"], row["attempts"], row["last_error"]) == ("FAILED", 1, "input is invalid")


def test_unknown_job_type_fails_without_retry(
    db: Database, owner_db: Database, worker: Worker, coaching_a: Coaching
) -> None:
    with db.transaction(coaching_a.context) as session:
        job_id = enqueue(session, "no.such.job", {}, context=coaching_a.context)

    worker.run_until_idle()

    assert job_row(owner_db, job_id)["state"] == "FAILED"


def test_idempotency_key_creates_one_job_per_coaching(
    db: Database, coaching_a: Coaching, coaching_b: Coaching
) -> None:
    first = add_job(db, coaching_a, idempotency_key="upload-42")
    again = add_job(db, coaching_a, idempotency_key="upload-42")
    other_coaching = add_job(db, coaching_b, idempotency_key="upload-42")

    assert first == again
    assert other_coaching != first


def test_reused_idempotency_key_with_a_different_payload_is_rejected(
    db: Database, coaching_a: Coaching
) -> None:
    add_job(db, coaching_a, idempotency_key="upload-43")  # payload {"n": 1}

    with pytest.raises(Conflict) as error, db.transaction(coaching_a.context) as session:
        enqueue(
            session,
            "test.record",
            {"n": 2},
            context=coaching_a.context,
            idempotency_key="upload-43",
        )

    assert error.value.code == "IDEMPOTENCY_KEY_REUSED"


def test_running_job_is_not_claimed_by_a_second_worker(
    db: Database, worker_db: Database, worker: Worker, recorder: Recorder, coaching_a: Coaching
) -> None:
    add_job(db, coaching_a)
    registry = JobRegistry()
    registry.register("test.record", recorder.handle)
    other = Worker(worker_db, registry, worker_id="worker-b")

    claimed = worker._claim()
    assert claimed is not None
    assert other._claim() is None  # locked by worker-a's lease


def test_job_of_a_crashed_worker_is_recovered_and_the_late_result_discarded(
    db: Database,
    worker_db: Database,
    owner_db: Database,
    worker: Worker,
    recorder: Recorder,
    coaching_a: Coaching,
) -> None:
    job_id = add_job(db, coaching_a)
    stuck = worker._claim()  # worker-a takes the job, then "hangs"
    assert stuck is not None
    with owner_db.transaction(TenantContext(is_platform=True)) as session:
        session.execute(  # worker-a's lease runs out
            text("UPDATE jobs SET locked_until = now() - interval '1 second' WHERE id = :id"),
            {"id": job_id},
        )

    registry = JobRegistry()
    registry.register("test.record", recorder.handle)
    assert Worker(worker_db, registry, worker_id="worker-b").run_until_idle() == 1

    worker._run(stuck)  # worker-a wakes up and finishes late

    assert job_row(owner_db, job_id)["state"] == "SUCCEEDED"
    assert job_row(owner_db, job_id)["attempts"] == 2
    assert audit_rows(owner_db, coaching_a, job_id) == 1  # worker-a's late writes were rolled back


def test_lease_is_renewed_while_a_long_job_runs(
    db: Database, worker_db: Database, owner_db: Database, coaching_a: Coaching
) -> None:
    job_id = add_job(db, coaching_a)
    taken_over: list[Job | None] = []
    other = Worker(worker_db, JobRegistry(), worker_id="worker-b")

    def slow(session: Session, job: Job) -> None:
        time.sleep(1.5)  # longer than worker-a's 1-second lease
        taken_over.append(other._claim())

    registry = JobRegistry()
    registry.register("test.record", slow)
    worker = Worker(worker_db, registry, worker_id="worker-a", lease=timedelta(seconds=1))

    assert worker.run_until_idle() == 1
    assert taken_over == [None]  # worker-a kept renewing its lease
    assert job_row(owner_db, job_id)["state"] == "SUCCEEDED"
    assert job_row(owner_db, job_id)["attempts"] == 1


def test_worker_keeps_polling_after_a_database_error(worker_db: Database) -> None:
    worker = Worker(worker_db, JobRegistry(), worker_id="worker-a", poll_interval=0.01)
    calls = 0

    def flaky_run_next() -> bool:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise OperationalError("SELECT jobs_claim(...)", {}, Exception("server restarting"))
        worker.stop()
        return False

    worker.run_next = flaky_run_next  # type: ignore[method-assign]
    worker.run_forever()  # must not raise

    assert calls == 2


def test_coachings_see_only_their_own_jobs(
    db: Database, coaching_a: Coaching, coaching_b: Coaching
) -> None:
    job_b = add_job(db, coaching_b)

    with db.transaction(coaching_a.context) as session:
        visible = session.execute(text("SELECT id FROM jobs WHERE id = :id"), {"id": job_b}).all()

    assert visible == []


@pytest.mark.parametrize(
    "call",
    [
        "SELECT * FROM jobs_claim('api', interval '1 minute')",
        "SELECT jobs_extend_lease(gen_random_uuid(), 'api', interval '1 minute')",
        "SELECT jobs_complete(gen_random_uuid(), 'api')",
        "SELECT jobs_fail(gen_random_uuid(), 'api', 'error', NULL)",
    ],
)
def test_api_role_cannot_use_the_cross_coaching_job_functions(db: Database, call: str) -> None:
    with (
        pytest.raises(DBAPIError, match="permission denied"),
        db.transaction(TenantContext()) as session,
    ):
        session.execute(text(call))


def test_runtime_role_cannot_change_job_state_directly(db: Database, coaching_a: Coaching) -> None:
    job_id = add_job(db, coaching_a)

    with (
        pytest.raises(DBAPIError, match="permission denied"),
        db.transaction(coaching_a.context) as session,
    ):
        session.execute(text("UPDATE jobs SET state = 'SUCCEEDED' WHERE id = :id"), {"id": job_id})


def test_retry_delays_grow() -> None:
    first, second, third = (retry_delay(n) for n in (1, 2, 3))

    assert timedelta(seconds=1.5) < first < timedelta(seconds=2.5)
    assert first < second < third
