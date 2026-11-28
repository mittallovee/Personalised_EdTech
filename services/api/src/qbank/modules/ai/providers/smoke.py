"""A tiny live check of one provider and key, for ``qbank ai-smoke`` (M5 design note §12).

CI never calls a real provider, so this is how the owner finds out that an adapter and a key really
work: list the models, and (when a model is named) ask one for ``{"ok": true}``. The report says
what happened in words and never contains the key.
"""

import secrets
import time
from collections.abc import Callable

from qbank.modules.ai.providers.base import (
    AIProvider,
    BatchProvider,
    BatchState,
    ProviderError,
    StructuredRequest,
)

_FIND_TRIES = 5
_FIND_PAUSE = 3.0
_POLL_PAUSE = 10.0

SCHEMA = {
    "type": "object",
    "properties": {"ok": {"type": "boolean"}},
    "required": ["ok"],
    "additionalProperties": False,
}


def smoke(provider: AIProvider, api_key: str, model_id: str | None) -> tuple[bool, list[str]]:
    """Returns whether every step worked, and one line per step."""
    lines: list[str] = []
    good = True
    try:
        models = provider.list_models(api_key)
        priced = sum(1 for m in models if m.price_in_per_mtok is not None)
        lines.append(f"List models: {len(models)} found, {priced} with a price.")
    except ProviderError as problem:
        return False, [f"List models: FAILED ({problem})"]
    if model_id is None:
        lines.append("Ask a model: skipped (name one with --model to try a request).")
        return good, lines
    request = StructuredRequest(
        model_id=model_id,
        system="You answer with JSON only.",
        user='Reply with {"ok": true}.',
        schema_name="smoke",
        schema=SCHEMA,
        max_output_tokens=50,
    )
    try:
        result = provider.generate_structured(api_key, request)
    except ProviderError as problem:
        return False, [*lines, f"Ask a model: FAILED ({problem})"]
    if result.data.get("ok") is not True:
        lines.append("Ask a model: FAILED (the answer was valid JSON but not what was asked for).")
        return False, lines
    lines.append(f"Ask a model: worked ({result.tokens_in} tokens in, {result.tokens_out} out).")
    return good, lines


def smoke_batch(
    adapter: BatchProvider,
    api_key: str,
    model_id: str,
    *,
    wait_seconds: int = 0,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> tuple[bool, list[str]]:
    """The same for Economy: send one tiny batch, find it again by its tag, read its state, and
    (given ``wait_seconds``) wait for its answer. A batch not done in time is cancelled.

    A batch is slow by design (up to 24 hours), so by default this proves the four calls Economy
    depends on (send, find by tag, status, cancel) and does not wait for an answer. Whatever the
    provider had already finished before a cancel may still be charged: a few tokens.
    """
    lines: list[str] = []
    tag = f"smoke-{secrets.token_hex(8)}"
    request = StructuredRequest(
        model_id=model_id,
        system="You answer with JSON only.",
        user='Reply with {"ok": true}.',
        schema_name="smoke",
        schema=SCHEMA,
        max_output_tokens=50,
    )
    try:
        batch_id = adapter.submit_batch(api_key, tag=tag, request=request)
    except ProviderError as problem:
        return False, [f"Send a batch: FAILED ({problem})"]
    lines.append("Send a batch: worked.")
    good = True
    try:
        found: list[str] = []
        for attempt in range(_FIND_TRIES):
            found = adapter.find_batches_by_tag(api_key, tag)
            if found or attempt == _FIND_TRIES - 1:
                break
            sleep(_FIND_PAUSE)  # a new batch can take a moment to show in the provider's list
        if batch_id in found:
            lines.append("Find it again by its tag: worked.")
        else:
            good = False
            lines.append("Find it again by its tag: FAILED (it was not in the provider's list).")
        state = adapter.batch_status(api_key, batch_id)
        lines.append(f"Ask its state: worked ({state.value}).")
        deadline = clock() + wait_seconds
        while state is BatchState.IN_PROGRESS and clock() < deadline:
            sleep(_POLL_PAUSE)
            state = adapter.batch_status(api_key, batch_id)
        if wait_seconds:
            lines.append(f"After waiting: {state.value}.")
        if state is BatchState.DONE:
            answer = adapter.fetch_batch_answer(api_key, batch_id, tag=tag)
            if answer.result is not None and answer.result.data.get("ok") is True:
                lines.append(
                    f"Read its answer: worked ({answer.result.tokens_in} tokens in,"
                    f" {answer.result.tokens_out} out)."
                )
            else:
                good = False
                lines.append("Read its answer: FAILED (not the answer that was asked for).")
        elif state is BatchState.IN_PROGRESS:
            adapter.cancel_batch(api_key, batch_id)
            lines.append("Cancel it: worked (asked the provider to stop).")
        else:
            good = False
            lines.append(f"The batch ended without an answer ({state.value}).")
    except ProviderError as problem:
        good = False
        lines.append(f"FAILED ({problem}).")
        try:  # leave nothing running that costs money
            adapter.cancel_batch(api_key, batch_id)
        except ProviderError:
            lines.append("The batch could not be cancelled: check the provider's dashboard.")
    return good, lines
