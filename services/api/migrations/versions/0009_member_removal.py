"""Ending a removed member's access (M2 PR 6a, B-10, T14).

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-21

The runtime role sees only its own user's sessions (migration 0002) and cannot touch the
platform-wide ``account_emails`` table (migration 0005), so two narrow SECURITY DEFINER functions
do the parts of removing a member that cross those walls. Both work only for someone who has a
membership in the coaching of the tenant context (``app.org_id``), and never for the caller.

- ``auth_revoke_member_sessions(user_id)``: ends the person's sign-in sessions, for a member
  whose membership in this coaching is REMOVED. Returns how many.
- ``auth_release_email(user_id)``: frees the sign-in email of a member who never activated, so a
  mistyped or abandoned invitation can be redone. Only for an INVITED account whose membership
  in this coaching is REMOVED. An activated account keeps its email: its history stays with the
  coaching. Returns whether an email was freed.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "qbank_app"


def upgrade() -> None:
    op.execute("""
        CREATE FUNCTION auth_revoke_member_sessions(p_user_id uuid)
        RETURNS integer
        LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = pg_catalog, public AS $$
        DECLARE
            revoked integer;
        BEGIN
            IF p_user_id IS NOT DISTINCT FROM app_current_user() OR NOT EXISTS (
                SELECT 1 FROM memberships m
                WHERE m.user_id = p_user_id AND m.organization_id = app_current_org()
                  AND m.status = 'REMOVED'
            ) THEN
                RAISE EXCEPTION 'auth_revoke_member_sessions is only for a removed member %',
                    'of this coaching, never for the caller';
            END IF;
            UPDATE sessions s SET revoked_at = now()
            WHERE s.user_id = p_user_id AND s.revoked_at IS NULL;
            GET DIAGNOSTICS revoked = ROW_COUNT;
            RETURN revoked;
        END
        $$;

        CREATE FUNCTION auth_release_email(p_user_id uuid)
        RETURNS boolean
        LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = pg_catalog, public AS $$
        DECLARE
            released integer;
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM users u JOIN memberships m ON m.user_id = u.id
                WHERE u.id = p_user_id AND u.status = 'INVITED'
                  AND m.organization_id = app_current_org() AND m.status = 'REMOVED'
            ) THEN
                RETURN false;
            END IF;
            DELETE FROM account_emails WHERE user_id = p_user_id;
            GET DIAGNOSTICS released = ROW_COUNT;
            RETURN released = 1;
        END
        $$;

        REVOKE EXECUTE ON FUNCTION auth_revoke_member_sessions(uuid) FROM PUBLIC;
        REVOKE EXECUTE ON FUNCTION auth_release_email(uuid) FROM PUBLIC;
    """)
    op.execute(f"""
        GRANT EXECUTE ON FUNCTION auth_revoke_member_sessions(uuid) TO {APP_ROLE};
        GRANT EXECUTE ON FUNCTION auth_release_email(uuid) TO {APP_ROLE};
    """)


def downgrade() -> None:
    op.execute("""
        DROP FUNCTION auth_release_email(uuid);
        DROP FUNCTION auth_revoke_member_sessions(uuid);
    """)
