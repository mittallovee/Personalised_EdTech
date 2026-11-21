"""What an admin sets for the AI features: operation defaults, the rate, budgets (M5 PR 5b-2).

Revision ID: 0036
Revises: 0035
Create Date: 2026-11-21

M5 design note §4, §7 (H-03, H-05, H-06).

- ``ai_settings``: one row per coaching: the US-dollar to rupee rate the admin entered (providers
  bill in dollars, budgets are in rupees; with no rate a budget cannot be applied) and the default
  monthly budget per person in rupees (``NULL`` = no limit).
- ``ai_operation_settings``: per coaching and operation (tag, translate, solve, verify), the model
  offered first, whether it runs Now or as an Economy (batch) run, and up to two fallback models.
  The models are rows of ``ai_models`` of the same coaching (composite keys), so a default can never
  name another coaching's model.
- ``ai_budgets``: a person's own monthly budget in rupees where it differs from the default
  (``0`` = no AI use).

Amounts are exact decimals. ``revision`` on each row is the ETag, so a save from a stale screen is
refused. Coaching-owned: FORCE row-level security with the tenant policy; the runtime role can
read, add and change rows, and can delete only a person's own budget (to go back to the default).
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0036"
down_revision: str | None = "0035"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "qbank_app"


def upgrade() -> None:
    op.execute("""
        CREATE TABLE ai_settings (
            organization_id   uuid PRIMARY KEY REFERENCES organizations (id),
            usd_to_inr        numeric(10, 4) CHECK (usd_to_inr > 0 AND usd_to_inr <= 10000),
            default_budget_inr numeric(12, 2) CHECK (default_budget_inr >= 0),
            revision          integer NOT NULL DEFAULT 1,
            updated_by        uuid NOT NULL REFERENCES users (id),
            updated_at        timestamptz NOT NULL DEFAULT now()
        );

        CREATE TABLE ai_operation_settings (
            id                uuid PRIMARY KEY,
            organization_id   uuid NOT NULL REFERENCES organizations (id),
            operation         text NOT NULL
                CHECK (operation IN ('TAG', 'TRANSLATE', 'SOLVE', 'VERIFY')),
            default_model_id  uuid,
            default_mode      text NOT NULL DEFAULT 'NOW'
                CHECK (default_mode IN ('NOW', 'ECONOMY')),
            fallback_1_id     uuid,
            fallback_2_id     uuid,
            revision          integer NOT NULL DEFAULT 1,
            updated_by        uuid NOT NULL REFERENCES users (id),
            updated_at        timestamptz NOT NULL DEFAULT now(),
            UNIQUE (organization_id, operation),
            FOREIGN KEY (organization_id, default_model_id)
                REFERENCES ai_models (organization_id, id),
            FOREIGN KEY (organization_id, fallback_1_id)
                REFERENCES ai_models (organization_id, id),
            FOREIGN KEY (organization_id, fallback_2_id)
                REFERENCES ai_models (organization_id, id),
            -- a second fallback only after a first, and no model twice in the chain
            CHECK (fallback_2_id IS NULL OR fallback_1_id IS NOT NULL),
            CHECK (fallback_1_id IS NULL OR fallback_1_id IS DISTINCT FROM default_model_id),
            CHECK (fallback_2_id IS NULL
                   OR (fallback_2_id IS DISTINCT FROM default_model_id
                       AND fallback_2_id IS DISTINCT FROM fallback_1_id))
        );

        CREATE TABLE ai_budgets (
            id                uuid PRIMARY KEY,
            organization_id   uuid NOT NULL REFERENCES organizations (id),
            user_id           uuid NOT NULL REFERENCES users (id),
            monthly_inr       numeric(12, 2) NOT NULL CHECK (monthly_inr >= 0),
            revision          integer NOT NULL DEFAULT 1,
            updated_by        uuid NOT NULL REFERENCES users (id),
            updated_at        timestamptz NOT NULL DEFAULT now(),
            UNIQUE (organization_id, user_id)
        );
    """)
    for table in ("ai_settings", "ai_operation_settings", "ai_budgets"):
        op.execute(f"""
            ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
            ALTER TABLE {table} FORCE ROW LEVEL SECURITY;
            CREATE POLICY {table}_tenant ON {table} FOR ALL
                USING (organization_id = app_current_org())
                WITH CHECK (organization_id = app_current_org());
        """)
    op.execute(f"""
        GRANT SELECT, INSERT, UPDATE ON ai_settings, ai_operation_settings TO {APP_ROLE};
        GRANT SELECT, INSERT, UPDATE, DELETE ON ai_budgets TO {APP_ROLE};
    """)


def downgrade() -> None:
    op.execute("DROP TABLE ai_budgets, ai_operation_settings, ai_settings;")
