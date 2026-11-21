"""What the AI module may do with a question, and nothing more (M5 design note §6, §9).

The AI module never reads question tables. It asks here for a question as it stands (the text, the
labels and a marker of the exact revision) and, when a run finishes, asks to fill in the labels. The
marker lets the answer be refused if the question changed in the meantime or if the person who
asked can no longer edit it (B-10): the result is then kept but changes nothing.
"""

from dataclasses import dataclass
from typing import Any, Literal
from uuid import UUID

from sqlalchemy.orm import Session

from qbank.core.auth import Principal
from qbank.core.errors import AppError, Conflict, NotFound, PermissionDenied, PreconditionFailed
from qbank.core.etag import etag
from qbank.core.permissions import may_access_draft
from qbank.modules.questions.bank_text import bank_text
from qbank.modules.questions.domain.workflow import EDITABLE_STATES
from qbank.modules.questions.service import get_question, save_working_revision

Applied = Literal["APPLIED", "OUT_OF_DATE", "NEEDS_REVIEW"]

_EDITABLE = frozenset(state.value for state in EDITABLE_STATES)
# The labels a tagging run may fill. Everything else in the metadata is left as the person set it.
TAGGABLE = ("chapter_id", "topic_id", "primary_concept_id", "difficulty", "bloom_level")


@dataclass(frozen=True, slots=True)
class QuestionForAi:
    """A question as a run reads it. ``revision_id`` and ``revision`` identify the working revision
    the run was based on."""

    question_id: UUID
    revision_id: UUID
    revision: int
    editable: bool
    content: dict[str, Any]
    text: str
    metadata: dict[str, Any]


def read_for_ai(session: Session, principal: Principal, question_id: UUID) -> QuestionForAi:
    """The question as it is now. Someone who may not open it gets "not found", as everywhere."""
    view = get_question(session, principal, question_id)
    revision = view.revision
    meta = revision.content.get("metadata")
    return QuestionForAi(
        question_id=view.master.id,
        revision_id=revision.id,
        revision=revision.revision,
        editable=(
            view.version.state in _EDITABLE
            and view.master.archived_at is None
            and may_access_draft(principal, view.master.created_by)
        ),
        content=revision.content,
        text=bank_text(revision.content).stem_text,
        metadata=dict(meta) if isinstance(meta, dict) else {},
    )


def apply_labels(
    session: Session,
    principal: Principal,
    question_id: UUID,
    *,
    revision_id: UUID,
    revision: int,
    labels: dict[str, Any],
) -> Applied:
    """Fill in ``labels`` on the working revision a run was based on.

    Returns ``APPLIED``, or ``OUT_OF_DATE`` when the question has moved on (another save, or it is
    no longer editable), or ``NEEDS_REVIEW`` when the person who asked can no longer see or edit it.
    Nothing is written unless it is ``APPLIED``. Only the labels in ``TAGGABLE`` are accepted.
    """
    wanted = {key: value for key, value in labels.items() if key in TAGGABLE}
    try:
        current = read_for_ai(session, principal, question_id)
    except NotFound, PermissionDenied:
        return "NEEDS_REVIEW"
    if not current.editable:
        return "OUT_OF_DATE"
    if current.revision_id != revision_id or current.revision != revision:
        return "OUT_OF_DATE"
    content = {**current.content, "metadata": {**current.metadata, **wanted}}
    try:
        save_working_revision(session, principal, question_id, content, if_match=etag(revision))
    except NotFound, PermissionDenied:
        return "NEEDS_REVIEW"
    except Conflict, PreconditionFailed:
        return "OUT_OF_DATE"
    except AppError:
        return "NEEDS_REVIEW"
    return "APPLIED"
