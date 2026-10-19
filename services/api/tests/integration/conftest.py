"""Integration-test database setup.

Needs a disposable PostgreSQL server reachable with an admin (superuser/owner) account:
  QBANK_TEST_ADMIN_URL      e.g. postgresql+psycopg://qbank_owner:PASSWORD@localhost:5432/postgres
  QBANK_TEST_APP_PASSWORD     password of the restricted `qbank_app` role (created here if missing)
  QBANK_TEST_WORKER_PASSWORD  password of the `qbank_worker` role (created here if missing)
Defaults match `.env.example`, so `docker compose up -d postgres` is enough locally.
Each test session creates a fresh database and drops it afterwards.
"""

import os
import secrets
from collections.abc import Iterator
from dataclasses import dataclass
from uuid import UUID

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from psycopg import sql
from sqlalchemy.engine import make_url

from qbank.core.config import SERVICE_ROOT
from qbank.core.db import Database
from qbank.core.ids import new_id
from qbank.core.tenancy import TenantContext
from qbank.modules.audit.models import AuditEvent
from qbank.modules.identity.models import User
from qbank.modules.organizations.models import Membership, Organization

ADMIN_URL = os.environ.get(
    "QBANK_TEST_ADMIN_URL",
    "postgresql+psycopg://qbank_owner:change-me-local-only@localhost:5432/postgres",
)
APP_PASSWORD = os.environ.get("QBANK_TEST_APP_PASSWORD", "change-me-app-local")
APP_ROLE = "qbank_app"
WORKER_PASSWORD = os.environ.get("QBANK_TEST_WORKER_PASSWORD", "change-me-worker-local")
WORKER_ROLE = "qbank_worker"


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        if "tests/integration" in str(item.path):
            item.add_marker(pytest.mark.integration)


def _admin_connection() -> psycopg.Connection:
    url = make_url(ADMIN_URL).set(drivername="postgresql")
    try:
        return psycopg.connect(url.render_as_string(hide_password=False), autocommit=True)
    except psycopg.OperationalError as exc:
        pytest.fail(f"Integration tests need PostgreSQL at QBANK_TEST_ADMIN_URL: {exc}")


def _ensure_role(conn: psycopg.Connection, role: str, password: str) -> None:
    """Same attributes as ``infra/db/ensure-app-role.sh`` gives the role locally."""
    if conn.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,)).fetchone():
        return
    conn.execute(
        sql.SQL(
            "CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE"
        ).format(sql.Identifier(role), sql.Literal(password))
    )


def create_database(name: str) -> tuple[str, str, str]:
    """Create an empty database; return (owner_url, app_url, worker_url) for it."""
    with _admin_connection() as conn:
        _ensure_role(conn, APP_ROLE, APP_PASSWORD)
        _ensure_role(conn, WORKER_ROLE, WORKER_PASSWORD)
        conn.execute(
            sql.SQL("GRANT {} TO {}").format(sql.Identifier(APP_ROLE), sql.Identifier(WORKER_ROLE))
        )
        conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    owner = make_url(ADMIN_URL).set(database=name)
    app = owner.set(username=APP_ROLE, password=APP_PASSWORD)
    worker = owner.set(username=WORKER_ROLE, password=WORKER_PASSWORD)
    return (
        owner.render_as_string(hide_password=False),
        app.render_as_string(hide_password=False),
        worker.render_as_string(hide_password=False),
    )


def drop_database(name: str) -> None:
    with _admin_connection() as conn:
        conn.execute(
            sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(name))
        )


def alembic_config(owner_url: str) -> Config:
    config = Config(str(SERVICE_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", owner_url.replace("%", "%%"))
    return config


@dataclass(frozen=True)
class MigratedDatabase:
    name: str
    owner_url: str
    app_url: str
    worker_url: str


@pytest.fixture(scope="session")
def migrated_database() -> Iterator[MigratedDatabase]:
    name = f"qbank_test_{secrets.token_hex(6)}"
    owner_url, app_url, worker_url = create_database(name)
    try:
        command.upgrade(alembic_config(owner_url), "head")
        yield MigratedDatabase(name, owner_url, app_url, worker_url)
    finally:
        drop_database(name)


@pytest.fixture
def db(migrated_database: MigratedDatabase) -> Iterator[Database]:
    """Runtime-role database access, exactly as the app uses it."""
    database = Database(migrated_database.app_url)
    yield database
    database.dispose()


@pytest.fixture
def worker_db(migrated_database: MigratedDatabase) -> Iterator[Database]:
    """Worker-role database access, exactly as the background worker uses it."""
    database = Database(migrated_database.worker_url)
    yield database
    database.dispose()


@pytest.fixture
def owner_db(migrated_database: MigratedDatabase) -> Iterator[Database]:
    """Table-owner access, used only to arrange test data the app itself may not write."""
    database = Database(migrated_database.owner_url)
    yield database
    database.dispose()


@dataclass(frozen=True)
class Coaching:
    org_id: UUID
    user_id: UUID
    membership_id: UUID
    audit_id: UUID

    @property
    def context(self) -> TenantContext:
        return TenantContext(organization_id=self.org_id, user_id=self.user_id)


PLATFORM = TenantContext(is_platform=True)


def make_coaching(db: Database, name: str) -> Coaching:
    org_id, user_id, membership_id, audit_id = new_id(), new_id(), new_id(), new_id()
    with db.transaction(PLATFORM) as session:
        session.add(Organization(id=org_id, display_name=name))
        session.add(User(id=user_id, display_name=f"Owner of {name}"))
    with db.transaction(TenantContext(organization_id=org_id)) as session:
        session.add(
            Membership(id=membership_id, organization_id=org_id, user_id=user_id, role="OWNER")
        )
        session.add(
            AuditEvent(
                id=audit_id,
                organization_id=org_id,
                action="TEST_EVENT",
                entity_type="organization",
                entity_id=org_id,
            )
        )
    return Coaching(org_id, user_id, membership_id, audit_id)


@pytest.fixture
def coaching_a(db: Database) -> Coaching:
    return make_coaching(db, "Coaching A")


@pytest.fixture
def coaching_b(db: Database) -> Coaching:
    return make_coaching(db, "Coaching B")
