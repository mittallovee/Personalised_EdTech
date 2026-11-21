"""Anthropic: the Messages API and the model list (ADR-0009, ADR-0023).

Written from Anthropic's published API reference and checked with recorded answers; not yet tried
against the live service (run ``qbank ai-smoke``). The key goes in ``x-api-key``; the answer is
asked for as JSON that matches the schema (``output_config.format``).
"""

from typing import Any

from qbank.modules.ai.names import Provider
from qbank.modules.ai.providers.base import (
    ModelInfo,
    ProviderError,
    ProviderErrorKind,
    StructuredRequest,
    StructuredResult,
)
from qbank.modules.ai.providers.http import Http, bad_output, count, json_object

BASE_URL = "https://api.anthropic.com"
API_VERSION = "2023-06-01"
_MAX_PAGES = 10
_PAGE = 1000


class AnthropicProvider:
    name = Provider.ANTHROPIC

    def __init__(self, http: Http) -> None:
        self._http = http

    @staticmethod
    def _headers(api_key: str) -> dict[str, str]:
        return {
            "x-api-key": api_key,
            "anthropic-version": API_VERSION,
            "content-type": "application/json",
        }

    def list_models(self, api_key: str) -> list[ModelInfo]:
        models: list[ModelInfo] = []
        after: str | None = None
        for _ in range(_MAX_PAGES):
            params: dict[str, Any] = {"limit": _PAGE}
            if after is not None:
                params["after_id"] = after
            page = self._http.get(
                f"{BASE_URL}/v1/models", headers=self._headers(api_key), params=params
            )
            for item in page.get("data") or []:
                model_id = item.get("id") if isinstance(item, dict) else None
                if not isinstance(model_id, str) or not model_id:
                    continue
                display = item.get("display_name")
                models.append(
                    ModelInfo(
                        model_id, display if isinstance(display, str) and display else model_id
                    )
                )
            last = page.get("last_id")
            if page.get("has_more") is True and isinstance(last, str) and last:
                after = last
            else:
                break
        return models

    def generate_structured(self, api_key: str, request: StructuredRequest) -> StructuredResult:
        body: dict[str, Any] = {
            "model": request.model_id,
            "max_tokens": request.max_output_tokens,
            "system": request.system,
            "messages": [{"role": "user", "content": request.user}],
            "output_config": {"format": {"type": "json_schema", "schema": request.schema}},
        }
        if request.temperature is not None:
            body["temperature"] = request.temperature
        answer = self._http.post(
            f"{BASE_URL}/v1/messages", headers=self._headers(api_key), body=body
        )
        if answer.get("stop_reason") in ("max_tokens", "refusal"):
            raise ProviderError(ProviderErrorKind.BAD_OUTPUT)
        blocks = answer.get("content")
        texts = [
            block["text"]
            for block in (blocks if isinstance(blocks, list) else [])
            if isinstance(block, dict)
            and block.get("type") == "text"
            and isinstance(block.get("text"), str)
        ]
        if not texts:
            raise bad_output()
        usage = answer.get("usage")
        usage = usage if isinstance(usage, dict) else {}
        return StructuredResult(
            data=json_object("".join(texts)),
            tokens_in=count(usage.get("input_tokens")),
            tokens_out=count(usage.get("output_tokens")),
        )
