from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from qbank.core.db import Database, get_database
from qbank.modules.health.schemas import LiveStatus, ReadyStatus

router = APIRouter(prefix="/health", tags=["health"])
log = structlog.get_logger("qbank.health")


@router.get("/live", summary="Process is running")
def live() -> LiveStatus:
    return LiveStatus(status="ok")


@router.get(
    "/ready",
    summary="Ready to serve: database reachable and schema up to date",
    response_model=ReadyStatus,
    responses={503: {"model": ReadyStatus, "description": "Not ready"}},
)
def ready(request: Request, database: Annotated[Database, Depends(get_database)]) -> JSONResponse:
    heads: frozenset[str] = request.app.state.migration_heads
    try:
        with database.engine.connect() as connection:
            current = connection.execute(text("SELECT version_num FROM alembic_version")).scalar()
    except SQLAlchemyError:
        log.warning("readiness_database_unavailable", exc_info=True)
        body = ReadyStatus(status="unavailable", database="unavailable", migrations="unknown")
        return JSONResponse(status_code=503, content=body.model_dump())

    migrations_ok = current in heads
    body = ReadyStatus(
        status="ok" if migrations_ok else "unavailable",
        database="ok",
        migrations="ok" if migrations_ok else "pending",
    )
    return JSONResponse(status_code=200 if migrations_ok else 503, content=body.model_dump())
