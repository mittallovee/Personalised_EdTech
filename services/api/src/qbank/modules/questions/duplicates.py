"""Possible duplicates of one question (D-16, M4 design note §7.4).

The text checked is the one a person is looking at: the revision under review (or published) once
the question was submitted, else the working copy of a draft or a returned question, which only
the people who may open drafts can see. A question nobody may open is "not found", as everywhere.
The candidates come from the bank index through ``search.public``, with the bank's visibility rule.
"""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from qbank.core.auth import Principal
from qbank.core.errors import NotFound
from qbank.core.permissions import Action, is_allowed, may_access_draft
from qbank.modules.questions.bank_text import bank_text
from qbank.modules.questions.domain.workflow import PRIVATE_STATES
from qbank.modules.questions.duplicate_key import duplicate_key
from qbank.modules.questions.models import QuestionMaster, QuestionRevision, QuestionVersion
from qbank.modules.search.public import DuplicateCandidate, find_duplicates

_PRIVATE = [state.value for state in PRIVATE_STATES]


@dataclass(frozen=True, slots=True)
class DuplicateCheck:
    master: QuestionMaster
    version: QuestionVersion
    revision: QuestionRevision
    candidates: list[DuplicateCandidate]


def _checked_text(
    session: Session, principal: Principal, question_id: UUID
) -> tuple[QuestionMaster, QuestionVersion, QuestionRevision]:
    master = session.get(QuestionMaster, question_id)
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
    candidates = find_duplicates(
        session,
        principal,
        master_id=master.id,
        key=duplicate_key(revision.content),
        text_to_match=bank_text(revision.content).match_text,
        timeout_ms=timeout_ms,
    )
    return DuplicateCheck(master, version, revision, candidates)
