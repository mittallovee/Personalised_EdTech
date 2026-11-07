"""The ``assets`` table (migration 0021): one stored file of a coaching."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from qbank.core.db import Base
from qbank.core.ids import new_id


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_id)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"))
    kind: Mapped[str] = mapped_column(String(16))
    content_type: Mapped[str] = mapped_column(String(32))
    byte_size: Mapped[int]
    sha256: Mapped[str] = mapped_column(String(64))
    width: Mapped[int]
    height: Mapped[int]
    storage_key: Mapped[str]
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
