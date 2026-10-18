"""M1 exit test T3: the runtime role cannot switch off or work around row-level security."""

import pytest
from sqlalchemy import delete, text, update
from sqlalchemy.exc import DBAPIError

from qbank.core.db import Database
from qbank.modules.audit.models import AuditEvent
from tests.integration.conftest import Coaching

TABLES = ("organizations", "users", "memberships", "audit_events")


def test_runtime_role_has_no_bypass_attributes(db: Database) -> None:
    with db.engine.connect() as conn:
        row = conn.execute(
            text("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user")
        ).one()

    assert row.rolsuper is False
    assert row.rolbypassrls is False


def test_runtime_role_owns_no_tables(db: Database) -> None:
    with db.engine.connect() as conn:
        owners = conn.execute(
            text("SELECT tablename, tableowner FROM pg_tables WHERE schemaname = 'public'")
        ).all()

    assert owners
    assert all(owner != "qbank_app" for _, owner in owners)


def test_all_tenant_tables_force_row_level_security(db: Database) -> None:
    with db.engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT relname, relrowsecurity, relforcerowsecurity FROM pg_class "
                "WHERE relname = ANY(:names)"
            ),
            {"names": list(TABLES)},
        ).all()

    assert {r.relname for r in rows} == set(TABLES)
    assert all(r.relrowsecurity and r.relforcerowsecurity for r in rows)


@pytest.mark.parametrize("table", TABLES)
def test_runtime_role_cannot_disable_row_level_security(db: Database, table: str) -> None:
    with pytest.raises(DBAPIError, match="must be owner"), db.engine.begin() as conn:
        conn.execute(text(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY"))


def test_turning_row_security_off_is_refused(db: Database, coaching_a: Coaching) -> None:
    with pytest.raises(DBAPIError, match="row-level security"), db.engine.begin() as conn:
        conn.execute(text("SET row_security = off"))
        conn.execute(text("SELECT count(*) FROM memberships"))


def test_audit_events_are_append_only(db: Database, coaching_a: Coaching) -> None:
    with (
        pytest.raises(DBAPIError, match="permission denied"),
        db.transaction(coaching_a.context) as s,
    ):
        s.execute(update(AuditEvent).where(AuditEvent.id == coaching_a.audit_id).values(action="X"))

    with (
        pytest.raises(DBAPIError, match="permission denied"),
        db.transaction(coaching_a.context) as s,
    ):
        s.execute(delete(AuditEvent).where(AuditEvent.id == coaching_a.audit_id))
