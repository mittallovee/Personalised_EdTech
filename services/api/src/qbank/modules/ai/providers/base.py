"""What every AI provider adapter offers, and the one way its calls fail (M5 design note §3).

No provider's name or request shape appears outside the adapter for it. An adapter is handed the
coaching's clear API key for one call and keeps nothing: it never stores, logs or returns the key,
and an error it raises never contains the key or any text of the request or the response.
"""

import base64
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

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
    # Pictures the model is shown with the data: JPEGs made by us (M6, G-04). Empty for every
    # operation that only reads text. Only a model whose catalogue entry says it can read pictures
    # may be given any (the orchestrator checks); each adapter puts them in its provider's shape.
    images: tuple[bytes, ...] = ()


def jpeg_base64(data: bytes) -> str:
    """A JPEG as base64 text, for the providers that take pictures inline."""
    return base64.b64encode(data).decode("ascii")


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


class BatchState(StrEnum):
    """Where a provider says a batch is. ``DONE`` means it ended and an answer (or the reason there
    is none) can be fetched; the others are endings without one."""

    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True, slots=True)
class BatchAnswer:
    """The answer of the one request in a batch: a result, or the kind of error the provider gave
    for it. Exactly one of the two is set."""

    result: StructuredResult | None = None
    error: ProviderErrorKind | None = None


@runtime_checkable
class BatchProvider(Protocol):
    """What an adapter adds when its provider has a batch service AND lets a batch be found again
    by a tag we gave it (ADR-0009: Economy is offered only for such providers, so a submission whose
    outcome is unknown can be reconciled and never sent twice).

    Each run is one request in its own batch. ``tag`` is the run's id; it is the only identifier a
    run has at the provider before the provider's own batch id comes back.
    """

    def submit_batch(self, api_key: str, *, tag: str, request: StructuredRequest) -> str:
        """Hand the request to the provider's batch service; returns the provider's batch id."""
        ...

    def batch_status(self, api_key: str, batch_id: str) -> BatchState: ...

    def fetch_batch_answer(self, api_key: str, batch_id: str, *, tag: str) -> BatchAnswer: ...

    def cancel_batch(self, api_key: str, batch_id: str) -> None:
        """Ask the provider to stop. It is not instant: an answer may still arrive."""
        ...

    def find_batches_by_tag(self, api_key: str, tag: str) -> list[str]:
        """The ids of the provider's batches that carry ``tag`` (empty if none is visible yet)."""
        ...
