"""Possible duplicates of one question, and what people decided about them (D-16, §7.4).

The text checked is the one a person is looking at: the revision under review (or published) once
the question was submitted, else the working copy of a draft or a returned question, which only
the people who may open drafts can see. A question nobody may open is "not found", as everywhere.
The candidates come from the bank index through ``search.public``, with the bank's visibility rule.

A decision (``NOT_DUPLICATE`` or ``DUPLICATE_OF``) is about one text: it is kept with that text's
duplicate key, and only decisions for the text as it is now count. Pass QC is refused while an
exact match in the shared bank has no "not a duplicate" decision, or when someone marked the
question a duplicate (``qc_blockers``). Nothing is merged or deleted.
"""

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from qbank.core.auth import Principal
from qbank.core.errors import Conflict, NotFound, PermissionDenied, ValidationFailed
from qbank.core.permissions import Action, Grant, has_grant, is_allowed, may_access_draft
from qbank.modules.audit.public import record_event
from qbank.modules.questions.bank_text import bank_text
from qbank.modules.questions.domain.workflow import PRIVATE_STATES
from qbank.modules.questions.duplicate_key import duplicate_key
from qbank.modules.questions.models import (
    DuplicateDecision,
    QuestionMaster,
    QuestionRevision,
    QuestionVersion,
)
from qbank.modules.search.public import (
    DuplicateCandidate,
    find_duplicates,
    shared_codes,
    shared_exact_duplicates,
)

_PRIVATE = [state.value for state in PRIVATE_STATES]


Decision = Literal["NOT_DUPLICATE", "DUPLICATE_OF"]


@dataclass(frozen=True, slots=True)
class DuplicateCheck:
    master: QuestionMaster
    version: QuestionVersion
    revision: QuestionRevision
    candidates: list[DuplicateCandidate]
    decisions: dict[UUID, DuplicateDecision]  # the newest decision per other question, this text
    blockers: list[tuple[UUID, str]]  # what stops Pass QC now: (question, code)


def _checked_text(
    session: Session, principal: Principal, question_id: UUID, *, lock: bool = False
) -> tuple[QuestionMaster, QuestionVersion, QuestionRevision]:
    # A decision locks the question first, as every change does, so it cannot interleave with a
    # Pass QC of the same question.
    by_id = select(QuestionMaster).where(QuestionMaster.id == question_id)
    master = session.scalars(by_id.with_for_update() if lock else by_id).first()
    if master is None or not is_allowed(principal, Action.CREATE_QUESTIONS):
        raise NotFound("No such question.")
    drafts = may_access_draft(principal, master.created_by)
    query = (
        select(QuestionVersion)
        .where(QuestionVersion.master_id == master.id)
        .order_by(QuestionVersion.number.desc())
        .limit(1)
    )
    if not drafts:
        query = query.where(QuestionVersion.state.not_in(_PRIVATE))
    version = session.scalars(query).first()
    if version is None:
        raise NotFound("No such question.")
    revision: QuestionRevision | None
    if version.review_revision_id is not None:
        revision = session.get(QuestionRevision, version.review_revision_id)
    else:  # a draft or a returned question: only people who may open drafts got this far
        revision = session.scalars(
            select(QuestionRevision).where(
                QuestionRevision.version_id == version.id, QuestionRevision.frozen_at.is_(None)
            )
        ).first()
    if revision is None:
        raise NotFound("No such question.")
    return master, version, revision


def check_duplicates(
    session: Session, principal: Principal, question_id: UUID, *, timeout_ms: int
) -> DuplicateCheck:
    """The exact and near duplicates of the text this person sees of the question."""
    master, version, revision = _checked_text(session, principal, question_id)
    key = duplicate_key(revision.content)
    candidates = find_duplicates(
        session,
        principal,
        master_id=master.id,
        key=key,
        text_to_match=bank_text(revision.content).match_text,
        timeout_ms=timeout_ms,
    )
    return DuplicateCheck(
        master,
        version,
        revision,
        candidates,
        newest_decisions(session, version.id, key),
        qc_blockers(session, master, version, key),
    )


def newest_decisions(
    session: Session, version_id: UUID, key: str | None
) -> dict[UUID, DuplicateDecision]:
    """The newest decision about each other question, for this text of the version."""
    if key is None:
        return {}
    found: dict[UUID, DuplicateDecision] = {}
    for decision in session.scalars(
        select(DuplicateDecision)
        .where(DuplicateDecision.version_id == version_id, DuplicateDecision.duplicate_key == key)
        .order_by(DuplicateDecision.created_at, DuplicateDecision.id)
    ):
        found[decision.other_master_id] = decision  # a later row replaces an earlier one
    return found


