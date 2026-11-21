"""The translation glossary: terms a coaching wants translated one way (M5 5d-2, H-14).

Revision ID: 0039
Revises: 0038
Create Date: 2026-11-21

M5 design note §4, §10, prompt spec PL-13. One row per coaching, target language and source term:
what that term must become when a question is translated into that language ("work done" becomes
the coaching's chosen Hindi term). The translation prompt receives the matching entries as data.
Terms are unique per coaching and language ignoring case, so one term cannot have two answers.

Coaching-owned: FORCE row-level security with the tenant policy. The runtime role can read, add,
change and delete entries (the audit log keeps who did what).
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0039"
down_revision: str | None = "0038"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "qbank_app"


def upgrade() -> None:
    op.execute("""
        CREATE TABLE translation_glossary (
            id              uuid PRIMARY KEY,
            organization_id uuid NOT NULL REFERENCES organizations (id),
            language        text NOT NULL CHECK (language ~ '^[a-z]{2,3}$'),
            source_term     text NOT NULL CHECK (length(source_term) BETWEEN 1 AND 200),
            target_term     text NOT NULL CHECK (length(target_term) BETWEEN 1 AND 200),
            note            text CHECK (length(note) <= 300),
            revision        integer NOT NULL DEFAULT 1,
            created_by      uuid NOT NULL REFERENCES users (id),
            updated_by      uuid NOT NULL REFERENCES users (id),
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now()
        );
        CREATE UNIQUE INDEX translation_glossary_one_term
            ON translation_glossary (organization_id, language, lower(source_term));

        ALTER TABLE translation_glossary ENABLE ROW LEVEL SECURITY;
        ALTER TABLE translation_glossary FORCE ROW LEVEL SECURITY;
        CREATE POLICY translation_glossary_tenant ON translation_glossary FOR ALL
            USING (organization_id = app_current_org())
            WITH CHECK (organization_id = app_current_org());
    """)
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON translation_glossary TO {APP_ROLE};")


def downgrade() -> None:
    op.execute("DROP TABLE translation_glossary;")
