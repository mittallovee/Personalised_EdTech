"""Members' sign-in emails for the member list (M2 PR 5a).

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-21

``account_emails`` is platform-wide and the runtime role cannot read it at all (migration 0005),
so one coaching can never look up another coaching's people. The member list still needs to show
each member's email. ``auth_member_emails(user_ids)`` returns the emails of only those users who
are members (any status) of the coaching in the tenant context (``app.org_id``); for anyone else,
or with no coaching in the context, it returns nothing. Who may call the endpoint that uses it
(Owner and admins) is decided in the API (core/permissions.py).
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "qbank_app"


def upgrade() -> None:
    op.execute("""
        CREATE FUNCTION auth_member_emails(p_user_ids uuid[])
        RETURNS TABLE (user_id uuid, email text)
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, public AS $$
            SELECT e.user_id, e.email FROM account_emails e
            WHERE e.user_id = ANY (p_user_ids)
              AND EXISTS (
                  SELECT 1 FROM memberships m
                  WHERE m.user_id = e.user_id AND m.organization_id = app_current_org()
              );
        $$;
        REVOKE EXECUTE ON FUNCTION auth_member_emails(uuid[]) FROM PUBLIC;
    """)
    op.execute(f"GRANT EXECUTE ON FUNCTION auth_member_emails(uuid[]) TO {APP_ROLE};")


def downgrade() -> None:
    op.execute("DROP FUNCTION auth_member_emails(uuid[]);")
