"""Claim jobs by type, and a restricted role for the sandboxed document worker (M6 6a, K-17).

Revision ID: 0043
Revises: 0042
Create Date: 2026-11-28

M6 design note §8, ADR-0024. Untrusted documents are parsed only in a separate worker that has a
database role of its own (``qbank_ingest``), so a bug in a document parser can reach no more than
that role may. Two things are needed first:

- ``jobs_claim_for(worker, lease, only, skip)`` takes the next ready job of the wanted types. The
  normal worker passes ``skip`` (it never takes the sandbox's jobs), the sandbox worker passes
  ``only`` (it never takes anything else). ``jobs_claim`` stays for older callers.
- ``qbank_ingest`` may run the job functions that claim, renew, complete and fail jobs. It is not
  a member of ``qbank_app``: it has no access to questions, users, keys or any other table. What it
  may touch beyond this (the upload and page tables of its own coaching) is granted by the
  migration that creates those tables.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0043"
down_revision: str | None = "0042"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

WORKER_ROLE = "qbank_worker"
INGEST_ROLE = "qbank_ingest"


def upgrade() -> None:
    op.execute("""
        CREATE FUNCTION jobs_claim_for(
            p_worker text, p_lease interval, p_only text[], p_skip text[])
        RETURNS SETOF jobs
        LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = pg_catalog, public AS $$
        BEGIN
            UPDATE jobs
            SET state = 'FAILED', last_error = 'worker lease expired on the final attempt',
                locked_by = NULL, locked_until = NULL, finished_at = now(), updated_at = now()
            WHERE state = 'RUNNING' AND locked_until < now() AND attempts >= max_attempts
              AND (p_only IS NULL OR type = ANY (p_only))
              AND NOT (type = ANY (coalesce(p_skip, ARRAY[]::text[])));

            RETURN QUERY
            UPDATE jobs
            SET state = 'RUNNING', attempts = attempts + 1, locked_by = p_worker,
                locked_until = now() + p_lease, updated_at = now()
            WHERE id = (
                SELECT id FROM jobs
                WHERE ((state = 'QUEUED' AND run_after <= now())
                       OR (state = 'RUNNING' AND locked_until < now()))
                  AND (p_only IS NULL OR type = ANY (p_only))
                  AND NOT (type = ANY (coalesce(p_skip, ARRAY[]::text[])))
                ORDER BY run_after, created_at
                FOR UPDATE SKIP LOCKED
                LIMIT 1
            )
            RETURNING *;
        END
        $$;
    """)
    op.execute(f"""
        REVOKE EXECUTE ON FUNCTION jobs_claim_for(text, interval, text[], text[]) FROM PUBLIC;
        GRANT EXECUTE ON FUNCTION jobs_claim_for(text, interval, text[], text[])
            TO {WORKER_ROLE}, {INGEST_ROLE};
        GRANT EXECUTE ON FUNCTION
            jobs_complete(uuid, text),
            jobs_extend_lease(uuid, text, interval),
            jobs_fail(uuid, text, text, interval)
        TO {INGEST_ROLE};
    """)


def downgrade() -> None:
    op.execute("""
        REVOKE EXECUTE ON FUNCTION
            jobs_complete(uuid, text),
            jobs_extend_lease(uuid, text, interval),
            jobs_fail(uuid, text, text, interval)
        FROM qbank_ingest;
        DROP FUNCTION jobs_claim_for(text, interval, text[], text[]);
    """)
