"""What every AI provider adapter offers, and the one way its calls fail (M5 design note §3).

No provider's name or request shape appears outside the adapter for it. An adapter is handed the
coaching's clear API key for one call and keeps nothing: it never stores, logs or returns the key,
and an error it raises never contains the key or any text of the request or the response.
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Any, Protocol

from qbank.modules.ai.names import Provider


@dataclass(frozen=True, slots=True)
class ModelInfo:
    """One model as a provider lists it. ``None`` means the provider did not say."""

    model_id: str
    display_name: str
    supports_vision: bool | None = None
    supports_json: bool | None = None
    context_tokens: int | None = None
    # US dollars per million tokens, from the provider's own list when it gives prices; else None
    # (unknown), and an admin can add them as an overlay (H-17). Never a float.
    price_in_per_mtok: Decimal | None = None
    price_out_per_mtok: Decimal | None = None


@dataclass(frozen=True, slots=True)
class StructuredRequest:
    """One request for an answer that must match a JSON schema. ``system`` holds the instructions
    and ``user`` the data (the question), kept apart so the data is never read as instructions."""

    model_id: str
    system: str
    user: str
    schema_name: str
    schema: dict[str, Any]
    max_output_tokens: int
    temperature: float | None = None


@dataclass(frozen=True, slots=True)
class StructuredResult:
    data: dict[str, Any]
    tokens_in: int | None
    tokens_out: int | None
    # What the provider itself says the call cost (OpenRouter does), in US dollars; else None, and
    # the ledger works it out from the model's prices.
    cost_usd: Decimal | None = None


class ProviderErrorKind(StrEnum):
    AUTH = "AUTH"  # the key was refused or is not allowed to do this
    RATE_LIMITED = "RATE_LIMITED"
    TIMEOUT = "TIMEOUT"
    UNAVAILABLE = "UNAVAILABLE"  # the provider is down, overloaded or unreachable
    BAD_REQUEST = "BAD_REQUEST"  # the provider refused the request itself
    BAD_OUTPUT = (
        "BAD_OUTPUT"  # an answer came back, but not one we can use (cut off, refused, not JSON)
    )
    TOO_LARGE = "TOO_LARGE"  # the answer was bigger than we read


_RETRYABLE = frozenset(
    {ProviderErrorKind.RATE_LIMITED, ProviderErrorKind.TIMEOUT, ProviderErrorKind.UNAVAILABLE}
)


class ProviderError(Exception):
    """A provider call failed. The message is safe to show and store: it says what kind of failure
    it was and the HTTP status, never the key, the request or the response."""

    def __init__(
        self,
        kind: ProviderErrorKind,
        *,
        status: int | None = None,
        retry_after_seconds: float | None = None,
    ) -> None:
        self.kind = kind
        self.status = status
        self.retry_after_seconds = retry_after_seconds
        suffix = f" (HTTP {status})" if status is not None else ""
        super().__init__(f"provider call failed: {kind.value}{suffix}")

    @property
    def retryable(self) -> bool:
        """Worth trying again, or another model: a timeout, a rate limit, an outage."""
        return self.kind in _RETRYABLE


class AIProvider(Protocol):
    """One provider behind the same two calls. Batch calls join this in the Economy step (5h)."""

    name: Provider

    def list_models(self, api_key: str) -> list[ModelInfo]: ...

    def generate_structured(self, api_key: str, request: StructuredRequest) -> StructuredResult: ...
