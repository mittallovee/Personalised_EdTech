"""The bank index table (migration 0029)."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, Uuid
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from qbank.core.db import Base


class BankRow(Base):
    """One question as the bank shows it. Derived: never the only copy of anything."""

    __tablename__ = "bank_index"

    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), primary_key=True)
    master_id: Mapped[UUID] = mapped_column(primary_key=True)
    code: Mapped[str]
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]

    version_number: Mapped[int]
    state: Mapped[str]
    is_private: Mapped[bool]
    is_archived: Mapped[bool]
    has_published: Mapped[bool]
    has_open_correction: Mapped[bool]

    question_type: Mapped[str | None]
    language: Mapped[str | None]
    class_id: Mapped[UUID | None]
    subject_id: Mapped[UUID | None]
    chapter_id: Mapped[UUID | None]
    topic_id: Mapped[UUID | None]
    primary_concept_id: Mapped[UUID | None]
    concept_ids: Mapped[list[UUID]] = mapped_column(ARRAY(Uuid))
    difficulty: Mapped[int | None]
    bloom_level: Mapped[str | None]
    is_pyq: Mapped[bool]
    exam_id: Mapped[UUID | None]
    exam_year: Mapped[int | None]
    has_solution: Mapped[bool]
    has_video: Mapped[bool]
