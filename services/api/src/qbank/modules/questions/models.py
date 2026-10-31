"""Tables of the questions module (migration 0020): master, version, revision."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, ForeignKeyConstraint, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from qbank.core.db import Base
from qbank.core.ids import new_id


class QuestionMaster(Base):
    """One bank question: its permanent code and who started it. Archived, never deleted."""

    __tablename__ = "question_masters"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_id)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"))
    code: Mapped[str] = mapped_column(String(8))
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revision: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class QuestionVersion(Base):
    """A line of work under a master: version 1 now, a correction of a published one is 2."""

    __tablename__ = "question_versions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "master_id"],
            ["question_masters.organization_id", "question_masters.id"],
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_id)
    organization_id: Mapped[UUID]
    master_id: Mapped[UUID]
    number: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class QuestionRevision(Base):
    """A saved snapshot of the content. The one with no ``frozen_at`` is the working revision."""

    __tablename__ = "question_revisions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "version_id"],
            ["question_versions.organization_id", "question_versions.id"],
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_id)
    organization_id: Mapped[UUID]
    version_id: Mapped[UUID]
    number: Mapped[int]
    content: Mapped[dict[str, Any]] = mapped_column(JSONB)
    content_hash: Mapped[str | None] = mapped_column(String(64))
    author_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    frozen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revision: Mapped[int] = mapped_column(default=1)  # the ETag of the working revision
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
