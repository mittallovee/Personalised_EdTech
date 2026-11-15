"""M3 exit check T30: no table of a coaching's data can be added without row-level security.

``test_database_role.py`` checks a fixed list of tables. This test finds the tables itself: every
table with an ``organization_id`` column must either force row-level security with a policy (so
even the table owner is held to it), or have row-level security on with **no** policy at all
(deny everything: only the owner-run functions that are written for that table can touch it). A new
table that forgets this fails here, whoever adds it and whichever PR it comes in.
"""

from typing import Any

import pytest
from sqlalchemy import text

from qbank.core.db import Database

# Tables with an organization_id that are deliberately not plain tenant tables, and why. An entry
# must stay true: ``test_each_exception_is_real_and_explained`` fails when it stops applying.
EXEMPT = {
    "jobs": "the queue is read by owner-run worker functions, which must see every coaching",
}


def _tables_with_organization_id(db: Database) -> list[str]:
    with db.engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT table_name FROM information_schema.columns"
                " WHERE table_schema = 'public' AND column_name = 'organization_id'"
                " AND table_name IN (SELECT table_name FROM information_schema.tables"
                "   WHERE table_schema = 'public' AND table_type = 'BASE TABLE')"
                " ORDER BY table_name"
            )
        ).all()
    return [row.table_name for row in rows]


def test_the_search_finds_the_tables_we_know_about(db: Database) -> None:
    found = set(_tables_with_organization_id(db))
    for table in ("memberships", "question_masters", "assets", "passages", "answer_rule_settings"):
        assert table in found, f"the search did not find {table}"


def test_every_table_with_an_organization_id_is_isolated(db: Database) -> None:
    names = [t for t in _tables_with_organization_id(db) if t not in EXEMPT]
    with db.engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity,"
                " (SELECT count(*) FROM pg_policy p WHERE p.polrelid = c.oid) AS policies"
                " FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace"
                " WHERE n.nspname = 'public' AND c.relname = ANY(:names)"
            ),
            {"names": names},
        ).all()
    assert {row.relname for row in rows} == set(names)

    def isolated(row: Any) -> bool:
        on, forced, policies = row.relrowsecurity, row.relforcerowsecurity, row.policies
        return bool(on and ((forced and policies >= 1) or policies == 0))

    weak = [row.relname for row in rows if not isolated(row)]
    assert weak == [], f"tables without forced row-level security and a policy: {weak}"


@pytest.mark.parametrize("table", sorted(EXEMPT))
def test_each_exception_is_real_and_explained(db: Database, table: str) -> None:
    # An exemption that no longer applies must be removed, not left to hide a future table.
    assert table in _tables_with_organization_id(db), f"{table} no longer has an organization_id"
    assert EXEMPT[table]
