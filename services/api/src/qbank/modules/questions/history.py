"""A question's history and the difference between two of its texts (M4 design note §8, E-08, E-09).

Both read only the question's own tables (and the audit module's public reader for archive and
restore). What a person may see is decided per version with the same rule as every other read
(``visibility``): the steps of a private correction are not listed to someone who may read only the
published version, and a revision of a version they may not read answers "not found", as if it did
not exist.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from qbank.core.auth import Principal
from qbank.core.errors import NotFound
from qbank.core.permissions import Action, is_allowed
from qbank.modules.audit.public import entity_actions
from qbank.modules.questions.domain.diff import Change, diff_content
from qbank.modules.questions.models import (
    QuestionMaster,
    QuestionRevision,
    QuestionVersion,
    ReviewDecision,
)
from qbank.modules.questions.visibility import may_read_revision, may_read_version

ENTITY_TYPE = "question"


class HistoryKind(StrEnum):
    """What happened. The first and the last two are not review steps; the rest are the ``Step``
    names of the workflow, so a step added there is added here on purpose."""

    CREATED = "CREATED"
    CHECKPOINT = "CHECKPOINT"
    SUBMIT = "SUBMIT"
    RETURN = "RETURN"
    PASS_QC = "PASS_QC"  # noqa: S105 (a step name, not a password)
    APPROVE = "APPROVE"
    PUBLISH = "PUBLISH"
    WITHDRAW = "WITHDRAW"
    START_CORRECTION = "START_CORRECTION"
    ARCHIVED = "ARCHIVED"
    RESTORED = "RESTORED"


# Entries stamped with the same instant (one request writes several) keep this order.
_RANK = {
    HistoryKind.CREATED: 0,
    HistoryKind.CHECKPOINT: 1,
    HistoryKind.ARCHIVED: 3,
    HistoryKind.RESTORED: 3,
}
_AUDIT_KIND = {
    "QUESTION_ARCHIVED": HistoryKind.ARCHIVED,
    "QUESTION_RESTORED": HistoryKind.RESTORED,
}
_CHECKPOINTED = "QUESTION_CHECKPOINTED"


@dataclass(frozen=True, slots=True)
class HistoryItem:
    kind: HistoryKind
    at: datetime
    actor_id: UUID | None
    version_number: int | None
    revision_id: UUID | None  # the frozen revision the entry is about, to compare it with another
    reasons: tuple[str, ...] = ()
    note: str | None = None


@dataclass(frozen=True, slots=True)
class RevisionRef:
    id: UUID
    version_number: int
    number: int
    frozen_at: datetime | None


@dataclass(frozen=True, slots=True)
class Diff:
    before: RevisionRef
    after: RevisionRef
    changes: list[Change]


def _master(session: Session, principal: Principal, question_id: UUID) -> QuestionMaster:
    master = session.get(QuestionMaster, question_id)
    if master is None or not is_allowed(principal, Action.CREATE_QUESTIONS):
        raise NotFound("No such question.")
    return master


def question_history(
    session: Session, principal: Principal, question_id: UUID
) -> list[HistoryItem]:
    """Everything that happened to the question, oldest first, limited to the versions the caller
    may read: its start, each saved checkpoint, every review step (a return with its reasons and
    note), the start of a correction, and archive and restore."""
    master = _master(session, principal, question_id)
    versions = [
        version
        for version in session.scalars(
            select(QuestionVersion)
            .where(QuestionVersion.master_id == master.id)
            .order_by(QuestionVersion.number)
        )
        if may_read_version(principal, master, version)
    ]
    if not versions:
        raise NotFound("No such question.")
    number_of = {version.id: version.number for version in versions}

    decisions = list(
        session.scalars(select(ReviewDecision).where(ReviewDecision.version_id.in_(number_of)))
    )
    # Columns only: a revision's content can be large and the timeline never shows it.
    revisions = session.execute(
        select(
            QuestionRevision.id,
            QuestionRevision.version_id,
            QuestionRevision.number,
            QuestionRevision.frozen_at,
        ).where(QuestionRevision.version_id.in_(number_of))
    ).all()

    items: list[tuple[tuple[datetime, int, str], HistoryItem]] = []

    def add(item: HistoryItem, rank: int, tie: UUID) -> None:
        items.append(((item.at, rank, str(tie)), item))

    if 1 in number_of.values():
        add(
            HistoryItem(HistoryKind.CREATED, master.created_at, master.created_by, 1, None),
            _RANK[HistoryKind.CREATED],
            master.id,
        )
    # A revision is frozen by a checkpoint, or by a step that takes its text into review: those
    # steps show it themselves, so only the rest are checkpoints.
    taken_by_a_step = {decision.revision_id for decision in decisions}
    events = entity_actions(
        session,
        organization_id=master.organization_id,
        entity_type=ENTITY_TYPE,
        entity_id=master.id,
        actions=[*_AUDIT_KIND, _CHECKPOINTED],
    )
    # Who took each checkpoint, from the event written with it: a revision row's ``author_id`` is
    # whoever saved it last, so reading it would credit a later edit's author with the checkpoint.
    # A checkpoint with no such event (taken before the event named its text) has no known actor.
    checkpointed_by = {
        str(event.after["revision_id"]): event.actor_user_id
        for event in events
        if event.action == _CHECKPOINTED and event.after and "revision_id" in event.after
    }
    for row in revisions:
        if row.frozen_at is None or row.id in taken_by_a_step:
            continue
        add(
            HistoryItem(
                HistoryKind.CHECKPOINT,
                row.frozen_at,
                checkpointed_by.get(str(row.id)),
                number_of[row.version_id],
                row.id,
            ),
            _RANK[HistoryKind.CHECKPOINT],
            row.id,
        )
    for decision in decisions:
        add(
            HistoryItem(
                HistoryKind(decision.step),
                decision.created_at,
                decision.actor_id,
                number_of[decision.version_id],
                decision.revision_id,
                reasons=tuple(decision.reasons),
                note=decision.note,
            ),
            2,
            decision.id,
        )
    for event in events:
        if event.action not in _AUDIT_KIND:
            continue
        kind = _AUDIT_KIND[event.action]
        add(HistoryItem(kind, event.at, event.actor_user_id, None, None), _RANK[kind], event.id)
    return [item for _, item in sorted(items, key=lambda pair: pair[0])]


def _readable_revision(
    session: Session, principal: Principal, master: QuestionMaster, revision_id: UUID
) -> tuple[QuestionVersion, QuestionRevision]:
    revision = session.get(QuestionRevision, revision_id)
    version = session.get(QuestionVersion, revision.version_id) if revision is not None else None
    if (
        revision is None
        or version is None
        or version.master_id != master.id
        or not may_read_revision(principal, master, version, revision)
    ):
        raise NotFound("No such revision.")
    return version, revision


def _ref(version: QuestionVersion, revision: QuestionRevision) -> RevisionRef:
    return RevisionRef(revision.id, version.number, revision.number, revision.frozen_at)


def diff_revisions(
    session: Session, principal: Principal, question_id: UUID, before_id: UUID, after_id: UUID
) -> Diff:
    """What changed from one revision of the question to another. Each is checked on its own: a
    revision of a version the caller may not read, or the working text of someone else's draft,
    or one of another question, is "not found"."""
    master = _master(session, principal, question_id)
    old_version, old = _readable_revision(session, principal, master, before_id)
    new_version, new = _readable_revision(session, principal, master, after_id)
    return Diff(
        _ref(old_version, old), _ref(new_version, new), diff_content(old.content, new.content)
    )
