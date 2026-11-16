from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query
from pydantic import Field

from qbank.core.auth import CurrentPrincipal
from qbank.core.db import Database, get_database
from qbank.core.pagination import DEFAULT_LIMIT, MAX_LIMIT, PageInfo, decode_cursor, encode_cursor
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
    responses=_DENIED,
)
def list_bank(
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
    after = decode_cursor(cursor) if cursor is not None else None
    with database.transaction(principal.tenant_context) as session:
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
