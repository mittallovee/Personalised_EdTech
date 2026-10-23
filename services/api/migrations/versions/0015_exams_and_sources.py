"""Exams and sources: the lists a past-year or sourced question points at (M3 PR 2b).

Revision ID: 0015
Revises: 0014
Create Date: 2026-10-23

M3 design note §4.3 (C-11, C-13):
- ``exams``: JEE Main, NEET, CBSE... managed by the coaching's admins. A name is unique within a
  coaching, compared without regard to case or spacing (``name_key``).
- ``sources``: a book, a module, a test series, a past-year paper... of a kind, with a name that is
  unique within the coaching and kind.
- Both are retired, never deleted, so a question that refers to one still resolves (C-04): the
  runtime role has no DELETE right.
- Coaching-owned, so FORCE row-level security with the tenant policy (ADR-0005).
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "qbank_app"


def upgrade() -> None:
    op.execute("""
        CREATE TABLE exams (
            id              uuid PRIMARY KEY,
            organization_id uuid NOT NULL REFERENCES organizations (id),
            name            text NOT NULL CHECK (length(name) BETWEEN 1 AND 200),
            name_key        text NOT NULL CHECK (length(name_key) BETWEEN 1 AND 400),
            short_code      text CHECK (length(short_code) BETWEEN 1 AND 20),
            state           text NOT NULL DEFAULT 'ACTIVE'
                                CHECK (state IN ('ACTIVE', 'DEPRECATED')),
            revision        integer NOT NULL DEFAULT 1,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            UNIQUE (organization_id, id)
        );
        CREATE UNIQUE INDEX exams_name ON exams (organization_id, name_key);

        CREATE TABLE sources (
            id              uuid PRIMARY KEY,
            organization_id uuid NOT NULL REFERENCES organizations (id),
            kind            text NOT NULL CHECK (kind IN
                                ('BOOK', 'MODULE', 'TEST_SERIES', 'PYQ_PAPER', 'OTHER')),
            name            text NOT NULL CHECK (length(name) BETWEEN 1 AND 200),
            name_key        text NOT NULL CHECK (length(name_key) BETWEEN 1 AND 400),
            state           text NOT NULL DEFAULT 'ACTIVE'
                                CHECK (state IN ('ACTIVE', 'DEPRECATED')),
            revision        integer NOT NULL DEFAULT 1,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            UNIQUE (organization_id, id)
        );
        CREATE UNIQUE INDEX sources_name ON sources (organization_id, kind, name_key);

        ALTER TABLE exams ENABLE ROW LEVEL SECURITY;
        ALTER TABLE exams FORCE ROW LEVEL SECURITY;
        CREATE POLICY exams_tenant ON exams FOR ALL
            USING (organization_id = app_current_org())
            WITH CHECK (organization_id = app_current_org());

        ALTER TABLE sources ENABLE ROW LEVEL SECURITY;
        ALTER TABLE sources FORCE ROW LEVEL SECURITY;
        CREATE POLICY sources_tenant ON sources FOR ALL
            USING (organization_id = app_current_org())
            WITH CHECK (organization_id = app_current_org());
    """)
    op.execute(f"""
        GRANT SELECT, INSERT, UPDATE ON exams, sources TO {APP_ROLE};  -- retire, never delete
    """)


def downgrade() -> None:
    op.execute("""
        DROP TABLE sources;
        DROP TABLE exams;
    """)
