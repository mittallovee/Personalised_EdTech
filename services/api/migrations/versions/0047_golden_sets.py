"""Golden sets: reviewed questions frozen as the answer key for measuring extraction (M6 6j, G-11).

Revision ID: 0047
Revises: 0046
Create Date: 2026-11-28

M6 design note §5. A golden set is a named list of cases. A case freezes what a person finished
and accepted from a page: the content they ended with, plus which page it came from. Measuring
reads those pages again with a model and scores the result against the frozen content (K-14).

Both tables are append-only for the application: nothing a case says is ever changed, so a score
can always be traced to the key it was measured against.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0047"
down_revision: str | None = "0046"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "qbank_app"
TABLES = ("golden_sets", "golden_cases")


def upgrade() -> None:
    op.execute("""
        CREATE TABLE golden_sets (
            id              uuid PRIMARY KEY,
            organization_id uuid NOT NULL REFERENCES organizations (id),
            name            text NOT NULL CHECK (char_length(name) BETWEEN 1 AND 120),
            created_by      uuid NOT NULL REFERENCES users (id),
            created_at      timestamptz NOT NULL DEFAULT now(),
            UNIQUE (organization_id, id),
            UNIQUE (organization_id, name)
        );

        CREATE TABLE golden_cases (
            id              uuid PRIMARY KEY,
            organization_id uuid NOT NULL,
            set_id          uuid NOT NULL,
            file_id         uuid NOT NULL,
            page_no         integer NOT NULL CHECK (page_no >= 1),
            candidate_id    uuid NOT NULL,
            expected        jsonb NOT NULL,
            created_by      uuid NOT NULL REFERENCES users (id),
            created_at      timestamptz NOT NULL DEFAULT now(),
            UNIQUE (set_id, candidate_id),
            FOREIGN KEY (organization_id, set_id) REFERENCES golden_sets (organization_id, id),
            FOREIGN KEY (organization_id, candidate_id)
                REFERENCES ingest_candidates (organization_id, id),
            FOREIGN KEY (organization_id, file_id) REFERENCES ingest_files (organization_id, id)
        );
        CREATE INDEX golden_cases_by_set
            ON golden_cases (organization_id, set_id, file_id, page_no);
    """)
    for table in TABLES:
        op.execute(f"""
            ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
            ALTER TABLE {table} FORCE ROW LEVEL SECURITY;
            CREATE POLICY {table}_tenant ON {table} FOR ALL
                USING (organization_id = app_current_org())
                WITH CHECK (organization_id = app_current_org());
        """)
    op.execute(f"GRANT SELECT, INSERT ON golden_sets, golden_cases TO {APP_ROLE};")


def downgrade() -> None:
    op.execute("DROP TABLE golden_cases; DROP TABLE golden_sets;")
