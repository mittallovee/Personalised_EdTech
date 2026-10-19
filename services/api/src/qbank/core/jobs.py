"""Background jobs on PostgreSQL (ADR-0007).

- ``enqueue`` adds a job inside the caller's transaction: if that transaction rolls back, the job
  never existed. The job belongs to the caller's coaching.
- A ``Worker`` claims one job at a time and runs its handler inside that job's coaching, in one
  transaction together with marking the job done. While the handler runs, a background thread
  renews the job's lease, so long jobs (PDF extraction, AI) are not taken over. Handlers must
  still be idempotent: if a worker crashes mid-job, the lease expires and the job runs again.
- A database outage does not stop the worker: it logs the error and retries with growing waits.
- Failed jobs retry with growing delays (2 s, 10 s, 60 s …) up to ``max_attempts``; a
  ``PermanentJobError`` stops retries at once.
"""

import json
import os
import random
import socket
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import timedelta
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import text
from sqlalchemy.orm import Session

from qbank.core.db import Database
from qbank.core.errors import Conflict
from qbank.core.ids import new_id
from qbank.core.tenancy import TenantContext

log = structlog.get_logger("qbank.jobs")

RETRY_DELAYS_SECONDS = (2, 10, 60, 300)
MAX_POLL_BACKOFF_SECONDS = 30.0


@dataclass(frozen=True, slots=True)
class Job:
    id: UUID
    type: str
    payload: dict[str, Any]
    organization_id: UUID | None
    created_by: UUID | None
    attempts: int
    max_attempts: int
    request_id: str | None

    @property
    def tenant_context(self) -> TenantContext:
        return TenantContext(
            organization_id=self.organization_id,
            user_id=self.created_by,
            is_platform=self.organization_id is None,
        )


JobHandler = Callable[[Session, Job], None]


class PermanentJobError(Exception):
    """Raise from a handler when retrying cannot help (bad input, missing record)."""


class _LeaseLost(Exception):
    """Another worker took the job over (our lease expired); our work must not be committed."""


class JobRegistry:
    """Maps job types (e.g. ``"ingestion.extract"``) to handler functions."""

    def __init__(self) -> None:
        self._handlers: dict[str, JobHandler] = {}

    def register(self, job_type: str, handler: JobHandler) -> None:
        if job_type in self._handlers:
            raise ValueError(f"Job type {job_type!r} is already registered")
        self._handlers[job_type] = handler

    def get(self, job_type: str) -> JobHandler | None:
        return self._handlers.get(job_type)


_ENQUEUE = text(
    "INSERT INTO jobs (id, organization_id, created_by, type, payload, max_attempts,"
    " idempotency_key, request_id)"
    " VALUES (:id, :organization_id, :created_by, :type, CAST(:payload AS jsonb), :max_attempts,"
    " :idempotency_key, :request_id)"
    " ON CONFLICT DO NOTHING"
)
_FIND_BY_KEY = text(
    "SELECT id, payload = CAST(:payload AS jsonb) AS same_payload FROM jobs"
    " WHERE type = :type AND idempotency_key = :key"
    " AND organization_id IS NOT DISTINCT FROM :organization_id"
)


def enqueue(
    session: Session,
    job_type: str,
    payload: dict[str, Any],
    *,
    context: TenantContext,
    idempotency_key: str | None = None,
    request_id: str | None = None,
    max_attempts: int = 3,
) -> UUID:
    """Add a job in the caller's transaction and coaching. Returns the job id.

    With an ``idempotency_key``, enqueueing the same job again returns the existing job's id;
    the same key with a different payload is a client error (409, API style guide §6).
    """
    job_id = new_id()
    session.execute(
        _ENQUEUE,
        {
            "id": job_id,
            "organization_id": context.organization_id,
            "created_by": context.user_id,
            "type": job_type,
            "payload": json.dumps(payload),
            "max_attempts": max_attempts,
            "idempotency_key": idempotency_key,
            "request_id": request_id,
        },
    )
    if idempotency_key is None:
        return job_id
    existing = session.execute(
        _FIND_BY_KEY,
        {
            "type": job_type,
            "key": idempotency_key,
            "organization_id": context.organization_id,
            "payload": json.dumps(payload),
        },
    ).one()
    if not existing.same_payload:
        raise Conflict(
            "This idempotency key was already used for a different request.",
            code="IDEMPOTENCY_KEY_REUSED",
        )
    existing_id: UUID = existing.id
    return existing_id


def retry_delay(attempt: int) -> timedelta:
    """Delay before retry number ``attempt`` (1-based), with ±20 % jitter."""
    base = RETRY_DELAYS_SECONDS[min(attempt, len(RETRY_DELAYS_SECONDS)) - 1]
    return timedelta(seconds=base * random.uniform(0.8, 1.2))  # noqa: S311 - not security


