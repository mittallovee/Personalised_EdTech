"""Google sign-in, part 2: activating an account with Google instead of a password (M2 PR 8b).

Revision ID: 0011
Revises: 0010
Create Date: 2026-10-22

M2 design note §5. A person with an activation link may choose "Continue with Google" instead of
setting a password. Two new ``SECURITY DEFINER`` functions, built like ``auth_redeem_link`` (0007):
- ``auth_oauth_begin_activation``: checks the link *before* the person leaves for Google (unused,
  unrevoked, unexpired, an activation link, member and coaching active, account still invited) and
  stores the flow with that link. It returns false, and stores nothing, if anything is wrong.
- ``auth_google_activate``: runs when Google calls back. It re-checks all of the above in the same
  transaction that changes anything, then links the Google account, activates the person and marks
  the link used. It returns no row, and changes nothing, if anything is wrong, including when that
  Google account is already linked to someone else.

The flow remembers the link's coaching (``organization_id``), because links can only be read inside
their coaching (row-level security). ``auth_oauth_take`` now also returns the flow's ``id`` and
``organization_id``; ``auth_google_activate`` takes the flow's id, never a link id from the caller,
and works only for a flow that has been taken (used) and is an ACTIVATE flow.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "qbank_app"

_TAKE_V10 = """
    CREATE FUNCTION auth_oauth_take(p_cookie_hash text, p_state_hash text)
    RETURNS TABLE (purpose text, code_verifier text, nonce text, return_origin text,
                   account_link_id uuid, user_id uuid, session_id uuid)
    LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = pg_catalog, public AS $$
    #variable_conflict use_column
    DECLARE
        flow oauth_flows%ROWTYPE;
    BEGIN
        SELECT * INTO flow FROM oauth_flows f WHERE f.cookie_hash = p_cookie_hash FOR UPDATE;
        IF NOT FOUND OR flow.used_at IS NOT NULL THEN
            RETURN;
        END IF;
        UPDATE oauth_flows SET used_at = now() WHERE id = flow.id;
        IF flow.expires_at <= now() OR flow.state_hash <> p_state_hash THEN
            RETURN;
        END IF;
        RETURN QUERY SELECT flow.purpose, flow.code_verifier, flow.nonce, flow.return_origin,
                            flow.account_link_id, flow.user_id, flow.session_id;
    END
    $$;
"""

_TAKE_V11 = """
    CREATE FUNCTION auth_oauth_take(p_cookie_hash text, p_state_hash text)
    RETURNS TABLE (id uuid, purpose text, code_verifier text, nonce text, return_origin text,
                   account_link_id uuid, organization_id uuid, user_id uuid, session_id uuid)
    LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = pg_catalog, public AS $$
    #variable_conflict use_column
    DECLARE
        flow oauth_flows%ROWTYPE;
    BEGIN
        SELECT * INTO flow FROM oauth_flows f WHERE f.cookie_hash = p_cookie_hash FOR UPDATE;
        IF NOT FOUND OR flow.used_at IS NOT NULL THEN
            RETURN;
        END IF;
        UPDATE oauth_flows SET used_at = now() WHERE oauth_flows.id = flow.id;
        IF flow.expires_at <= now() OR flow.state_hash <> p_state_hash THEN
            RETURN;
        END IF;
        RETURN QUERY SELECT flow.id, flow.purpose, flow.code_verifier, flow.nonce,
                            flow.return_origin, flow.account_link_id, flow.organization_id,
                            flow.user_id, flow.session_id;
    END
    $$;
