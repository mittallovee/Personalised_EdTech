"""The bank index table (migration 0029)."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import Computed, ForeignKey, Uuid
from sqlalchemy.dialects.postgresql import ARRAY, TSVECTOR
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

    # What a free-text search reads (migration 0030). The text and its word index are left out of
    # a plain list query; only ``preview`` is shown, and the search compares against the other two.
    stem_text: Mapped[str] = mapped_column(deferred=True)
    preview: Mapped[str]
    search_vector: Mapped[str] = mapped_column(
        TSVECTOR, Computed("to_tsvector('simple', stem_text)", persisted=True), deferred=True
    )


class BankWord(Base):
    """A distinct word of a coaching's bank (migration 0031), for typo search. Written by a
    database trigger on ``bank_index``; never by the app."""

    __tablename__ = "bank_words"

    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), primary_key=True)
    word: Mapped[str] = mapped_column(primary_key=True)