class Worker:
    def __init__(
        self,
        database: Database,
        registry: JobRegistry,
        *,
        lease: timedelta = timedelta(minutes=5),
        poll_interval: float = 1.0,
        worker_id: str | None = None,
    ) -> None:
        self._database = database
        self._registry = registry
        self._lease = lease
        self._poll_interval = poll_interval
        self.worker_id = worker_id or f"{socket.gethostname()}:{os.getpid()}:{new_id().hex[-6:]}"
        self._stopping = False

    def stop(self) -> None:
        """Finish the current job, then exit ``run_forever``."""
        self._stopping = True

    def run_forever(self) -> None:
        log.info("worker_started", worker_id=self.worker_id)
        failures = 0
        while not self._stopping:
            try:
                worked = self.run_next()
            except Exception:  # e.g. the database is restarting: wait, then try again
                failures += 1
                log.exception("worker_poll_failed", failures=failures)
                time.sleep(min(self._poll_interval * 2**failures, MAX_POLL_BACKOFF_SECONDS))
                continue
            failures = 0
            if not worked:
                time.sleep(self._poll_interval)
        log.info("worker_stopped", worker_id=self.worker_id)

    def run_until_idle(self) -> int:
        """Process jobs until none is ready. Returns how many were processed (used in tests)."""
        processed = 0
        while self.run_next():
            processed += 1
        return processed

    def run_next(self) -> bool:
        """Claim and run one job. Returns False if no job was ready."""
        job = self._claim()
        if job is None:
            return False
        structlog.contextvars.bind_contextvars(job_id=str(job.id), request_id=job.request_id)
        try:
            self._run(job)
        finally:
            structlog.contextvars.unbind_contextvars("job_id", "request_id")
        return True

    def _claim(self) -> Job | None:
        with self._database.transaction(TenantContext()) as session:
            row = session.execute(
                text("SELECT * FROM jobs_claim(:worker, :lease)"),
                {"worker": self.worker_id, "lease": self._lease},
            ).first()
        if row is None:
            return None
        return Job(
            id=row.id,
            type=row.type,
            payload=row.payload,
            organization_id=row.organization_id,
            created_by=row.created_by,
            attempts=row.attempts,
            max_attempts=row.max_attempts,
            request_id=row.request_id,
        )

    def _run(self, job: Job) -> None:
        handler = self._registry.get(job.type)
        if handler is None:
            self._fail(job, f"No handler registered for job type {job.type!r}", retry=False)
            return
        started = time.perf_counter()
        try:
            # The handler's writes and "job done" commit together, or not at all.
            with self._database.transaction(job.tenant_context) as session:
                with self._lease_kept(job):
                    handler(session, job)
                completed = session.execute(
                    text("SELECT jobs_complete(:id, :worker)"),
                    {"id": job.id, "worker": self.worker_id},
                ).scalar()
                if not completed:
                    raise _LeaseLost
        except _LeaseLost:
            log.warning("job_lease_lost", job_type=job.type, attempt=job.attempts)
        except PermanentJobError as exc:
            self._fail(job, str(exc) or type(exc).__name__, retry=False)
        except Exception as exc:  # any other error: retry later if attempts remain
            log.warning(
                "job_attempt_failed", job_type=job.type, attempt=job.attempts, exc_info=True
            )
            self._fail(job, f"{type(exc).__name__}: {exc}", retry=True)
        else:
            log.info(
                "job_succeeded",
                job_type=job.type,
                attempt=job.attempts,
                duration_ms=round((time.perf_counter() - started) * 1000, 1),
            )

    @contextmanager
    def _lease_kept(self, job: Job) -> Iterator[None]:
        """Renew the job's lease in a background thread until the block ends."""
        done = threading.Event()
        renewer = threading.Thread(
            target=self._renew_lease, args=(job, done), name=f"lease-{job.id}", daemon=True
        )
        renewer.start()
        try:
            yield
        finally:
            done.set()
            renewer.join()

    def _renew_lease(self, job: Job, done: threading.Event) -> None:
        while not done.wait(self._lease.total_seconds() / 3):
            try:
                with self._database.transaction(TenantContext()) as session:
                    renewed = session.execute(
                        text("SELECT jobs_extend_lease(:id, :worker, :lease)"),
                        {"id": job.id, "worker": self.worker_id, "lease": self._lease},
                    ).scalar()
            except Exception:  # keep trying; if the lease runs out, completion is refused
                log.warning("job_lease_renewal_failed", job_id=str(job.id), exc_info=True)
                continue
            if not renewed:
                log.warning("job_lease_lost", job_id=str(job.id), job_type=job.type)
                return

    def _fail(self, job: Job, error: str, *, retry: bool) -> None:
        with self._database.transaction(TenantContext()) as session:
            state = session.execute(
                text("SELECT jobs_fail(:id, :worker, :error, :retry_in)"),
                {
                    "id": job.id,
                    "worker": self.worker_id,
                    "error": error,
                    "retry_in": retry_delay(job.attempts) if retry else None,
                },
            ).scalar()
        log.warning(
            "job_failed" if state == "FAILED" else "job_retry_scheduled",
            job_type=job.type,
            attempt=job.attempts,
            error=error[:200],
        )
