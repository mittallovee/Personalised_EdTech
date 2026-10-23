"""Routes for exams and sources: everyone in the coaching reads, admins change."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status

from qbank.core.auth import CurrentPrincipal
from qbank.core.db import Database, get_database
from qbank.core.etag import IfMatchHeader, etag
from qbank.core.idempotency import IdempotencyKeyHeader
from qbank.core.pagination import DEFAULT_LIMIT, MAX_LIMIT, PageInfo
from qbank.core.permissions import Action, require
from qbank.modules.taxonomy import catalogue_service as service
from qbank.modules.taxonomy.cursors import MAX_CURSOR_LENGTH, decode_cursor
from qbank.modules.taxonomy.models import Exam, Source
from qbank.modules.taxonomy.schemas import (
    CreateExam,
    CreateSource,
    ExamOut,
    ExamPage,
    NodeState,
    SourceKind,
    SourceOut,
    SourcePage,
    UpdateExam,
    UpdateSource,
)

exams_router = APIRouter(prefix="/api/v1/exams", tags=["exams and sources"])
sources_router = APIRouter(prefix="/api/v1/sources", tags=["exams and sources"])

_DENIED: dict[int | str, dict[str, Any]] = {
    403: {"description": "Your role may not do this (`PERMISSION_DENIED`)"}
}
_NOT_FOUND: dict[int | str, dict[str, Any]] = {
    404: {"description": "No such item in your coaching (`NOT_FOUND`)"}
}
_STALE: dict[int | str, dict[str, Any]] = {
    412: {"description": "Changed by someone else since you read it (`REVISION_STALE`)"},
    428: {"description": "`If-Match` is missing (`IF_MATCH_REQUIRED`)"},
}
_CREATE_CONFLICT: dict[int | str, dict[str, Any]] = {
    409: {
        "description": "Another item has this name (`DUPLICATE_NAME`), or the Idempotency-Key"
        " was used for a different request (`IDEMPOTENCY_KEY_REUSED`)"
    }
}
_RENAME_CONFLICT: dict[int | str, dict[str, Any]] = {
    409: {"description": "Another item has this name (`DUPLICATE_NAME`)"}
}
_NAME_TOO_LONG: dict[int | str, dict[str, Any]] = {
    422: {"description": "The name is too long once normalised for comparing (`NAME_TOO_LONG`)"}
}


def _exam_out(exam: Exam) -> ExamOut:
    return ExamOut(
        id=exam.id,
        name=exam.name,
        short_code=exam.short_code,
        state=exam.state,
        revision=exam.revision,
        created_at=exam.created_at,
        updated_at=exam.updated_at,
    )


def _source_out(source: Source) -> SourceOut:
    return SourceOut(
        id=source.id,
        kind=source.kind,
        name=source.name,
        state=source.state,
        revision=source.revision,
        created_at=source.created_at,
        updated_at=source.updated_at,
    )


def _changes(sent: dict[str, Any]) -> dict[str, Any]:
    """The fields that were sent. A name cannot be cleared, so a null name means "not sent"."""
    return {key: value for key, value in sent.items() if not (key == "name" and value is None)}


# --- Exams ------------------------------------------------------------------------------------


@exams_router.get(
    "",
    summary="Exams, in name order",
    description="Retired exams are included unless you ask for `state=ACTIVE`, which is what a"
    " picker for a new question should do.",
    responses=_DENIED,
)
def list_exams(
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
    exam_state: Annotated[NodeState | None, Query(alias="state")] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
    cursor: Annotated[str | None, Query(max_length=MAX_CURSOR_LENGTH)] = None,
) -> ExamPage:
    require(principal, Action.VIEW_CATALOGUES)
    after = decode_cursor(cursor) if cursor is not None else None
    with database.transaction(principal.tenant_context) as session:
        rows, has_more = service.list_items(
            session, service.EXAMS, state=exam_state, limit=limit, after=after
        )
        data = [_exam_out(row) for row in rows]
    return ExamPage(
        data=data, page=PageInfo(next_cursor=service.next_cursor(rows, has_more), has_more=has_more)
    )


@exams_router.get(
    "/{exam_id}",
    summary="One exam",
    description="The ETag is its revision, for changes that need `If-Match`.",
    responses={**_DENIED, **_NOT_FOUND},
)
def get_exam(
    exam_id: UUID,
    principal: CurrentPrincipal,
    response: Response,
    database: Annotated[Database, Depends(get_database)],
) -> ExamOut:
    require(principal, Action.VIEW_CATALOGUES)
    with database.transaction(principal.tenant_context) as session:
        exam = service.get_item(session, service.EXAMS, exam_id)
        response.headers["ETag"] = etag(exam.revision)
        return _exam_out(exam)


@exams_router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Add an exam",
    description="Owner and admins. Send an `Idempotency-Key` so a retry after a lost response"
    " returns the same exam instead of failing.",
    responses={**_DENIED, **_CREATE_CONFLICT, **_NAME_TOO_LONG},
)
def create_exam(
    body: CreateExam,
    principal: CurrentPrincipal,
    request: Request,
    response: Response,
    database: Annotated[Database, Depends(get_database)],
    idempotency_key: Annotated[str | None, IdempotencyKeyHeader] = None,
) -> ExamOut:
    with database.transaction(principal.tenant_context) as session:
        exam = service.create_item(
            session,
            principal,
            service.EXAMS,
            body.model_dump(),
            idempotency_key=idempotency_key,
            request_id=request.state.request_id,
        )
        result = _exam_out(exam)
    response.headers["Location"] = f"/api/v1/exams/{result.id}"
    response.headers["ETag"] = etag(result.revision)
    return result


@exams_router.patch(
    "/{exam_id}",
    summary="Rename an exam or change its short code",
    description="Send the ETag you last read in `If-Match`.",
    responses={**_DENIED, **_NOT_FOUND, **_STALE, **_RENAME_CONFLICT, **_NAME_TOO_LONG},
)
def update_exam(
    exam_id: UUID,
    body: UpdateExam,
    principal: CurrentPrincipal,
    request: Request,
    response: Response,
    database: Annotated[Database, Depends(get_database)],
    if_match: Annotated[str | None, IfMatchHeader] = None,
) -> ExamOut:
    with database.transaction(principal.tenant_context) as session:
        exam = service.update_item(
            session,
            principal,
            service.EXAMS,
            exam_id,
            _changes(body.model_dump(exclude_unset=True)),
            if_match=if_match,
            request_id=request.state.request_id,
        )
        response.headers["ETag"] = etag(exam.revision)
        return _exam_out(exam)


def _exam_state(
    exam_id: UUID,
    exam_state: str,
    principal: CurrentPrincipal,
    request: Request,
    response: Response,
    database: Database,
    if_match: str | None,
) -> ExamOut:
    with database.transaction(principal.tenant_context) as session:
        exam = service.set_state(
            session,
            principal,
            service.EXAMS,
            exam_id,
            exam_state,
            if_match=if_match,
            request_id=request.state.request_id,
        )
        response.headers["ETag"] = etag(exam.revision)
        return _exam_out(exam)


@exams_router.post(
    "/{exam_id}/deprecate",
    summary="Retire an exam",
    description="It can no longer be chosen for new questions; questions that use it keep it.",
    responses={**_DENIED, **_NOT_FOUND, **_STALE},
)
def deprecate_exam(
    exam_id: UUID,
    principal: CurrentPrincipal,
    request: Request,
    response: Response,
    database: Annotated[Database, Depends(get_database)],
    if_match: Annotated[str | None, IfMatchHeader] = None,
) -> ExamOut:
    return _exam_state(exam_id, "DEPRECATED", principal, request, response, database, if_match)


@exams_router.post(
    "/{exam_id}/restore",
    summary="Bring a retired exam back",
    responses={**_DENIED, **_NOT_FOUND, **_STALE},
)
def restore_exam(
    exam_id: UUID,
    principal: CurrentPrincipal,
    request: Request,
    response: Response,
    database: Annotated[Database, Depends(get_database)],
    if_match: Annotated[str | None, IfMatchHeader] = None,
) -> ExamOut:
    return _exam_state(exam_id, "ACTIVE", principal, request, response, database, if_match)


# --- Sources ----------------------------------------------------------------------------------


@sources_router.get(
    "",
    summary="Sources, in name order",
    description="Filter by `kind`. Retired sources are included unless you ask for `state=ACTIVE`.",
    responses=_DENIED,
)
def list_sources(
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
    kind: SourceKind | None = None,
    source_state: Annotated[NodeState | None, Query(alias="state")] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
    cursor: Annotated[str | None, Query(max_length=MAX_CURSOR_LENGTH)] = None,
) -> SourcePage:
    require(principal, Action.VIEW_CATALOGUES)
    after = decode_cursor(cursor) if cursor is not None else None
    where = (Source.kind == kind,) if kind is not None else ()
    with database.transaction(principal.tenant_context) as session:
        rows, has_more = service.list_items(
            session, service.SOURCES, state=source_state, limit=limit, after=after, where=where
        )
        data = [_source_out(row) for row in rows]
    return SourcePage(
        data=data, page=PageInfo(next_cursor=service.next_cursor(rows, has_more), has_more=has_more)
    )


@sources_router.get(
    "/{source_id}",
    summary="One source",
    description="The ETag is its revision, for changes that need `If-Match`.",
    responses={**_DENIED, **_NOT_FOUND},
)
def get_source(
    source_id: UUID,
    principal: CurrentPrincipal,
    response: Response,
    database: Annotated[Database, Depends(get_database)],
) -> SourceOut:
    require(principal, Action.VIEW_CATALOGUES)
    with database.transaction(principal.tenant_context) as session:
        source = service.get_item(session, service.SOURCES, source_id)
        response.headers["ETag"] = etag(source.revision)
        return _source_out(source)


@sources_router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Add a source",
    description="Owner and admins. Send an `Idempotency-Key` so a retry after a lost response"
    " returns the same source instead of failing.",
    responses={**_DENIED, **_CREATE_CONFLICT, **_NAME_TOO_LONG},
)
def create_source(
    body: CreateSource,
    principal: CurrentPrincipal,
    request: Request,
    response: Response,
    database: Annotated[Database, Depends(get_database)],
    idempotency_key: Annotated[str | None, IdempotencyKeyHeader] = None,
) -> SourceOut:
    with database.transaction(principal.tenant_context) as session:
        source = service.create_item(
            session,
            principal,
            service.SOURCES,
            body.model_dump(),
            idempotency_key=idempotency_key,
            request_id=request.state.request_id,
        )
        result = _source_out(source)
    response.headers["Location"] = f"/api/v1/sources/{result.id}"
    response.headers["ETag"] = etag(result.revision)
    return result


@sources_router.patch(
    "/{source_id}",
    summary="Rename a source",
    description="Send the ETag you last read in `If-Match`. The kind never changes.",
    responses={**_DENIED, **_NOT_FOUND, **_STALE, **_RENAME_CONFLICT, **_NAME_TOO_LONG},
)
def update_source(
    source_id: UUID,
    body: UpdateSource,
    principal: CurrentPrincipal,
    request: Request,
    response: Response,
    database: Annotated[Database, Depends(get_database)],
    if_match: Annotated[str | None, IfMatchHeader] = None,
) -> SourceOut:
    with database.transaction(principal.tenant_context) as session:
        source = service.update_item(
            session,
            principal,
            service.SOURCES,
            source_id,
            _changes(body.model_dump(exclude_unset=True)),
            if_match=if_match,
            request_id=request.state.request_id,
        )
        response.headers["ETag"] = etag(source.revision)
        return _source_out(source)


def _source_state(
    source_id: UUID,
    source_state: str,
    principal: CurrentPrincipal,
    request: Request,
    response: Response,
    database: Database,
    if_match: str | None,
) -> SourceOut:
    with database.transaction(principal.tenant_context) as session:
        source = service.set_state(
            session,
            principal,
            service.SOURCES,
            source_id,
            source_state,
            if_match=if_match,
            request_id=request.state.request_id,
        )
        response.headers["ETag"] = etag(source.revision)
        return _source_out(source)


@sources_router.post(
    "/{source_id}/deprecate",
    summary="Retire a source",
    description="It can no longer be chosen for new questions; questions that use it keep it.",
    responses={**_DENIED, **_NOT_FOUND, **_STALE},
)
def deprecate_source(
    source_id: UUID,
    principal: CurrentPrincipal,
    request: Request,
    response: Response,
    database: Annotated[Database, Depends(get_database)],
    if_match: Annotated[str | None, IfMatchHeader] = None,
) -> SourceOut:
    return _source_state(source_id, "DEPRECATED", principal, request, response, database, if_match)


@sources_router.post(
    "/{source_id}/restore",
    summary="Bring a retired source back",
    responses={**_DENIED, **_NOT_FOUND, **_STALE},
)
def restore_source(
    source_id: UUID,
    principal: CurrentPrincipal,
    request: Request,
    response: Response,
    database: Annotated[Database, Depends(get_database)],
    if_match: Annotated[str | None, IfMatchHeader] = None,
) -> SourceOut:
    return _source_state(source_id, "ACTIVE", principal, request, response, database, if_match)
