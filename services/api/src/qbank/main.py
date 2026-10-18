"""FastAPI application factory. Run with: ``uvicorn qbank.main:create_app --factory``."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from qbank.core.config import AppEnv, Settings, get_settings
from qbank.core.db import Database
from qbank.core.errors import install_error_handlers
from qbank.core.logging import configure_logging, install_request_logging
from qbank.core.migrations import migration_heads
from qbank.modules.health.api import router as health_router


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    database = Database(settings.database_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield
        database.dispose()

    is_production = settings.app_env == AppEnv.PRODUCTION
    app = FastAPI(
        title="Question Bank API",
        version="0.1.0",
        docs_url=None if is_production else "/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.db = database
    app.state.migration_heads = migration_heads(settings.migrations_dir)

    install_request_logging(app)
    install_error_handlers(app)
    app.include_router(health_router)
    return app
