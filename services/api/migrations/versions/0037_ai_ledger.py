"""The AI usage ledger: what each person's runs cost, append-only (M5 PR 5c, H-05, H-06).

Revision ID: 0037
Revises: 0036
Create Date: 2026-11-21

M5 design note §4, §7. Every cost is an **entry**; nothing is ever changed or removed, so a bug (or
a person) cannot rewrite history, and a correction is a new entry. For one run the entries are:

- ``RESERVE``: the estimated cost, set aside before the provider is called (positive);
- ``RELEASE``: the reservation given back (negative), written when the run ends;
- ``SETTLE``: what the run really cost (positive, from the provider's own token counts), or its
  estimate (``cost_kind`` ``ESTIMATED``) or nothing (``UNKNOWN``) when the price is not known;
- ``ADJUST``: an admin's correction after reading the provider's invoice (either sign);
- ``NOTICE_80`` / ``NOTICE_100``: a marker that the person was told they reached 80 % or 100 % of
  the month's budget (amount 0). A unique index makes each notice once per person per month.

A person's spend this month is the sum of their entries of that month, so a reservation counts while
it is held and disappears (replaced by the real cost) when the run ends. ``period`` is the first day
of the month in India time, fixed when the run starts, so a run that ends after midnight on the 1st
still belongs to the month it began in. Amounts: ``amount_usd`` (what the providers bill) and
``amount_inr`` (rupees at the rate the admin had entered when the entry was written, kept on the
entry; ``NULL`` when no rate was entered). A unique index per run keeps a run from being settled or
released twice.

Coaching-owned: FORCE row-level security with the tenant policy. The runtime role can read and add
entries and can do nothing else; a trigger refuses UPDATE, DELETE and TRUNCATE for everyone,
including the table owner.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0037"
down_revision: str | None = "0036"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "qbank_app"


def upgrade() -> None:
    op.execute("""
        CREATE TABLE ai_ledger (
            id              uuid PRIMARY KEY,
            organization_id uuid NOT NULL REFERENCES organizations (id),
            user_id         uuid NOT NULL REFERENCES users (id),
            run_id          uuid,
            entry_kind      text NOT NULL CHECK (entry_kind IN
                ('RESERVE', 'RELEASE', 'SETTLE', 'ADJUST', 'NOTICE_80', 'NOTICE_100')),
            period          date NOT NULL CHECK (extract(day FROM period) = 1),
            amount_usd      numeric(14, 6) NOT NULL,
            amount_inr      numeric(16, 4),
            rate            numeric(10, 4) CHECK (rate > 0),
            cost_kind       text CHECK (cost_kind IN ('ACTUAL', 'ESTIMATED', 'UNKNOWN')),
            note            text CHECK (length(note) <= 300),
            created_by      uuid REFERENCES users (id),
            created_at      timestamptz NOT NULL DEFAULT now(),
            CHECK (entry_kind <> 'RESERVE' OR (amount_usd >= 0 AND coalesce(amount_inr, 0) >= 0)),
            CHECK (entry_kind <> 'RELEASE' OR (amount_usd <= 0 AND coalesce(amount_inr, 0) <= 0)),
            CHECK (entry_kind <> 'SETTLE' OR (amount_usd >= 0 AND coalesce(amount_inr, 0) >= 0)),
            CHECK (entry_kind NOT IN ('NOTICE_80', 'NOTICE_100')
                   OR (amount_usd = 0 AND coalesce(amount_inr, 0) = 0)),
            CHECK (entry_kind NOT IN ('RESERVE', 'RELEASE', 'SETTLE') OR run_id IS NOT NULL),
            CHECK (entry_kind <> 'ADJUST' OR (created_by IS NOT NULL AND note IS NOT NULL))
        );
        CREATE INDEX ai_ledger_by_person_month ON ai_ledger (organization_id, user_id, period);
        CREATE INDEX ai_ledger_by_run ON ai_ledger (run_id) WHERE run_id IS NOT NULL;
        -- One reservation, one release and one settlement per run, however often a step is retried.
        CREATE UNIQUE INDEX ai_ledger_one_reserve ON ai_ledger (run_id)
            WHERE entry_kind = 'RESERVE';
        CREATE UNIQUE INDEX ai_ledger_one_release ON ai_ledger (run_id)
            WHERE entry_kind = 'RELEASE';
        CREATE UNIQUE INDEX ai_ledger_one_settle ON ai_ledger (run_id)
            WHERE entry_kind = 'SETTLE';
        -- Each notice is sent once per person per month.
        CREATE UNIQUE INDEX ai_ledger_one_notice
            ON ai_ledger (organization_id, user_id, period, entry_kind)
            WHERE entry_kind IN ('NOTICE_80', 'NOTICE_100');

        CREATE FUNCTION ai_ledger_refuse_change() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'ai_ledger is append-only: add an entry instead'
                USING ERRCODE = 'restrict_violation';
        END;
        $$;
        CREATE TRIGGER ai_ledger_no_update_delete BEFORE UPDATE OR DELETE ON ai_ledger
            FOR EACH ROW EXECUTE FUNCTION ai_ledger_refuse_change();
        CREATE TRIGGER ai_ledger_no_truncate BEFORE TRUNCATE ON ai_ledger
            FOR EACH STATEMENT EXECUTE FUNCTION ai_ledger_refuse_change();

        ALTER TABLE ai_ledger ENABLE ROW LEVEL SECURITY;
        ALTER TABLE ai_ledger FORCE ROW LEVEL SECURITY;
        CREATE POLICY ai_ledger_tenant ON ai_ledger FOR ALL
            USING (organization_id = app_current_org())
            WITH CHECK (organization_id = app_current_org());
    """)
    op.execute(f"GRANT SELECT, INSERT ON ai_ledger TO {APP_ROLE};  -- append-only")


def downgrade() -> None:
    op.execute("""
        DROP TABLE ai_ledger;
        DROP FUNCTION ai_ledger_refuse_change();
    """)
