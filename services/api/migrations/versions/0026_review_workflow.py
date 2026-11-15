"""Review workflow: the state of a question version and its decisions (M4 PR 4a-2).

Revision ID: 0026
Revises: 0025
Create Date: 2026-11-15

M4 design note §4 and §9, ADR-0020 (E-01, E-04):
- ``question_versions`` gains ``state`` (every M3 row becomes DRAFT), ``flow_revision`` (the counter
  behind the workflow ETag ``"flow-N"``), ``review_revision_id`` (the frozen revision under review)
  and ``state_changed_at``.
- A trigger repeats the allowed state pairs of ``questions/domain/workflow.py``, so a bug in code
  cannot skip a step: even the table owner cannot move a version along a pair the table does not
  list, change the revision under review, or touch a PUBLISHED version.
- ``review_decisions``: one row for every step taken, append-only (no UPDATE or DELETE right for the
  runtime role, and a trigger that refuses both for the owner too).
- Coaching-owned, so FORCE row-level security with the tenant policy and composite foreign keys.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0026"
down_revision: str | None = "0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "qbank_app"


def upgrade() -> None:
    op.execute("""
        ALTER TABLE question_versions
            ADD COLUMN state text NOT NULL DEFAULT 'DRAFT' CHECK (state IN (
                'DRAFT', 'IN_REVIEW', 'CHANGES_REQUESTED', 'QC_PASSED', 'APPROVED', 'PUBLISHED')),
            ADD COLUMN flow_revision integer NOT NULL DEFAULT 1 CHECK (flow_revision >= 1),
            ADD COLUMN review_revision_id uuid,
            ADD COLUMN state_changed_at timestamptz NOT NULL DEFAULT now(),
            ADD CONSTRAINT question_versions_review_revision_fkey
                FOREIGN KEY (organization_id, review_revision_id)
                REFERENCES question_revisions (organization_id, id),
            -- A draft or returned question has nothing under review; every other state has one.
            ADD CONSTRAINT question_versions_review_revision_matches_state
                CHECK ((state IN ('DRAFT', 'CHANGES_REQUESTED')) = (review_revision_id IS NULL));

        CREATE FUNCTION question_versions_workflow_guard() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP = 'INSERT' THEN
                IF NEW.state <> 'DRAFT' THEN
                    RAISE EXCEPTION 'A new version starts as a draft.';
                END IF;
                RETURN NEW;
            END IF;
            IF OLD.state = 'PUBLISHED' THEN
                RAISE EXCEPTION 'A published version never changes.';
            END IF;
            IF NEW.state = OLD.state THEN
                IF NEW.review_revision_id IS DISTINCT FROM OLD.review_revision_id
                    OR NEW.flow_revision <> OLD.flow_revision THEN
                    RAISE EXCEPTION 'The revision under review changes only with the state.';
                END IF;
                RETURN NEW;
            END IF;
            -- The same pairs as questions/domain/workflow.py (T33 tests both from one table).
            IF (OLD.state || '>' || NEW.state) <> ALL (ARRAY[
                'DRAFT>IN_REVIEW', 'CHANGES_REQUESTED>IN_REVIEW',
                'IN_REVIEW>CHANGES_REQUESTED', 'IN_REVIEW>QC_PASSED', 'IN_REVIEW>DRAFT',
                'QC_PASSED>APPROVED', 'QC_PASSED>CHANGES_REQUESTED', 'QC_PASSED>DRAFT',
                'APPROVED>PUBLISHED', 'APPROVED>CHANGES_REQUESTED', 'APPROVED>DRAFT'
            ]) THEN
                RAISE EXCEPTION 'A version cannot go from % to %.', OLD.state, NEW.state;
            END IF;
            IF NEW.flow_revision <> OLD.flow_revision + 1 THEN
                RAISE EXCEPTION 'Every change of state raises the workflow revision by one.';
            END IF;
            IF NEW.state = 'IN_REVIEW' THEN
                IF NOT EXISTS (
                    SELECT 1 FROM question_revisions r
                    WHERE r.id = NEW.review_revision_id AND r.version_id = NEW.id
                        AND r.frozen_at IS NOT NULL
                ) THEN
                    RAISE EXCEPTION 'Review needs a frozen revision of this version.';
                END IF;
            ELSIF NEW.state IN ('QC_PASSED', 'APPROVED', 'PUBLISHED')
                AND NEW.review_revision_id IS DISTINCT FROM OLD.review_revision_id THEN
                RAISE EXCEPTION 'The revision under review cannot change after it was submitted.';
            END IF;
            RETURN NEW;
        END;
        $$;
        CREATE TRIGGER question_versions_workflow
            BEFORE INSERT OR UPDATE ON question_versions
            FOR EACH ROW EXECUTE FUNCTION question_versions_workflow_guard();

        CREATE TABLE review_decisions (
            id              uuid PRIMARY KEY,
            organization_id uuid NOT NULL,
            version_id      uuid NOT NULL,
            revision_id     uuid NOT NULL,
            step            text NOT NULL CHECK (step IN (
                'SUBMIT', 'RETURN', 'PASS_QC', 'APPROVE', 'PUBLISH', 'WITHDRAW',
                'START_CORRECTION')),
            from_state      text NOT NULL,
            to_state        text NOT NULL,
            flow_revision   integer NOT NULL,
            actor_id        uuid NOT NULL REFERENCES users (id),
            reasons         jsonb NOT NULL DEFAULT '[]' CHECK (jsonb_typeof(reasons) = 'array'),
            note            text,
            checklist       jsonb,
            created_at      timestamptz NOT NULL DEFAULT now(),
            FOREIGN KEY (organization_id, version_id)
                REFERENCES question_versions (organization_id, id),
            FOREIGN KEY (organization_id, revision_id)
                REFERENCES question_revisions (organization_id, id)
        );
        CREATE INDEX review_decisions_version ON review_decisions (version_id, created_at);

        CREATE FUNCTION review_decisions_append_only() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'A review decision is never changed or deleted.';
        END;
        $$;
        CREATE TRIGGER review_decisions_append_only
            BEFORE UPDATE OR DELETE ON review_decisions
            FOR EACH ROW EXECUTE FUNCTION review_decisions_append_only();

        ALTER TABLE review_decisions ENABLE ROW LEVEL SECURITY;
        ALTER TABLE review_decisions FORCE ROW LEVEL SECURITY;
        CREATE POLICY review_decisions_tenant ON review_decisions FOR ALL
            USING (organization_id = app_current_org())
            WITH CHECK (organization_id = app_current_org());
    """)
    op.execute(f"GRANT SELECT, INSERT ON review_decisions TO {APP_ROLE};")


def downgrade() -> None:
    op.execute("""
        DROP TABLE review_decisions;
        DROP FUNCTION review_decisions_append_only();
        DROP TRIGGER question_versions_workflow ON question_versions;
        DROP FUNCTION question_versions_workflow_guard();
        ALTER TABLE question_versions
            DROP CONSTRAINT question_versions_review_revision_matches_state,
            DROP CONSTRAINT question_versions_review_revision_fkey,
            DROP COLUMN state_changed_at,
            DROP COLUMN review_revision_id,
            DROP COLUMN flow_revision,
            DROP COLUMN state;
    """)
