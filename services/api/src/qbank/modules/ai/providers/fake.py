"""A provider that answers from a script, for tests and for trying the screens (M5 design note §12).

It speaks the same interface as the real adapters, never touches the network and records every call,
so the orchestrator, budgets and screens can be tested end to end without a real key. Nothing in the
running app selects it unless a later step turns it on for local development.
"""

from collections import deque
from dataclasses import dataclass, field
from decimal import Decimal

from qbank.modules.ai.names import Provider
from qbank.modules.ai.providers.base import (
    ModelInfo,
    ProviderError,
    StructuredRequest,
    StructuredResult,
)

DEFAULT_MODELS = (
    ModelInfo(
        "fake-small",
        "Fake small",
        supports_vision=False,
        supports_json=True,
        price_in_per_mtok=Decimal("1"),
        price_out_per_mtok=Decimal("2"),
    ),
    ModelInfo("fake-unpriced", "Fake with no price", supports_json=True),
)


@dataclass
class FakeProvider:
    """Answers each ``generate_structured`` call with the next scripted outcome (a result, or a
    ``ProviderError`` to raise); when the script is empty it answers ``{"ok": true}``."""

    name: Provider = Provider.OPENAI
    models: tuple[ModelInfo, ...] = DEFAULT_MODELS
    script: deque[StructuredResult | ProviderError] = field(default_factory=deque)
    calls: list[tuple[str, StructuredRequest]] = field(default_factory=list)
    listed: list[str] = field(default_factory=list)

    def list_models(self, api_key: str) -> list[ModelInfo]:
        self.listed.append(api_key)
        return list(self.models)

    def generate_structured(self, api_key: str, request: StructuredRequest) -> StructuredResult:
        self.calls.append((api_key, request))
        outcome = self.script.popleft() if self.script else StructuredResult({"ok": True}, 10, 5)
        if isinstance(outcome, ProviderError):
            raise outcome
        return outcome
