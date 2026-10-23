from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, ForeignKeyConstraint, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from qbank.core.db import Base
from qbank.core.ids import new_id


class TaxonomyNode(Base):
    """One place in a coaching's syllabus: a class, subject, chapter, topic or subtopic."""

    __tablename__ = "taxonomy_nodes"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "parent_id", "parent_kind"],
            ["taxonomy_nodes.organization_id", "taxonomy_nodes.id", "taxonomy_nodes.kind"],
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_id)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"))
    kind: Mapped[str] = mapped_column(String(20))
    parent_id: Mapped[UUID | None]
    parent_kind: Mapped[str | None] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(200))  # the English label
    name_key: Mapped[str] = mapped_column(String(400))  # ``name`` normalised; unique among siblings
    state: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    sort_order: Mapped[int] = mapped_column(default=0)
    revision: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TaxonomyLabel(Base):
    """The name of a node in one language other than English."""

    __tablename__ = "taxonomy_labels"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "node_id"],
            ["taxonomy_nodes.organization_id", "taxonomy_nodes.id"],
        ),
    )

    organization_id: Mapped[UUID]
    node_id: Mapped[UUID] = mapped_column(primary_key=True)
    language: Mapped[str] = mapped_column(String(3), primary_key=True)
    label: Mapped[str] = mapped_column(String(200))


class Exam(Base):
    """An exam a past-year question comes from: JEE Main, NEET, CBSE..."""

    __tablename__ = "exams"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_id)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"))
    name: Mapped[str] = mapped_column(String(200))
    name_key: Mapped[str] = mapped_column(String(400))  # ``name`` normalised; unique per coaching
    short_code: Mapped[str | None] = mapped_column(String(20))
    state: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    revision: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Source(Base):
    """Where a question was taken from: a book, a module, a test series, a past-year paper."""

    __tablename__ = "sources"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_id)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"))
    kind: Mapped[str] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(200))
    name_key: Mapped[str] = mapped_column(String(400))  # unique per coaching and kind
    state: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    revision: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Concept(Base):
    """An idea a question is about, belonging to one subject of the syllabus."""

    __tablename__ = "concepts"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "subject_id", "subject_kind"],
            ["taxonomy_nodes.organization_id", "taxonomy_nodes.id", "taxonomy_nodes.kind"],
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_id)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"))
    subject_id: Mapped[UUID]
    subject_kind: Mapped[str] = mapped_column(String(20), default="SUBJECT")
    name: Mapped[str] = mapped_column(String(200))  # the English name
    name_key: Mapped[str] = mapped_column(String(400))  # unique within the subject
    state: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    revision: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ConceptLabel(Base):
    """The name of a concept in one language other than English."""

    __tablename__ = "concept_labels"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "concept_id"], ["concepts.organization_id", "concepts.id"]
        ),
    )

    organization_id: Mapped[UUID]
    concept_id: Mapped[UUID] = mapped_column(primary_key=True)
    language: Mapped[str] = mapped_column(String(3), primary_key=True)
    label: Mapped[str] = mapped_column(String(200))


class ConceptAlias(Base):
    """Another way to say a concept's name; names one concept within its subject."""

    __tablename__ = "concept_aliases"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "concept_id", "subject_id"],
            ["concepts.organization_id", "concepts.id", "concepts.subject_id"],
        ),
    )

    organization_id: Mapped[UUID]
    concept_id: Mapped[UUID] = mapped_column(primary_key=True)
    subject_id: Mapped[UUID]
    alias: Mapped[str] = mapped_column(String(200))
    alias_key: Mapped[str] = mapped_column(String(400), primary_key=True)


class CatalogueImport(Base):
    """A syllabus import the admin has previewed: the checked rows, kept until applied."""

    __tablename__ = "catalogue_imports"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_id)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"))
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    file_name: Mapped[str] = mapped_column(String(200))
    file_sha256: Mapped[str] = mapped_column(String(64))
    state: Mapped[str] = mapped_column(String(20), default="PREVIEWED")  # or APPLIED
    counts: Mapped[dict[str, int]] = mapped_column(JSONB)
    base_fingerprint: Mapped[str] = mapped_column(String(64))  # the syllabus the preview saw
    rows: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
