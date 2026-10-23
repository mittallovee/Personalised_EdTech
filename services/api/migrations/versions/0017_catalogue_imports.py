"""Syllabus import previews: the parsed rows an admin has seen, kept until applied (M3 PR 2c-2).

Revision ID: 0017
Revises: 0016
Create Date: 2026-10-23

M3 design note §4.4 (C-03): an import is a preview, then apply. The preview stores what the file
said, already parsed and checked (not the file itself), so applying later uses exactly the rows
the admin was shown. ``base_fingerprint`` is a hash of the syllabus at preview time; applying
refuses a preview whose syllabus has changed since.

- Coaching-owned, so FORCE row-level security with the tenant policy (ADR-0005).
- A preview is never changed once written except to be marked applied: the runtime role may update
  only ``state`` and ``applied_at``, and may not delete.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "qbank_app"


def upgrade() -> None:
    op.execute("""
        CREATE TABLE catalogue_imports (
            id               uuid PRIMARY KEY,
            organization_id  uuid NOT NULL REFERENCES organizations (id),
            created_by       uuid NOT NULL REFERENCES users (id),
            file_name        text NOT NULL CHECK (length(file_name) BETWEEN 1 AND 200),
            file_sha256      text NOT NULL CHECK (file_sha256 ~ '^[0-9a-f]{64}$'),
            state            text NOT NULL DEFAULT 'PREVIEWED'
                                 CHECK (state IN ('PREVIEWED', 'APPLIED')),
            counts           jsonb NOT NULL,
            base_fingerprint text NOT NULL CHECK (base_fingerprint ~ '^[0-9a-f]{64}$'),
            rows             jsonb NOT NULL,
            created_at       timestamptz NOT NULL DEFAULT now(),
            applied_at       timestamptz,
            UNIQUE (organization_id, id),
            CHECK ((state = 'APPLIED') = (applied_at IS NOT NULL))
        );
        CREATE INDEX catalogue_imports_recent
            ON catalogue_imports (organization_id, created_at DESC, id);

        ALTER TABLE catalogue_imports ENABLE ROW LEVEL SECURITY;
        ALTER TABLE catalogue_imports FORCE ROW LEVEL SECURITY;
        CREATE POLICY catalogue_imports_tenant ON catalogue_imports FOR ALL
            USING (organization_id = app_current_org())
            WITH CHECK (organization_id = app_current_org());
    """)
    op.execute(f"""
        GRANT SELECT, INSERT ON catalogue_imports TO {APP_ROLE};
        GRANT UPDATE (state, applied_at) ON catalogue_imports TO {APP_ROLE};  -- never deleted
    """)


def downgrade() -> None:
    op.execute("DROP TABLE catalogue_imports;")
