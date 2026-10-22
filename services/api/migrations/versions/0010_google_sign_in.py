"""Google sign-in, part 1: linked Google accounts and pending flows (ADR-0015, M2 PR 8a).

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-22

M2 design note §5 and §6:
- ``external_identities``: which Google account (its permanent ``subject``, never its email) belongs
  to which person. One Google account belongs to one person, and a person has at most one.
- ``oauth_flows``: a sign-in that has left for Google and not come back yet. Only hashes of the
  browser cookie and of ``state`` are stored (a callback needs both), plus what the callback needs
  to finish: the PKCE verifier and the nonce. A flow lives 10 minutes and is used at most once.

Neither table is reachable by the runtime role: row-level security is on with no policy and no
privileges are granted, exactly like ``account_emails``. The app goes through three narrow
``SECURITY DEFINER`` functions:
- ``auth_oauth_begin_sign_in``: store a new sign-in flow (and tidy away old ones);
- ``auth_oauth_take``: use a flow once. The flow is marked used *before* anything is checked, so a
  wrong ``state`` or a replay can never be retried. It returns nothing unless the flow is unused,
  unexpired and its ``state`` matches;
- ``auth_google_user``: the person a Google subject is linked to.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "qbank_app"


def upgrade() -> None:
    op.execute("""
        CREATE TABLE external_identities (
            user_id       uuid NOT NULL REFERENCES users (id),
            provider      text NOT NULL CHECK (provider IN ('google')),
            subject       text NOT NULL CHECK (length(subject) BETWEEN 1 AND 255),
            email_at_link text CHECK (length(email_at_link) <= 320),
            linked_at     timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (provider, subject),
            UNIQUE (user_id, provider)
        );
        ALTER TABLE external_identities ENABLE ROW LEVEL SECURITY;  -- no policies: deny all

        CREATE TABLE oauth_flows (
            id              uuid PRIMARY KEY,
            cookie_hash     text NOT NULL UNIQUE,
            state_hash      text NOT NULL UNIQUE,
            code_verifier   text NOT NULL,
            nonce           text NOT NULL,
            purpose         text NOT NULL CHECK (purpose IN ('SIGN_IN', 'ACTIVATE', 'LINK')),
            account_link_id uuid REFERENCES account_links (id),
            user_id         uuid REFERENCES users (id),
            session_id      uuid REFERENCES sessions (id),
            return_origin   text NOT NULL,
            created_at      timestamptz NOT NULL DEFAULT now(),
            expires_at      timestamptz NOT NULL,
            used_at         timestamptz
        );
        ALTER TABLE oauth_flows ENABLE ROW LEVEL SECURITY;  -- no policies: deny all

        CREATE FUNCTION auth_oauth_begin_sign_in(
            p_id uuid, p_cookie_hash text, p_state_hash text, p_code_verifier text, p_nonce text,
            p_return_origin text
        ) RETURNS void
        LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = pg_catalog, public AS $$
        BEGIN
            DELETE FROM oauth_flows WHERE expires_at < now() - interval '1 day';
            INSERT INTO oauth_flows (id, cookie_hash, state_hash, code_verifier, nonce, purpose,
                                     return_origin, expires_at)
                VALUES (p_id, p_cookie_hash, p_state_hash, p_code_verifier, p_nonce, 'SIGN_IN',
                        p_return_origin, now() + interval '10 minutes');
        END
        $$;

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

        CREATE FUNCTION auth_google_user(p_subject text)
        RETURNS uuid
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, public AS $$
            SELECT user_id FROM external_identities
            WHERE provider = 'google' AND subject = p_subject
        $$;

        REVOKE EXECUTE ON FUNCTION
            auth_oauth_begin_sign_in(uuid, text, text, text, text, text),
            auth_oauth_take(text, text),
            auth_google_user(text)
        FROM PUBLIC;
    """)
    op.execute(f"""
        GRANT EXECUTE ON FUNCTION
            auth_oauth_begin_sign_in(uuid, text, text, text, text, text),
            auth_oauth_take(text, text),
            auth_google_user(text)
        TO {APP_ROLE};
    """)


def downgrade() -> None:
    op.execute("""
        DROP FUNCTION auth_google_user(text);
        DROP FUNCTION auth_oauth_take(text, text);
        DROP FUNCTION auth_oauth_begin_sign_in(uuid, text, text, text, text, text);
        DROP TABLE oauth_flows;
        DROP TABLE external_identities;
    """)
