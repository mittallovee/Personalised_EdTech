"""What the AI module may do with a question, and nothing more (M5 design note §6, §9).

The AI module never reads question tables. It asks here for a question as it stands (the text, the
labels and a marker of the exact revision) and, when a run finishes, asks to fill in the labels. The
marker lets the answer be refused if the question changed in the meantime or if the person who
asked can no longer edit it (B-10): the result is then kept but changes nothing.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal
from uuid import UUID

from sqlalchemy.orm import Session

from qbank.core.auth import Principal
from qbank.core.errors import AppError, Conflict, NotFound, PermissionDenied, PreconditionFailed
from qbank.core.etag import etag
from qbank.core.permissions import may_access_draft
from qbank.modules.audit.public import record_event
from qbank.modules.questions.bank_text import bank_text
from qbank.modules.questions.domain.workflow import EDITABLE_STATES
from qbank.modules.questions.service import create_question, get_question, save_working_revision
from qbank.modules.questions.translation import add_link

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
    version_number: int
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
        version_number=view.version.number,
        editable=(
            view.version.state in _EDITABLE
            and view.master.archived_at is None
            and may_access_draft(principal, view.master.created_by)
        ),
        content=revision.content,
        text=bank_text(revision.content).stem_text,
        metadata=dict(meta) if isinstance(meta, dict) else {},
    )


def apply_changes(
    session: Session,
    principal: Principal,
    question_id: UUID,
    *,
    revision_id: UUID,
    revision: int,
    change: Callable[[dict[str, Any]], dict[str, Any]],
) -> Applied:
    """Replace the working revision's content with ``change(current content)``, if it is still the
    revision a run was based on.

    Returns ``APPLIED``, or ``OUT_OF_DATE`` when the question has moved on (another save, or it is
    no longer editable), or ``NEEDS_REVIEW`` when the person applying can no longer see or edit it.
    Nothing is written unless it is ``APPLIED``.
    """
    try:
        current = read_for_ai(session, principal, question_id)
    except NotFound, PermissionDenied:
        return "NEEDS_REVIEW"
    if not current.editable:
        return "OUT_OF_DATE"
    if current.revision_id != revision_id or current.revision != revision:
        return "OUT_OF_DATE"
    try:
        save_working_revision(
            session, principal, question_id, change(current.content), if_match=etag(revision)
        )
    except NotFound, PermissionDenied:
        return "NEEDS_REVIEW"
    except Conflict, PreconditionFailed:
        return "OUT_OF_DATE"
    except AppError:
        return "NEEDS_REVIEW"
    return "APPLIED"


def apply_labels(
    session: Session,
    principal: Principal,
    question_id: UUID,
    *,
    revision_id: UUID,
    revision: int,
    labels: dict[str, Any],
) -> Applied:
    """Fill in ``labels`` (only ``TAGGABLE`` ones) on the working revision a run was based on."""
    wanted = {key: value for key, value in labels.items() if key in TAGGABLE}

    def merge(content: dict[str, Any]) -> dict[str, Any]:
        meta = content.get("metadata")
        return {**content, "metadata": {**(meta if isinstance(meta, dict) else {}), **wanted}}

    return apply_changes(
        session, principal, question_id, revision_id=revision_id, revision=revision, change=merge
    )


@dataclass(frozen=True, slots=True)
class CreatedQuestion:
    id: UUID
    code: str


def create_translation(
    session: Session,
    principal: Principal,
    source_id: UUID,
    *,
    revision_id: UUID,
    revision: int,
    language: str,
    content: dict[str, Any],
    request_id: str | None,
) -> tuple[Applied, CreatedQuestion | None]:
    """Make a translation of a question a new draft question of the person, linked to its source.

    The source is never changed. It must still be at the revision the run read (else
    ``OUT_OF_DATE``, so a translation of old text is not made), and the person must still be able
    to open it and to create questions (else ``NEEDS_REVIEW``)."""
    try:
        source = read_for_ai(session, principal, source_id)
    except NotFound, PermissionDenied:
        return "NEEDS_REVIEW", None
    if source.revision_id != revision_id or source.revision != revision:
        return "OUT_OF_DATE", None
    try:
        view = create_question(
            session, principal, content, idempotency_key=None, request_id=request_id
        )
    except NotFound, PermissionDenied:
        return "NEEDS_REVIEW", None
    organization_id = principal.tenant_context.organization_id
    if organization_id is None:
        return "NEEDS_REVIEW", None
    add_link(
        session,
        principal,
        organization_id=organization_id,
        source_id=source_id,
        source_version_number=source.version_number,
        target_id=view.master.id,
        language=language,
    )
    record_event(
        session,
        action="QUESTION_TRANSLATION_LINKED",
        entity_type="question",
        entity_id=view.master.id,
        organization_id=organization_id,
        actor_user_id=principal.user_id,
        actor_is_platform=principal.acting_organization_id is not None,
        request_id=request_id,
        after={"source_id": str(source_id), "language": language},
    )
    return "APPLIED", CreatedQuestion(view.master.id, view.master.code)
