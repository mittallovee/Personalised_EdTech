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
    # The version readers see once something is published (migration 0027). A correction leaves it
    # alone until that version is published too. Its foreign key is in the database only.
    published_version_id: Mapped[UUID | None]
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
    # The review workflow (migration 0026, M4 design note §4). ``state`` moves only along the pairs
    # of ``domain/workflow.py``, which a database trigger repeats; ``flow_revision`` is the number
    # in the workflow ETag ("flow-N"). The foreign key from ``review_revision_id`` to the revision
    # under review is in the database only: the two tables point at each other.
    state: Mapped[str] = mapped_column(String(20), default="DRAFT", server_default="DRAFT")
    flow_revision: Mapped[int] = mapped_column(default=1, server_default="1")
    review_revision_id: Mapped[UUID | None]
    state_changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ReviewDecision(Base):
    """One step taken on a version (migration 0026). Append-only: written, never changed."""

    __tablename__ = "review_decisions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "version_id"],
            ["question_versions.organization_id", "question_versions.id"],
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_id)
    organization_id: Mapped[UUID]
    version_id: Mapped[UUID]
    revision_id: Mapped[UUID]  # the frozen revision the step was taken on
    step: Mapped[str] = mapped_column(String(20))
    from_state: Mapped[str] = mapped_column(String(20))
    to_state: Mapped[str] = mapped_column(String(20))
    flow_revision: Mapped[int]  # the workflow revision the version had after the step
    actor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    reasons: Mapped[list[str]] = mapped_column(JSONB, default=list)
    note: Mapped[str | None]
    checklist: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PublishedVersion(Base):
    """One publication (migration 0027): the label names as they were that day, and the hash of
    the published text. Append-only: written, never changed."""

    __tablename__ = "published_versions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "version_id"],
            ["question_versions.organization_id", "question_versions.id"],
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_id)
    organization_id: Mapped[UUID]
    version_id: Mapped[UUID]
    revision_id: Mapped[UUID]  # the frozen revision that was published
    published_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    content_hash: Mapped[str] = mapped_column(String(64))
    labels: Mapped[dict[str, Any]] = mapped_column(JSONB)


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


class RevisionAsset(Base):
    """A picture that a revision uses (migration 0022). The working revision's rows follow its
    content; the rows of a frozen revision never change."""

    __tablename__ = "revision_assets"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "revision_id"],
            ["question_revisions.organization_id", "question_revisions.id"],
        ),
    )

    organization_id: Mapped[UUID]
    revision_id: Mapped[UUID] = mapped_column(primary_key=True)
    asset_id: Mapped[UUID] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Passage(Base):
    """Shared text that questions sit under (migration 0023). It has no public code."""

    __tablename__ = "passages"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_id)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"))
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PassageRevision(Base):
    """A saved snapshot of a passage. The one with no ``frozen_at`` is the working revision."""

    __tablename__ = "passage_revisions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "passage_id"], ["passages.organization_id", "passages.id"]
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_id)
    organization_id: Mapped[UUID]
    passage_id: Mapped[UUID]
    number: Mapped[int]
    content: Mapped[dict[str, Any]] = mapped_column(JSONB)
    content_hash: Mapped[str | None] = mapped_column(String(64))
    author_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    frozen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revision: Mapped[int] = mapped_column(default=1)  # the ETag of the working revision
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PassageRevisionAsset(Base):
    """A picture that a passage revision uses (migration 0023); same rules as ``RevisionAsset``."""

    __tablename__ = "passage_revision_assets"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "revision_id"],
            ["passage_revisions.organization_id", "passage_revisions.id"],
        ),
    )

    organization_id: Mapped[UUID]
    revision_id: Mapped[UUID] = mapped_column(primary_key=True)
    asset_id: Mapped[UUID] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AnswerRuleSettings(Base):
    """What a coaching changed in the answer limits (migration 0024): one row per coaching."""

    __tablename__ = "answer_rule_settings"

    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), primary_key=True)
    revision: Mapped[int] = mapped_column(default=1)  # the ETag
    defaults: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    exams: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    updated_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
