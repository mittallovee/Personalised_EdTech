"""Routes for golden sets (M6 6j, G-11): admins collect reviewed questions into an answer key.

The measurement itself is a command (``qbank ingest-measure``), not a route: it calls a real model
and is run on purpose, by a person, before and after a change.
"""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from qbank.core.auth import CurrentPrincipal
from qbank.core.db import Database, get_database
from qbank.modules.ingestion import golden
from qbank.modules.ingestion.schemas import (
    GoldenCaseIn,
    GoldenCaseOut,
    GoldenSetIn,
    GoldenSetOut,
    GoldenSetsOut,
)

router = APIRouter(prefix="/api/v1/ingest/golden-sets", tags=["ingestion"])

_RESPONSES: dict[int | str, dict[str, Any]] = {
    403: {"description": "Owner and admins only (`PERMISSION_DENIED`)"},
    404: {"description": "No such set or candidate of yours (`NOT_FOUND`)"},
}


def _rid(request: Request) -> str | None:
    value: str | None = getattr(request.state, "request_id", None)
    return value


@router.get("", summary="The golden sets", responses=_RESPONSES)
def list_sets(
    principal: CurrentPrincipal, database: Annotated[Database, Depends(get_database)]
) -> GoldenSetsOut:
    with database.transaction(principal.tenant_context) as session:
        return GoldenSetsOut(
            data=[
                GoldenSetOut(id=row.id, name=row.name, cases=n, created_at=row.created_at)
                for row, n in golden.list_sets(session, principal)
            ]
        )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Start a golden set",
    responses={**_RESPONSES, 409: {"description": "The name is taken (`GOLDEN_SET_EXISTS`)"}},
)
def create_set(
    body: GoldenSetIn,
    request: Request,
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
) -> GoldenSetOut:
    with database.transaction(principal.tenant_context) as session:
        row = golden.create_set(session, principal, body.name, request_id=_rid(request))
        return GoldenSetOut(id=row.id, name=row.name, cases=0, created_at=row.created_at)


@router.post(
    "/{set_id}/cases",
    status_code=status.HTTP_201_CREATED,
    summary="Add an accepted question to the key",
    description=(
        "Freezes the content the candidate was accepted with. Only an accepted candidate can be"
        " added (`GOLDEN_NOT_ACCEPTED`), once per set (`GOLDEN_CASE_EXISTS`)."
    ),
    responses={**_RESPONSES, 409: {"description": "Not accepted, already added, or full"}},
)
def add_case(
    set_id: UUID,
    body: GoldenCaseIn,
    request: Request,
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
) -> GoldenCaseOut:
    with database.transaction(principal.tenant_context) as session:
        row = golden.add_case(
            session, principal, set_id, body.candidate_id, request_id=_rid(request)
        )
        return GoldenCaseOut(
            id=row.id,
            set_id=row.set_id,
            file_id=row.file_id,
            page_no=row.page_no,
            candidate_id=row.candidate_id,
        )
