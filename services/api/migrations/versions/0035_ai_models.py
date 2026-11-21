"""The coaching's list of AI models, fetched from the providers (M5 PR 5b-1, H-03, H-17).

Revision ID: 0035
Revises: 0034
Create Date: 2026-11-21

M5 design note §4. One row per coaching, provider and model id: what the provider's own model list
said (display name, capabilities, context size, prices), an admin **overlay** of the same facts (the
overlay wins when set, so a price the provider does not publish can still be entered), whether the
admin **enabled** the model, and whether the provider still **lists** it (``available``: a model
that disappears from a refresh stays on record, and cannot be chosen). Prices are dollars per
million tokens as exact decimals, ``NULL`` meaning unknown. A refresh never changes the overlay or
``enabled``.

``ai_provider_keys`` gains when each provider's list was last fetched and the kind of failure of the
last try (never any text from the provider).

Coaching-owned: FORCE row-level security with the tenant policy, as the other AI tables.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0035"
down_revision: str | None = "0034"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "qbank_app"


def upgrade() -> None:
    op.execute("""
        ALTER TABLE ai_provider_keys
            ADD COLUMN models_fetched_at timestamptz,
            ADD COLUMN models_error text CHECK (models_error ~ '^[A-Z_]{1,30}$');

        CREATE TABLE ai_models (
            id                     uuid PRIMARY KEY,
            organization_id        uuid NOT NULL REFERENCES organizations (id),
            provider               text NOT NULL
                CHECK (provider IN ('ANTHROPIC', 'OPENAI', 'GOOGLE', 'OPENROUTER')),
            model_id               text NOT NULL CHECK (length(model_id) BETWEEN 1 AND 200),
            display_name           text NOT NULL CHECK (length(display_name) BETWEEN 1 AND 300),
            supports_vision        boolean,
            supports_json          boolean,
            context_tokens         integer CHECK (context_tokens >= 0),
            price_in               numeric(14, 6) CHECK (price_in >= 0),
            price_out              numeric(14, 6) CHECK (price_out >= 0),
            overlay_supports_vision boolean,
            overlay_supports_json  boolean,
            overlay_price_in       numeric(14, 6) CHECK (overlay_price_in >= 0),
            overlay_price_out      numeric(14, 6) CHECK (overlay_price_out >= 0),
            overlay_batch_supported boolean,
            overlay_batch_discount numeric(5, 4)
                CHECK (overlay_batch_discount > 0 AND overlay_batch_discount <= 1),
            enabled                boolean NOT NULL DEFAULT false,
            available              boolean NOT NULL DEFAULT true,
            fetched_at             timestamptz NOT NULL DEFAULT now(),
            created_at             timestamptz NOT NULL DEFAULT now(),
            updated_at             timestamptz NOT NULL DEFAULT now(),
            revision               integer NOT NULL DEFAULT 1,
            UNIQUE (organization_id, provider, model_id),
            UNIQUE (organization_id, id)
        );
        CREATE INDEX ai_models_by_provider ON ai_models (organization_id, provider, model_id);

        ALTER TABLE ai_models ENABLE ROW LEVEL SECURITY;
        ALTER TABLE ai_models FORCE ROW LEVEL SECURITY;
        CREATE POLICY ai_models_tenant ON ai_models FOR ALL
            USING (organization_id = app_current_org())
            WITH CHECK (organization_id = app_current_org());
    """)
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON ai_models TO {APP_ROLE};")


def downgrade() -> None:
    op.execute("""
        DROP TABLE ai_models;
        ALTER TABLE ai_provider_keys DROP COLUMN models_fetched_at, DROP COLUMN models_error;
    """)
