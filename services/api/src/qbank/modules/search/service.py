"""Reading the bank: the list with its filters and total, and one question by its code (F-01, F-02).

What a person may see is decided in the query, once, by ``_readable``: work in progress (a draft, a
returned question) is read by its author, admins and edit-others holders, and to anyone else it does
not exist, so it is never listed, counted or found by its code. The rule is the questions module's
(``questions/visibility.py``), written here over the row's own ``is_private`` and ``created_by``; a
test checks that the two agree for every state and role.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import ColumnElement, false, func, or_, select, true, tuple_
from sqlalchemy.orm import Session

from qbank.core.auth import Principal
from qbank.core.codes import normalize_code
from qbank.core.errors import NotFound
from qbank.core.permissions import Action, is_allowed, may_access_all_drafts, require
from qbank.modules.search.models import BankRow


@dataclass(frozen=True, slots=True)
class BankFilters:
    """What to narrow the bank by. Filters combine with AND; the values of one filter with OR, and
    a left-out filter does not narrow. ``archived`` picks the archive instead of the live bank."""

    class_ids: tuple[UUID, ...] = ()
    subject_ids: tuple[UUID, ...] = ()
    chapter_ids: tuple[UUID, ...] = ()
    topic_ids: tuple[UUID, ...] = ()
    concept_ids: tuple[UUID, ...] = ()  # the main concept or any other concept
    difficulties: tuple[int, ...] = ()
    bloom_levels: tuple[str, ...] = ()
    question_types: tuple[str, ...] = ()
    languages: tuple[str, ...] = ()
    exam_ids: tuple[UUID, ...] = ()
    exam_years: tuple[int, ...] = ()
    states: tuple[str, ...] = ()
    author_ids: tuple[UUID, ...] = ()
    is_pyq: bool | None = None
    has_solution: bool | None = None
    has_video: bool | None = None
    archived: bool = False


@dataclass(frozen=True, slots=True)
class BankPage:
    rows: list[BankRow]
    has_more: bool
    total: int


def _readable(principal: Principal) -> ColumnElement[bool]:
    if not is_allowed(principal, Action.CREATE_QUESTIONS):
        return false()
    if may_access_all_drafts(principal):
        return true()
    return or_(BankRow.is_private.is_(False), BankRow.created_by == principal.user_id)


def _conditions(principal: Principal, filters: BankFilters) -> list[ColumnElement[bool]]:
    organization_id = principal.tenant_context.organization_id
    if organization_id is None:  # the permission check already refuses this
        raise NotFound("No such question.")
    # Row-level security already keeps to this coaching; saying so here as well costs nothing.
    found = [
        BankRow.organization_id == organization_id,
        _readable(principal),
        BankRow.is_archived.is_(filters.archived),
    ]
    one_of: list[tuple[Any, tuple[Any, ...]]] = [
        (BankRow.class_id, filters.class_ids),
        (BankRow.subject_id, filters.subject_ids),
        (BankRow.chapter_id, filters.chapter_ids),
        (BankRow.topic_id, filters.topic_ids),
        (BankRow.difficulty, filters.difficulties),
        (BankRow.bloom_level, filters.bloom_levels),
        (BankRow.question_type, filters.question_types),
        (BankRow.language, tuple(value.lower() for value in filters.languages)),
        (BankRow.exam_id, filters.exam_ids),
        (BankRow.exam_year, filters.exam_years),
        (BankRow.state, filters.states),
        (BankRow.created_by, filters.author_ids),
    ]
    found += [column.in_(values) for column, values in one_of if values]
    if filters.concept_ids:
        found.append(BankRow.concept_ids.overlap(list(filters.concept_ids)))
    flags = (
        (BankRow.is_pyq, filters.is_pyq),
        (BankRow.has_solution, filters.has_solution),
        (BankRow.has_video, filters.has_video),
    )
    found += [column.is_(wanted) for column, wanted in flags if wanted is not None]
    return found


def list_bank(
    session: Session,
    principal: Principal,
    filters: BankFilters,
    *,
    limit: int,
    after: tuple[datetime, UUID] | None,
) -> BankPage:
    """One page of the bank, the most recently changed first, after ``after`` (a cursor), with the
    number of questions that match the same filters and visibility, so the number on the screen is
    the number of matches."""
    require(principal, Action.CREATE_QUESTIONS)
    where = _conditions(principal, filters)
    total = session.scalar(select(func.count()).select_from(BankRow).where(*where)) or 0
    query = select(BankRow).where(*where)
    if after is not None:
        query = query.where(tuple_(BankRow.updated_at, BankRow.master_id) < after)
    found = list(
        session.scalars(
            query.order_by(BankRow.updated_at.desc(), BankRow.master_id.desc()).limit(limit + 1)
        )
    )
    return BankPage(rows=found[:limit], has_more=len(found) > limit, total=total)


def find_by_code(session: Session, principal: Principal, typed_code: str) -> BankRow:
    """The question with this code (lower case, spaces and dashes forgiven). Another coaching's
    code, a missing one and a private draft that is not yours answer the same: not found."""
    require(principal, Action.CREATE_QUESTIONS)
    code = normalize_code(typed_code)
    row = session.scalars(
        select(BankRow).where(*_conditions(principal, BankFilters()), BankRow.code == code)
    ).first()
    if row is None:
        # An archived question is still found by its code: a person pasting a code wants it.
        row = session.scalars(
            select(BankRow).where(
                *_conditions(principal, BankFilters(archived=True)), BankRow.code == code
            )
        ).first()
    if row is None:
        raise NotFound("No such question.")
    return row
