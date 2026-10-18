"""FastAPI application factory."""

from fastapi import FastAPI

from qbank.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Question Bank API",
        version="0.1.0",
        docs_url="/api/docs" if settings.app_env != "production" else None,
        openapi_url="/api/openapi.json",
    )

    @app.get("/health/live", tags=["health"], summary="Process is running")
    def live() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
