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
