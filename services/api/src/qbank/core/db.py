"""Database engine, ORM base class and tenant-scoped transactions."""

from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import Request
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from qbank.core.tenancy import TenantContext, apply_tenant_context


class Base(DeclarativeBase):
    """Base class for all ORM models. Each module defines its own tables in ``models.py``."""


class Database:
    def __init__(self, url: str) -> None:
        self.engine = create_engine(url, pool_pre_ping=True)
        self._sessions = sessionmaker(self.engine, expire_on_commit=False)

    @contextmanager
    def transaction(
        self, context: TenantContext, *, isolation_level: str | None = None
    ) -> Iterator[Session]:
        """Open a transaction with the tenant context set; commit on success, roll back on error.

        Every database access in request handlers and jobs goes through this, so row-level
        security always sees the right coaching. ``isolation_level="REPEATABLE READ"`` makes
        every query in the transaction see the database as of its first query, for reads that
        must be consistent with each other.
        """
        with self._sessions() as session, session.begin():
            if isolation_level is not None:
                session.connection(execution_options={"isolation_level": isolation_level})
            apply_tenant_context(session, context)
            yield session

    def dispose(self) -> None:
        self.engine.dispose()


def get_database(request: Request) -> Database:
    """FastAPI dependency: the process-wide ``Database`` created in ``create_app``."""
    database: Database = request.app.state.db
    return database
