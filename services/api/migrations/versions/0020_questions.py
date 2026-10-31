"""Questions: master, version and revision (M3 PR 3b-1).

Revision ID: 0020
Revises: 0019
Create Date: 2026-10-31

M3 design note §5.1 (D-11, D-12, E-04):
- ``question_masters``: one bank question with its permanent code (reserved in ``public_codes``) and
  the person who started it. Archived, never deleted, so a printed code never dangles.
- ``question_versions``: a line of work under a master (version 1 now; M4 adds corrections).
- ``question_revisions``: a saved snapshot of the content (JSON). The newest, unfrozen one is the
  *working revision*, and there is at most one per version. A checkpoint freezes a revision (sets
  ``frozen_at`` and ``content_hash`` together); a frozen revision never changes, and a trigger
  enforces it even for the table owner.
- The labels (metadata) live inside the content, so a checkpoint keeps the labels it was written
  with; filter columns arrive with the bank list (M4).
- Coaching-owned, so FORCE row-level security with the tenant policy, composite foreign keys
  (ADR-0005), and no DELETE right for the runtime role.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0020"
down_revision: str | None = "0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "qbank_app"
TABLES = ("question_masters", "question_versions", "question_revisions")


def upgrade() -> None:
    op.execute("""
        CREATE TABLE question_masters (
            id              uuid PRIMARY KEY,
            organization_id uuid NOT NULL REFERENCES organizations (id),
            code            text NOT NULL UNIQUE REFERENCES public_codes (code),
            created_by      uuid NOT NULL REFERENCES users (id),
            archived_at     timestamptz,
            revision        integer NOT NULL DEFAULT 1,
            created_at      timestamptz NOT NULL DEFAULT now(),
            UNIQUE (organization_id, id)
        );

        CREATE TABLE question_versions (
            id              uuid PRIMARY KEY,
            organization_id uuid NOT NULL,
            master_id       uuid NOT NULL,
            number          integer NOT NULL CHECK (number >= 1),
            created_at      timestamptz NOT NULL DEFAULT now(),
            FOREIGN KEY (organization_id, master_id)
                REFERENCES question_masters (organization_id, id),
            UNIQUE (master_id, number),
            UNIQUE (organization_id, id)
        );

        CREATE TABLE question_revisions (
            id              uuid PRIMARY KEY,
            organization_id uuid NOT NULL,
            version_id      uuid NOT NULL,
            number          integer NOT NULL CHECK (number >= 1),
            content         jsonb NOT NULL CHECK (jsonb_typeof(content) = 'object'),
            content_hash    text CHECK (length(content_hash) = 64),
            author_id       uuid NOT NULL REFERENCES users (id),
            frozen_at       timestamptz,
            revision        integer NOT NULL DEFAULT 1,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            FOREIGN KEY (organization_id, version_id)
                REFERENCES question_versions (organization_id, id),
            UNIQUE (version_id, number),
            CHECK ((frozen_at IS NULL) = (content_hash IS NULL))
        );
        CREATE UNIQUE INDEX question_revisions_one_working
            ON question_revisions (version_id) WHERE frozen_at IS NULL;

        CREATE FUNCTION question_revisions_frozen_guard() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'A frozen revision never changes.';
        END;
        $$;
        CREATE TRIGGER question_revisions_frozen
            BEFORE UPDATE ON question_revisions
            FOR EACH ROW WHEN (OLD.frozen_at IS NOT NULL)
            EXECUTE FUNCTION question_revisions_frozen_guard();
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
        GRANT SELECT, INSERT, UPDATE ON {", ".join(TABLES)} TO {APP_ROLE};  -- archive, never delete
    """)


def downgrade() -> None:
    op.execute("""
        DROP TABLE question_revisions;
        DROP FUNCTION question_revisions_frozen_guard();
        DROP TABLE question_versions;
        DROP TABLE question_masters;
    """)
