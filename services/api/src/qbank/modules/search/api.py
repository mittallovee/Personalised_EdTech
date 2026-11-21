import math
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, Request
from pydantic import Field

from qbank.core.auth import CurrentPrincipal
from qbank.core.db import Database, get_database
from qbank.core.errors import MalformedRequest, TooManyRequests
from qbank.core.metrics import RATE_LIMITED
from qbank.core.pagination import DEFAULT_LIMIT, MAX_LIMIT, PageInfo, decode_cursor, encode_cursor
from qbank.core.ratelimit import SlidingWindowLimiter
from qbank.modules.search import service
from qbank.modules.search.models import BankRow
from qbank.modules.search.schemas import BankItem, BankPage

router = APIRouter(prefix="/api/v1/bank", tags=["bank"])

_DENIED: dict[int | str, dict[str, Any]] = {
    403: {"description": "You may not use the bank (`PERMISSION_DENIED`)"}
}
_NOT_FOUND: dict[int | str, dict[str, Any]] = {404: {"description": "No such question"}}
_MAX_VALUES = 50
_MAX_CURSOR_LENGTH = 200
_MAX_SEARCH_LENGTH = 200
_Several = Query(max_length=_MAX_VALUES)


def _item(row: BankRow) -> BankItem:
    return BankItem(
        question_id=row.master_id,
        code=row.code,
        author_id=row.created_by,
        state=row.state,
        version_number=row.version_number,
        archived=row.is_archived,
        has_published=row.has_published,
        has_open_correction=row.has_open_correction,
        question_type=row.question_type,
        language=row.language,
        class_id=row.class_id,
        subject_id=row.subject_id,
        chapter_id=row.chapter_id,
        topic_id=row.topic_id,
        primary_concept_id=row.primary_concept_id,
        concept_ids=list(row.concept_ids),
        difficulty=row.difficulty,
        bloom_level=row.bloom_level,
        is_pyq=row.is_pyq,
        exam_id=row.exam_id,
        exam_year=row.exam_year,
        has_solution=row.has_solution,
        has_video=row.has_video,
        preview=row.preview,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.get(
    "/questions",
    summary="The bank: questions with filters and a total (F-01, F-02)",
    description="The most recently changed first. Each question shows the version everyone reads:"
    " the published one if there is one, else the newest. Filters combine with AND; give a filter"
    " several times to match any of its values. `total` counts every match, not only this page."
    " A draft, or a returned question, is listed only to its author, admins and holders of the"
    " edit-others grant; to everyone else it does not exist. `archived=true` lists the archive.",
    responses={
        **_DENIED,
        429: {"description": "Too many searches (`RATE_LIMITED`)"},
        503: {"description": "The search took too long and was stopped (`SEARCH_TIMED_OUT`)"},
    },
)
def list_bank(
    request: Request,
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
    class_id: Annotated[list[UUID] | None, _Several] = None,
    subject_id: Annotated[list[UUID] | None, _Several] = None,
    chapter_id: Annotated[list[UUID] | None, _Several] = None,
    topic_id: Annotated[list[UUID] | None, _Several] = None,
    concept_id: Annotated[
        list[UUID] | None,
        Query(max_length=_MAX_VALUES, description="The main concept or any of the other concepts."),
    ] = None,
    difficulty: Annotated[list[Annotated[int, Field(ge=1, le=10)]] | None, _Several] = None,
    bloom_level: Annotated[
        list[Annotated[str, Field(pattern=r"^[A-Z]{1,20}$")]] | None, _Several
    ] = None,
    question_type: Annotated[
        list[Annotated[str, Field(pattern=r"^[A-Z_]{1,30}$")]] | None, _Several
    ] = None,
    language: Annotated[
        list[Annotated[str, Field(pattern=r"^[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8})*$", max_length=20)]]
        | None,
        _Several,
    ] = None,
    exam_id: Annotated[list[UUID] | None, _Several] = None,
    exam_year: Annotated[list[Annotated[int, Field(ge=1950, le=2100)]] | None, _Several] = None,
    state: Annotated[
        list[Annotated[str, Field(pattern=r"^[A-Z_]{1,20}$")]] | None, _Several
    ] = None,
    author_id: Annotated[list[UUID] | None, _Several] = None,
    is_pyq: bool | None = None,
    has_solution: bool | None = None,
    has_video: bool | None = None,
    archived: Annotated[bool, Query(description="List the archive instead.")] = False,
    q: Annotated[
        str | None,
        Query(
            min_length=1,
            max_length=_MAX_SEARCH_LENGTH,
            description="Words to search for in the stem, options and solution. Quotes match a"
            " phrase, `-word` leaves a word out. Results are ranked, exact words first, then close"
            " words (typos); there is no next page, so give `limit` up to 100 and narrow with"
            " filters. Cannot be combined with `cursor`.",
        ),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
    cursor: Annotated[str | None, Query(max_length=_MAX_CURSOR_LENGTH)] = None,
) -> BankPage:
    filters = service.BankFilters(
        class_ids=tuple(class_id or ()),
        subject_ids=tuple(subject_id or ()),
        chapter_ids=tuple(chapter_id or ()),
        topic_ids=tuple(topic_id or ()),
        concept_ids=tuple(concept_id or ()),
        difficulties=tuple(difficulty or ()),
        bloom_levels=tuple(bloom_level or ()),
        question_types=tuple(question_type or ()),
        languages=tuple(language or ()),
        exam_ids=tuple(exam_id or ()),
        exam_years=tuple(exam_year or ()),
        states=tuple(state or ()),
        author_ids=tuple(author_id or ()),
        is_pyq=is_pyq,
        has_solution=has_solution,
        has_video=has_video,
        archived=archived,
    )
    if q is not None:
        if cursor is not None:
            raise MalformedRequest(
                "A search has no next page. Narrow it with a more specific word or a filter."
            )
        return _search(request, principal, database, filters, q, limit)
    after = decode_cursor(cursor) if cursor is not None else None
    # One snapshot for the count and the page, so `total` is the number of matches of these rows.
    with database.transaction(
        principal.tenant_context, isolation_level="REPEATABLE READ"
    ) as session:
        found = service.list_bank(session, principal, filters, limit=limit, after=after)
        data = [_item(row) for row in found.rows]
    next_cursor = (
        encode_cursor(found.rows[-1].updated_at, found.rows[-1].master_id)
        if found.has_more and found.rows
        else None
    )
    return BankPage(
        data=data,
        page=PageInfo(next_cursor=next_cursor, has_more=found.has_more),
        total=found.total,
    )


def _search(
    request: Request,
    principal: CurrentPrincipal,
    database: Database,
    filters: service.BankFilters,
    q: str,
    limit: int,
) -> BankPage:
    # Before any work is done, so a refused search costs nothing. Counted per signed-in person.
    limiter: SlidingWindowLimiter = request.app.state.search_limiter
    wait = limiter.hit(str(principal.user_id))
    if wait > 0:
        RATE_LIMITED.labels("bank_search").inc()
        raise TooManyRequests(
            "You have searched many times in a short while. Please wait a moment.",
            retry_after_seconds=math.ceil(wait),
        )
    timeout_ms: int = request.app.state.settings.search_timeout_ms
    with database.transaction(
        principal.tenant_context, isolation_level="REPEATABLE READ"
    ) as session:
        found = service.search_bank(
            session, principal, filters, q, limit=limit, timeout_ms=timeout_ms
        )
        data = [_item(row) for row in found.rows]
    return BankPage(
        data=data,
        page=PageInfo(next_cursor=None, has_more=False),
        total=found.total,
        truncated=found.truncated,
    )


@router.get(
    "/questions/by-code/{code}",
    summary="One question of the bank, found by its code (F-02)",
    description="Typed codes are forgiven: lower case, spaces and dashes are fine, and `O`, `I`"
    " and `L` read as `0`, `1` and `1`. Another coaching's code, a code that does not exist and"
    " a private draft that is not yours all answer 404.",
    responses={**_DENIED, **_NOT_FOUND, 422: {"description": "Not a code (`INVALID_CODE`)"}},
)
def get_by_code(
    code: Annotated[str, Path(max_length=40)],
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
) -> BankItem:
    with database.transaction(principal.tenant_context) as session:
        return _item(service.find_by_code(session, principal, code))
