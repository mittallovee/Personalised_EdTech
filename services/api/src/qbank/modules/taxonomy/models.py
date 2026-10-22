from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, ForeignKeyConstraint, String, func
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
