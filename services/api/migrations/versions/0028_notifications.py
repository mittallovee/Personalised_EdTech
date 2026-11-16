"""In-app notifications (M4 PR 4b).

Revision ID: 0028
Revises: 0027
Create Date: 2026-11-16

M4 design note §6 (I-01): a small table the app reads on page load. A notification belongs to one
person in one coaching; the coaching's row-level security applies, and on top of it a person can
read and mark only their own. Anyone in the coaching may *create* one for a colleague (a reviewer
returns a question to its author), so the insert policy checks the coaching only.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0028"
down_revision: str | None = "0027"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "qbank_app"


def upgrade() -> None:
    op.execute("""
        CREATE TABLE notifications (
            id              uuid PRIMARY KEY,
            organization_id uuid NOT NULL REFERENCES organizations (id),
            user_id         uuid NOT NULL REFERENCES users (id),
            kind            text NOT NULL CHECK (kind ~ '^[A-Z][A-Z_]{0,59}$'),
            data            jsonb NOT NULL CHECK (jsonb_typeof(data) = 'object'),
            created_at      timestamptz NOT NULL DEFAULT now(),
            read_at         timestamptz
        );
        CREATE INDEX notifications_by_user
            ON notifications (user_id, created_at DESC, id DESC);
        CREATE INDEX notifications_unread
            ON notifications (user_id) WHERE read_at IS NULL;

        ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
        ALTER TABLE notifications FORCE ROW LEVEL SECURITY;
        CREATE POLICY notifications_own_read ON notifications FOR SELECT
            USING (organization_id = app_current_org() AND user_id = app_current_user());
        CREATE POLICY notifications_own_update ON notifications FOR UPDATE
            USING (organization_id = app_current_org() AND user_id = app_current_user())
            WITH CHECK (organization_id = app_current_org() AND user_id = app_current_user());
        CREATE POLICY notifications_insert ON notifications FOR INSERT
            WITH CHECK (organization_id = app_current_org());
    """)
    # Only the read time may change; the app never deletes one.
    op.execute(f"GRANT SELECT, INSERT, UPDATE (read_at) ON notifications TO {APP_ROLE};")


def downgrade() -> None:
    op.execute("DROP TABLE notifications;")
