"""Coaching roles and grants: one Owner per coaching, faculty grants, revisions for If-Match.

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-21

M2 design note §3 and §6:
- ``users.status`` gains ``INVITED``: an account created by an invitation that has not been
  activated yet. It cannot sign in (``_load_principal`` accepts only ACTIVE users).
- ``organizations.revision`` and ``memberships.revision`` count changes, so a client can say which
  version it saw (``If-Match``) and a stale screen gets 412 instead of overwriting newer work.
- At most one active OWNER per coaching, enforced by the database (ownership transfer, B-08).
- ``membership_grants``: extra rights given to faculty (QC, APPROVE, PUBLISH, EDIT_OTHERS,
  MANAGE_AI_PROMPTS). Coaching-owned, so FORCE row-level security with the tenant policy, and a
  composite foreign key so a grant can never point at another coaching's membership (ADR-0005).
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "qbank_app"


def upgrade() -> None:
    op.execute("""
        ALTER TABLE users DROP CONSTRAINT users_status_check;
        ALTER TABLE users ADD CONSTRAINT users_status_check
            CHECK (status IN ('INVITED', 'ACTIVE', 'DISABLED'));

        ALTER TABLE organizations ADD COLUMN revision integer NOT NULL DEFAULT 1;
        ALTER TABLE memberships ADD COLUMN revision integer NOT NULL DEFAULT 1;

        CREATE UNIQUE INDEX memberships_one_owner_per_coaching
            ON memberships (organization_id) WHERE role = 'OWNER' AND status = 'ACTIVE';

        CREATE TABLE membership_grants (
            organization_id uuid NOT NULL,
            membership_id   uuid NOT NULL,
            grant_name      text NOT NULL CHECK (grant_name IN
                                ('QC', 'APPROVE', 'PUBLISH', 'EDIT_OTHERS', 'MANAGE_AI_PROMPTS')),
            granted_by      uuid REFERENCES users (id),
            granted_at      timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (membership_id, grant_name),
            FOREIGN KEY (organization_id, membership_id)
                REFERENCES memberships (organization_id, id)
        );
        CREATE INDEX membership_grants_org ON membership_grants (organization_id);

        ALTER TABLE membership_grants ENABLE ROW LEVEL SECURITY;
        ALTER TABLE membership_grants FORCE ROW LEVEL SECURITY;
        CREATE POLICY membership_grants_tenant ON membership_grants FOR ALL
            USING (organization_id = app_current_org())
            WITH CHECK (organization_id = app_current_org());
    """)
    op.execute(f"""
        -- Granting and revoking replace rows; there is nothing to update in place.
        GRANT SELECT, INSERT, DELETE ON membership_grants TO {APP_ROLE};
    """)


def downgrade() -> None:
    # Fails if invited accounts exist: decide what they become before going back to 0003.
    op.execute("""
        DROP TABLE membership_grants;
        DROP INDEX memberships_one_owner_per_coaching;
        ALTER TABLE memberships DROP COLUMN revision;
        ALTER TABLE organizations DROP COLUMN revision;
        ALTER TABLE users DROP CONSTRAINT users_status_check;
        ALTER TABLE users ADD CONSTRAINT users_status_check
            CHECK (status IN ('ACTIVE', 'DISABLED'));
    """)
