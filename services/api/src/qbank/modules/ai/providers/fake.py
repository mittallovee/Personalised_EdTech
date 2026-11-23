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
    BatchAnswer,
    BatchState,
    ModelInfo,
    ProviderError,
    ProviderErrorKind,
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
class FakeBatch:
    """One batch held by the fake provider: the tag the run gave it, and how it stands."""

    tag: str
    request: StructuredRequest
    state: BatchState = BatchState.IN_PROGRESS
    answer: BatchAnswer | None = None


@dataclass
class FakeProvider:
    """Answers each ``generate_structured`` call with the next scripted outcome (a result, or a
    ``ProviderError`` to raise); when the script is empty it answers ``{"ok": true}``."""

    name: Provider = Provider.OPENAI
    models: tuple[ModelInfo, ...] = DEFAULT_MODELS
    script: deque[StructuredResult | ProviderError] = field(default_factory=deque)
    calls: list[tuple[str, StructuredRequest]] = field(default_factory=list)
    listed: list[str] = field(default_factory=list)
    # Batch service (Economy runs). ``submit_calls`` counts every call to ``submit_batch``, so a
    # test can prove a run was handed over at most once.
    batches: dict[str, FakeBatch] = field(default_factory=dict)
    submit_calls: int = 0
    cancelled: list[str] = field(default_factory=list)
    reject_submit: ProviderError | None = None  # a definite refusal: nothing was created
    lose_submit_answer: bool = False  # the batch IS created, but the reply never arrives (timeout)

    def list_models(self, api_key: str) -> list[ModelInfo]:
        self.listed.append(api_key)
        return list(self.models)

    def generate_structured(self, api_key: str, request: StructuredRequest) -> StructuredResult:
        self.calls.append((api_key, request))
        outcome = self.script.popleft() if self.script else StructuredResult({"ok": True}, 10, 5)
        if isinstance(outcome, ProviderError):
            raise outcome
        return outcome

    # --- the batch service ---------------------------------------------------------------------

    def submit_batch(self, api_key: str, *, tag: str, request: StructuredRequest) -> str:
        self.submit_calls += 1
        if self.reject_submit is not None:
            raise self.reject_submit
        batch_id = f"fake-batch-{len(self.batches) + 1}"
        self.batches[batch_id] = FakeBatch(tag, request)
        if self.lose_submit_answer:
            self.lose_submit_answer = False
            raise ProviderError(ProviderErrorKind.TIMEOUT)
        return batch_id

    def batch_status(self, api_key: str, batch_id: str) -> BatchState:
        return self.batches[batch_id].state

    def fetch_batch_answer(self, api_key: str, batch_id: str, *, tag: str) -> BatchAnswer:
        answer = self.batches[batch_id].answer
        return answer if answer is not None else BatchAnswer(error=ProviderErrorKind.BAD_OUTPUT)

    def cancel_batch(self, api_key: str, batch_id: str) -> None:
        self.cancelled.append(batch_id)

    def find_batches_by_tag(self, api_key: str, tag: str) -> list[str]:
        return [batch_id for batch_id, batch in self.batches.items() if batch.tag == tag]

    # Test controls: what the provider does with a batch, later.

    def finish(self, batch_id: str, result: StructuredResult) -> None:
        batch = self.batches[batch_id]
        batch.state, batch.answer = BatchState.DONE, BatchAnswer(result=result)

    def finish_with_error(self, batch_id: str, kind: ProviderErrorKind) -> None:
        batch = self.batches[batch_id]
        batch.state, batch.answer = BatchState.DONE, BatchAnswer(error=kind)

    def end(self, batch_id: str, state: BatchState) -> None:
        self.batches[batch_id].state = state
