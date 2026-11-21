from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    Numeric,
    String,
    func,
)
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
    # When this provider's model list was last fetched, and the kind of failure of the last try
    # (``None`` when it worked). Never any text from the provider.
    models_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    models_error: Mapped[str | None] = mapped_column(String(30))


class AiModel(Base):
    """One model a provider lists for a coaching (migration 0035, H-03, H-17).

    ``supports_*`` and ``price_*`` are what the provider's list said; the ``overlay_*`` columns are
    the admin's own values and win where set. A refresh changes the first group and ``available``,
    never the overlay or ``enabled``. Prices are US dollars per million tokens, exact, ``None`` =
    unknown.
    """

    __tablename__ = "ai_models"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_id)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"))
    provider: Mapped[str] = mapped_column(String(20))
    model_id: Mapped[str] = mapped_column(String(200))
    display_name: Mapped[str] = mapped_column(String(300))
    supports_vision: Mapped[bool | None] = mapped_column(Boolean)
    supports_json: Mapped[bool | None] = mapped_column(Boolean)
    context_tokens: Mapped[int | None] = mapped_column(Integer)
    price_in: Mapped[Decimal | None] = mapped_column(Numeric(14, 6))
    price_out: Mapped[Decimal | None] = mapped_column(Numeric(14, 6))
    overlay_supports_vision: Mapped[bool | None] = mapped_column(Boolean)
    overlay_supports_json: Mapped[bool | None] = mapped_column(Boolean)
    overlay_price_in: Mapped[Decimal | None] = mapped_column(Numeric(14, 6))
    overlay_price_out: Mapped[Decimal | None] = mapped_column(Numeric(14, 6))
    overlay_batch_supported: Mapped[bool | None] = mapped_column(Boolean)
    overlay_batch_discount: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    available: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), server_default=func.now()
    )
    revision: Mapped[int] = mapped_column(Integer, default=1, server_default="1")


class AiSettings(Base):
    """A coaching's dollar-to-rupee rate and default monthly budget (migration 0036).

    ``None`` rate = not entered, so no budget can be applied; ``None`` budget = no limit.
    """

    __tablename__ = "ai_settings"

    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), primary_key=True)
    usd_to_inr: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    default_budget_inr: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    revision: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    updated_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), server_default=func.now()
    )


class OperationSetting(Base):
    """The model, mode and fallbacks a coaching offers first for one operation (migration 0036)."""

    __tablename__ = "ai_operation_settings"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_id)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"))
    operation: Mapped[str] = mapped_column(String(20))
    default_model_id: Mapped[UUID | None] = mapped_column()
    default_mode: Mapped[str] = mapped_column(String(10), default="NOW", server_default="NOW")
    fallback_1_id: Mapped[UUID | None] = mapped_column()
    fallback_2_id: Mapped[UUID | None] = mapped_column()
    revision: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    updated_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), server_default=func.now()
    )


class AiBudget(Base):
    """A person's own monthly budget in rupees, where not the default (migration 0036)."""

    __tablename__ = "ai_budgets"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_id)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"))
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    monthly_inr: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    revision: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    updated_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), server_default=func.now()
    )
