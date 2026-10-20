"""Invitations: one email per person, one-time account links, safe retries (ADR-0015).

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-21

M2 design note §4 and §6:
- ``account_emails``: each normalised email belongs to at most one person, platform-wide (B-07).
  The runtime role has no privileges on it; it can only reserve an email for an account it is
  inviting, through ``auth_reserve_email``. Filled here from existing password logins.
- ``account_links``: activation and reset links. Only the SHA-256 hash of a link's token is
  stored, and the runtime role cannot even read that column. Coaching-owned: FORCE row-level
  security with the tenant policy, and a composite key to ``memberships (organization_id, id,
  user_id)``, so a link can only name a member of its own coaching (ADR-0005). Redemption
  arrives with M2 PR 4.
- ``idempotency_keys``: lets a client retry "create" requests safely (API style guide §6). Keys
  belong to the person who sent them, and are scoped by operation; they are honoured for 24 hours.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "qbank_app"


def upgrade() -> None:
    op.execute("""
        CREATE TABLE account_emails (
            email   text PRIMARY KEY CHECK (email = lower(btrim(email)) AND length(email) <= 320),
            user_id uuid NOT NULL UNIQUE REFERENCES users (id)
        );
        INSERT INTO account_emails (email, user_id)
            SELECT email, user_id FROM password_credentials;
        ALTER TABLE account_emails ENABLE ROW LEVEL SECURITY;  -- no policies: deny all

        ALTER TABLE memberships
            ADD CONSTRAINT memberships_org_id_user UNIQUE (organization_id, id, user_id);

        CREATE TABLE account_links (
            id              uuid PRIMARY KEY,
            organization_id uuid NOT NULL,
            membership_id   uuid NOT NULL,
            user_id         uuid NOT NULL,
            purpose         text NOT NULL CHECK (purpose IN ('ACTIVATION', 'RESET')),
            token_hash      text NOT NULL UNIQUE,
            created_by      uuid REFERENCES users (id),
            created_at      timestamptz NOT NULL DEFAULT now(),
            expires_at      timestamptz NOT NULL,
            used_at         timestamptz,
            revoked_at      timestamptz,
            FOREIGN KEY (organization_id, membership_id, user_id)
                REFERENCES memberships (organization_id, id, user_id)
        );
        CREATE INDEX account_links_user ON account_links (user_id);
        ALTER TABLE account_links ENABLE ROW LEVEL SECURITY;
        ALTER TABLE account_links FORCE ROW LEVEL SECURITY;
        CREATE POLICY account_links_tenant ON account_links FOR ALL
            USING (organization_id = app_current_org())
            WITH CHECK (organization_id = app_current_org());

        CREATE TABLE idempotency_keys (
            actor_user_id uuid NOT NULL REFERENCES users (id),
            operation     text NOT NULL,
            key           text NOT NULL CHECK (length(key) BETWEEN 1 AND 200),
            request_hash  text NOT NULL,
            resource_id   uuid NOT NULL,
            created_at    timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (actor_user_id, operation, key)
        );
        ALTER TABLE idempotency_keys ENABLE ROW LEVEL SECURITY;
        ALTER TABLE idempotency_keys FORCE ROW LEVEL SECURITY;
        CREATE POLICY idempotency_keys_own ON idempotency_keys FOR ALL
            USING (actor_user_id = app_current_user())
            WITH CHECK (actor_user_id = app_current_user());
    """)
    # Reserve the email of an account being invited. Returns false if the email is already taken
    # (by anyone, in any coaching). The row is written in the caller's transaction, so it vanishes
    # if the invitation fails; a concurrent second reservation waits for the first and then fails.
    # Only for brand-new invited accounts, and only by a caller acting in a coaching or as platform.
    op.execute("""
        CREATE FUNCTION auth_reserve_email(p_email text, p_user_id uuid)
        RETURNS boolean
        LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = pg_catalog, public AS $$
        DECLARE
            reserved integer;
        BEGIN
            IF app_current_org() IS NULL AND NOT app_is_platform() THEN
                RAISE EXCEPTION 'auth_reserve_email needs a coaching or platform context';
            END IF;
            IF NOT EXISTS (SELECT 1 FROM users WHERE id = p_user_id AND status = 'INVITED')
               OR EXISTS (SELECT 1 FROM account_emails WHERE user_id = p_user_id) THEN
                RAISE EXCEPTION 'auth_reserve_email is only for a new invited account';
            END IF;
            INSERT INTO account_emails (email, user_id)
                VALUES (lower(btrim(p_email)), p_user_id)
                ON CONFLICT (email) DO NOTHING;
            GET DIAGNOSTICS reserved = ROW_COUNT;
            RETURN reserved = 1;
        END
        $$;
        REVOKE EXECUTE ON FUNCTION auth_reserve_email(text, uuid) FROM PUBLIC;
    """)
    op.execute(f"""
        GRANT EXECUTE ON FUNCTION auth_reserve_email(text, uuid) TO {APP_ROLE};
        -- The token hash is not readable by the runtime role; links are redeemed by a definer
        -- function (M2 PR 4). Only revoking changes an existing link.
        GRANT SELECT (id, organization_id, membership_id, user_id, purpose, created_by, created_at,
                      expires_at, used_at, revoked_at),
              INSERT
            ON account_links TO {APP_ROLE};
        GRANT UPDATE (revoked_at) ON account_links TO {APP_ROLE};
        GRANT SELECT, INSERT, DELETE ON idempotency_keys TO {APP_ROLE};
    """)


def downgrade() -> None:
    op.execute("""
        DROP FUNCTION auth_reserve_email(text, uuid);
        DROP TABLE idempotency_keys;
        DROP TABLE account_links;
        ALTER TABLE memberships DROP CONSTRAINT memberships_org_id_user;
        DROP TABLE account_emails;
    """)
