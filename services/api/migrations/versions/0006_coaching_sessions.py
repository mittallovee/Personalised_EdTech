"""Suspending a coaching ends its members' sign-in sessions (A-07).

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-21

The runtime role sees only the signed-in user's own sessions (migration 0002), so ending other
people's sessions goes through this narrow SECURITY DEFINER function. It runs only with platform
authority inside the coaching being suspended, and never touches the caller's own sessions.
Without it, a session paused by suspension would quietly work again after reactivation.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "qbank_app"


def upgrade() -> None:
    op.execute("""
        CREATE FUNCTION auth_revoke_coaching_sessions(p_organization_id uuid)
        RETURNS integer
        LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = pg_catalog, public AS $$
        DECLARE
            revoked integer;
        BEGIN
            IF NOT app_is_platform() OR app_current_org() IS DISTINCT FROM p_organization_id THEN
                RAISE EXCEPTION 'auth_revoke_coaching_sessions needs platform authority %',
                    'inside that coaching';
            END IF;
            UPDATE sessions s SET revoked_at = now()
            WHERE s.revoked_at IS NULL
              AND s.user_id <> app_current_user()
              AND EXISTS (
                  SELECT 1 FROM memberships m
                  WHERE m.user_id = s.user_id AND m.organization_id = p_organization_id
                    AND m.status = 'ACTIVE'
              );
            GET DIAGNOSTICS revoked = ROW_COUNT;
            RETURN revoked;
        END
        $$;
        REVOKE EXECUTE ON FUNCTION auth_revoke_coaching_sessions(uuid) FROM PUBLIC;
    """)
    op.execute(f"GRANT EXECUTE ON FUNCTION auth_revoke_coaching_sessions(uuid) TO {APP_ROLE};")


def downgrade() -> None:
    op.execute("DROP FUNCTION auth_revoke_coaching_sessions(uuid);")
