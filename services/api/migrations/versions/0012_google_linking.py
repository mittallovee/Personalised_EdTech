"""Google sign-in, part 3: linking and unlinking a Google account while signed in (M2 PR 8c).

Revision ID: 0012
Revises: 0011
Create Date: 2026-10-22

M2 design note §5. Narrow ``SECURITY DEFINER`` functions, because the runtime role can read neither
``password_credentials`` nor ``external_identities``. Those that act "for me" use the caller's own
``app_current_user()``, never an id the caller passes in:
- ``auth_my_credential``: the caller's password hash and lockout state, so the API can check the
  password that must come with a request to link Google (a session alone is never proof);
- ``auth_my_login_methods``: whether the caller has a password and a linked Google account;
- ``auth_oauth_begin_link``: store a pending LINK flow for the caller's own, still valid session;
  refuses (without storing anything) if a Google account is already linked;
- ``auth_google_link``: runs when Google calls back for a taken LINK flow. It locks and re-checks
  the session that started the flow (still the same person's, not revoked, not expired), then links
  the Google account. It links nothing if that Google account belongs to anyone;
- ``auth_google_unlink``: removes the caller's Google account, but only if a password remains, so
  nobody locks themselves out.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "qbank_app"


def upgrade() -> None:
    op.execute("""
        CREATE FUNCTION auth_my_credential()
        RETURNS TABLE (password_hash text, failed_attempts integer, locked_until timestamptz)
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, public AS $$
            SELECT c.password_hash, c.failed_attempts, c.locked_until
            FROM password_credentials c WHERE c.user_id = app_current_user()
        $$;

        CREATE FUNCTION auth_my_login_methods()
        RETURNS TABLE (has_password boolean, google_linked boolean, google_email text)
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, public AS $$
            SELECT EXISTS (SELECT 1 FROM password_credentials c
                           WHERE c.user_id = app_current_user()),
                   EXISTS (SELECT 1 FROM external_identities e
                           WHERE e.user_id = app_current_user() AND e.provider = 'google'),
                   (SELECT e.email_at_link FROM external_identities e
                    WHERE e.user_id = app_current_user() AND e.provider = 'google')
        $$;

        CREATE FUNCTION auth_oauth_begin_link(
            p_id uuid, p_cookie_hash text, p_state_hash text, p_code_verifier text, p_nonce text,
            p_return_origin text, p_session_id uuid
        ) RETURNS text
        LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = pg_catalog, public AS $$
        BEGIN
            IF app_current_user() IS NULL OR NOT EXISTS (
                SELECT 1 FROM sessions s
                WHERE s.id = p_session_id AND s.user_id = app_current_user()
                  AND s.revoked_at IS NULL AND s.idle_expires_at > now()
                  AND s.absolute_expires_at > now()
            ) THEN
                RETURN 'NO_SESSION';
            END IF;
            IF EXISTS (SELECT 1 FROM external_identities e
                       WHERE e.user_id = app_current_user() AND e.provider = 'google') THEN
                RETURN 'ALREADY_LINKED';
            END IF;
            DELETE FROM oauth_flows WHERE expires_at < now() - interval '1 day';
            INSERT INTO oauth_flows (id, cookie_hash, state_hash, code_verifier, nonce, purpose,
                                     user_id, session_id, return_origin, expires_at)
                VALUES (p_id, p_cookie_hash, p_state_hash, p_code_verifier, p_nonce, 'LINK',
                        app_current_user(), p_session_id, p_return_origin,
                        now() + interval '10 minutes');
            RETURN 'STARTED';
        END
        $$;

        CREATE FUNCTION auth_google_link(p_flow_id uuid, p_subject text, p_email text)
        RETURNS uuid
        LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = pg_catalog, public AS $$
        #variable_conflict use_column
        DECLARE
            flow oauth_flows%ROWTYPE;
            linked integer;
        BEGIN
            SELECT * INTO flow FROM oauth_flows f
                WHERE f.id = p_flow_id AND f.purpose = 'LINK' AND f.used_at IS NOT NULL;
            IF NOT FOUND THEN
                RETURN NULL;
            END IF;
            -- The session that started the flow must still be this person's and still valid.
            -- It is locked, so a sign-out or a removal that revokes it either finishes first (and
            -- is seen here) or waits until this transaction ends.
            PERFORM 1 FROM sessions s
                WHERE s.id = flow.session_id AND s.user_id = flow.user_id
                  AND s.revoked_at IS NULL AND s.idle_expires_at > now()
                  AND s.absolute_expires_at > now()
                FOR SHARE;
            IF NOT FOUND THEN
                RETURN NULL;
            END IF;
            -- One Google account per person, and each Google account belongs to one person.
            INSERT INTO external_identities (user_id, provider, subject, email_at_link)
                VALUES (flow.user_id, 'google', p_subject, left(p_email, 320))
                ON CONFLICT DO NOTHING;
            GET DIAGNOSTICS linked = ROW_COUNT;
            IF linked = 0 THEN
                RETURN NULL;
            END IF;
            RETURN flow.user_id;
        END
        $$;

        CREATE FUNCTION auth_google_unlink()
        RETURNS text
        LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = pg_catalog, public AS $$
        BEGIN
            IF app_current_user() IS NULL THEN
                RETURN 'NOT_LINKED';
            END IF;
            -- Lock the password row: nothing may take the password away while we decide.
            PERFORM 1 FROM password_credentials c WHERE c.user_id = app_current_user() FOR SHARE;
            IF NOT FOUND THEN
                RETURN CASE WHEN EXISTS (
                    SELECT 1 FROM external_identities e
                    WHERE e.user_id = app_current_user() AND e.provider = 'google'
                ) THEN 'NO_PASSWORD' ELSE 'NOT_LINKED' END;
            END IF;
            DELETE FROM external_identities
                WHERE user_id = app_current_user() AND provider = 'google';
            RETURN CASE WHEN FOUND THEN 'UNLINKED' ELSE 'NOT_LINKED' END;
        END
        $$;

        REVOKE EXECUTE ON FUNCTION
            auth_my_credential(),
            auth_my_login_methods(),
            auth_oauth_begin_link(uuid, text, text, text, text, text, uuid),
            auth_google_link(uuid, text, text),
            auth_google_unlink()
        FROM PUBLIC;
    """)
    op.execute(f"""
        GRANT EXECUTE ON FUNCTION
            auth_my_credential(),
            auth_my_login_methods(),
            auth_oauth_begin_link(uuid, text, text, text, text, text, uuid),
            auth_google_link(uuid, text, text),
            auth_google_unlink()
        TO {APP_ROLE};
    """)


def downgrade() -> None:
    op.execute("""
        DROP FUNCTION auth_google_unlink();
        DROP FUNCTION auth_google_link(uuid, text, text);
        DROP FUNCTION auth_oauth_begin_link(uuid, text, text, text, text, text, uuid);
        DROP FUNCTION auth_my_login_methods();
        DROP FUNCTION auth_my_credential();
    """)
