"""Starting a reading and deciding each question found (M6 6f/6g, G-04, D-16).

Nothing here is automatic: AI proposes candidates, a person decides each one. Accepting makes a
new **draft** question of the person's own (the normal checks show what is left to fix); it never
submits or publishes anything. Each decision is written to the candidate's history.
"""

from typing import Any
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from qbank.core.auth import Principal
from qbank.core.errors import Conflict, NotFound, ValidationFailed
from qbank.core.etag import require_if_match
from qbank.core.jobs import enqueue
from qbank.core.permissions import Action, require
from qbank.modules.ai.public import check_model
from qbank.modules.audit.public import record_event
from qbank.modules.ingestion.extract import prompt
from qbank.modules.ingestion.models import (
    IngestCandidate,
    IngestCandidateEvent,
    IngestFile,
    IngestPage,
    IngestRun,
    IngestSettings,
)
from qbank.modules.ingestion.public import EXTRACT_JOB
from qbank.modules.ingestion.service import get_file, may_see_all
from qbank.modules.questions.public import (
    DuplicateCandidate,
    create_question_from_content,
    duplicates_of_content,
    read_for_ai,
    validate_content,
)

MOST_REJECT_REASON = 500


def _org(principal: Principal) -> UUID:
    org = principal.tenant_context.organization_id
    if org is None:
        raise NotFound("No coaching.")
    return org


# --- Settings ---------------------------------------------------------------------------------


def get_settings(session: Session, principal: Principal) -> IngestSettings | None:
    require(principal, Action.MANAGE_INGEST)
    return session.get(IngestSettings, _org(principal))


def save_settings(
    session: Session,
    principal: Principal,
    model_id: UUID | None,
    *,
    if_match: str | None,
    request_id: str | None,
) -> IngestSettings:
    """Choose the model pages are read with (null clears it). The model must be one the coaching
    can use today and know how to read pictures."""
    require(principal, Action.MANAGE_INGEST)
    organization_id = _org(principal)
    row = session.get(IngestSettings, organization_id, with_for_update=True)
    require_if_match(if_match, row.revision if row is not None else 0)
    if model_id is not None:
        check_model(session, organization_id, model_id, needs_pictures=True)
    if row is None:
        row = IngestSettings(
            organization_id=organization_id, model_id=model_id, updated_by=principal.user_id
        )
        session.add(row)
    else:
        row.model_id, row.updated_by = model_id, principal.user_id
        row.revision += 1
        row.updated_at = func.now()
    record_event(
        session,
        action="INGEST_SETTINGS_CHANGED",
        entity_type="ingest_settings",
        entity_id=organization_id,
        organization_id=organization_id,
        actor_user_id=principal.user_id,
        request_id=request_id,
        after={"model_id": str(model_id) if model_id else None},
    )
    session.flush()
    return row


# --- Runs -------------------------------------------------------------------------------------


def start_run(
    session: Session,
    principal: Principal,
    file_id: UUID,
    *,
    request_id: str | None,
) -> IngestRun:
    """Begin reading a file that has its pages. One reading at a time per file."""
    require(principal, Action.USE_INGEST)
    require(principal, Action.USE_AI)
    organization_id = _org(principal)
    file = get_file(session, principal, file_id)
    settings = session.get(IngestSettings, organization_id)
    if settings is None or settings.model_id is None:
        raise Conflict(
            "No model is chosen for reading documents. An admin chooses one under the uploads"
            " settings.",
            code="INGEST_NO_MODEL",
        )
    if file.state not in ("READY", "DONE", "PARTIAL", "FAILED"):
        raise Conflict(
            "This document is not ready to be read yet, or is already being read.",
            code="INGEST_NOT_READY",
        )
    pages = session.scalar(
        select(func.count())
        .select_from(IngestPage)
        .where(IngestPage.file_id == file_id, IngestPage.state == "READY")
    )
    if not pages:
        raise Conflict("This document has no readable page.", code="INGEST_NO_PAGES")
    run = IngestRun(
        organization_id=organization_id,
        file_id=file_id,
        requested_by=principal.user_id,
        model_ref=settings.model_id,
        prompt_version=prompt.PROMPT_VERSION,
        prompt_hash=prompt.prompt_hash(),
        pages_total=pages,
    )
    session.add(run)
    session.flush()
    session.execute(
        update(IngestFile)
        .where(IngestFile.id == file_id)
        .values(state="EXTRACTING", error_code=None, updated_at=func.now())
    )
    enqueue(
        session,
        EXTRACT_JOB,
        {"run_id": str(run.id)},
        context=principal.tenant_context,
        idempotency_key=str(run.id),
        request_id=request_id,
        max_attempts=3,
    )
    record_event(
        session,
        action="INGEST_RUN_STARTED",
        entity_type="ingest_file",
        entity_id=file_id,
        organization_id=organization_id,
        actor_user_id=principal.user_id,
        request_id=request_id,
        after={"run_id": str(run.id), "pages": pages, "prompt_version": prompt.PROMPT_VERSION},
    )
    return run


def list_runs(session: Session, principal: Principal, file_id: UUID) -> list[IngestRun]:
    get_file(session, principal, file_id)
    return list(
        session.scalars(
            select(IngestRun)
            .where(IngestRun.file_id == file_id)
            .order_by(IngestRun.started_at.desc(), IngestRun.id.desc())
        )
    )


# --- Candidates -------------------------------------------------------------------------------


