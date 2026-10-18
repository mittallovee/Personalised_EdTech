"""Foundation: coachings, users, memberships, audit log, with row-level security.

Revision ID: 0001
Revises:
Create Date: 2026-10-18

Security model (ADR-0005):
- Tables are owned by the migration role. The runtime role ``qbank_app`` (created outside
  migrations, see infra/db/init) gets only the privileges listed below and cannot bypass
  row-level security.
- Policies read transaction-local settings set by ``qbank.core.tenancy``. When no coaching is set,
  tenant tables return no rows (fail closed).
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "qbank_app"


def upgrade() -> None:
    # --- Context helper functions used by every policy -------------------------------------------
    op.execute("""
        CREATE FUNCTION app_current_org() RETURNS uuid LANGUAGE sql STABLE AS
        $$ SELECT NULLIF(current_setting('app.org_id', true), '')::uuid $$;

        CREATE FUNCTION app_current_user() RETURNS uuid LANGUAGE sql STABLE AS
        $$ SELECT NULLIF(current_setting('app.user_id', true), '')::uuid $$;

        CREATE FUNCTION app_is_platform() RETURNS boolean LANGUAGE sql STABLE AS
        $$ SELECT coalesce(current_setting('app.is_platform', true), '') = 'true' $$;
    """)

    # --- Tables ----------------------------------------------------------------------------------
    op.execute("""
        CREATE TABLE organizations (
            id           uuid PRIMARY KEY,
            display_name text NOT NULL CHECK (length(display_name) BETWEEN 1 AND 200),
            status       text NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'SUSPENDED')),
            timezone     text NOT NULL DEFAULT 'Asia/Kolkata',
            created_at   timestamptz NOT NULL DEFAULT now(),
            updated_at   timestamptz NOT NULL DEFAULT now()
        );

        CREATE TABLE users (
            id           uuid PRIMARY KEY,
            display_name text NOT NULL CHECK (length(display_name) BETWEEN 1 AND 200),
            status       text NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'DISABLED')),
            created_at   timestamptz NOT NULL DEFAULT now(),
            updated_at   timestamptz NOT NULL DEFAULT now()
        );

        CREATE TABLE memberships (
            id              uuid PRIMARY KEY,
            organization_id uuid NOT NULL REFERENCES organizations (id),
            user_id         uuid NOT NULL REFERENCES users (id),
            role            text NOT NULL CHECK (role IN ('OWNER', 'ADMIN', 'FACULTY')),
            status          text NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'REMOVED')),
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            -- Lets later tenant-owned tables reference (organization_id, id) so a row can never
            -- point at a membership of another coaching.
            UNIQUE (organization_id, id)
        );
        -- B-07: a user has at most one active coaching membership.
        CREATE UNIQUE INDEX memberships_one_active_per_user
            ON memberships (user_id) WHERE status = 'ACTIVE';
        CREATE INDEX memberships_org_status ON memberships (organization_id, status);

        CREATE TABLE audit_events (
            id                uuid PRIMARY KEY,
            organization_id   uuid REFERENCES organizations (id),
            actor_user_id     uuid REFERENCES users (id),
            actor_is_platform boolean NOT NULL DEFAULT false,
            action            text NOT NULL,
            entity_type       text NOT NULL,
            entity_id         uuid,
            before            jsonb,
            after             jsonb,
            request_id        text,
            created_at        timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX audit_events_org_time ON audit_events (organization_id, created_at);
        CREATE INDEX audit_events_entity ON audit_events (entity_type, entity_id);
    """)

    # --- Row-level security ----------------------------------------------------------------------
    op.execute("""
        ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
        ALTER TABLE organizations FORCE ROW LEVEL SECURITY;
        -- Members see their own coaching; the platform admin sees all.
        -- Only the platform creates or changes coachings.
        CREATE POLICY organizations_read ON organizations FOR SELECT
            USING (id = app_current_org() OR app_is_platform());
        CREATE POLICY organizations_platform_insert ON organizations FOR INSERT
            WITH CHECK (app_is_platform());
        CREATE POLICY organizations_platform_update ON organizations FOR UPDATE
            USING (app_is_platform()) WITH CHECK (app_is_platform());

        ALTER TABLE memberships ENABLE ROW LEVEL SECURITY;
        ALTER TABLE memberships FORCE ROW LEVEL SECURITY;
        CREATE POLICY memberships_tenant ON memberships FOR ALL
            USING (organization_id = app_current_org())
            WITH CHECK (organization_id = app_current_org());

        ALTER TABLE users ENABLE ROW LEVEL SECURITY;
        ALTER TABLE users FORCE ROW LEVEL SECURITY;
        -- A user record is visible to the user, to the platform, and inside their own coaching.
        CREATE POLICY users_read ON users FOR SELECT
            USING (
                id = app_current_user()
                OR app_is_platform()
                OR EXISTS (
                    SELECT 1 FROM memberships m
                    WHERE m.user_id = users.id AND m.organization_id = app_current_org()
                )
            );
        -- Users are created by the platform or by a coaching admin (invitation, M2).
        CREATE POLICY users_insert ON users FOR INSERT
            WITH CHECK (app_is_platform() OR app_current_org() IS NOT NULL);
        CREATE POLICY users_update ON users FOR UPDATE
            USING (
                id = app_current_user()
                OR app_is_platform()
                OR EXISTS (
                    SELECT 1 FROM memberships m
                    WHERE m.user_id = users.id AND m.organization_id = app_current_org()
                )
            );

        ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY;
        ALTER TABLE audit_events FORCE ROW LEVEL SECURITY;
        CREATE POLICY audit_events_tenant ON audit_events FOR ALL
            USING (
                organization_id = app_current_org()
                OR (organization_id IS NULL AND app_is_platform())
            )
            WITH CHECK (
                organization_id = app_current_org()
                OR (organization_id IS NULL AND app_is_platform())
            );
    """)

    # --- Privileges for the runtime role (least privilege; no DELETE anywhere yet) ---------------
    op.execute(f"""
        GRANT USAGE ON SCHEMA public TO {APP_ROLE};
        GRANT SELECT, INSERT, UPDATE ON organizations, users, memberships TO {APP_ROLE};
        GRANT SELECT, INSERT ON audit_events TO {APP_ROLE};  -- append-only
        GRANT SELECT ON alembic_version TO {APP_ROLE};       -- readiness check
        GRANT EXECUTE ON FUNCTION app_current_org(), app_current_user(), app_is_platform()
            TO {APP_ROLE};
    """)


def downgrade() -> None:
    op.execute(f"""
        REVOKE ALL ON alembic_version FROM {APP_ROLE};
        -- These policies on users query memberships, so they must go before that table.
        DROP POLICY users_read ON users;
        DROP POLICY users_update ON users;
        DROP TABLE audit_events;
        DROP TABLE memberships;
        DROP TABLE users;
        DROP TABLE organizations;
        DROP FUNCTION app_is_platform();
        DROP FUNCTION app_current_user();
        DROP FUNCTION app_current_org();
        REVOKE USAGE ON SCHEMA public FROM {APP_ROLE};
    """)
