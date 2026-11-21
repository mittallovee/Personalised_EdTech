"""Economy (batch) runs: the states and columns a run needs to wait for a provider (M5 5h, H-18).

Revision ID: 0042
Revises: 0041
Create Date: 2026-11-21

M5 design note §8, ADR-0009. A "Now" run lives and ends inside one request. An Economy run is
handed to a provider's batch service and finished later by background jobs, so it needs states in
between and somewhere to keep what it will need:

- ``status`` gains ``QUEUED`` (reserved, waiting for the submit job), ``SUBMITTING`` (the one
  worker that won it is calling the provider), ``SUBMITTED`` (the provider has it;
  ``provider_batch_id`` is set), ``CANCELLED``, ``EXPIRED`` and ``SUBMISSION_UNKNOWN`` (the
  outcome of the submission could not be learned; its whole reservation stays held until an admin
  settles it).
- ``request`` keeps the rendered request (prompt, schema, limits) and a snapshot of the question's
  content the run was based on, so the result can be checked and applied hours later against
  exactly what was sent, even if the question has changed since.
- ``cancel_requested_at`` is the person's intent, recorded before the provider is asked to stop:
  a result that still arrives afterwards is kept and charged but never applied.
- ``batch_discount`` is the discount the reservation assumed, so the settled charge uses the same.

A batch id is unique within a coaching, so one provider batch can never belong to two runs.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0042"
down_revision: str | None = "0041"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE ai_runs DROP CONSTRAINT ai_runs_status_check;
        ALTER TABLE ai_runs ADD CONSTRAINT ai_runs_status_check CHECK (status IN
            ('RUNNING', 'QUEUED', 'SUBMITTING', 'SUBMITTED', 'SUCCEEDED', 'FAILED', 'CANCELLED',
             'EXPIRED', 'SUBMISSION_UNKNOWN'));
        ALTER TABLE ai_runs
            ADD COLUMN request             jsonb,
            ADD COLUMN provider_batch_id   text CHECK (length(provider_batch_id) <= 300),
            ADD COLUMN submit_started_at   timestamptz,
            ADD COLUMN cancel_requested_at timestamptz,
            ADD COLUMN batch_discount      numeric(5, 4) CHECK (batch_discount >= 0
                                                                AND batch_discount < 1);
        CREATE UNIQUE INDEX ai_runs_one_run_per_batch
            ON ai_runs (organization_id, provider_batch_id) WHERE provider_batch_id IS NOT NULL;
        CREATE INDEX ai_runs_waiting ON ai_runs (started_at)
            WHERE status IN ('QUEUED', 'SUBMITTING', 'SUBMITTED');
    """)


def downgrade() -> None:
    op.execute("""
        DROP INDEX ai_runs_waiting;
        DROP INDEX ai_runs_one_run_per_batch;
        ALTER TABLE ai_runs
            DROP COLUMN batch_discount,
            DROP COLUMN cancel_requested_at,
            DROP COLUMN submit_started_at,
            DROP COLUMN provider_batch_id,
            DROP COLUMN request;
        ALTER TABLE ai_runs DROP CONSTRAINT ai_runs_status_check;
        ALTER TABLE ai_runs ADD CONSTRAINT ai_runs_status_check CHECK (status IN
            ('RUNNING', 'SUCCEEDED', 'FAILED'));
    """)