def list_candidates(
    session: Session,
    principal: Principal,
    file_id: UUID,
    *,
    state: str | None,
    page_no: int | None,
) -> list[IngestCandidate]:
    """The questions found in a file, in page order. A new reading of the file adds its own
    candidates; earlier ones stay on record with the decisions already made on them."""
    get_file(session, principal, file_id)
    query = (
        select(IngestCandidate)
        .where(IngestCandidate.file_id == file_id)
        .order_by(IngestCandidate.page_no, IngestCandidate.ordinal, IngestCandidate.created_at)
    )
    if state is not None:
        query = query.where(IngestCandidate.state == state)
    if page_no is not None:
        query = query.where(IngestCandidate.page_no == page_no)
    return list(session.scalars(query.limit(2000)))


def get_candidate(session: Session, principal: Principal, candidate_id: UUID) -> IngestCandidate:
    require(principal, Action.USE_INGEST)
    row = session.get(IngestCandidate, candidate_id)
    if row is None:
        raise NotFound("No such candidate.")
    try:
        get_file(session, principal, row.file_id)  # the same visibility as its file
    except NotFound:
        raise NotFound("No such candidate.") from None
    return row


def _event(
    session: Session, principal: Principal, row: IngestCandidate, action: str, **detail: Any
) -> None:
    session.add(
        IngestCandidateEvent(
            organization_id=row.organization_id,
            candidate_id=row.id,
            actor_user_id=principal.user_id,
            action=action,
            detail=detail,
        )
    )


def _open(row: IngestCandidate) -> None:
    if row.state != "NEW":
        raise Conflict("This candidate has already been decided.", code="INGEST_CANDIDATE_DECIDED")


def update_content(
    session: Session,
    principal: Principal,
    candidate_id: UUID,
    content: dict[str, Any],
    *,
    if_match: str | None,
) -> IngestCandidate:
    """Replace the editable content (the model's reading stays in ``raw``) and check it again."""
    row = get_candidate(session, principal, candidate_id)
    require_if_match(if_match, row.revision)
    _open(row)
    findings = [
        {"path": f.path, "code": f.code, "level": f.level.value, "message": f.message}
        for f in validate_content(content)
    ]
    row.content, row.findings = content, findings
    row.revision += 1
    row.updated_at = func.now()
    _event(session, principal, row, "EDITED")
    session.flush()
    return row


def accept(
    session: Session, principal: Principal, candidate_id: UUID, *, request_id: str | None
) -> IngestCandidate:
    """Make the candidate a new draft question of this person, and remember where it came from."""
    row = get_candidate(session, principal, candidate_id)
    _open(row)
    created = create_question_from_content(
        session, principal, dict(row.content), request_id=request_id
    )
    row.state, row.question_id = "ACCEPTED", created.id
    row.decided_by, row.updated_at = principal.user_id, func.now()
    row.revision += 1
    _event(session, principal, row, "ACCEPTED", question_id=str(created.id), code=created.code)
    record_event(
        session,
        action="INGEST_CANDIDATE_ACCEPTED",
        entity_type="question",
        entity_id=created.id,
        organization_id=row.organization_id,
        actor_user_id=principal.user_id,
        request_id=request_id,
        after={"file_id": str(row.file_id), "page_no": row.page_no, "candidate": str(row.id)},
    )
    session.flush()
    return row


def same_as(
    session: Session,
    principal: Principal,
    candidate_id: UUID,
    question_id: UUID,
    *,
    request_id: str | None,
) -> IngestCandidate:
    """The page shows a question the bank already has: nothing new is made, the source is kept."""
    row = get_candidate(session, principal, candidate_id)
    _open(row)
    read_for_ai(session, principal, question_id)  # the person must be able to open that question
    row.state, row.question_id = "DUPLICATE", question_id
    row.decided_by, row.updated_at = principal.user_id, func.now()
    row.revision += 1
    _event(session, principal, row, "SAME_AS", question_id=str(question_id))
    record_event(
        session,
        action="INGEST_CANDIDATE_SAME_AS",
        entity_type="ingest_file",
        entity_id=row.file_id,
        organization_id=row.organization_id,
        actor_user_id=principal.user_id,
        request_id=request_id,
        after={"candidate": str(row.id), "question_id": str(question_id)},
    )
    session.flush()
    return row


def reject(
    session: Session,
    principal: Principal,
    candidate_id: UUID,
    reason: str,
    *,
    request_id: str | None,
) -> IngestCandidate:
    row = get_candidate(session, principal, candidate_id)
    _open(row)
    cleaned = " ".join(reason.split())
    if not cleaned or len(cleaned) > MOST_REJECT_REASON:
        raise ValidationFailed(
            f"Give a reason of up to {MOST_REJECT_REASON} characters.", code="INGEST_REASON_NEEDED"
        )
    row.state, row.reject_reason = "REJECTED", cleaned
    row.decided_by, row.updated_at = principal.user_id, func.now()
    row.revision += 1
    _event(session, principal, row, "REJECTED", reason=cleaned)
    record_event(
        session,
        action="INGEST_CANDIDATE_REJECTED",
        entity_type="ingest_file",
        entity_id=row.file_id,
        organization_id=row.organization_id,
        actor_user_id=principal.user_id,
        request_id=request_id,
        after={"candidate": str(row.id)},
    )
    session.flush()
    return row


def duplicates(
    session: Session, principal: Principal, candidate_id: UUID, *, timeout_ms: int
) -> list[DuplicateCandidate]:
    row = get_candidate(session, principal, candidate_id)
    return duplicates_of_content(session, principal, dict(row.content), timeout_ms=timeout_ms)


def sees_all(principal: Principal) -> bool:
    return may_see_all(principal)
