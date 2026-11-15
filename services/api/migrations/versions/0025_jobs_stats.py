"""Let the worker count the waiting jobs (K-06f, ADR-0019).

Revision ID: 0025
Revises: 0024
Create Date: 2026-11-14

The dashboards show how many jobs are waiting or running, and how long the oldest ready job has
waited. The worker's database role cannot read the ``jobs`` table (row-level security shows a role
only its own coaching's jobs, and the worker has no coaching), so it asks through
``jobs_stats()``: a SECURITY DEFINER function, like the other ``jobs_*`` functions, executable only
by ``qbank_worker``. It returns counts per job type and state, never a job's payload or coaching.

Downgrade drops the function.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0025"
down_revision: str | None = "0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

WORKER_ROLE = "qbank_worker"


def upgrade() -> None:
    op.execute("""
        -- Waiting (QUEUED) and running jobs by type; the age is how long the oldest job that is
        -- ready to run (its run_after has passed) has been waiting.
        CREATE FUNCTION jobs_stats()
        RETURNS TABLE (
            job_type text, state text, jobs bigint, oldest_ready_age_seconds double precision
        )
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, public AS $$
            SELECT j.type, j.state, count(*),
                   max(extract(epoch FROM now() - j.run_after))
                       FILTER (WHERE j.state = 'QUEUED' AND j.run_after <= now())
            FROM public.jobs j
            WHERE j.state IN ('QUEUED', 'RUNNING')
            GROUP BY j.type, j.state
        $$;
    """)
    op.execute(f"""
        REVOKE EXECUTE ON FUNCTION jobs_stats() FROM PUBLIC;
        GRANT EXECUTE ON FUNCTION jobs_stats() TO {WORKER_ROLE};
    """)


def downgrade() -> None:
    op.execute("DROP FUNCTION jobs_stats()")
