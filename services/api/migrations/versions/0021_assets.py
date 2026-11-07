"""Assets: uploaded pictures (M3 PR 3g-1).

Revision ID: 0021
Revises: 0020
Create Date: 2026-11-07

M3 design note §5.7 and ADR-0012:
- ``assets``: one stored file of a coaching. The bytes live in file storage under an opaque
  ``storage_key``; the row keeps what the file is (type, size, width, height), its SHA-256 and who
  uploaded it. A row never changes after it is written, and the runtime role has no UPDATE or
  DELETE right on it (a picture used by a saved question must keep rendering).
- Coaching-owned: FORCE row-level security with the tenant policy and a composite key for the
  tables that will refer to it (ADR-0005).
- ``revision_assets`` (which saved revision uses which picture) arrives with the PR that checks and
  records the references.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0021"
down_revision: str | None = "0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "qbank_app"


def upgrade() -> None:
    op.execute(f"""
        CREATE TABLE assets (
            id              uuid PRIMARY KEY,
            organization_id uuid NOT NULL REFERENCES organizations (id),
            kind            text NOT NULL CHECK (kind IN ('IMAGE')),
            content_type    text NOT NULL
                CHECK (content_type IN ('image/png', 'image/jpeg', 'image/webp')),
            byte_size       integer NOT NULL CHECK (byte_size > 0),
            sha256          text NOT NULL CHECK (length(sha256) = 64),
            width           integer NOT NULL CHECK (width > 0),
            height          integer NOT NULL CHECK (height > 0),
            storage_key     text NOT NULL UNIQUE,
            created_by      uuid NOT NULL REFERENCES users (id),
            created_at      timestamptz NOT NULL DEFAULT now(),
            UNIQUE (organization_id, id)
        );
        ALTER TABLE assets ENABLE ROW LEVEL SECURITY;
        ALTER TABLE assets FORCE ROW LEVEL SECURITY;
        CREATE POLICY assets_tenant ON assets FOR ALL
            USING (organization_id = app_current_org())
            WITH CHECK (organization_id = app_current_org());
        GRANT SELECT, INSERT ON assets TO {APP_ROLE};  -- written once, never changed or deleted
    """)


def downgrade() -> None:
    op.execute("DROP TABLE assets;")
