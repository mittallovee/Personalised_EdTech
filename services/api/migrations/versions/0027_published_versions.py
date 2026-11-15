"""Published versions: the pointer, the label snapshot and the immutability triggers (M4 PR 4a-4).

Revision ID: 0027
Revises: 0026
Create Date: 2026-11-15

M4 design note §4.5 and §9, ADR-0020 (E-01, E-04, E-07):
- ``question_masters.published_version_id`` points at the version readers see once something is
  published; a correction (version n+1) leaves it alone until that version is published too. A
  trigger lets it name only a PUBLISHED version of the same master, and only move forward.
- ``published_versions``: one row per publication, with the English names of the labels as they
  were that day (so renaming a syllabus item later cannot change how a published question reads)
  and the hash of the published text. Append-only, even for the table owner.
- A trigger refuses any insert, change or delete of a revision of a PUBLISHED version, even for
  the table owner (the version row itself is already guarded by 0026).
- A master has at most one version that is not PUBLISHED: one correction at a time.
- Coaching-owned, so FORCE row-level security with the tenant policy and composite foreign keys.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0027"
down_revision: str | None = "0026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "qbank_app"


def upgrade() -> None:
    op.execute("""
        ALTER TABLE question_masters ADD COLUMN published_version_id uuid;
        ALTER TABLE question_masters
            ADD CONSTRAINT question_masters_published_version_fkey
                FOREIGN KEY (organization_id, published_version_id)
                REFERENCES question_versions (organization_id, id);

        CREATE FUNCTION question_masters_published_guard() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE
            old_number integer;
            new_number integer;
        BEGIN
            IF NEW.published_version_id IS NOT DISTINCT FROM OLD.published_version_id THEN
                RETURN NEW;
            END IF;
            IF NEW.published_version_id IS NULL THEN
                RAISE EXCEPTION 'A question is never unpublished.';
            END IF;
            SELECT number INTO new_number FROM question_versions
                WHERE id = NEW.published_version_id AND master_id = NEW.id
                    AND state = 'PUBLISHED';
            IF new_number IS NULL THEN
                RAISE EXCEPTION 'A question can point only at one of its published versions.';
            END IF;
            IF OLD.published_version_id IS NOT NULL THEN
                SELECT number INTO old_number FROM question_versions
                    WHERE id = OLD.published_version_id;
                IF new_number <= old_number THEN
                    RAISE EXCEPTION 'The published version only moves forward.';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$;
        CREATE TRIGGER question_masters_published
            BEFORE UPDATE OF published_version_id ON question_masters
            FOR EACH ROW EXECUTE FUNCTION question_masters_published_guard();

        -- One correction at a time: only a PUBLISHED version may sit beside the open one.
        CREATE UNIQUE INDEX question_versions_one_open
            ON question_versions (master_id) WHERE state <> 'PUBLISHED';

        CREATE FUNCTION question_revisions_published_guard() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP <> 'INSERT' AND EXISTS (
                SELECT 1 FROM question_versions WHERE id = OLD.version_id AND state = 'PUBLISHED'
            ) THEN
                RAISE EXCEPTION 'The revisions of a published version never change.';
            END IF;
            IF TG_OP <> 'DELETE' AND EXISTS (
                SELECT 1 FROM question_versions WHERE id = NEW.version_id AND state = 'PUBLISHED'
            ) THEN
                RAISE EXCEPTION 'The revisions of a published version never change.';
            END IF;
            IF TG_OP = 'DELETE' THEN
                RETURN OLD;
            END IF;
            RETURN NEW;
        END;
        $$;
        CREATE TRIGGER question_revisions_published
            BEFORE INSERT OR UPDATE OR DELETE ON question_revisions
            FOR EACH ROW EXECUTE FUNCTION question_revisions_published_guard();

        CREATE TABLE published_versions (
            id              uuid PRIMARY KEY,
            organization_id uuid NOT NULL,
            version_id      uuid NOT NULL UNIQUE,
            revision_id     uuid NOT NULL,
            published_by    uuid NOT NULL REFERENCES users (id),
            published_at    timestamptz NOT NULL DEFAULT now(),
            content_hash    text NOT NULL CHECK (length(content_hash) = 64),
            labels          jsonb NOT NULL CHECK (jsonb_typeof(labels) = 'object'),
            FOREIGN KEY (organization_id, version_id)
                REFERENCES question_versions (organization_id, id),
            FOREIGN KEY (organization_id, revision_id)
                REFERENCES question_revisions (organization_id, id)
        );

        CREATE FUNCTION published_versions_append_only() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'A publication record is never changed or deleted.';
        END;
        $$;
        CREATE TRIGGER published_versions_append_only
            BEFORE UPDATE OR DELETE ON published_versions
            FOR EACH ROW EXECUTE FUNCTION published_versions_append_only();

        ALTER TABLE published_versions ENABLE ROW LEVEL SECURITY;
        ALTER TABLE published_versions FORCE ROW LEVEL SECURITY;
        CREATE POLICY published_versions_tenant ON published_versions FOR ALL
            USING (organization_id = app_current_org())
            WITH CHECK (organization_id = app_current_org());
    """)
    op.execute(f"GRANT SELECT, INSERT ON published_versions TO {APP_ROLE};")


def downgrade() -> None:
    op.execute("""
        DROP TABLE published_versions;
        DROP FUNCTION published_versions_append_only();
        DROP TRIGGER question_revisions_published ON question_revisions;
        DROP FUNCTION question_revisions_published_guard();
        DROP INDEX question_versions_one_open;
        DROP TRIGGER question_masters_published ON question_masters;
        DROP FUNCTION question_masters_published_guard();
        ALTER TABLE question_masters
            DROP CONSTRAINT question_masters_published_version_fkey,
            DROP COLUMN published_version_id;
    """)
