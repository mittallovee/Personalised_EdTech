"""Routes for passages: start one, read it, autosave it, checkpoint it (M3 design note §5.6)."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status

from qbank.core.auth import CurrentPrincipal
from qbank.core.db import Database, get_database
from qbank.core.etag import IfMatchHeader, etag
from qbank.core.idempotency import IdempotencyKeyHeader
from qbank.core.pagination import DEFAULT_LIMIT, MAX_LIMIT, PageInfo, decode_cursor, encode_cursor
from qbank.modules.questions import passage_service as service
from qbank.modules.questions.models import PassageRevision
from qbank.modules.questions.schemas import (
    CreatePassage,
    FindingOut,
    PassageCheckpointOut,
    PassageOut,
    PassagePage,
    PassageRevisionList,
    PassageRevisionOut,
    PassageRevisionSummary,
    PassageSummary,
    SavePassage,
)

router = APIRouter(prefix="/api/v1/passages", tags=["passages"])
checkpoints_router = APIRouter(prefix="/api/v1/passage-revisions", tags=["passages"])

_DENIED: dict[int | str, dict[str, Any]] = {
    403: {"description": "Your role may not do this (`PERMISSION_DENIED`)"}
}
_NOT_FOUND: dict[int | str, dict[str, Any]] = {
    404: {
        "description": "No such passage that you may open. Someone else's draft is also 404,"
        " so its existence is not given away (`NOT_FOUND`)"
    }
}
_STALE: dict[int | str, dict[str, Any]] = {
    412: {"description": "Changed since you read it; reload (`REVISION_STALE`)"},
    428: {"description": "`If-Match` is missing (`IF_MATCH_REQUIRED`)"},
}
_MAX_CURSOR_LENGTH = 200


def _checkpoint(revision: PassageRevision | None) -> PassageCheckpointOut | None:
    if revision is None or revision.frozen_at is None:
        return None
    return PassageCheckpointOut(
        id=revision.id, number=revision.number, frozen_at=revision.frozen_at
    )


def _findings(found: list[Any]) -> list[FindingOut]:
    return [FindingOut(path=f.path, code=f.code, level=f.level, message=f.message) for f in found]


def _out(view: service.PassageView) -> PassageOut:
    return PassageOut(
        id=view.passage.id,
        working_revision_id=view.revision.id,
        revision=view.revision.revision,
        created_by=view.passage.created_by,
        created_at=view.passage.created_at,
        updated_at=view.revision.updated_at,
        latest_checkpoint=_checkpoint(view.latest_checkpoint),
        content=view.revision.content,
        findings=_findings(view.findings),
    )


def _revision_summary(revision: PassageRevision) -> PassageRevisionSummary:
    return PassageRevisionSummary(
        id=revision.id,
        number=revision.number,
        working=revision.frozen_at is None,
        author_id=revision.author_id,
        content_hash=revision.content_hash,
        frozen_at=revision.frozen_at,
        created_at=revision.created_at,
        updated_at=revision.updated_at,
    )


def _title(content: dict[str, Any]) -> str:
    title = content.get("title")
    return title if isinstance(title, str) else ""


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Start a passage",
    description="Anyone in the coaching. A passage is shared text that several questions sit"
    " under; it has no public code. Leave `content` out to start an empty one. Send an"
    " `Idempotency-Key` so a retry after a lost response returns the same passage.",
    responses={
        **_DENIED,
        409: {"description": "The Idempotency-Key was used for a different request"},
        422: {
            "description": "Too large (`CONTENT_TOO_LARGE`) or not plain data (`CONTENT_NOT_JSON`)"
        },
    },
)
def create_passage(
    body: CreatePassage,
    principal: CurrentPrincipal,
    request: Request,
    response: Response,
    database: Annotated[Database, Depends(get_database)],
    idempotency_key: Annotated[str | None, IdempotencyKeyHeader] = None,
) -> PassageOut:
    with database.transaction(principal.tenant_context) as session:
        view = service.create_passage(
            session,
            principal,
            body.content,
            idempotency_key=idempotency_key,
            request_id=request.state.request_id,
        )
        result = _out(view)
    response.headers["Location"] = f"{router.prefix}/{result.id}"
    response.headers["ETag"] = etag(result.revision)
    return result


@router.get(
    "",
    summary="Passages you may open, newest first",
    description="Your own drafts; admins and people with the edit-others grant see every passage"
    " in the coaching (`mine=true` narrows it to their own).",
    responses=_DENIED,
)
def list_passages(
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
    mine: bool = False,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
    cursor: Annotated[str | None, Query(max_length=_MAX_CURSOR_LENGTH)] = None,
) -> PassagePage:
    after = decode_cursor(cursor) if cursor is not None else None
    with database.transaction(principal.tenant_context) as session:
        rows, has_more = service.list_passages(
            session, principal, mine_only=mine, limit=limit, after=after
        )
        data = [
            PassageSummary(
                id=passage.id,
                title=_title(revision.content),
                created_by=passage.created_by,
                created_at=passage.created_at,
                updated_at=revision.updated_at,
                latest_checkpoint_number=number,
            )
            for passage, revision, number in rows
        ]
        next_cursor = (
            encode_cursor(rows[-1][0].created_at, rows[-1][0].id) if has_more and rows else None
        )
    return PassagePage(data=data, page=PageInfo(next_cursor=next_cursor, has_more=has_more))


@router.get(
    "/{passage_id}",
    summary="One passage",
    description="The ETag is the working revision, for the changes that need `If-Match`.",
    responses={**_DENIED, **_NOT_FOUND},
)
def get_passage(
    passage_id: UUID,
    principal: CurrentPrincipal,
    response: Response,
    database: Annotated[Database, Depends(get_database)],
) -> PassageOut:
    with database.transaction(principal.tenant_context) as session:
        result = _out(service.get_passage(session, principal, passage_id))
    response.headers["ETag"] = etag(result.revision)
    return result


@router.put(
    "/{passage_id}/working-revision",
    summary="Autosave: replace the working content",
    description="Send the whole content and the ETag you last read in `If-Match`. A save from a"
    " stale screen is refused (412) instead of overwriting newer work. Gaps and mistakes are"
    " saved and come back as findings.",
    responses={**_DENIED, **_NOT_FOUND, **_STALE},
)
def save_working_revision(
    passage_id: UUID,
    body: SavePassage,
    principal: CurrentPrincipal,
    response: Response,
    database: Annotated[Database, Depends(get_database)],
    if_match: Annotated[str | None, IfMatchHeader] = None,
) -> PassageOut:
    with database.transaction(principal.tenant_context) as session:
        view = service.save_working_revision(
            session, principal, passage_id, body.content, if_match=if_match
        )
        result = _out(view)
    response.headers["ETag"] = etag(result.revision)
    return result


@router.post(
    "/{passage_id}/checkpoints",
    status_code=status.HTTP_201_CREATED,
    summary="Save a checkpoint",
    description="Freezes the working revision for good (with a hash of its content) and starts a"
    " new working revision as a copy. The answer is that new working revision, whose"
    " `latest_checkpoint` is the revision just frozen: the one a child question pins.",
    responses={**_DENIED, **_NOT_FOUND, **_STALE},
)
def save_checkpoint(
    passage_id: UUID,
    principal: CurrentPrincipal,
    request: Request,
    response: Response,
    database: Annotated[Database, Depends(get_database)],
    if_match: Annotated[str | None, IfMatchHeader] = None,
) -> PassageOut:
    with database.transaction(principal.tenant_context) as session:
        view, frozen = service.checkpoint(
            session,
            principal,
            passage_id,
            if_match=if_match,
            request_id=request.state.request_id,
        )
        result = _out(view)
    response.headers["Location"] = f"{checkpoints_router.prefix}/{frozen.id}"
    response.headers["ETag"] = etag(result.revision)
    return result


@router.get(
    "/{passage_id}/revisions",
    summary="The saved revisions, newest first",
    description="The working revision first, then the checkpoints.",
    responses={**_DENIED, **_NOT_FOUND},
)
def list_revisions(
    passage_id: UUID,
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
) -> PassageRevisionList:
    with database.transaction(principal.tenant_context) as session:
        revisions = service.list_revisions(session, principal, passage_id)
        return PassageRevisionList(data=[_revision_summary(r) for r in revisions])


@checkpoints_router.get(
    "/{revision_id}",
    summary="One checkpoint of a passage, by its id",
    description="What a child question pins in `context.passage_revision_id`. Any member of the"
    " coaching may read it, because the questions under it show it; a draft (working) revision"
    " is not served here and answers 404.",
    responses={
        **_DENIED,
        404: {"description": "No such checkpoint in your coaching (`NOT_FOUND`)"},
    },
)
def get_checkpoint(
    revision_id: UUID,
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
) -> PassageRevisionOut:
    with database.transaction(principal.tenant_context) as session:
        revision, found = service.get_checkpoint(session, principal, revision_id)
        summary = _revision_summary(revision)
        return PassageRevisionOut(
            **summary.model_dump(),
            passage_id=revision.passage_id,
            content=revision.content,
            findings=_findings(found),
        )
