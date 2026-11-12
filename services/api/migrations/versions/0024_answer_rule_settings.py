"""Answer limits a coaching can change (M3 PR 3i-1).

Revision ID: 0024
Revises: 0023
Create Date: 2026-11-12

M3 design note §5.4 (D-03): the numbers that say what an answer may be (items in a matching
question, the range of an integer, digit or numerical key) are settings, with built-in defaults, a
value per coaching and optional values per exam.

- ``answer_rule_settings``: one row per coaching holding only what it changed: ``defaults`` (setting
  name to value) and ``exams`` (exam id to the values for that exam). ``revision`` is the ETag, so a
  save from a stale screen is refused. A changed limit never rewrites a saved revision; findings are
  computed from the content and these settings on every read.
- Coaching-owned: FORCE row-level security with the tenant policy. The runtime role can read,
  add and change the row, never delete it.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0024"
down_revision: str | None = "0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "qbank_app"


def upgrade() -> None:
    op.execute("""
        CREATE TABLE answer_rule_settings (
            organization_id uuid PRIMARY KEY REFERENCES organizations (id),
            revision        integer NOT NULL DEFAULT 1,
            defaults        jsonb NOT NULL DEFAULT '{}'
                CHECK (jsonb_typeof(defaults) = 'object'),
            exams           jsonb NOT NULL DEFAULT '{}'
                CHECK (jsonb_typeof(exams) = 'object'),
            updated_by      uuid NOT NULL REFERENCES users (id),
            updated_at      timestamptz NOT NULL DEFAULT now()
        );
        ALTER TABLE answer_rule_settings ENABLE ROW LEVEL SECURITY;
        ALTER TABLE answer_rule_settings FORCE ROW LEVEL SECURITY;
        CREATE POLICY answer_rule_settings_tenant ON answer_rule_settings FOR ALL
            USING (organization_id = app_current_org())
            WITH CHECK (organization_id = app_current_org());
    """)
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON answer_rule_settings TO {APP_ROLE}")


def downgrade() -> None:
    op.execute("DROP TABLE answer_rule_settings;")
