"""A tiny live check of one provider and key, for ``qbank ai-smoke`` (M5 design note §12).

CI never calls a real provider, so this is how the owner finds out that an adapter and a key really
work: list the models, and (when a model is named) ask one for ``{"ok": true}``. The report says
what happened in words and never contains the key.
"""

from qbank.modules.ai.providers.base import AIProvider, ProviderError, StructuredRequest

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
