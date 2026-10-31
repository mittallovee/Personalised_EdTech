"""Routes for questions: start one, read it by id or by code, list the ones you may open."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, Request, Response, status

from qbank.core.auth import CurrentPrincipal
from qbank.core.db import Database, get_database
from qbank.core.etag import IfMatchHeader, etag
from qbank.core.idempotency import IdempotencyKeyHeader
from qbank.core.pagination import DEFAULT_LIMIT, MAX_LIMIT, PageInfo, decode_cursor, encode_cursor
from qbank.modules.questions import service
from qbank.modules.questions.findings import Level
from qbank.modules.questions.schemas import (
    CreateQuestion,
    FindingCounts,
    FindingOut,
    QuestionOut,
    QuestionPage,
    QuestionSummary,
    RevisionList,
    RevisionOut,
    RevisionSummary,
    SaveQuestion,
)

router = APIRouter(prefix="/api/v1/questions", tags=["questions"])

_DENIED: dict[int | str, dict[str, Any]] = {
    403: {"description": "Your role may not do this (`PERMISSION_DENIED`)"}
}
_NOT_FOUND: dict[int | str, dict[str, Any]] = {
    404: {
        "description": "No such question that you may open. Someone else's draft is also 404,"
        " so its existence is not given away (`NOT_FOUND`)"
    }
}
_STALE: dict[int | str, dict[str, Any]] = {
    412: {"description": "Changed since you read it; reload (`REVISION_STALE`)"},
    428: {"description": "`If-Match` is missing (`IF_MATCH_REQUIRED`)"},
}
_ARCHIVED: dict[int | str, dict[str, Any]] = {
    409: {"description": "The question is archived (`QUESTION_ARCHIVED`)"}
}
_MAX_CURSOR_LENGTH = 200


def _out(view: service.QuestionView) -> QuestionOut:
    return QuestionOut(
        id=view.master.id,
        code=view.master.code,
        version_number=view.version.number,
        revision=view.revision.revision,
        archived=view.master.archived_at is not None,
        created_by=view.master.created_by,
        created_at=view.master.created_at,
        updated_at=view.revision.updated_at,
        content=view.revision.content,
        findings=[
            FindingOut(path=f.path, code=f.code, level=f.level, message=f.message)
            for f in view.findings
        ],
    )


def _revision_summary(version_number: int, revision: Any) -> RevisionSummary:
    return RevisionSummary(
        number=revision.number,
        working=revision.frozen_at is None,
        version_number=version_number,
        author_id=revision.author_id,
        content_hash=revision.content_hash,
        frozen_at=revision.frozen_at,
        created_at=revision.created_at,
        updated_at=revision.updated_at,
    )


def _summary(view: service.QuestionView) -> QuestionSummary:
    question_type = view.revision.content.get("question_type")
    return QuestionSummary(
        id=view.master.id,
        code=view.master.code,
        question_type=question_type if isinstance(question_type, str) else None,
        archived=view.master.archived_at is not None,
        created_by=view.master.created_by,
        created_at=view.master.created_at,
        updated_at=view.revision.updated_at,
        finding_counts=FindingCounts(
            error=sum(f.level == Level.ERROR for f in view.findings),
            incomplete=sum(f.level == Level.INCOMPLETE for f in view.findings),
            warning=sum(f.level == Level.WARNING for f in view.findings),
        ),
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Start a question",
    description="Anyone in the coaching. A draft with gaps is saved; the findings in the answer"
    " say what is missing. Send an `Idempotency-Key` so a retry after a lost response returns"
    " the same question instead of making a second one.",
    responses={
        **_DENIED,
        409: {"description": "The Idempotency-Key was used for a different request"},
        422: {
            "description": "Too large (`CONTENT_TOO_LARGE`) or not plain data (`CONTENT_NOT_JSON`)"
        },
    },
)
def create_question(
    body: CreateQuestion,
    principal: CurrentPrincipal,
    request: Request,
    response: Response,
    database: Annotated[Database, Depends(get_database)],
    idempotency_key: Annotated[str | None, IdempotencyKeyHeader] = None,
) -> QuestionOut:
    with database.transaction(principal.tenant_context) as session:
        view = service.create_question(
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
    summary="Questions you may open, newest first",
    description="Your own drafts; admins and people with the edit-others grant see every draft"
    " in the coaching (`mine=true` narrows it to their own). Each row carries the number of"
    " findings by level; open a question for the findings themselves.",
    responses=_DENIED,
)
def list_questions(
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
    mine: bool = False,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
    cursor: Annotated[str | None, Query(max_length=_MAX_CURSOR_LENGTH)] = None,
) -> QuestionPage:
    after = decode_cursor(cursor) if cursor is not None else None
    with database.transaction(principal.tenant_context) as session:
        views, has_more = service.list_questions(
            session, principal, mine_only=mine, limit=limit, after=after
        )
        data = [_summary(view) for view in views]
        next_cursor = (
            encode_cursor(views[-1].master.created_at, views[-1].master.id)
            if has_more and views
            else None
        )
    return QuestionPage(data=data, page=PageInfo(next_cursor=next_cursor, has_more=has_more))


@router.get(
    "/by-code/{code}",
    summary="One question, found by its code",
    description="Typed codes are forgiven: lower case, spaces and dashes are fine.",
    responses={**_DENIED, **_NOT_FOUND, 422: {"description": "Not a code (`INVALID_CODE`)"}},
)
def get_question_by_code(
    code: Annotated[str, Path(max_length=40)],
    principal: CurrentPrincipal,
    response: Response,
    database: Annotated[Database, Depends(get_database)],
) -> QuestionOut:
    with database.transaction(principal.tenant_context) as session:
        result = _out(service.get_question_by_code(session, principal, code))
    response.headers["ETag"] = etag(result.revision)
    return result


@router.get(
    "/{question_id}",
    summary="One question",
    description="The ETag is the working revision, for the changes that need `If-Match`.",
    responses={**_DENIED, **_NOT_FOUND},
)
def get_question(
    question_id: UUID,
    principal: CurrentPrincipal,
    response: Response,
    database: Annotated[Database, Depends(get_database)],
) -> QuestionOut:
    with database.transaction(principal.tenant_context) as session:
        result = _out(service.get_question(session, principal, question_id))
    response.headers["ETag"] = etag(result.revision)
    return result


@router.put(
    "/{question_id}/working-revision",
    summary="Autosave: replace the working content",
    description="Send the whole content and the ETag you last read in `If-Match`. A save from a"
    " stale screen is refused (412) instead of overwriting newer work. Gaps and mistakes are"
    " saved and come back as findings. Not written to the audit log (it would bury it).",
    responses={**_DENIED, **_NOT_FOUND, **_STALE, **_ARCHIVED},
)
def save_working_revision(
    question_id: UUID,
    body: SaveQuestion,
    principal: CurrentPrincipal,
    response: Response,
    database: Annotated[Database, Depends(get_database)],
    if_match: Annotated[str | None, IfMatchHeader] = None,
) -> QuestionOut:
    with database.transaction(principal.tenant_context) as session:
        view = service.save_working_revision(
            session, principal, question_id, body.content, if_match=if_match
        )
        result = _out(view)
    response.headers["ETag"] = etag(result.revision)
    return result


@router.post(
    "/{question_id}/checkpoints",
    status_code=status.HTTP_201_CREATED,
    summary="Save a checkpoint",
    description="Freezes the working revision for good (with a hash of its content) and starts a"
    " new working revision as a copy. The answer is that new working revision; its ETag is for"
    " the next save. `Location` is the frozen revision.",
    responses={**_DENIED, **_NOT_FOUND, **_STALE, **_ARCHIVED},
)
def save_checkpoint(
    question_id: UUID,
    principal: CurrentPrincipal,
    request: Request,
    response: Response,
    database: Annotated[Database, Depends(get_database)],
    if_match: Annotated[str | None, IfMatchHeader] = None,
) -> QuestionOut:
    with database.transaction(principal.tenant_context) as session:
        view, frozen_number = service.checkpoint(
            session,
            principal,
            question_id,
            if_match=if_match,
            request_id=request.state.request_id,
        )
        result = _out(view)
    response.headers["Location"] = f"{router.prefix}/{question_id}/revisions/{frozen_number}"
    response.headers["ETag"] = etag(result.revision)
    return result


@router.get(
    "/{question_id}/revisions",
    summary="The saved revisions, newest first",
    description="The working revision on top, then the checkpoints. Contents are not included;"
    " open one revision for its content.",
    responses={**_DENIED, **_NOT_FOUND},
)
def list_revisions(
    question_id: UUID,
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
) -> RevisionList:
    with database.transaction(principal.tenant_context) as session:
        _, rows = service.list_revisions(session, principal, question_id)
        data = [_revision_summary(version.number, revision) for version, revision in rows]
    return RevisionList(data=data)


@router.get(
    "/{question_id}/revisions/{number}",
    summary="One revision of the current version",
    description="Read-only. Findings are computed as of now, with today's rules.",
    responses={**_DENIED, **_NOT_FOUND},
)
def get_revision(
    question_id: UUID,
    number: Annotated[int, Path(ge=1, le=1_000_000)],
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
) -> RevisionOut:
    with database.transaction(principal.tenant_context) as session:
        view = service.get_revision(session, principal, question_id, number)
        return RevisionOut(
            **_revision_summary(view.version.number, view.revision).model_dump(),
            content=view.revision.content,
            findings=_out(view).findings,
        )
