"""What a person decided about a possible duplicate (M4 PR 4g-2, D-16).

Revision ID: 0033
Revises: 0032
Create Date: 2026-11-17

M4 design note §7.4. A person looks at two questions side by side and records **NOT_DUPLICATE** or
**DUPLICATE_OF** (the other question), with a note. The row keeps the version and revision it was
made on and that text's ``duplicate_key``: a decision is about one text, so an edit that changes the
question's meaning needs a new decision. An exact match with no decision, or a DUPLICATE_OF, blocks
Pass QC (``QC_BLOCKED_DUPLICATE``). Nothing is merged or deleted: the author archives a copy.

Append-only (a trigger refuses UPDATE and DELETE, and the app role may only SELECT and INSERT): a
person changes their mind by recording a new decision, the newest counts, and the old one stays as
history. Coaching-owned: FORCE row-level security with the tenant policy, composite foreign keys to
this coaching's versions, revisions and questions.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0033"
down_revision: str | None = "0032"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "qbank_app"


def upgrade() -> None:
    op.execute("""
        CREATE TABLE duplicate_decisions (
            id               uuid PRIMARY KEY,
            organization_id  uuid NOT NULL REFERENCES organizations (id),
            version_id       uuid NOT NULL,
            revision_id      uuid NOT NULL,
            duplicate_key    text NOT NULL CHECK (length(duplicate_key) = 64),
            other_master_id  uuid NOT NULL,
            decision         text NOT NULL CHECK (decision IN ('NOT_DUPLICATE', 'DUPLICATE_OF')),
            note             text NOT NULL CHECK (length(note) BETWEEN 1 AND 1000),
            actor_id         uuid NOT NULL REFERENCES users (id),
            created_at       timestamptz NOT NULL DEFAULT now(),
            FOREIGN KEY (organization_id, version_id)
                REFERENCES question_versions (organization_id, id),
            FOREIGN KEY (organization_id, revision_id)
                REFERENCES question_revisions (organization_id, id),
            FOREIGN KEY (organization_id, other_master_id)
                REFERENCES question_masters (organization_id, id)
        );
        CREATE INDEX duplicate_decisions_version
            ON duplicate_decisions (version_id, duplicate_key, other_master_id, created_at);

        CREATE FUNCTION duplicate_decisions_append_only() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'A duplicate decision is never changed or deleted.';
        END;
        $$;
        CREATE TRIGGER duplicate_decisions_append_only
            BEFORE UPDATE OR DELETE ON duplicate_decisions
            FOR EACH ROW EXECUTE FUNCTION duplicate_decisions_append_only();

        ALTER TABLE duplicate_decisions ENABLE ROW LEVEL SECURITY;
        ALTER TABLE duplicate_decisions FORCE ROW LEVEL SECURITY;
        CREATE POLICY duplicate_decisions_tenant ON duplicate_decisions FOR ALL
            USING (organization_id = app_current_org())
            WITH CHECK (organization_id = app_current_org());
    """)
    op.execute(f"GRANT SELECT, INSERT ON duplicate_decisions TO {APP_ROLE};")


def downgrade() -> None:
    op.execute("""
        DROP TABLE duplicate_decisions;
        DROP FUNCTION duplicate_decisions_append_only();
    """)
