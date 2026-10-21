"""Redeeming activation and reset links (ADR-0015, M2 PR 4).

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-21

``auth_redeem_link(token_hash, password_hash)`` does the whole redemption in one step:
check the link (unused, unrevoked, unexpired), its membership and coaching (active) and the
account (an invited one for activation, an active one for a reset); set the password; activate
the account; mark the link used; and for a reset end every session of that person. It returns
the account, or no row when anything is wrong, so every failure looks the same to the caller.

The person redeeming is not signed in, so there is no coaching in the tenant context yet, and
``account_links`` has FORCE row-level security (its owner is subject to the policies too, unless
it is a superuser, which a managed cloud database usually does not give us). Therefore:
- a new policy lets a row be read when ``app.redeem_token_hash`` equals its token hash, i.e. by
  whoever holds the token (the runtime role cannot read ``token_hash`` itself);
- the function sets that setting to find the link, then works inside the link's coaching
  (``app.org_id``), and finally puts both settings back as they were.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "qbank_app"


def upgrade() -> None:
    op.execute("""
        CREATE POLICY account_links_by_token ON account_links FOR SELECT
            USING (token_hash = current_setting('app.redeem_token_hash', true));

        CREATE FUNCTION auth_redeem_link(p_token_hash text, p_password_hash text)
        RETURNS TABLE (user_id uuid, organization_id uuid, purpose text)
        LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = pg_catalog, public AS $$
        #variable_conflict use_column
        DECLARE
            link account_links%ROWTYPE;
            link_email text;
            previous_org text := current_setting('app.org_id', true);
        BEGIN
            PERFORM set_config('app.redeem_token_hash', p_token_hash, true);
            SELECT * INTO link FROM account_links l WHERE l.token_hash = p_token_hash FOR UPDATE;
            PERFORM set_config('app.redeem_token_hash', '', true);
            IF NOT FOUND OR link.used_at IS NOT NULL OR link.revoked_at IS NOT NULL
               OR link.expires_at <= now() THEN
                RETURN;
            END IF;

            PERFORM set_config('app.org_id', link.organization_id::text, true);
            IF NOT EXISTS (
                SELECT 1 FROM memberships m JOIN organizations o ON o.id = m.organization_id
                WHERE m.id = link.membership_id AND m.status = 'ACTIVE' AND o.status = 'ACTIVE'
            ) OR NOT EXISTS (
                SELECT 1 FROM users u WHERE u.id = link.user_id AND u.status =
                    CASE link.purpose WHEN 'ACTIVATION' THEN 'INVITED' ELSE 'ACTIVE' END
            ) THEN
                PERFORM set_config('app.org_id', coalesce(previous_org, ''), true);
                RETURN;
            END IF;
            SELECT e.email INTO link_email FROM account_emails e WHERE e.user_id = link.user_id;
            IF link_email IS NULL THEN
                PERFORM set_config('app.org_id', coalesce(previous_org, ''), true);
                RETURN;
            END IF;

            INSERT INTO password_credentials (user_id, email, password_hash)
                VALUES (link.user_id, link_email, p_password_hash)
                ON CONFLICT ON CONSTRAINT password_credentials_pkey DO UPDATE
                SET password_hash = EXCLUDED.password_hash, failed_attempts = 0,
                    locked_until = NULL, updated_at = now();
            UPDATE users SET status = 'ACTIVE', updated_at = now()
                WHERE id = link.user_id AND status = 'INVITED';
            UPDATE account_links SET used_at = now() WHERE id = link.id;
            IF link.purpose = 'RESET' THEN
                UPDATE sessions SET revoked_at = now()
                    WHERE sessions.user_id = link.user_id AND revoked_at IS NULL;
            END IF;

            PERFORM set_config('app.org_id', coalesce(previous_org, ''), true);
            RETURN QUERY SELECT link.user_id, link.organization_id, link.purpose;
        END
        $$;
        REVOKE EXECUTE ON FUNCTION auth_redeem_link(text, text) FROM PUBLIC;
    """)
    op.execute(f"GRANT EXECUTE ON FUNCTION auth_redeem_link(text, text) TO {APP_ROLE};")


def downgrade() -> None:
    op.execute("""
        DROP FUNCTION auth_redeem_link(text, text);
        DROP POLICY account_links_by_token ON account_links;
    """)
