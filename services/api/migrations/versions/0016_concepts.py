"""Concepts: what a question is about, with names in each language and aliases (M3 PR 2b).

Revision ID: 0016
Revises: 0015
Create Date: 2026-10-23

M3 design note §4.2 (C-02, C-03):
- ``concepts``: an idea such as "Newton's second law", belonging to exactly one subject of the
  syllabus. The database enforces it: the subject is referenced together with its kind, and a CHECK
  says that kind is SUBJECT, so a concept can never hang under a chapter or another coaching's
  subject. Two concepts of a subject cannot share a name (compared without regard to case or
  spacing). A concept never changes subject.
- ``concept_labels``: the concept's name in the other languages.
- ``concept_aliases``: other ways to say the same thing ("Newton's 2nd law"). An alias is unique
  within a subject (it can name only one concept there), and carries its concept's subject through
  a composite foreign key, so the two can never disagree.
- Retired, never deleted (C-04): the runtime role has no DELETE right on ``concepts``.
- Coaching-owned, so FORCE row-level security with the tenant policy (ADR-0005).
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "qbank_app"


def upgrade() -> None:
    op.execute("""
        CREATE TABLE concepts (
            id              uuid PRIMARY KEY,
            organization_id uuid NOT NULL REFERENCES organizations (id),
            subject_id      uuid NOT NULL,
            subject_kind    text NOT NULL DEFAULT 'SUBJECT' CHECK (subject_kind = 'SUBJECT'),
            name            text NOT NULL CHECK (length(name) BETWEEN 1 AND 200),
            name_key        text NOT NULL CHECK (length(name_key) BETWEEN 1 AND 400),
            state           text NOT NULL DEFAULT 'ACTIVE'
                                CHECK (state IN ('ACTIVE', 'DEPRECATED')),
            revision        integer NOT NULL DEFAULT 1,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            UNIQUE (organization_id, id),
            UNIQUE (organization_id, id, subject_id),
            FOREIGN KEY (organization_id, subject_id, subject_kind)
                REFERENCES taxonomy_nodes (organization_id, id, kind)
        );
        CREATE UNIQUE INDEX concepts_name ON concepts (organization_id, subject_id, name_key);
        -- The concept picker lists one subject's concepts in name order.
        CREATE INDEX concepts_by_subject
            ON concepts (organization_id, subject_id, state, name_key, id);

        CREATE TABLE concept_labels (
            organization_id uuid NOT NULL,
            concept_id      uuid NOT NULL,
            language        text NOT NULL CHECK (language ~ '^[a-z]{2,3}$'),
            label           text NOT NULL CHECK (length(label) BETWEEN 1 AND 200),
            PRIMARY KEY (concept_id, language),
            FOREIGN KEY (organization_id, concept_id) REFERENCES concepts (organization_id, id)
        );
        CREATE INDEX concept_labels_org ON concept_labels (organization_id);

        CREATE TABLE concept_aliases (
            organization_id uuid NOT NULL,
            concept_id      uuid NOT NULL,
            subject_id      uuid NOT NULL,
            alias           text NOT NULL CHECK (length(alias) BETWEEN 1 AND 200),
            alias_key       text NOT NULL CHECK (length(alias_key) BETWEEN 1 AND 400),
            PRIMARY KEY (concept_id, alias_key),
            FOREIGN KEY (organization_id, concept_id, subject_id)
                REFERENCES concepts (organization_id, id, subject_id)
        );
        -- An alias names one concept in a subject; the picker also looks aliases up by key.
        CREATE UNIQUE INDEX concept_aliases_key
            ON concept_aliases (organization_id, subject_id, alias_key);

        ALTER TABLE concepts ENABLE ROW LEVEL SECURITY;
        ALTER TABLE concepts FORCE ROW LEVEL SECURITY;
        CREATE POLICY concepts_tenant ON concepts FOR ALL
            USING (organization_id = app_current_org())
            WITH CHECK (organization_id = app_current_org());

        ALTER TABLE concept_labels ENABLE ROW LEVEL SECURITY;
        ALTER TABLE concept_labels FORCE ROW LEVEL SECURITY;
        CREATE POLICY concept_labels_tenant ON concept_labels FOR ALL
            USING (organization_id = app_current_org())
            WITH CHECK (organization_id = app_current_org());

        ALTER TABLE concept_aliases ENABLE ROW LEVEL SECURITY;
        ALTER TABLE concept_aliases FORCE ROW LEVEL SECURITY;
        CREATE POLICY concept_aliases_tenant ON concept_aliases FOR ALL
            USING (organization_id = app_current_org())
            WITH CHECK (organization_id = app_current_org());
    """)
    op.execute(f"""
        GRANT SELECT, INSERT, UPDATE ON concepts TO {APP_ROLE};  -- retire, never delete
        GRANT SELECT, INSERT, UPDATE, DELETE ON concept_labels, concept_aliases TO {APP_ROLE};
    """)


def downgrade() -> None:
    op.execute("""
        DROP TABLE concept_aliases;
        DROP TABLE concept_labels;
        DROP TABLE concepts;
    """)
