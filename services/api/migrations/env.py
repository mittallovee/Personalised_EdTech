"""Alembic environment. Migrations run as the table-owner role, never as the runtime app role."""

import os

from alembic import context
from sqlalchemy import create_engine

config = context.config


def database_url() -> str:
    # Tests pass the URL through the Alembic config; normal runs use the environment.
    url = config.get_main_option("sqlalchemy.url") or os.environ.get("MIGRATION_DATABASE_URL")
    if not url:
        raise RuntimeError("Set MIGRATION_DATABASE_URL (table-owner role) to run migrations.")
    return url


def run_migrations() -> None:
    engine = create_engine(database_url())
    with engine.connect() as connection:
        context.configure(connection=connection, transaction_per_migration=True)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    raise RuntimeError("Offline (SQL script) migrations are not supported.")
run_migrations()
