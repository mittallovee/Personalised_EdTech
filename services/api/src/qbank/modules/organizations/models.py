from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, ForeignKeyConstraint, String, func
from sqlalchemy.orm import Mapped, mapped_column

from qbank.core.db import Base
from qbank.core.ids import new_id


class Organization(Base):
    """A coaching (tenant). Every coaching-owned row elsewhere carries its ``id``."""

    __tablename__ = "organizations"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_id)
    display_name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Kolkata")
    revision: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Membership(Base):
    """Links a user to a coaching with a role (OWNER, ADMIN or FACULTY)."""

    __tablename__ = "memberships"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_id)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"))
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    role: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    revision: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MembershipGrant(Base):
    """One extra right (QC, APPROVE, …) given to a faculty membership (core/permissions.Grant)."""

    __tablename__ = "membership_grants"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "membership_id"], ["memberships.organization_id", "memberships.id"]
        ),
    )

    organization_id: Mapped[UUID]
    membership_id: Mapped[UUID] = mapped_column(primary_key=True)
    grant_name: Mapped[str] = mapped_column(String(40), primary_key=True)
    granted_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
