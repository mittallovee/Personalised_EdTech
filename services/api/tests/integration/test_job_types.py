"""M6 PR 6a: workers claim jobs by type; the sandboxed document worker has a role of its own (K-17).

The normal worker must never take a document-rendering job, and the sandbox worker must take nothing
else, because only the sandbox may open an untrusted file. Its database role can run the job
functions and nothing more: it is not a member of the application role.
"""

from collections.abc import Iterator

import pytest
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from qbank.core.db import Database
from qbank.core.jobs import Job, JobRegistry, Worker, enqueue
from qbank.core.tenancy import TenantContext
from qbank.modules.ingestion.public import RENDER_JOB, SANDBOX_JOB_TYPES
from tests.integration.conftest import Coaching, MigratedDatabase


@pytest.fixture(autouse=True)
def empty_queue(owner_db: Database) -> None:
    with owner_db.transaction(TenantContext(is_platform=True)) as session:
        session.execute(
            text("UPDATE jobs SET state = 'FAILED' WHERE state IN ('QUEUED', 'RUNNING')")
        )


@pytest.fixture
def ingest_db(migrated_database: MigratedDatabase) -> Iterator[Database]:
    database = Database(migrated_database.ingest_url)
    yield database
    database.dispose()


def add(db: Database, coaching: Coaching, job_type: str) -> None:
    with db.transaction(coaching.context) as session:
        enqueue(session, job_type, {}, context=coaching.context)


def registry(seen: list[str], *types: str) -> JobRegistry:
    found = JobRegistry()
    for job_type in types:
        found.register(job_type, lambda _session, job: seen.append(job.type))
    return found


def test_the_normal_worker_skips_document_jobs_and_the_sandbox_takes_only_them(
    db: Database, worker_db: Database, ingest_db: Database, coaching_a: Coaching
) -> None:
    add(db, coaching_a, "test.other")
    add(db, coaching_a, RENDER_JOB)
    normal: list[str] = []
    sandbox: list[str] = []
    both = (RENDER_JOB, "test.other")
    Worker(worker_db, registry(normal, *both), skip_types=SANDBOX_JOB_TYPES).run_until_idle()
    assert normal == ["test.other"]  # the document job was left alone
    Worker(ingest_db, registry(sandbox, *both), only_types=SANDBOX_JOB_TYPES).run_until_idle()
    assert sandbox == [RENDER_JOB]


def test_a_sandbox_worker_never_takes_other_work_even_when_it_is_the_only_one_running(
    db: Database, ingest_db: Database, coaching_a: Coaching
) -> None:
    add(db, coaching_a, "test.other")
    seen: list[str] = []
    done = Worker(
        ingest_db, registry(seen, "test.other", RENDER_JOB), only_types=SANDBOX_JOB_TYPES
    ).run_until_idle()
    assert done == 0 and seen == []


def test_without_a_filter_a_worker_takes_everything_as_before(
    db: Database, worker_db: Database, coaching_a: Coaching
) -> None:
    add(db, coaching_a, "test.other")
    seen: list[str] = []
    assert Worker(worker_db, registry(seen, "test.other")).run_until_idle() == 1


def test_the_sandbox_role_can_run_the_job_functions_and_read_no_table(
    ingest_db: Database, owner_db: Database
) -> None:
    """Every table that exists today is closed to it (later migrations open only upload tables)."""
    with owner_db.transaction(TenantContext(is_platform=True)) as session:
        tables = session.scalars(
            text("SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY 1")
        ).all()
    assert "users" in tables and "jobs" in tables and "ai_provider_keys" in tables
    allowed: set[str] = set()
    for table in tables:
        if table in allowed or table.startswith("ingest_"):
            continue
        with (
            pytest.raises(ProgrammingError, match="permission denied"),
            ingest_db.transaction(TenantContext(is_platform=True)) as session,
        ):
            # The name comes from the catalogue just read, not from any input.
            session.execute(text(f'SELECT count(*) FROM "{table}"'))  # noqa: S608


def test_the_sandbox_role_is_not_a_member_of_the_application_role(
    owner_db: Database,
) -> None:
    with owner_db.transaction(TenantContext(is_platform=True)) as session:
        member = session.scalar(text("SELECT pg_has_role('qbank_ingest', 'qbank_app', 'MEMBER')"))
        elevated = session.scalar(
            text(
                "SELECT rolsuper OR rolbypassrls OR rolcreatedb"
                " FROM pg_roles WHERE rolname = 'qbank_ingest'"
            )
        )
    assert member is False and elevated is False


def test_a_job_handler_in_the_sandbox_runs_inside_the_jobs_coaching(
    db: Database, ingest_db: Database, coaching_a: Coaching
) -> None:
    add(db, coaching_a, RENDER_JOB)
    seen: list[object] = []

    def handle(session: object, job: Job) -> None:
        seen.append(session.scalar(text("SELECT app_current_org()")))  # type: ignore[attr-defined]

    found = JobRegistry()
    found.register(RENDER_JOB, handle)
    Worker(ingest_db, found, only_types=SANDBOX_JOB_TYPES).run_until_idle()
    assert seen == [coaching_a.org_id]
