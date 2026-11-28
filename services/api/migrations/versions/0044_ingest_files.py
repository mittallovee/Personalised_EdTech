"""Uploaded documents: one row per original file (M6 6b, G-01, G-09).

Revision ID: 0044
Revises: 0043
Create Date: 2026-11-28

M6 design note §5. The original is kept as it arrived (storage key
``org/<coaching>/ingest/<id>``); the row records what it is, who sent it and where it stands.
Nothing about the file's content is stored here: pages and candidates come later (6c, 6f).

- ``kind`` is decided from the file's first bytes by the API (it never parses a document); the
  sandboxed worker checks the structure when it renders (ADR-0024).
- ``state``: UPLOADED, RENDERING, READY, EXTRACTING, DONE, PARTIAL, FAILED, CANCELLED.
- The API role may add a row and change only ``state``, ``error_code`` and ``updated_at`` (cancel);
  the sandbox role may read the rows of the job's own coaching (row-level security applies to it
  too) and change only ``state``, ``page_count``, ``error_code`` and ``updated_at``.
- The file name is a label only: never a path, never trusted (control characters are stripped
  and the length capped before it is stored).
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0044"
down_revision: str | None = "0043"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "qbank_app"
INGEST_ROLE = "qbank_ingest"


def upgrade() -> None:
    op.execute(f"""
        CREATE TABLE ingest_files (
            id              uuid PRIMARY KEY,
            organization_id uuid NOT NULL REFERENCES organizations (id),
            uploaded_by     uuid NOT NULL REFERENCES users (id),
            file_name       text NOT NULL CHECK (char_length(file_name) BETWEEN 1 AND 200),
            kind            text NOT NULL
                CHECK (kind IN ('PDF', 'DOCX', 'JPEG', 'PNG', 'WEBP', 'HEIC')),
            byte_size       integer NOT NULL CHECK (byte_size > 0),
            sha256          text NOT NULL CHECK (length(sha256) = 64),
            storage_key     text NOT NULL UNIQUE,
            state           text NOT NULL DEFAULT 'UPLOADED'
                CHECK (state IN ('UPLOADED', 'RENDERING', 'READY', 'EXTRACTING', 'DONE',
                                 'PARTIAL', 'FAILED', 'CANCELLED')),
            page_count      integer CHECK (page_count IS NULL OR page_count >= 0),
            error_code      text,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            UNIQUE (organization_id, id)
        );
        CREATE INDEX ingest_files_org_created
            ON ingest_files (organization_id, created_at DESC, id);
        CREATE INDEX ingest_files_org_sha ON ingest_files (organization_id, sha256);
        CREATE INDEX ingest_files_org_state ON ingest_files (organization_id, state);

        ALTER TABLE ingest_files ENABLE ROW LEVEL SECURITY;
        ALTER TABLE ingest_files FORCE ROW LEVEL SECURITY;
        CREATE POLICY ingest_files_tenant ON ingest_files FOR ALL
            USING (organization_id = app_current_org())
            WITH CHECK (organization_id = app_current_org());

        GRANT SELECT, INSERT ON ingest_files TO {APP_ROLE};
        GRANT UPDATE (state, error_code, updated_at) ON ingest_files TO {APP_ROLE};
        GRANT SELECT ON ingest_files TO {INGEST_ROLE};
        GRANT UPDATE (state, page_count, error_code, updated_at) ON ingest_files TO {INGEST_ROLE};
    """)


def downgrade() -> None:
    op.execute("DROP TABLE ingest_files;")
