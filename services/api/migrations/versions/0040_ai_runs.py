"""AI runs and their provider calls (M5 5e, H-04, H-07).

Revision ID: 0040
Revises: 0039
Create Date: 2026-11-21

M5 design note §4, §6. One ``ai_runs`` row per run of an operation on a question: who asked, which
question and exactly which working revision it was based on, which prompt (a saved version, or the
one-off text typed for that run), a hash of the rendered prompt, the model that answered, the cost
bookkeeping lives in ``ai_ledger`` (by run id), the result and how it was applied. One
``ai_run_attempts`` row per provider call, so a fallback to another model is visible (H-04).

A run is created ``RUNNING`` in the same transaction that reserves its budget, and ends
``SUCCEEDED`` or ``FAILED``. ``apply_status`` says what happened to the result: ``APPLIED``,
``NOT_APPLIED`` (a suggestion not yet accepted, a test run, or a failed run), ``OUT_OF_DATE``
(the question changed while the run was going) or ``NEEDS_REVIEW`` (the person who asked can no
longer edit it).

Coaching-owned: FORCE row-level security with the tenant policy; composite keys keep a run and its
attempts inside one coaching. The runtime role can read, add and change runs and attempts, never
delete them.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0040"
down_revision: str | None = "0039"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "qbank_app"


def upgrade() -> None:
    op.execute("""
        CREATE TABLE ai_runs (
            id                   uuid PRIMARY KEY,
            organization_id      uuid NOT NULL REFERENCES organizations (id),
            user_id              uuid NOT NULL REFERENCES users (id),
            question_id          uuid NOT NULL,
            operation            text NOT NULL CHECK (operation IN
                ('TAG', 'TRANSLATE', 'SOLVE', 'VERIFY')),
            mode                 text NOT NULL DEFAULT 'NOW' CHECK (mode IN ('NOW', 'ECONOMY')),
            status               text NOT NULL DEFAULT 'RUNNING' CHECK (status IN
                ('RUNNING', 'SUCCEEDED', 'FAILED')),
            apply_status         text NOT NULL DEFAULT 'NOT_APPLIED' CHECK (apply_status IN
                ('NOT_APPLIED', 'APPLIED', 'OUT_OF_DATE', 'NEEDS_REVIEW')),
            is_test              boolean NOT NULL DEFAULT false,
            question_revision_id uuid NOT NULL,
            question_revision    integer NOT NULL,
            prompt_source        text NOT NULL CHECK (prompt_source IN
                ('ONE_OFF', 'PERSONAL', 'COACHING', 'PLATFORM')),
            prompt_version_id    uuid,
            one_off_instructions text CHECK (length(one_off_instructions) <= 8000),
            extra_instructions   text CHECK (length(extra_instructions) <= 1000),
            prompt_hash          text NOT NULL,
            model_ref            uuid,
            answered_by          text,
            result               jsonb,
            error_code           text,
            started_at           timestamptz NOT NULL DEFAULT now(),
            finished_at          timestamptz,
            UNIQUE (organization_id, id),
            FOREIGN KEY (organization_id, question_id)
                REFERENCES question_masters (organization_id, id)
        );
        CREATE INDEX ai_runs_by_question ON ai_runs (organization_id, question_id, started_at DESC);
        CREATE INDEX ai_runs_by_person ON ai_runs (organization_id, user_id, started_at DESC);
        CREATE INDEX ai_runs_unfinished ON ai_runs (started_at) WHERE status = 'RUNNING';

        CREATE TABLE ai_run_attempts (
            id              uuid PRIMARY KEY,
            organization_id uuid NOT NULL REFERENCES organizations (id),
            run_id          uuid NOT NULL,
            position        integer NOT NULL CHECK (position BETWEEN 1 AND 3),
            model_ref       uuid,
            provider_model  text NOT NULL,
            outcome         text NOT NULL,
            tokens_in       integer CHECK (tokens_in >= 0),
            tokens_out      integer CHECK (tokens_out >= 0),
            latency_ms      integer CHECK (latency_ms >= 0),
            cost_usd        numeric(14, 6) CHECK (cost_usd >= 0),
            created_at      timestamptz NOT NULL DEFAULT now(),
            UNIQUE (run_id, position),
            FOREIGN KEY (organization_id, run_id) REFERENCES ai_runs (organization_id, id)
        );

        ALTER TABLE ai_runs ENABLE ROW LEVEL SECURITY;
        ALTER TABLE ai_runs FORCE ROW LEVEL SECURITY;
        CREATE POLICY ai_runs_tenant ON ai_runs FOR ALL
            USING (organization_id = app_current_org())
            WITH CHECK (organization_id = app_current_org());
        ALTER TABLE ai_run_attempts ENABLE ROW LEVEL SECURITY;
        ALTER TABLE ai_run_attempts FORCE ROW LEVEL SECURITY;
        CREATE POLICY ai_run_attempts_tenant ON ai_run_attempts FOR ALL
            USING (organization_id = app_current_org())
            WITH CHECK (organization_id = app_current_org());
    """)
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON ai_runs TO {APP_ROLE};")
    op.execute(f"GRANT SELECT, INSERT ON ai_run_attempts TO {APP_ROLE};")


def downgrade() -> None:
    op.execute("DROP TABLE ai_run_attempts; DROP TABLE ai_runs;")