def qc_blockers(
    session: Session, master: QuestionMaster, version: QuestionVersion, key: str | None
) -> list[tuple[UUID, str]]:
    """The other questions that stop this text passing QC: each exact match in the shared bank that
    nobody has decided is not a duplicate, and each question of the shared bank someone said this
    one duplicates. A private draft or an archived question never blocks (design note §7.9)."""
    if key is None:
        return []
    decisions = newest_decisions(session, version.id, key)
    exact = shared_exact_duplicates(session, master.organization_id, master_id=master.id, key=key)
    blockers = [
        (other, code)
        for other, code in exact
        if other not in decisions or decisions[other].decision != "NOT_DUPLICATE"
    ]
    blocked = {other for other, _ in blockers}
    confirmed = [
        other
        for other, decision in decisions.items()
        if decision.decision == "DUPLICATE_OF" and other not in blocked
    ]
    shared = shared_codes(session, master.organization_id, confirmed)
    blockers += [(other, shared[other]) for other in confirmed if other in shared]
    return blockers


def require_no_duplicate_blockers(
    session: Session, master: QuestionMaster, version: QuestionVersion, revision: QuestionRevision
) -> None:
    """Refuse Pass QC while a possible exact duplicate is undecided or a duplicate was confirmed."""
    blockers = qc_blockers(session, master, version, duplicate_key(revision.content))
    if blockers:
        raise Conflict(
            "This question may be a copy of another one. Open Possible duplicates and record a"
            " decision for each exact match first.",
            code="QC_BLOCKED_DUPLICATE",
            details={"duplicates": [{"question_id": str(q), "code": c} for q, c in blockers]},
        )


def _may_decide(principal: Principal, master: QuestionMaster) -> bool:
    """The author, whoever may open all drafts, and quality control."""
    return may_access_draft(principal, master.created_by) or has_grant(principal, Grant.QC)


def _readable_other(session: Session, principal: Principal, other_id: UUID) -> QuestionMaster:
    other = session.get(QuestionMaster, other_id)
    if other is None:
        raise NotFound("No such other question.")
    if may_access_draft(principal, other.created_by):
        return other
    shared = session.scalar(
        select(QuestionVersion.id)
        .where(QuestionVersion.master_id == other.id, QuestionVersion.state.not_in(_PRIVATE))
        .limit(1)
    )
    if shared is None:  # someone else's private draft: as if it did not exist
        raise NotFound("No such other question.")
    return other


def decide(
    session: Session,
    principal: Principal,
    question_id: UUID,
    *,
    other_question_id: UUID,
    decision: Decision,
    note: str,
    request_id: str | None,
) -> DuplicateDecision:
    """Record that the question is, or is not, a duplicate of another, for its text as it is now."""
    master, version, revision = _checked_text(session, principal, question_id, lock=True)
    if not _may_decide(principal, master):
        raise PermissionDenied("Only the author, an editor or quality control may decide this.")
    if version.state == "PUBLISHED":
        raise Conflict(
            "A published question is not checked again. Decide on the other question instead.",
            code="DUPLICATE_DECISION_CLOSED",
        )
    if other_question_id == master.id:
        raise ValidationFailed("A question cannot be a duplicate of itself.", code="SAME_QUESTION")
    other = _readable_other(session, principal, other_question_id)
    key = duplicate_key(revision.content)
    if key is None:
        raise ValidationFailed(
            "Write the question before deciding about duplicates.", code="QUESTION_EMPTY"
        )
    clean_note = note.strip()
    if not clean_note:
        raise ValidationFailed("Say in a few words why.", code="NOTE_REQUIRED")
    row = DuplicateDecision(
        organization_id=master.organization_id,
        version_id=version.id,
        revision_id=revision.id,
        duplicate_key=key,
        other_master_id=other.id,
        decision=decision,
        note=clean_note,
        actor_id=principal.user_id,
        # The clock now, after the question is locked, not when the transaction began: of two
        # decisions about the same question, the one recorded last is the newest (Codex, #137).
        created_at=func.clock_timestamp(),
    )
    session.add(row)
    session.flush()
    record_event(
        session,
        action="QUESTION_DUPLICATE_DECIDED",
        entity_type="question",
        entity_id=master.id,
        organization_id=master.organization_id,
        actor_user_id=principal.user_id,
        actor_is_platform=principal.acting_organization_id is not None,
        request_id=request_id,
        after={
            "other_question_id": str(other.id),
            "other_code": other.code,
            "decision": decision,
            "note": clean_note,
            "version_number": version.number,
            "revision_id": str(revision.id),
        },
    )
    return row
