"""Reading documents with AI: settings, runs, candidates (M6 6f, G-04, G-06, D-16).

Revision ID: 0046
Revises: 0045
Create Date: 2026-11-28

M6 design note §5 and §7.

- ``ingest_settings``: which model a coaching reads pages with (one row per coaching; an admin
  sets it).
- ``ingest_runs``: one reading of one file by one model and prompt; a retry is a new run.
- ``ingest_run_pages``: where each page of a run stands, so a restart does only the pages not
  done. ``ledger_id`` names the budget reservation of the current attempt (each attempt has its
  own, so a reservation a crash left behind can be given back before the page is read again).
- ``ingest_candidates``: one question found on a page: the model's own reading (``raw``, never
  changed), the editable content a person fixes, findings from the question checks, and what was
  decided. ``(run_id, page_no, ordinal)`` is unique, so a retried page cannot make a candidate
  twice.
- ``ingest_candidate_events``: append-only history of who did what to a candidate.

The normal worker is a member of the application role, so it reads and writes these like the API.
The sandboxed render worker (``qbank_ingest``) has no access to any of them.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0046"
down_revision: str | None = "0045"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "qbank_app"
TABLES = (
    "ingest_settings",
    "ingest_runs",
    "ingest_run_pages",
    "ingest_candidates",
    "ingest_candidate_events",
)


def upgrade() -> None:
    op.execute("""
        CREATE TABLE ingest_settings (
            organization_id uuid PRIMARY KEY REFERENCES organizations (id),
            model_id        uuid,
            revision        integer NOT NULL DEFAULT 1,
            updated_by      uuid NOT NULL REFERENCES users (id),
            updated_at      timestamptz NOT NULL DEFAULT now()
        );

        CREATE TABLE ingest_runs (
            id              uuid PRIMARY KEY,
            organization_id uuid NOT NULL REFERENCES organizations (id),
            file_id         uuid NOT NULL,
            requested_by    uuid NOT NULL REFERENCES users (id),
            model_ref       uuid NOT NULL,
            prompt_version  text NOT NULL,
            prompt_hash     text NOT NULL,
            state           text NOT NULL DEFAULT 'RUNNING'
                CHECK (state IN ('RUNNING', 'DONE', 'PARTIAL', 'FAILED', 'CANCELLED')),
            pages_total     integer NOT NULL CHECK (pages_total >= 0),
            pages_done      integer NOT NULL DEFAULT 0,
            pages_failed    integer NOT NULL DEFAULT 0,
            error_code      text,
            started_at      timestamptz NOT NULL DEFAULT now(),
            finished_at     timestamptz,
            UNIQUE (organization_id, id),
            FOREIGN KEY (organization_id, file_id) REFERENCES ingest_files (organization_id, id)
        );
        CREATE INDEX ingest_runs_by_file ON ingest_runs (organization_id, file_id, started_at DESC);

        CREATE TABLE ingest_run_pages (
            id              uuid PRIMARY KEY,
            organization_id uuid NOT NULL,
            run_id          uuid NOT NULL,
            page_no         integer NOT NULL CHECK (page_no >= 1),
            state           text NOT NULL CHECK (state IN ('RUNNING', 'DONE', 'FAILED')),
            ledger_id       uuid NOT NULL,
            error_code      text,
            candidate_count integer NOT NULL DEFAULT 0,
            started_at      timestamptz NOT NULL DEFAULT now(),
            finished_at     timestamptz,
            UNIQUE (run_id, page_no),
            FOREIGN KEY (organization_id, run_id) REFERENCES ingest_runs (organization_id, id)
        );

        CREATE TABLE ingest_candidates (
            id              uuid PRIMARY KEY,
            organization_id uuid NOT NULL,
            file_id         uuid NOT NULL,
            run_id          uuid NOT NULL,
            page_no         integer NOT NULL CHECK (page_no >= 1),
            ordinal         integer NOT NULL CHECK (ordinal >= 1),
            region          jsonb,
            raw             jsonb NOT NULL,
            content         jsonb NOT NULL,
            findings        jsonb NOT NULL DEFAULT '[]'::jsonb,
            confidence      text NOT NULL CHECK (confidence IN ('HIGH', 'MEDIUM', 'LOW')),
            warnings        jsonb NOT NULL DEFAULT '[]'::jsonb,
            state           text NOT NULL DEFAULT 'NEW'
                CHECK (state IN ('NEW', 'ACCEPTED', 'REJECTED', 'DUPLICATE')),
            question_id     uuid,
            reject_reason   text CHECK (reject_reason IS NULL OR char_length(reject_reason) <= 500),
            revision        integer NOT NULL DEFAULT 1,
            decided_by      uuid REFERENCES users (id),
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            UNIQUE (run_id, page_no, ordinal),
            UNIQUE (organization_id, id),
            FOREIGN KEY (organization_id, run_id) REFERENCES ingest_runs (organization_id, id),
            FOREIGN KEY (organization_id, file_id) REFERENCES ingest_files (organization_id, id)
        );
        CREATE INDEX ingest_candidates_by_file
            ON ingest_candidates (organization_id, file_id, page_no, ordinal);
        CREATE INDEX ingest_candidates_by_state ON ingest_candidates (organization_id, state);

        CREATE TABLE ingest_candidate_events (
            id              uuid PRIMARY KEY,
            organization_id uuid NOT NULL,
            candidate_id    uuid NOT NULL,
            actor_user_id   uuid REFERENCES users (id),
            action          text NOT NULL,
            detail          jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_at      timestamptz NOT NULL DEFAULT now(),
            FOREIGN KEY (organization_id, candidate_id)
                REFERENCES ingest_candidates (organization_id, id)
        );
    """)
    for table in TABLES:
        op.execute(f"""
            ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
            ALTER TABLE {table} FORCE ROW LEVEL SECURITY;
            CREATE POLICY {table}_tenant ON {table} FOR ALL
                USING (organization_id = app_current_org())
                WITH CHECK (organization_id = app_current_org());
        """)
    op.execute(f"""
        GRANT SELECT, INSERT, UPDATE ON
            ingest_settings, ingest_runs, ingest_run_pages, ingest_candidates TO {APP_ROLE};
        GRANT SELECT, INSERT ON ingest_candidate_events TO {APP_ROLE};
    """)


def downgrade() -> None:
    op.execute("""
        DROP TABLE ingest_candidate_events;
        DROP TABLE ingest_candidates;
        DROP TABLE ingest_run_pages;
        DROP TABLE ingest_runs;
        DROP TABLE ingest_settings;
    """)