"""


def upgrade() -> None:
    op.execute("""
        ALTER TABLE oauth_flows ADD COLUMN organization_id uuid REFERENCES organizations (id);
        DROP FUNCTION auth_oauth_take(text, text);
    """)
    op.execute(_TAKE_V11)
    op.execute("""
        CREATE FUNCTION auth_oauth_begin_activation(
            p_id uuid, p_cookie_hash text, p_state_hash text, p_code_verifier text, p_nonce text,
            p_return_origin text, p_token_hash text
        ) RETURNS boolean
        LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = pg_catalog, public AS $$
        #variable_conflict use_column
        DECLARE
            link account_links%ROWTYPE;
            previous_org text := current_setting('app.org_id', true);
            usable boolean;
        BEGIN
            PERFORM set_config('app.redeem_token_hash', p_token_hash, true);
            SELECT * INTO link FROM account_links l WHERE l.token_hash = p_token_hash;
            PERFORM set_config('app.redeem_token_hash', '', true);
            IF NOT FOUND OR link.purpose <> 'ACTIVATION' OR link.used_at IS NOT NULL
               OR link.revoked_at IS NOT NULL OR link.expires_at <= now() THEN
                RETURN false;
            END IF;

            PERFORM set_config('app.org_id', link.organization_id::text, true);
            SELECT EXISTS (
                SELECT 1 FROM memberships m JOIN organizations o ON o.id = m.organization_id
                JOIN users u ON u.id = m.user_id
                WHERE m.id = link.membership_id AND m.status = 'ACTIVE' AND o.status = 'ACTIVE'
                  AND u.id = link.user_id AND u.status = 'INVITED'
            ) INTO usable;
            PERFORM set_config('app.org_id', coalesce(previous_org, ''), true);
            IF NOT usable THEN
                RETURN false;
            END IF;

            DELETE FROM oauth_flows WHERE expires_at < now() - interval '1 day';
            INSERT INTO oauth_flows (id, cookie_hash, state_hash, code_verifier, nonce, purpose,
                                     account_link_id, organization_id, return_origin, expires_at)
                VALUES (p_id, p_cookie_hash, p_state_hash, p_code_verifier, p_nonce, 'ACTIVATE',
                        link.id, link.organization_id, p_return_origin,
                        now() + interval '10 minutes');
            RETURN true;
        END
        $$;

        CREATE FUNCTION auth_google_activate(p_flow_id uuid, p_subject text, p_email text)
        RETURNS TABLE (user_id uuid, organization_id uuid)
        LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = pg_catalog, public AS $$
        #variable_conflict use_column
        DECLARE
            flow oauth_flows%ROWTYPE;
            link account_links%ROWTYPE;
            previous_org text := current_setting('app.org_id', true);
            linked integer;
        BEGIN
            SELECT * INTO flow FROM oauth_flows f
                WHERE f.id = p_flow_id AND f.purpose = 'ACTIVATE' AND f.used_at IS NOT NULL;
            IF NOT FOUND THEN
                RETURN;
            END IF;

            PERFORM set_config('app.org_id', flow.organization_id::text, true);
            -- Locks are taken in the order everything else takes them (the membership, then its
            -- link: removing a member locks the membership and then revokes their link), or two
            -- people working at once could wait for each other. So first read the link without a
            -- lock, only to learn which membership it belongs to.
            SELECT * INTO link FROM account_links l WHERE l.id = flow.account_link_id;
            IF NOT FOUND THEN
                PERFORM set_config('app.org_id', coalesce(previous_org, ''), true);
                RETURN;
            END IF;
            -- Lock the membership and the coaching while checking them (and until the caller's
            -- transaction ends, so until the new session exists). A suspension or removal that is
            -- half-done then makes this wait, and afterwards see its result: otherwise the session
            -- could appear just after the suspension had revoked every session (Codex, PR #25).
            PERFORM 1
                FROM memberships m
                JOIN organizations o ON o.id = m.organization_id
                JOIN users u ON u.id = m.user_id
                WHERE m.id = link.membership_id AND m.status = 'ACTIVE'
                  AND o.status = 'ACTIVE' AND u.id = link.user_id AND u.status = 'INVITED'
                FOR SHARE OF m, o;
            IF NOT FOUND THEN
                PERFORM set_config('app.org_id', coalesce(previous_org, ''), true);
                RETURN;
            END IF;
            -- Now the link itself, locked and checked again, as it may have changed meanwhile.
            SELECT * INTO link FROM account_links l WHERE l.id = flow.account_link_id FOR UPDATE;
            IF NOT FOUND OR link.purpose <> 'ACTIVATION' OR link.used_at IS NOT NULL
               OR link.revoked_at IS NOT NULL OR link.expires_at <= now() THEN
                PERFORM set_config('app.org_id', coalesce(previous_org, ''), true);
                RETURN;
            END IF;

            -- A Google account already linked to anyone (or a person who has one) is refused.
            INSERT INTO external_identities (user_id, provider, subject, email_at_link)
                VALUES (link.user_id, 'google', p_subject, left(p_email, 320))
                ON CONFLICT DO NOTHING;
            GET DIAGNOSTICS linked = ROW_COUNT;
            IF linked = 0 THEN
                PERFORM set_config('app.org_id', coalesce(previous_org, ''), true);
                RETURN;
            END IF;
            UPDATE users SET status = 'ACTIVE', updated_at = now() WHERE id = link.user_id;
            UPDATE account_links SET used_at = now() WHERE id = link.id;

            PERFORM set_config('app.org_id', coalesce(previous_org, ''), true);
            RETURN QUERY SELECT link.user_id, link.organization_id;
        END
        $$;

        REVOKE EXECUTE ON FUNCTION
            auth_oauth_begin_activation(uuid, text, text, text, text, text, text),
            auth_google_activate(uuid, text, text),
            auth_oauth_take(text, text)
        FROM PUBLIC;
    """)
    op.execute(f"""
        GRANT EXECUTE ON FUNCTION
            auth_oauth_begin_activation(uuid, text, text, text, text, text, text),
            auth_google_activate(uuid, text, text),
            auth_oauth_take(text, text)
        TO {APP_ROLE};
    """)


def downgrade() -> None:
    op.execute("""
        DROP FUNCTION auth_google_activate(uuid, text, text);
        DROP FUNCTION auth_oauth_begin_activation(uuid, text, text, text, text, text, text);
        DROP FUNCTION auth_oauth_take(text, text);
    """)
    op.execute(_TAKE_V10)
    op.execute("""
        REVOKE EXECUTE ON FUNCTION auth_oauth_take(text, text) FROM PUBLIC;
        DELETE FROM oauth_flows WHERE purpose <> 'SIGN_IN';
        ALTER TABLE oauth_flows DROP COLUMN organization_id;
    """)
    op.execute(f"GRANT EXECUTE ON FUNCTION auth_oauth_take(text, text) TO {APP_ROLE};")
