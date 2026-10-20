"""M1 exit test T8: migrations go up, down and up again cleanly on an empty database."""

import secrets
from collections.abc import Iterator

import pytest
from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect

from qbank.main import create_app
from tests.conftest import make_settings
from tests.integration.conftest import (
    MigratedDatabase,
    alembic_config,
    create_database,
    drop_database,
)


@pytest.fixture
def empty_database() -> Iterator[tuple[str, str]]:
    name = f"qbank_test_{secrets.token_hex(6)}"
    owner_url, app_url, _worker_url = create_database(name)
    try:
        yield owner_url, app_url
    finally:
        drop_database(name)


def table_names(url: str) -> set[str]:
    engine = create_engine(url)
    try:
        return set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def test_upgrade_downgrade_upgrade(empty_database: tuple[str, str]) -> None:
    owner_url, _ = empty_database
    config = alembic_config(owner_url)

    command.upgrade(config, "head")
    assert {
        "organizations",
        "users",
        "memberships",
        "audit_events",
        "password_credentials",
        "platform_roles",
        "sessions",
        "jobs",
        "public_codes",
        "membership_grants",
    } <= table_names(owner_url)

    command.downgrade(config, "base")
    assert table_names(owner_url) <= {"alembic_version"}

    command.upgrade(config, "head")
    assert "memberships" in table_names(owner_url)


def test_ready_when_schema_is_current(migrated_database: MigratedDatabase) -> None:
    with TestClient(create_app(make_settings(migrated_database.app_url))) as client:
        response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok", "migrations": "ok"}


def test_not_ready_when_migrations_are_pending(empty_database: tuple[str, str]) -> None:
    owner_url, app_url = empty_database
    command.upgrade(alembic_config(owner_url), "head")
    command.downgrade(alembic_config(owner_url), "base")
    # alembic_version still exists (empty) but the runtime role lost access to it on downgrade.

    with TestClient(create_app(make_settings(app_url))) as client:
        response = client.get("/health/ready")

    assert response.status_code == 503
