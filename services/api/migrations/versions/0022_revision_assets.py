"""Which saved revision uses which picture (M3 PR 3g-2).

Revision ID: 0022
Revises: 0021
Create Date: 2026-11-10

M3 design note §5.7: an image referenced by a saved revision cannot be deleted, so history keeps
rendering, and pictures nobody refers to can be found and cleaned up later (M7).

- ``revision_assets`` has one row per picture a revision uses. The working revision's rows follow
  its content on every save (rows are added and removed). The rows of a frozen revision never
  change: a trigger refuses to add or remove them.
- The foreign key from ``revision_assets`` to ``assets`` has no ON DELETE action, so a picture that
  a revision uses cannot be deleted, even by the table owner.
- ``question_revisions`` gets ``UNIQUE (organization_id, id)`` so the table can be pointed at by a
  composite key (ADR-0005). Adding a constraint does not change the migration that made the table.
- Coaching-owned: FORCE row-level security with the tenant policy.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0022"
down_revision: str | None = "0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "qbank_app"


def upgrade() -> None:
    op.execute("""
        ALTER TABLE question_revisions
            ADD CONSTRAINT question_revisions_org_id_key UNIQUE (organization_id, id);

        CREATE TABLE revision_assets (
            organization_id uuid NOT NULL,
            revision_id     uuid NOT NULL,
            asset_id        uuid NOT NULL,
            created_at      timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (revision_id, asset_id),
            FOREIGN KEY (organization_id, revision_id)
                REFERENCES question_revisions (organization_id, id),
            FOREIGN KEY (organization_id, asset_id)
                REFERENCES assets (organization_id, id)
        );
        CREATE INDEX revision_assets_asset ON revision_assets (asset_id);

        CREATE FUNCTION revision_assets_frozen_guard() RETURNS trigger
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
                SELECT 1 FROM question_revisions WHERE id = target AND frozen_at IS NOT NULL
            ) THEN
                RAISE EXCEPTION 'The pictures of a frozen revision never change.';
            END IF;
            IF TG_OP = 'DELETE' THEN
                RETURN OLD;
            END IF;
            RETURN NEW;
        END;
        $$;
        CREATE TRIGGER revision_assets_frozen
            BEFORE INSERT OR UPDATE OR DELETE ON revision_assets
            FOR EACH ROW EXECUTE FUNCTION revision_assets_frozen_guard();

        ALTER TABLE revision_assets ENABLE ROW LEVEL SECURITY;
        ALTER TABLE revision_assets FORCE ROW LEVEL SECURITY;
        CREATE POLICY revision_assets_tenant ON revision_assets FOR ALL
            USING (organization_id = app_current_org())
            WITH CHECK (organization_id = app_current_org());
    """)
    # A row is added or removed only while its revision is the working one (the trigger).
    op.execute(f"GRANT SELECT, INSERT, DELETE ON revision_assets TO {APP_ROLE}")


def downgrade() -> None:
    op.execute("""
        DROP TABLE revision_assets;
        DROP FUNCTION revision_assets_frozen_guard();
        ALTER TABLE question_revisions DROP CONSTRAINT question_revisions_org_id_key;
    """)
