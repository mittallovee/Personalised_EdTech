"""Links from a translated question to the question it was translated from (M5 5g, H-08, D-13).

Revision ID: 0041
Revises: 0040
Create Date: 2026-11-21

M5 design note §4, §9. A translation is an ordinary new question (its own code, its own workflow).
This row says which question it came from and **which version of that question was translated**.
Whether the source has moved on ("source updated", D-13) is worked out when a question is read, by
comparing ``source_version_number`` with the source's published version; it is never stored.

One row per translation (``target_master_id`` is unique), so a question has at most one source.
Coaching-owned: composite keys keep both questions in one coaching, and FORCE row-level security
with the tenant policy applies. The runtime role can read and add links, nothing else: a translation
stays linked to its source.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0041"
down_revision: str | None = "0040"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "qbank_app"


def upgrade() -> None:
    op.execute("""
        CREATE TABLE question_links (
            id                    uuid PRIMARY KEY,
            organization_id       uuid NOT NULL REFERENCES organizations (id),
            kind                  text NOT NULL CHECK (kind IN ('TRANSLATION')),
            source_master_id      uuid NOT NULL,
            source_version_number integer NOT NULL CHECK (source_version_number >= 1),
            target_master_id      uuid NOT NULL,
            language              text NOT NULL CHECK (language ~ '^[a-z]{2,3}$'),
            created_by            uuid NOT NULL REFERENCES users (id),
            created_at            timestamptz NOT NULL DEFAULT now(),
            UNIQUE (target_master_id),
            CHECK (source_master_id <> target_master_id),
            FOREIGN KEY (organization_id, source_master_id)
                REFERENCES question_masters (organization_id, id),
            FOREIGN KEY (organization_id, target_master_id)
                REFERENCES question_masters (organization_id, id)
        );
        CREATE INDEX question_links_by_source ON question_links (organization_id, source_master_id);

        ALTER TABLE question_links ENABLE ROW LEVEL SECURITY;
        ALTER TABLE question_links FORCE ROW LEVEL SECURITY;
        CREATE POLICY question_links_tenant ON question_links FOR ALL
            USING (organization_id = app_current_org())
            WITH CHECK (organization_id = app_current_org());
    """)
    op.execute(f"GRANT SELECT, INSERT ON question_links TO {APP_ROLE};")


def downgrade() -> None:
    op.execute("DROP TABLE question_links;")
