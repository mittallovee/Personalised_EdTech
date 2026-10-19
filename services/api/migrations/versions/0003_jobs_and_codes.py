"""Background jobs queue and globally unique public codes.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-18

Jobs (ADR-0007): a PostgreSQL table is both the queue and the durable record of every background
job. Workers claim work with ``FOR UPDATE SKIP LOCKED`` so two workers never take the same job,
and a lease (``locked_until``) lets another worker recover a job whose worker crashed.
- The runtime role may enqueue and read jobs of its own coaching (tenant policy, like other tables).
- Claiming, renewing, completing and failing jobs across coachings happens only through the
  ``jobs_*`` SECURITY DEFINER functions below, executable only by the ``qbank_worker`` role. The
  API's role cannot call them, so no API code path can reach another coaching's jobs.
  ``qbank_worker`` is a member of ``qbank_app`` (granted where the roles are created), so job
  handlers get the same tenant-restricted table access as the API; the worker runs each job
  inside that job's coaching, renewing its lease while the job runs.

Public codes (ADR-0011): one row per issued 8-character code, globally unique and never reused.
The unique primary key detects collisions across all coachings; each coaching sees only its rows.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "qbank_app"
WORKER_ROLE = "qbank_worker"


def upgrade() -> None:
    op.execute("""
        CREATE TABLE jobs (
            id              uuid PRIMARY KEY,
            organization_id uuid REFERENCES organizations (id),  -- NULL = platform/system job
            created_by      uuid REFERENCES users (id),
            type            text NOT NULL,
            payload         jsonb NOT NULL DEFAULT '{}'::jsonb,
            state           text NOT NULL DEFAULT 'QUEUED'
                            CHECK (state IN ('QUEUED', 'RUNNING', 'SUCCEEDED', 'FAILED')),
            attempts        integer NOT NULL DEFAULT 0,
            max_attempts    integer NOT NULL DEFAULT 3 CHECK (max_attempts >= 1),
            run_after       timestamptz NOT NULL DEFAULT now(),
            locked_by       text,
            locked_until    timestamptz,
            last_error      text,
            idempotency_key text,
            request_id      text,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            finished_at     timestamptz
        );
        -- The worker's "next job" query.
        CREATE INDEX jobs_ready ON jobs (run_after, created_at) WHERE state = 'QUEUED';
        CREATE INDEX jobs_running_lease ON jobs (locked_until) WHERE state = 'RUNNING';
        CREATE INDEX jobs_org_state ON jobs (organization_id, state, created_at);
        -- The same request enqueued twice creates one job (P-13 idempotency).
        CREATE UNIQUE INDEX jobs_idempotency ON jobs (
            coalesce(organization_id, '00000000-0000-0000-0000-000000000000'::uuid),
            type,
            idempotency_key
        ) WHERE idempotency_key IS NOT NULL;

        CREATE TABLE public_codes (
            code            text PRIMARY KEY CHECK (code ~ '^[0-9A-HJKMNP-TV-Z]{8}$'),
            entity_type     text NOT NULL,
            organization_id uuid NOT NULL REFERENCES organizations (id),
            created_at      timestamptz NOT NULL DEFAULT now()
        );
    """)

    op.execute("""
        -- Not FORCE: the owner-run jobs_* functions must see every coaching's queue.
        ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;
        CREATE POLICY jobs_tenant ON jobs FOR ALL
            USING (
                organization_id = app_current_org()
                OR (organization_id IS NULL AND app_is_platform())
            )
            WITH CHECK (
                organization_id = app_current_org()
                OR (organization_id IS NULL AND app_is_platform())
            );

        ALTER TABLE public_codes ENABLE ROW LEVEL SECURITY;
        ALTER TABLE public_codes FORCE ROW LEVEL SECURITY;
        CREATE POLICY public_codes_tenant ON public_codes FOR ALL
            USING (organization_id = app_current_org())
            WITH CHECK (organization_id = app_current_org());
    """)

    op.execute("""
        -- Take the next ready job (or one whose worker's lease expired) for this worker.
        CREATE FUNCTION jobs_claim(p_worker text, p_lease interval)
        RETURNS SETOF jobs
        LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = pg_catalog, public AS $$
        BEGIN
            -- Jobs whose worker died too many times are given up on, not retried forever.
            UPDATE jobs
            SET state = 'FAILED', last_error = 'worker lease expired on the final attempt',
                locked_by = NULL, locked_until = NULL, finished_at = now(), updated_at = now()
            WHERE state = 'RUNNING' AND locked_until < now() AND attempts >= max_attempts;

            RETURN QUERY
            UPDATE jobs
            SET state = 'RUNNING', attempts = attempts + 1, locked_by = p_worker,
                locked_until = now() + p_lease, updated_at = now()
            WHERE id = (
                SELECT id FROM jobs
                WHERE (state = 'QUEUED' AND run_after <= now())
                   OR (state = 'RUNNING' AND locked_until < now())
                ORDER BY run_after, created_at
                FOR UPDATE SKIP LOCKED
                LIMIT 1
            )
            RETURNING *;
        END
        $$;

        -- Mark a job done. Only the worker holding the lease can do this.
        CREATE FUNCTION jobs_complete(p_job_id uuid, p_worker text)
        RETURNS boolean
        LANGUAGE sql VOLATILE SECURITY DEFINER SET search_path = pg_catalog, public AS $$
            WITH done AS (
                UPDATE jobs
                SET state = 'SUCCEEDED', locked_by = NULL, locked_until = NULL,
                    finished_at = now(), updated_at = now()
                WHERE id = p_job_id AND state = 'RUNNING' AND locked_by = p_worker
                RETURNING 1
            )
            SELECT EXISTS (SELECT 1 FROM done)
        $$;

        -- Keep a long-running job: push the lease forward. False = another worker has it now.
        CREATE FUNCTION jobs_extend_lease(p_job_id uuid, p_worker text, p_lease interval)
        RETURNS boolean
        LANGUAGE sql VOLATILE SECURITY DEFINER SET search_path = pg_catalog, public AS $$
            WITH renewed AS (
                UPDATE jobs
                SET locked_until = now() + p_lease, updated_at = now()
                WHERE id = p_job_id AND state = 'RUNNING' AND locked_by = p_worker
                RETURNING 1
            )
            SELECT EXISTS (SELECT 1 FROM renewed)
        $$;

        -- Record a failure: retry later if attempts remain and the error is retryable.
        CREATE FUNCTION jobs_fail(
            p_job_id uuid, p_worker text, p_error text, p_retry_in interval)
        RETURNS text
        LANGUAGE sql VOLATILE SECURITY DEFINER SET search_path = pg_catalog, public AS $$
            UPDATE jobs
            SET state = CASE WHEN p_retry_in IS NOT NULL AND attempts < max_attempts
                             THEN 'QUEUED' ELSE 'FAILED' END,
                run_after = CASE WHEN p_retry_in IS NOT NULL AND attempts < max_attempts
                                 THEN now() + p_retry_in ELSE run_after END,
                finished_at = CASE WHEN p_retry_in IS NOT NULL AND attempts < max_attempts
                                   THEN NULL ELSE now() END,
                last_error = left(p_error, 2000),
                locked_by = NULL, locked_until = NULL, updated_at = now()
            WHERE id = p_job_id AND state = 'RUNNING' AND locked_by = p_worker
            RETURNING state
        $$;
    """)

    op.execute(f"""
        REVOKE EXECUTE ON FUNCTION
            jobs_claim(text, interval),
            jobs_complete(uuid, text),
            jobs_extend_lease(uuid, text, interval),
            jobs_fail(uuid, text, text, interval)
        FROM PUBLIC;
        GRANT EXECUTE ON FUNCTION
            jobs_claim(text, interval),
            jobs_complete(uuid, text),
            jobs_extend_lease(uuid, text, interval),
            jobs_fail(uuid, text, text, interval)
        TO {WORKER_ROLE};

        GRANT SELECT, INSERT ON jobs TO {APP_ROLE};   -- state changes only via jobs_* functions
        GRANT SELECT, INSERT ON public_codes TO {APP_ROLE};  -- codes are never changed or reused
    """)


def downgrade() -> None:
    op.execute("""
        DROP FUNCTION jobs_fail(uuid, text, text, interval);
        DROP FUNCTION jobs_extend_lease(uuid, text, interval);
        DROP FUNCTION jobs_complete(uuid, text);
        DROP FUNCTION jobs_claim(text, interval);
        DROP TABLE public_codes;
        DROP TABLE jobs;
    """)
