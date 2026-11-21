from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, LargeBinary, String, func
from sqlalchemy.orm import Mapped, mapped_column

from qbank.core.db import Base
from qbank.core.ids import new_id


class ProviderKey(Base):
    """A coaching's API key for one provider, sealed (migration 0034, ADR-0023).

    The clear key is never stored: ``ciphertext`` is AES-256-GCM output, ``nonce`` its nonce and
    ``key_id`` names the master key that sealed it. ``last4`` is all that is ever shown.
    """

    __tablename__ = "ai_provider_keys"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_id)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"))
    provider: Mapped[str] = mapped_column(String(20))
    ciphertext: Mapped[bytes] = mapped_column(LargeBinary)
    nonce: Mapped[bytes] = mapped_column(LargeBinary)
    key_id: Mapped[str] = mapped_column(String(20))
    last4: Mapped[str] = mapped_column(String(4))
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), server_default=func.now()
    )
    revision: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
