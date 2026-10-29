"""FastAPI application factory. Run with: ``uvicorn qbank.main:create_app --factory``."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from qbank.core.config import AppEnv, Settings, get_settings
from qbank.core.db import Database
from qbank.core.errors import install_error_handlers
from qbank.core.logging import configure_logging, install_request_logging
from qbank.core.metrics import install_request_metrics, start_metrics_server, watch_pool
from qbank.core.migrations import migration_heads
from qbank.core.openapi import install_openapi
from qbank.core.origin import install_origin_check
from qbank.core.ratelimit import ConcurrencyGate, LoginRateLimiter, SlidingWindowLimiter
from qbank.modules.audit.api import router as audit_router
from qbank.modules.health.api import router as health_router
from qbank.modules.identity.api import router as identity_router
from qbank.modules.identity.authenticator import SessionCookieAuthenticator
from qbank.modules.identity.google import GoogleOidc
from qbank.modules.identity.google_api import router as google_router
from qbank.modules.organizations.api import router as organizations_router
from qbank.modules.organizations.members_api import router as members_router
from qbank.modules.organizations.ownership_api import router as ownership_router
from qbank.modules.taxonomy.api import catalogues as catalogues_router
from qbank.modules.taxonomy.api import router as taxonomy_router
from qbank.modules.taxonomy.catalogue_api import exams_router, sources_router
from qbank.modules.taxonomy.concepts_api import router as concepts_router
from qbank.modules.taxonomy.import_api import router as import_router


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    database = Database(settings.database_url)
    watch_pool(database)
    if settings.metrics_port:
        start_metrics_server(settings.metrics_port)

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
    # Ways a caller can sign in, tried in order (ADR-0006). Bearer tokens join this list in P4.
    app.state.authenticators = [SessionCookieAuthenticator(database, settings)]
    app.state.login_limiter = LoginRateLimiter(
        per_ip=settings.login_attempts_per_ip,
        per_email=settings.login_attempts_per_email,
        window_seconds=settings.login_rate_window_seconds,
    )
    app.state.import_upload_limiter = SlidingWindowLimiter(
        settings.import_uploads_per_user, settings.import_upload_window_seconds
    )
    app.state.import_parse_gate = ConcurrencyGate(settings.import_parses_at_once)

    # Google sign-in is available only when its client ID and secret are configured (B-02).
    app.state.google = (
        GoogleOidc(settings.google_client_id, settings.google_client_secret.get_secret_value())
        if settings.google_client_id and settings.google_client_secret
        else None
    )

    install_origin_check(app, settings.allowed_origins)  # added first, so it runs inside logging
    install_request_logging(app)
    install_request_metrics(app)  # after logging: outermost, so it also counts logged 500s
    install_error_handlers(app)
    app.include_router(health_router)
    app.include_router(identity_router)
    app.include_router(google_router)
    app.include_router(audit_router)
    app.include_router(organizations_router)
    app.include_router(members_router)
    app.include_router(ownership_router)
    app.include_router(catalogues_router)
    app.include_router(taxonomy_router)
    app.include_router(concepts_router)
    app.include_router(import_router)
    app.include_router(exams_router)
    app.include_router(sources_router)
    install_openapi(app)
    return app
