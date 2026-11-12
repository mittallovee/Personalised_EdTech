"""Passages: shared text with questions under it (M3 PR 3h-1).

Revision ID: 0023
Revises: 0022
Create Date: 2026-11-12

M3 design note §5.6 (D-14):
- ``passages``: one passage and who started it. It has no public code: it is only context.
- ``passage_revisions``: saved snapshots of the passage's content (JSON), like question revisions.
  The newest unfrozen one is the *working revision* (at most one per passage). A checkpoint freezes
  it (``frozen_at`` and ``content_hash`` together), and a trigger keeps a frozen revision from ever
  changing, even for the table owner. A child question pins one frozen revision.
- ``passage_revision_assets``: which picture a passage revision uses, like ``revision_assets``: the
  rows follow the working revision, a trigger keeps a frozen revision's rows fixed, and the key to
  ``assets`` has no delete action, so a picture in use cannot be deleted.
- Coaching-owned: FORCE row-level security with the tenant policy, composite foreign keys
  (ADR-0005), and no DELETE right on the passage tables for the runtime role.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0023"
down_revision: str | None = "0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "qbank_app"
TABLES = ("passages", "passage_revisions", "passage_revision_assets")


def upgrade() -> None:
    op.execute("""
        CREATE TABLE passages (
            id              uuid PRIMARY KEY,
            organization_id uuid NOT NULL REFERENCES organizations (id),
            created_by      uuid NOT NULL REFERENCES users (id),
            created_at      timestamptz NOT NULL DEFAULT now(),
            UNIQUE (organization_id, id)
        );

        CREATE TABLE passage_revisions (
            id              uuid PRIMARY KEY,
            organization_id uuid NOT NULL,
            passage_id      uuid NOT NULL,
            number          integer NOT NULL CHECK (number >= 1),
            content         jsonb NOT NULL CHECK (jsonb_typeof(content) = 'object'),
            content_hash    text CHECK (length(content_hash) = 64),
            author_id       uuid NOT NULL REFERENCES users (id),
            frozen_at       timestamptz,
            revision        integer NOT NULL DEFAULT 1,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            FOREIGN KEY (organization_id, passage_id)
                REFERENCES passages (organization_id, id),
            UNIQUE (passage_id, number),
            UNIQUE (organization_id, id),
            CHECK ((frozen_at IS NULL) = (content_hash IS NULL))
        );
        CREATE UNIQUE INDEX passage_revisions_one_working
            ON passage_revisions (passage_id) WHERE frozen_at IS NULL;

        CREATE FUNCTION passage_revisions_frozen_guard() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'A frozen revision never changes.';
        END;
        $$;
        CREATE TRIGGER passage_revisions_frozen
            BEFORE UPDATE ON passage_revisions
            FOR EACH ROW WHEN (OLD.frozen_at IS NOT NULL)
            EXECUTE FUNCTION passage_revisions_frozen_guard();

        CREATE TABLE passage_revision_assets (
            organization_id uuid NOT NULL,
            revision_id     uuid NOT NULL,
            asset_id        uuid NOT NULL,
            created_at      timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (revision_id, asset_id),
            FOREIGN KEY (organization_id, revision_id)
                REFERENCES passage_revisions (organization_id, id),
            FOREIGN KEY (organization_id, asset_id)
                REFERENCES assets (organization_id, id)
        );
        CREATE INDEX passage_revision_assets_asset ON passage_revision_assets (asset_id);

        CREATE FUNCTION passage_revision_assets_frozen_guard() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE
            target uuid;
        BEGIN
            IF TG_OP = 'DELETE' THEN
                target := OLD.revision_id;
            ELSE
                target := NEW.revision_id;
            END IF;
            IF EXISTS (
                SELECT 1 FROM passage_revisions WHERE id = target AND frozen_at IS NOT NULL
            ) THEN
                RAISE EXCEPTION 'The pictures of a frozen revision never change.';
            END IF;
            IF TG_OP = 'DELETE' THEN
                RETURN OLD;
            END IF;
            RETURN NEW;
        END;
        $$;
        CREATE TRIGGER passage_revision_assets_frozen
            BEFORE INSERT OR UPDATE OR DELETE ON passage_revision_assets
            FOR EACH ROW EXECUTE FUNCTION passage_revision_assets_frozen_guard();

        -- Children find their passage by the revision they pin (a lookup by id inside JSON).
        CREATE INDEX question_revisions_passage_pin
            ON question_revisions ((content -> 'context' ->> 'passage_revision_id'))
            WHERE content ? 'context';
    """)
    for table in TABLES:
        op.execute(f"""
            ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
            ALTER TABLE {table} FORCE ROW LEVEL SECURITY;
            CREATE POLICY {table}_tenant ON {table} FOR ALL
                USING (organization_id = app_current_org())
                WITH CHECK (organization_id = app_current_org());
        """)
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON passages, passage_revisions TO {APP_ROLE}")
    # Rows follow the working revision (the trigger stops a frozen one's), so they can go too.
    op.execute(f"GRANT SELECT, INSERT, DELETE ON passage_revision_assets TO {APP_ROLE}")


def downgrade() -> None:
    op.execute("""
        DROP INDEX question_revisions_passage_pin;
        DROP TABLE passage_revision_assets;
        DROP FUNCTION passage_revision_assets_frozen_guard();
        DROP TABLE passage_revisions;
        DROP FUNCTION passage_revisions_frozen_guard();
        DROP TABLE passages;
    """)
