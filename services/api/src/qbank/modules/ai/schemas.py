from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SecretStr

from qbank.modules.ai.names import Provider


class SetKey(BaseModel):
    """The key as the provider gave it. Write-only: no response ever carries it."""

    key: SecretStr = Field(
        description="The provider's API key, as copied from the provider. It is sealed on the"
        " server and never shown again; only its last four characters are.",
    )


class ProviderKeyOut(BaseModel):
    provider: Provider
    configured: bool
    last4: str | None = Field(
        description="The last four characters, so a person can tell which key is stored."
    )
    updated_at: datetime | None


class KeysOut(BaseModel):
    encryption_ready: bool = Field(
        description="False when the server has no master encryption key: keys cannot be stored"
        " until whoever runs the server sets `AI_KEYS_MASTER_KEY`."
    )
    data: list[ProviderKeyOut]


# --- The model list (H-03, H-17) -----------------------------------------------------------------

Price = Annotated[Decimal, Field(ge=0, le=100000, max_digits=12, decimal_places=6)]
Discount = Annotated[Decimal, Field(gt=0, le=1, max_digits=5, decimal_places=4)]


class OverlayOut(BaseModel):
    """What the admin entered; null where nothing was entered (the provider's value counts)."""

    supports_vision: bool | None
    supports_json: bool | None
    price_in: str | None
    price_out: str | None
    batch_supported: bool | None
    batch_discount: str | None


class ModelOut(BaseModel):
    id: UUID
    provider: Provider
    model_id: str
    display_name: str
    enabled: bool
    available: bool = Field(
        description="False when the provider's list no longer includes it; it cannot be enabled."
    )
    supports_vision: bool | None = Field(description="Effective: the overlay, else the provider's.")
    supports_json: bool | None = Field(description="Effective: the overlay, else the provider's.")
    context_tokens: int | None
    price_in_per_mtok: str | None = Field(
        description="US dollars per million input tokens, effective; null = unknown."
    )
    price_out_per_mtok: str | None = Field(
        description="US dollars per million output tokens, effective; null = unknown."
    )
    price_source: Literal["PROVIDER", "ADMIN", "UNKNOWN"]
    batch_supported: bool = Field(
        description="Whether Economy (batch) runs are offered: only when the admin says so."
    )
    batch_discount: str | None
    overlay: OverlayOut
    fetched_at: datetime
    revision: int


class ProviderStateOut(BaseModel):
    provider: Provider
    configured: bool = Field(description="Whether the coaching has a key stored for it.")
    last_refreshed_at: datetime | None
    last_error: str | None = Field(
        description="The kind of failure of the last refresh (`AUTH`, `RATE_LIMITED`, `TIMEOUT`,"
        " `UNAVAILABLE`, `NO_KEY`, `KEY_UNREADABLE` ...), or null when it worked."
    )


class ModelsOut(BaseModel):
    data: list[ModelOut]
    providers: list[ProviderStateOut]


class OverlayIn(BaseModel):
    """Only what is sent changes. A value of `null` removes the admin's entry for that fact, so the
    provider's value counts again."""

    model_config = ConfigDict(extra="forbid")

    supports_vision: bool | None = None
    supports_json: bool | None = None
    price_in: Price | None = None
    price_out: Price | None = None
    batch_supported: bool | None = None
    batch_discount: Discount | None = None


class UpdateModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool | None = Field(
        default=None, description="Offer the model to faculty (true) or stop offering it (false)."
    )
    overlay: OverlayIn | None = None


class RefreshIn(BaseModel):
    provider: Provider


class RefreshOut(BaseModel):
    job_id: UUID
