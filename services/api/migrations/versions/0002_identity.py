"""Identity: password logins, platform admins and sessions.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-18

Security model (ADR-0005, M1 design note §5):
- ``password_credentials``: the runtime role has NO privileges on it. Login goes through the narrow
  ``auth_*`` functions below (SECURITY DEFINER, owned by the migration role), so a bug in the app
  cannot list accounts or dump password hashes.
- ``sessions``: the runtime role sees and changes only the signed-in user's sessions (policy on
  ``app.user_id``). Looking a session up by its cookie, before anyone is signed in, also goes
  through an ``auth_*`` function. Only hashes of session/CSRF tokens are stored.
- ``platform_roles``: read-only for the runtime role, and only the user's own row. Platform admins
  are created by the ``qbank create-platform-admin`` command, which runs as the table owner.
- These tables are not coaching-owned, so they use RLS without FORCE: the owner (migrations, the
  ``auth_*`` functions, the admin CLI) is exempt; the runtime role never is.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "qbank_app"


def upgrade() -> None:
    op.execute("""
        CREATE TABLE password_credentials (
            user_id         uuid PRIMARY KEY REFERENCES users (id),
            email           text NOT NULL CHECK (email = lower(email) AND length(email) <= 320),
            password_hash   text NOT NULL,
            failed_attempts integer NOT NULL DEFAULT 0,
            locked_until    timestamptz,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now()
        );
        CREATE UNIQUE INDEX password_credentials_email ON password_credentials (email);

        CREATE TABLE platform_roles (
            user_id    uuid NOT NULL REFERENCES users (id),
            role       text NOT NULL CHECK (role IN ('PLATFORM_ADMIN')),
            granted_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (user_id, role)
        );

        CREATE TABLE sessions (
            id                     uuid PRIMARY KEY,
            user_id                uuid NOT NULL REFERENCES users (id),
            token_hash             text NOT NULL UNIQUE,
            csrf_token_hash        text NOT NULL,
            acting_organization_id uuid REFERENCES organizations (id),
            created_at             timestamptz NOT NULL DEFAULT now(),
            last_seen_at           timestamptz NOT NULL DEFAULT now(),
            idle_expires_at        timestamptz NOT NULL,
            absolute_expires_at    timestamptz NOT NULL,
            revoked_at             timestamptz
        );
        CREATE INDEX sessions_user ON sessions (user_id);
    """)

    op.execute("""
        ALTER TABLE password_credentials ENABLE ROW LEVEL SECURITY;  -- no policies: deny all

        ALTER TABLE platform_roles ENABLE ROW LEVEL SECURITY;
        CREATE POLICY platform_roles_self_read ON platform_roles FOR SELECT
            USING (user_id = app_current_user());

        ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
        CREATE POLICY sessions_self ON sessions FOR ALL
            USING (user_id = app_current_user())
            WITH CHECK (user_id = app_current_user());

        -- A signed-in user may read their own membership(s); needed to find their coaching.
        CREATE POLICY memberships_self_read ON memberships FOR SELECT
            USING (user_id = app_current_user());
    """)

    # --- Narrow login functions (run as the owner; callable by the runtime role only) ------------
    op.execute("""
        CREATE FUNCTION auth_find_login(p_email text)
        RETURNS TABLE (user_id uuid, password_hash text, failed_attempts integer,
                       locked_until timestamptz)
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, public AS $$
            SELECT c.user_id, c.password_hash, c.failed_attempts, c.locked_until
            FROM password_credentials c
            WHERE c.email = lower(p_email)
        $$;

        CREATE FUNCTION auth_register_login_failure(
            p_user_id uuid, p_max_failures integer, p_lock_for interval)
        RETURNS void
        LANGUAGE sql VOLATILE SECURITY DEFINER SET search_path = pg_catalog, public AS $$
            UPDATE password_credentials
            SET failed_attempts = failed_attempts + 1,
                locked_until = CASE WHEN failed_attempts + 1 >= p_max_failures
                                    THEN now() + p_lock_for ELSE locked_until END,
                updated_at = now()
            WHERE user_id = p_user_id
        $$;

        CREATE FUNCTION auth_register_login_success(p_user_id uuid)
        RETURNS void
        LANGUAGE sql VOLATILE SECURITY DEFINER SET search_path = pg_catalog, public AS $$
            UPDATE password_credentials
            SET failed_attempts = 0, locked_until = NULL, updated_at = now()
            WHERE user_id = p_user_id
        $$;

        CREATE FUNCTION auth_find_session(p_token_hash text)
        RETURNS TABLE (id uuid, user_id uuid, csrf_token_hash text,
                       acting_organization_id uuid, last_seen_at timestamptz,
                       idle_expires_at timestamptz, absolute_expires_at timestamptz,
                       revoked_at timestamptz)
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, public AS $$
            SELECT s.id, s.user_id, s.csrf_token_hash, s.acting_organization_id, s.last_seen_at,
                   s.idle_expires_at, s.absolute_expires_at, s.revoked_at
            FROM sessions s
            WHERE s.token_hash = p_token_hash
        $$;
    """)

    op.execute(f"""
        -- Functions are executable by everyone by default; restrict these to the runtime role.
        REVOKE EXECUTE ON FUNCTION
            auth_find_login(text),
            auth_register_login_failure(uuid, integer, interval),
            auth_register_login_success(uuid),
            auth_find_session(text)
        FROM PUBLIC;
        GRANT EXECUTE ON FUNCTION
            auth_find_login(text),
            auth_register_login_failure(uuid, integer, interval),
            auth_register_login_success(uuid),
            auth_find_session(text)
        TO {APP_ROLE};

        GRANT SELECT ON platform_roles TO {APP_ROLE};
        GRANT SELECT, INSERT, UPDATE ON sessions TO {APP_ROLE};
        -- No grant at all on password_credentials.
    """)


def downgrade() -> None:
    op.execute("""
        DROP FUNCTION auth_find_session(text);
        DROP FUNCTION auth_register_login_success(uuid);
        DROP FUNCTION auth_register_login_failure(uuid, integer, interval);
        DROP FUNCTION auth_find_login(text);
        DROP POLICY memberships_self_read ON memberships;
        DROP TABLE sessions;
        DROP TABLE platform_roles;
        DROP TABLE password_credentials;
    """)
