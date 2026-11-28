"""Storing an upload and finding uploads. The API only stores bytes and queues a job (ADR-0024)."""

import hashlib
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select, tuple_, update
from sqlalchemy.orm import Session

from qbank.core.auth import Principal
from qbank.core.errors import Conflict, NotFound
from qbank.core.ids import new_id
from qbank.core.jobs import enqueue
from qbank.core.permissions import Action, is_allowed
from qbank.core.storage import Storage
from qbank.modules.audit.public import record_event
from qbank.modules.ingestion.filetype import Detected, clean_name
from qbank.modules.ingestion.models import IngestFile, IngestPage
from qbank.modules.ingestion.public import RENDER_JOB

IN_FLIGHT_STATES = ("UPLOADED", "RENDERING", "EXTRACTING")


def may_see_all(principal: Principal) -> bool:
    return is_allowed(principal, Action.MANAGE_INGEST)


def create_file(
    session: Session,
    principal: Principal,
    storage: Storage,
    *,
    data: bytes,
    detected: Detected,
    file_name: str,
    in_flight_limit: int,
    request_id: str | None,
) -> tuple[IngestFile, UUID | None]:
    """Keep the original, write its row and queue the render job, all or nothing.

    Returns the row and, if the coaching already holds a file with exactly these bytes, that file's
    id. The new upload is kept anyway: a person may mean it."""
    organization_id = principal.tenant_context.organization_id
    if organization_id is None:  # the permission check refuses this first
        raise NotFound("No coaching to upload to.")
    waiting = session.scalar(
        select(func.count()).select_from(IngestFile).where(IngestFile.state.in_(IN_FLIGHT_STATES))
    )
    if (waiting or 0) >= in_flight_limit:
        raise Conflict(
            "Too many documents are waiting to be read. Wait for some to finish, then try again.",
            code="INGEST_TOO_MANY_IN_FLIGHT",
            details={"limit": in_flight_limit},
        )
    digest = hashlib.sha256(data).hexdigest()
    same = session.scalar(
        select(IngestFile.id)
        .where(IngestFile.sha256 == digest)
        .order_by(IngestFile.created_at)
        .limit(1)
    )
    file_id = new_id()
    key = f"org/{organization_id}/ingest/{file_id}"
    storage.put(key, data)
    row = IngestFile(
        id=file_id,
        organization_id=organization_id,
        uploaded_by=principal.user_id,
        file_name=clean_name(file_name),
        kind=detected.kind,
        byte_size=len(data),
        sha256=digest,
        storage_key=key,
        state="UPLOADED",
    )
    try:
        session.add(row)
        session.flush()
        enqueue(
            session,
            RENDER_JOB,
            {"file_id": str(file_id)},
            context=principal.tenant_context,
            idempotency_key=str(file_id),
            request_id=request_id,
            max_attempts=3,
        )
        record_event(
            session,
            action="INGEST_FILE_UPLOADED",
            entity_type="ingest_file",
            entity_id=file_id,
            organization_id=organization_id,
            actor_user_id=principal.user_id,
            request_id=request_id,
            after={"kind": detected.kind, "byte_size": len(data)},
        )
    except Exception:
        storage.delete(key)  # no row, so nothing may keep pointing at the file
        raise
    return row, same


def get_file(session: Session, principal: Principal, file_id: UUID) -> IngestFile:
    """The coaching's own file; faculty see only their uploads. Anything else is not found."""
    row = session.scalars(select(IngestFile).where(IngestFile.id == file_id)).one_or_none()
    if row is None or (not may_see_all(principal) and row.uploaded_by != principal.user_id):
        raise NotFound("No such document.")
    return row


def list_files(
    session: Session,
    principal: Principal,
    *,
    limit: int,
    after: tuple[datetime, UUID] | None,
    state: str | None,
) -> tuple[list[IngestFile], bool]:
    query = select(IngestFile).order_by(IngestFile.created_at.desc(), IngestFile.id.desc())
    if not may_see_all(principal):
        query = query.where(IngestFile.uploaded_by == principal.user_id)
    if state is not None:
        query = query.where(IngestFile.state == state)
    if after is not None:
        query = query.where(tuple_(IngestFile.created_at, IngestFile.id) < after)
    rows = list(session.scalars(query.limit(limit + 1)))
    return rows[:limit], len(rows) > limit


TERMINAL_STATES = ("DONE", "PARTIAL", "FAILED", "CANCELLED")


def list_pages(session: Session, principal: Principal, file_id: UUID) -> list[IngestPage]:
    get_file(session, principal, file_id)  # the same visibility as the file
    return list(
        session.scalars(
            select(IngestPage).where(IngestPage.file_id == file_id).order_by(IngestPage.page_no)
        )
    )


def get_page(session: Session, principal: Principal, file_id: UUID, page_no: int) -> IngestPage:
    get_file(session, principal, file_id)
    page = session.scalars(
        select(IngestPage).where(IngestPage.file_id == file_id, IngestPage.page_no == page_no)
    ).one_or_none()
    if page is None:
        raise NotFound("No such page.")
    return page


def cancel_file(
    session: Session, principal: Principal, file_id: UUID, *, request_id: str | None
) -> IngestFile:
    """Stop a file that is waiting or being read. What is already made is kept."""
    row = get_file(session, principal, file_id)
    if row.state in TERMINAL_STATES:
        raise Conflict("This document has already finished.", code="INGEST_ALREADY_FINISHED")
    session.execute(
        update(IngestFile)
        .where(IngestFile.id == file_id, IngestFile.state.not_in(TERMINAL_STATES))
        .values(state="CANCELLED", error_code=None, updated_at=func.now())
    )
    session.refresh(row)
    record_event(
        session,
        action="INGEST_FILE_CANCELLED",
        entity_type="ingest_file",
        entity_id=file_id,
        organization_id=row.organization_id,
        actor_user_id=principal.user_id,
        request_id=request_id,
    )
    return row


def retry_file(
    session: Session, principal: Principal, file_id: UUID, *, request_id: str | None
) -> IngestFile:
    """Read a failed or cancelled file again. Pages already made are kept and not made twice."""
    row = get_file(session, principal, file_id)
    if row.state not in ("FAILED", "CANCELLED"):
        raise Conflict(
            "Only a failed or cancelled document can be tried again.", code="INGEST_NOT_RETRYABLE"
        )
    session.execute(
        update(IngestFile)
        .where(IngestFile.id == file_id)
        .values(state="UPLOADED", error_code=None, updated_at=func.now())
    )
    session.refresh(row)
    enqueue(
        session,
        RENDER_JOB,
        {"file_id": str(file_id)},
        context=principal.tenant_context,
        idempotency_key=f"{file_id}-retry-{new_id()}",
        request_id=request_id,
        max_attempts=3,
    )
    record_event(
        session,
        action="INGEST_FILE_RETRIED",
        entity_type="ingest_file",
        entity_id=file_id,
        organization_id=row.organization_id,
        actor_user_id=principal.user_id,
        request_id=request_id,
    )
    return row
