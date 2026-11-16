"""The shared review queue and its counts (M4 design note §5 and §10, E-05).

The queue is the newest version of each question that waits for a step: in review, passed QC, or
approved. A fourth view, "returned", lists what the caller sent in that came back; it is theirs
alone, because a returned question is its author's work in progress again. Oldest first, because
what has waited longest is reviewed first.

Who may see the queue at all is decided by the caller (``may_see_review_queue``). What each row may
show is decided here by the same visibility condition every list uses, and the author is whoever
sent that version in (the actor of its latest submit), which for a correction is whoever started it.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import ColumnElement, Select, and_, func, or_, select, tuple_
from sqlalchemy.orm import Session, aliased

from qbank.core.auth import Principal
from qbank.modules.questions.blocks import as_dict
from qbank.modules.questions.domain.workflow import State, Step
from qbank.modules.questions.models import (
    QuestionMaster,
    QuestionRevision,
    QuestionVersion,
    ReviewDecision,
)
from qbank.modules.questions.visibility import readable

# The states a reviewer works through, in the order a question passes them.
QUEUE_STATES = (State.IN_REVIEW, State.QC_PASSED, State.APPROVED)
_WAITING = [state.value for state in QUEUE_STATES]


@dataclass(frozen=True, slots=True)
class QueueFilters:
    """What to narrow the queue by. ``state`` is one of the queue states or ``CHANGES_REQUESTED``
    (the caller's own returned questions); left out, the queue is everything that waits."""

    state: State | None = None
    subject_id: UUID | None = None
    chapter_id: UUID | None = None
    author_id: UUID | None = None
    language: str | None = None
    older_than_days: int | None = None


@dataclass(frozen=True, slots=True)
class QueueRow:
    question_id: UUID
    code: str
    question_type: str | None
    language: str | None
    subject_id: UUID | None
    chapter_id: UUID | None
    state: State
    version_number: int
    submitted_by: UUID
    waiting_since: datetime


@dataclass(frozen=True, slots=True)
class QueueCounts:
    waiting_for_qc: int
    waiting_for_approval: int
    waiting_to_publish: int
    returned_to_me: int


def _submitted_by() -> ColumnElement[UUID]:
    """Who sent this version in: the actor of its latest submit; the question's first author if
    no submit is recorded."""
    latest = (
        select(ReviewDecision.actor_id)
        .where(
            ReviewDecision.version_id == QuestionVersion.id,
            ReviewDecision.step == Step.SUBMIT.value,
        )
        .order_by(ReviewDecision.flow_revision.desc())
        .limit(1)
        .correlate(QuestionVersion)
        .scalar_subquery()
    )
    return func.coalesce(latest, QuestionMaster.created_by)


def _newest_readable(principal: Principal) -> Select[QuestionMaster, QuestionVersion]:
    """The newest version of each question the caller may read, leaving out archived questions."""
    other = aliased(QuestionVersion)
    newest = (
        select(func.max(other.number)).where(other.master_id == QuestionMaster.id).scalar_subquery()
    )
    return (
        select(QuestionMaster, QuestionVersion)
        .join(QuestionVersion, QuestionVersion.master_id == QuestionMaster.id)
        .where(
            QuestionVersion.number == newest,
            QuestionMaster.archived_at.is_(None),
            readable(principal),
        )
    )


def _returned_to(principal: Principal) -> ColumnElement[bool]:
    return and_(
        QuestionVersion.state == State.CHANGES_REQUESTED.value,
        _submitted_by() == principal.user_id,
    )


def _in_view(principal: Principal, state: State | None) -> ColumnElement[bool]:
    if state is None:
        return QuestionVersion.state.in_(_WAITING)
    if state is State.CHANGES_REQUESTED:
        return _returned_to(principal)
    if state in QUEUE_STATES:
        return QuestionVersion.state == state.value
    raise ValueError(f"{state.value} is not a queue state")


def _text(content: object, *path: str) -> str | None:
    """A string at ``path`` in the content, or None. Content is whatever the author saved, so
    nothing here may assume its shape."""
    value: object = content
    for key in path:
        node = as_dict(value)
        if node is None:
            return None
        value = node.get(key)
    return value if isinstance(value, str) else None


def _uuid(value: str | None) -> UUID | None:
    if value is None:
        return None
    try:
        return UUID(value)
    except ValueError:
        return None


def _field(*path: str) -> ColumnElement[str]:
    """The text at ``path`` in a revision's content, as the database reads it (lower case, so
    ids and language codes compare whatever case they were typed in)."""
    return func.lower(func.jsonb_extract_path_text(QuestionRevision.content, *path))


def _narrowed(
    query: Select[Any], principal: Principal, filters: QueueFilters, now: datetime
) -> Select[Any]:
    query = query.where(_in_view(principal, filters.state))
    if filters.subject_id is not None:
        query = query.where(_field("metadata", "subject_id") == str(filters.subject_id))
    if filters.chapter_id is not None:
        query = query.where(_field("metadata", "chapter_id") == str(filters.chapter_id))
    if filters.author_id is not None:
        query = query.where(_submitted_by() == filters.author_id)
    if filters.language is not None:
        query = query.where(_field("language") == filters.language.lower())
    if filters.older_than_days is not None:
        cutoff = now - timedelta(days=filters.older_than_days)
        query = query.where(QuestionVersion.state_changed_at <= cutoff)
    return query


def list_queue(
    session: Session,
    principal: Principal,
    filters: QueueFilters,
    *,
    limit: int,
    after: tuple[datetime, UUID] | None,
) -> tuple[list[QueueRow], bool]:
    """One page of the queue, oldest waiting first, after ``after`` (a cursor); and whether more
    follow. The labels and language are read from the text the reviewers act on: the frozen
    review revision, or for a returned question the author's working copy."""
    shown = and_(
        QuestionRevision.version_id == QuestionVersion.id,
        or_(
            QuestionRevision.id == QuestionVersion.review_revision_id,
            and_(
                QuestionVersion.review_revision_id.is_(None), QuestionRevision.frozen_at.is_(None)
            ),
        ),
    )
    query = (
        _newest_readable(principal)
        .join(QuestionRevision, shown)
        .add_columns(QuestionRevision.content, _submitted_by().label("submitted_by"))
    )
    query = _narrowed(query, principal, filters, datetime.now(UTC))
    if after is not None:
        query = query.where(tuple_(QuestionVersion.state_changed_at, QuestionMaster.id) > after)
    query = query.order_by(QuestionVersion.state_changed_at, QuestionMaster.id).limit(limit + 1)
    found = session.execute(query).all()
    rows = [
        QueueRow(
            question_id=master.id,
            code=master.code,
            question_type=_text(content, "question_type"),
            language=_text(content, "language"),
            subject_id=_uuid(_text(content, "metadata", "subject_id")),
            chapter_id=_uuid(_text(content, "metadata", "chapter_id")),
            state=State(version.state),
            version_number=version.number,
            submitted_by=submitted_by,
            waiting_since=version.state_changed_at,
        )
        for master, version, content, submitted_by in found[:limit]
    ]
    return rows, len(found) > limit


def queue_counts(session: Session, principal: Principal) -> QueueCounts:
    """How many wait at each step, and how many of the caller's own came back. Not narrowed by
    the filters: it is the size of each tab."""
    query = (
        _newest_readable(principal)
        .where(or_(QuestionVersion.state.in_(_WAITING), _returned_to(principal)))
        .with_only_columns(QuestionVersion.state, func.count(), maintain_column_froms=True)
        .group_by(QuestionVersion.state)
    )
    by_state = {state: count for state, count in session.execute(query).all()}
    return QueueCounts(
        waiting_for_qc=by_state.get(State.IN_REVIEW.value, 0),
        waiting_for_approval=by_state.get(State.QC_PASSED.value, 0),
        waiting_to_publish=by_state.get(State.APPROVED.value, 0),
        returned_to_me=by_state.get(State.CHANGES_REQUESTED.value, 0),
    )
