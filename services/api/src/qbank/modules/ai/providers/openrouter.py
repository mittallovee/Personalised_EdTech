"""OpenRouter: chat completions and the model list with prices (ADR-0009, ADR-0023).

Written from OpenRouter's published API reference and checked with recorded answers; not yet tried
against the live service (run ``qbank ai-smoke``). The key goes in the ``Authorization`` header. The
model list gives prices (US dollars per token, as text), which become dollars per million tokens;
a price that is missing, negative or "dynamic" is unknown.
"""

from decimal import Decimal, InvalidOperation
from typing import Any

from qbank.modules.ai.names import Provider
from qbank.modules.ai.providers.base import (
    ModelInfo,
    ProviderError,
    ProviderErrorKind,
    StructuredRequest,
    StructuredResult,
    jpeg_base64,
)
from qbank.modules.ai.providers.http import Http, bad_output, count, json_object

BASE_URL = "https://openrouter.ai/api/v1"
_MILLION = Decimal(1_000_000)


def per_million(value: object) -> Decimal | None:
    """A per-token price as given (text such as "0.000003") in dollars per million tokens."""
    if isinstance(value, bool) or not isinstance(value, str | int):
        return None
    try:
        price = Decimal(str(value))
    except InvalidOperation:
        return None
    if not price.is_finite() or price < 0:  # "-1" marks a price that depends on the request
        return None
    return (price * _MILLION).normalize()


def _cost(value: object) -> Decimal | None:
    if isinstance(value, bool) or not isinstance(value, int | float | str):
        return None
    try:
        cost = Decimal(str(value))
    except InvalidOperation:
        return None
    return cost if cost.is_finite() and cost >= 0 else None


def _content(request: StructuredRequest) -> str | list[dict[str, Any]]:
    """The user's text, or the text and the pictures as parts of one message."""
    if not request.images:
        return request.user
    parts: list[dict[str, Any]] = [{"type": "text", "text": request.user}]
    parts += [
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{jpeg_base64(data)}"}}
        for data in request.images
    ]
    return parts


class OpenRouterProvider:
    name = Provider.OPENROUTER

    def __init__(self, http: Http) -> None:
        self._http = http

    @staticmethod
    def _headers(api_key: str) -> dict[str, str]:
        return {"authorization": f"Bearer {api_key}", "content-type": "application/json"}

    def list_models(self, api_key: str) -> list[ModelInfo]:
        page = self._http.get(f"{BASE_URL}/models", headers=self._headers(api_key))
        models: list[ModelInfo] = []
        for item in page.get("data") or []:
            model_id = item.get("id") if isinstance(item, dict) else None
            if not isinstance(model_id, str) or not model_id:
                continue
            name = item.get("name")
            pricing = item.get("pricing")
            pricing = pricing if isinstance(pricing, dict) else {}
            architecture = item.get("architecture")
            inputs = (
                architecture.get("input_modalities") if isinstance(architecture, dict) else None
            )
            parameters = item.get("supported_parameters")
            models.append(
                ModelInfo(
                    model_id,
                    name if isinstance(name, str) and name else model_id,
                    supports_vision=("image" in inputs) if isinstance(inputs, list) else None,
                    supports_json=(
                        "structured_outputs" in parameters or "response_format" in parameters
                    )
                    if isinstance(parameters, list)
                    else None,
                    context_tokens=count(item.get("context_length")),
                    price_in_per_mtok=per_million(pricing.get("prompt")),
                    price_out_per_mtok=per_million(pricing.get("completion")),
                )
            )
        return models

    def generate_structured(self, api_key: str, request: StructuredRequest) -> StructuredResult:
        body: dict[str, Any] = {
            "model": request.model_id,
            "messages": [
                {"role": "system", "content": request.system},
                {"role": "user", "content": _content(request)},
            ],
            "max_tokens": request.max_output_tokens,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": request.schema_name,
                    "strict": True,
                    "schema": request.schema,
                },
            },
        }
        if request.temperature is not None:
            body["temperature"] = request.temperature
        answer = self._http.post(
            f"{BASE_URL}/chat/completions", headers=self._headers(api_key), body=body
        )
        choices = answer.get("choices")
        first = choices[0] if isinstance(choices, list) and choices else None
        if not isinstance(first, dict) or first.get("finish_reason") in (
            "length",
            "content_filter",
        ):
            raise ProviderError(ProviderErrorKind.BAD_OUTPUT)
        message = first.get("message")
        text = message.get("content") if isinstance(message, dict) else None
        if not isinstance(text, str) or not text.strip():
            raise bad_output()
        usage = answer.get("usage")
        usage = usage if isinstance(usage, dict) else {}
        return StructuredResult(
            data=json_object(text),
            tokens_in=count(usage.get("prompt_tokens")),
            tokens_out=count(usage.get("completion_tokens")),
            cost_usd=_cost(usage.get("cost")),
        )
