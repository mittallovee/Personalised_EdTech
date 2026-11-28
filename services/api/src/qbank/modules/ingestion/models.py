"""Tables of the ingestion module (migration 0044 onwards)."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from qbank.core.db import Base
from qbank.core.ids import new_id


class IngestFile(Base):
    __tablename__ = "ingest_files"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_id)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"))
    uploaded_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    file_name: Mapped[str]
    kind: Mapped[str] = mapped_column(String(8))
    byte_size: Mapped[int]
    sha256: Mapped[str] = mapped_column(String(64))
    storage_key: Mapped[str]
    state: Mapped[str] = mapped_column(String(16), default="UPLOADED")
    page_count: Mapped[int | None]
    error_code: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class IngestPage(Base):
    __tablename__ = "ingest_pages"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_id)
    organization_id: Mapped[UUID]
    file_id: Mapped[UUID]
    page_no: Mapped[int]
    state: Mapped[str] = mapped_column(String(8))
    image_key: Mapped[str | None]
    thumb_key: Mapped[str | None]
    width: Mapped[int | None]
    height: Mapped[int | None]
    text: Mapped[str | None]
    figures: Mapped[list[dict[str, object]]] = mapped_column(JSONB, default=list)
    warnings: Mapped[list[str]] = mapped_column(JSONB, default=list)
    error_code: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class IngestSettings(Base):
    __tablename__ = "ingest_settings"

    organization_id: Mapped[UUID] = mapped_column(primary_key=True)
    model_id: Mapped[UUID | None]
    revision: Mapped[int] = mapped_column(default=1)
    updated_by: Mapped[UUID]
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class IngestRun(Base):
    __tablename__ = "ingest_runs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_id)
    organization_id: Mapped[UUID]
    file_id: Mapped[UUID]
    requested_by: Mapped[UUID]
    model_ref: Mapped[UUID]
    prompt_version: Mapped[str]
    prompt_hash: Mapped[str]
    state: Mapped[str] = mapped_column(String(10), default="RUNNING")
    pages_total: Mapped[int]
    pages_done: Mapped[int] = mapped_column(default=0)
    pages_failed: Mapped[int] = mapped_column(default=0)
    error_code: Mapped[str | None]
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class IngestRunPage(Base):
    __tablename__ = "ingest_run_pages"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_id)
    organization_id: Mapped[UUID]
    run_id: Mapped[UUID]
    page_no: Mapped[int]
    state: Mapped[str] = mapped_column(String(8))
    ledger_id: Mapped[UUID]
    error_code: Mapped[str | None]
    candidate_count: Mapped[int] = mapped_column(default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class IngestCandidate(Base):
    __tablename__ = "ingest_candidates"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_id)
    organization_id: Mapped[UUID]
    file_id: Mapped[UUID]
    run_id: Mapped[UUID]
    page_no: Mapped[int]
    ordinal: Mapped[int]
    region: Mapped[dict[str, float] | None] = mapped_column(JSONB)
    raw: Mapped[dict[str, object]] = mapped_column(JSONB)
    content: Mapped[dict[str, object]] = mapped_column(JSONB)
    findings: Mapped[list[dict[str, str]]] = mapped_column(JSONB, default=list)
    confidence: Mapped[str] = mapped_column(String(6))
    warnings: Mapped[list[str]] = mapped_column(JSONB, default=list)
    state: Mapped[str] = mapped_column(String(10), default="NEW")
    question_id: Mapped[UUID | None]
    reject_reason: Mapped[str | None]
    revision: Mapped[int] = mapped_column(default=1)
    decided_by: Mapped[UUID | None]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class IngestCandidateEvent(Base):
    __tablename__ = "ingest_candidate_events"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_id)
    organization_id: Mapped[UUID]
    candidate_id: Mapped[UUID]
    actor_user_id: Mapped[UUID | None]
    action: Mapped[str]
    detail: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class GoldenSet(Base):
    __tablename__ = "golden_sets"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_id)
    organization_id: Mapped[UUID]
    name: Mapped[str]
    created_by: Mapped[UUID]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class GoldenCase(Base):
    __tablename__ = "golden_cases"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_id)
    organization_id: Mapped[UUID]
    set_id: Mapped[UUID]
    file_id: Mapped[UUID]
    page_no: Mapped[int]
    candidate_id: Mapped[UUID]
    expected: Mapped[dict[str, object]] = mapped_column(JSONB)
    created_by: Mapped[UUID]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
