from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from qbank.core.auth import CurrentPrincipal
from qbank.core.db import Database, get_database
from qbank.core.pagination import DEFAULT_LIMIT, MAX_LIMIT, PageInfo, decode_cursor, encode_cursor
from qbank.modules.questions.public import State
from qbank.modules.review import service
from qbank.modules.review.schemas import QueueCounts, QueueItem, QueuePage, QueueState

router = APIRouter(prefix="/api/v1/review", tags=["review"])

_WHO = (
    "For people who hold at least one of the QC, approve and publish grants, and for admins."
    " A question that is still a draft, or that came back to someone else, is never shown."
)
_DENIED: dict[int | str, dict[str, Any]] = {
    403: {"description": "You hold no review grant (`PERMISSION_DENIED`)"}
}
_MAX_CURSOR_LENGTH = 200


@router.get(
    "/queue",
    summary="The review queue, oldest first (E-05)",
    description=f"What waits for QC, approval or publication, the longest-waiting first. {_WHO}"
    " `state` picks one view; `CHANGES_REQUESTED` is the questions you sent in that came back,"
    " and it is yours alone. Left out, you get everything that waits. Each row is the newest"
    " version of its question; a correction shows as version 2 or more. The labels and"
    " language are those of the text the reviewers act on. `author_id` is whoever sent that"
    " version in.",
    responses=_DENIED,
)
def get_queue(
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
    state: QueueState | None = None,
    subject_id: UUID | None = None,
    chapter_id: UUID | None = None,
    author_id: UUID | None = None,
    language: Annotated[
        str | None,
        Query(
            max_length=20,
            pattern=r"^[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8})*$",
            description="A language code such as `en` or `hi`.",
        ),
    ] = None,
    older_than_days: Annotated[
        int | None,
        Query(ge=1, le=3650, description="Only what has waited at least this many days."),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
    cursor: Annotated[str | None, Query(max_length=_MAX_CURSOR_LENGTH)] = None,
) -> QueuePage:
    after = decode_cursor(cursor) if cursor is not None else None
    with database.transaction(principal.tenant_context) as session:
        rows, has_more = service.queue(
            session,
            principal,
            state=State(state.value) if state is not None else None,
            subject_id=subject_id,
            chapter_id=chapter_id,
            author_id=author_id,
            language=language,
            older_than_days=older_than_days,
            limit=limit,
            after=after,
        )
        data = [
            QueueItem(
                question_id=row.question_id,
                code=row.code,
                question_type=row.question_type,
                language=row.language,
                subject_id=row.subject_id,
                chapter_id=row.chapter_id,
                state=QueueState(row.state.value),
                version_number=row.version_number,
                submitted_by=row.submitted_by,
                waiting_since=row.waiting_since,
            )
            for row in rows
        ]
    next_cursor = (
        encode_cursor(rows[-1].waiting_since, rows[-1].question_id) if has_more and rows else None
    )
    return QueuePage(data=data, page=PageInfo(next_cursor=next_cursor, has_more=has_more))


@router.get(
    "/queue/counts",
    summary="How many wait at each step",
    description=f"The size of each tab of the queue, not narrowed by any filter. {_WHO}",
    responses=_DENIED,
)
def get_counts(
    principal: CurrentPrincipal, database: Annotated[Database, Depends(get_database)]
) -> QueueCounts:
    with database.transaction(principal.tenant_context) as session:
        found = service.counts(session, principal)
    return QueueCounts(
        waiting_for_qc=found.waiting_for_qc,
        waiting_for_approval=found.waiting_for_approval,
        waiting_to_publish=found.waiting_to_publish,
        returned_to_me=found.returned_to_me,
    )
