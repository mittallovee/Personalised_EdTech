"""Routes for concepts: everyone in the coaching reads, admins change."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status

from qbank.core.auth import CurrentPrincipal
from qbank.core.db import Database, get_database
from qbank.core.etag import IfMatchHeader, etag
from qbank.core.idempotency import IdempotencyKeyHeader
from qbank.core.pagination import DEFAULT_LIMIT, MAX_LIMIT, PageInfo
from qbank.core.permissions import Action, require
from qbank.modules.taxonomy import concepts as service
from qbank.modules.taxonomy.cursors import MAX_CURSOR_LENGTH, decode_cursor
from qbank.modules.taxonomy.schemas import (
    ConceptOut,
    ConceptPage,
    CreateConcept,
    NodeState,
    UpdateConcept,
)

router = APIRouter(prefix="/api/v1/taxonomy/concepts", tags=["taxonomy"])

_DENIED: dict[int | str, dict[str, Any]] = {
    403: {"description": "Your role may not do this (`PERMISSION_DENIED`)"}
}
_NOT_FOUND: dict[int | str, dict[str, Any]] = {
    404: {"description": "No such concept (or subject) in your coaching (`NOT_FOUND`)"}
}
_STALE: dict[int | str, dict[str, Any]] = {
    412: {"description": "Changed by someone else since you read it (`REVISION_STALE`)"},
    428: {"description": "`If-Match` is missing (`IF_MATCH_REQUIRED`)"},
}
_TOO_LONG = "A name or alias is too long once normalised for comparing (`NAME_TOO_LONG`)"


@router.get(
    "",
    summary="Concepts, in name order",
    description=(
        "Filter by `subject_id` and `state` (use `state=ACTIVE` for a picker for a new question)."
        " `q` finds concepts whose name or an alias contains the text, in any case or spacing."
    ),
    responses={**_DENIED, 422: {"description": _TOO_LONG}},
)
def list_concepts(
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
    subject_id: UUID | None = None,
    concept_state: Annotated[NodeState | None, Query(alias="state")] = None,
    q: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
    cursor: Annotated[str | None, Query(max_length=MAX_CURSOR_LENGTH)] = None,
) -> ConceptPage:
    require(principal, Action.VIEW_CATALOGUES)
    after = decode_cursor(cursor) if cursor is not None else None
    with database.transaction(principal.tenant_context) as session:
        rows, has_more = service.list_concepts(
            session, subject_id=subject_id, state=concept_state, text=q, limit=limit, after=after
        )
        data = service.describe(session, rows)
    return ConceptPage(
        data=data,
        page=PageInfo(next_cursor=service.next_cursor(rows, has_more), has_more=has_more),
    )


@router.get(
    "/{concept_id}",
    summary="One concept",
    description="The ETag is its revision, for changes that need `If-Match`.",
    responses={**_DENIED, **_NOT_FOUND},
)
def get_concept(
    concept_id: UUID,
    principal: CurrentPrincipal,
    response: Response,
    database: Annotated[Database, Depends(get_database)],
) -> ConceptOut:
    require(principal, Action.VIEW_CATALOGUES)
    with database.transaction(principal.tenant_context) as session:
        concept = service.get_concept(session, concept_id)
        response.headers["ETag"] = etag(concept.revision)
        return service.describe(session, [concept])[0]


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Add a concept",
    description=(
        "Owner and admins. A concept belongs under a subject and never changes subject. Its name"
        " and aliases must differ from every other name and alias in the subject. Send an"
        " `Idempotency-Key` so a retry after a lost response returns the same concept."
    ),
    responses={
        **_DENIED,
        404: {"description": "No such subject in your coaching (`NOT_FOUND`)"},
        409: {
            "description": "A name or alias is taken in this subject (`DUPLICATE_NAME`), the"
            " subject is retired (`PARENT_DEPRECATED`), or the Idempotency-Key was used for a"
            " different request (`IDEMPOTENCY_KEY_REUSED`)"
        },
        422: {
            "description": "The parent is not a subject (`HIERARCHY_INVALID`), or "
            + _TOO_LONG[0].lower()
            + _TOO_LONG[1:]
        },
    },
)
def create_concept(
    body: CreateConcept,
    principal: CurrentPrincipal,
    request: Request,
    response: Response,
    database: Annotated[Database, Depends(get_database)],
    idempotency_key: Annotated[str | None, IdempotencyKeyHeader] = None,
) -> ConceptOut:
    with database.transaction(principal.tenant_context) as session:
        concept = service.create_concept(
            session,
            principal,
            body,
            idempotency_key=idempotency_key,
            request_id=request.state.request_id,
        )
        result = service.describe(session, [concept])[0]
    response.headers["Location"] = f"/api/v1/taxonomy/concepts/{result.id}"
    response.headers["ETag"] = etag(result.revision)
    return result


@router.patch(
    "/{concept_id}",
    summary="Rename a concept, or change its other-language names or aliases",
    description="Send the ETag you last read in `If-Match`. The subject never changes.",
    responses={
        **_DENIED,
        **_NOT_FOUND,
        **_STALE,
        409: {"description": "A name or alias is taken in this subject (`DUPLICATE_NAME`)"},
        422: {"description": _TOO_LONG},
    },
)
def update_concept(
    concept_id: UUID,
    body: UpdateConcept,
    principal: CurrentPrincipal,
    request: Request,
    response: Response,
    database: Annotated[Database, Depends(get_database)],
    if_match: Annotated[str | None, IfMatchHeader] = None,
) -> ConceptOut:
    with database.transaction(principal.tenant_context) as session:
        concept = service.update_concept(
            session,
            principal,
            concept_id,
            body,
            if_match=if_match,
            request_id=request.state.request_id,
        )
        response.headers["ETag"] = etag(concept.revision)
        return service.describe(session, [concept])[0]


def _set_state(
    concept_id: UUID,
    concept_state: str,
    principal: CurrentPrincipal,
    request: Request,
    response: Response,
    database: Database,
    if_match: str | None,
) -> ConceptOut:
    with database.transaction(principal.tenant_context) as session:
        concept = service.set_state(
            session,
            principal,
            concept_id,
            concept_state,
            if_match=if_match,
            request_id=request.state.request_id,
        )
        response.headers["ETag"] = etag(concept.revision)
        return service.describe(session, [concept])[0]


@router.post(
    "/{concept_id}/deprecate",
    summary="Retire a concept",
    description="It can no longer be chosen for new questions; questions that use it keep it.",
    responses={**_DENIED, **_NOT_FOUND, **_STALE},
)
def deprecate_concept(
    concept_id: UUID,
    principal: CurrentPrincipal,
    request: Request,
    response: Response,
    database: Annotated[Database, Depends(get_database)],
    if_match: Annotated[str | None, IfMatchHeader] = None,
) -> ConceptOut:
    return _set_state(concept_id, "DEPRECATED", principal, request, response, database, if_match)


@router.post(
    "/{concept_id}/restore",
    summary="Bring a retired concept back",
    responses={
        **_DENIED,
        **_NOT_FOUND,
        **_STALE,
        409: {"description": "Its subject is retired; restore that first (`PARENT_DEPRECATED`)"},
    },
)
def restore_concept(
    concept_id: UUID,
    principal: CurrentPrincipal,
    request: Request,
    response: Response,
    database: Annotated[Database, Depends(get_database)],
    if_match: Annotated[str | None, IfMatchHeader] = None,
) -> ConceptOut:
    return _set_state(concept_id, "ACTIVE", principal, request, response, database, if_match)
