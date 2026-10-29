"""Sign-in and job metrics (ADR-0019): counted by outcome, with bounded labels."""

import secrets
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY
from sqlalchemy import text
from sqlalchemy.orm import Session

from qbank.core.config import AppEnv, Settings
from qbank.core.db import Database
from qbank.core.jobs import Job, JobRegistry, PermanentJobError, Worker, enqueue
from qbank.core.tenancy import TenantContext
from qbank.main import create_app
from tests.integration.conftest import (
    MEMBER_PASSWORD,
    Coaching,
    MigratedDatabase,
    platform_admin,
)


def sample(name: str, **labels: str) -> float:
    return REGISTRY.get_sample_value(name, labels) or 0.0


@pytest.fixture
def client(migrated_database: MigratedDatabase) -> Iterator[TestClient]:
    settings = Settings(
        app_env=AppEnv.TEST, database_url=migrated_database.app_url, session_cookie_secure=False
    )
    with TestClient(create_app(settings)) as test_client:
        yield test_client


def test_sign_ins_are_counted_by_outcome_and_reason(client: TestClient, owner_db: Database) -> None:
    ok = {"method": "password", "outcome": "success", "reason": ""}
    unknown = {"method": "password", "outcome": "failure", "reason": "unknown_email"}
    bad = {"method": "password", "outcome": "failure", "reason": "bad_password"}
    before = [sample("qbank_login_attempts_total", **labels) for labels in (ok, unknown, bad)]
    email = platform_admin(owner_db)
    ghost = f"ghost-{secrets.token_hex(4)}@example.com"

    client.post("/api/v1/auth/login", json={"email": ghost, "password": "x"})
    client.post("/api/v1/auth/login", json={"email": email, "password": "wrong"})
    client.post("/api/v1/auth/login", json={"email": email, "password": MEMBER_PASSWORD})

    after = [sample("qbank_login_attempts_total", **labels) for labels in (ok, unknown, bad)]
    assert [a - b for a, b in zip(after, before, strict=True)] == [1, 1, 1]
    exposed = "".join(str(m) for m in REGISTRY.collect())
    assert email not in exposed and ghost not in exposed  # emails are never labels


def test_job_outcomes_are_counted_per_type_and_coaching(
    db: Database, worker_db: Database, coaching_a: Coaching, owner_db: Database
) -> None:
    with owner_db.transaction(TenantContext(is_platform=True)) as session:
        session.execute(
            text("UPDATE jobs SET state = 'FAILED' WHERE state IN ('QUEUED', 'RUNNING')")
        )

    def handler(_session: Session, job: Job) -> None:
        if job.payload.get("bad"):
            raise PermanentJobError("input is invalid")

    registry = JobRegistry()
    registry.register("metrics.test", handler)
    org = str(coaching_a.org_id)
    done = {"job_type": "metrics.test", "outcome": "succeeded", "organization_id": org}
    failed = {"job_type": "metrics.test", "outcome": "failed", "organization_id": org}
    before_done = sample("qbank_jobs_finished_total", **done)
    before_failed = sample("qbank_jobs_finished_total", **failed)
    with db.transaction(coaching_a.context) as session:
        enqueue(session, "metrics.test", {}, context=coaching_a.context)
        enqueue(session, "metrics.test", {"bad": True}, context=coaching_a.context)

    assert Worker(worker_db, registry).run_until_idle() == 2

    assert sample("qbank_jobs_finished_total", **done) == before_done + 1
    assert sample("qbank_jobs_finished_total", **failed) == before_failed + 1
    assert sample("qbank_job_duration_seconds_count", job_type="metrics.test") >= 1
