"""A coaching's sealed AI provider keys (M5 PR 5a-1, H-02, ADR-0023).

Revision ID: 0034
Revises: 0033
Create Date: 2026-11-21

M5 design note §4. One row per coaching and provider. The key itself is never stored: ``ciphertext``
is AES-256-GCM output sealed with a master key that lives in the environment (never in the database
or its backups), ``nonce`` is the 96-bit nonce, and ``key_id`` names the master key used, so a
rotation can open old rows and reseal them. ``last4`` is all the screen ever shows.

Coaching-owned: FORCE row-level security with the tenant policy. The runtime role may read, add,
change and delete its coaching's rows.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0034"
down_revision: str | None = "0033"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "qbank_app"


def upgrade() -> None:
    op.execute("""
        CREATE TABLE ai_provider_keys (
            id               uuid PRIMARY KEY,
            organization_id  uuid NOT NULL REFERENCES organizations (id),
            provider         text NOT NULL
                CHECK (provider IN ('ANTHROPIC', 'OPENAI', 'GOOGLE', 'OPENROUTER')),
            ciphertext       bytea NOT NULL CHECK (length(ciphertext) BETWEEN 17 AND 1100),
            nonce            bytea NOT NULL CHECK (length(nonce) = 12),
            key_id           text NOT NULL CHECK (key_id ~ '^[a-z0-9_-]{1,20}$'),
            last4            text NOT NULL CHECK (length(last4) BETWEEN 1 AND 4),
            created_by       uuid NOT NULL REFERENCES users (id),
            created_at       timestamptz NOT NULL DEFAULT now(),
            updated_at       timestamptz NOT NULL DEFAULT now(),
            revision         integer NOT NULL DEFAULT 1,
            UNIQUE (organization_id, provider)
        );

        ALTER TABLE ai_provider_keys ENABLE ROW LEVEL SECURITY;
        ALTER TABLE ai_provider_keys FORCE ROW LEVEL SECURITY;
        CREATE POLICY ai_provider_keys_tenant ON ai_provider_keys FOR ALL
            USING (organization_id = app_current_org())
            WITH CHECK (organization_id = app_current_org());
    """)
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON ai_provider_keys TO {APP_ROLE};")


def downgrade() -> None:
    op.execute("DROP TABLE ai_provider_keys;")
