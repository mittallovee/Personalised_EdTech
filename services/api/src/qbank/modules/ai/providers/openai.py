"""OpenAI: the Responses API and the model list (ADR-0009, ADR-0023).

Written from OpenAI's published API reference and checked with recorded answers; not yet tried
against the live service (run ``qbank ai-smoke``). The key goes in the ``Authorization`` header; the
answer is asked for as JSON that matches the schema (``text.format``, strict).
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

BASE_URL = "https://api.openai.com"
# The list holds every kind of model; these are not ones that read and write text.
_NOT_TEXT = (
    "embedding",
    "whisper",
    "tts",
    "dall-e",
    "moderation",
    "image",
    "audio",
    "realtime",
    "transcribe",
    "sora",
    "speech",
)


class OpenAIProvider:
    name = Provider.OPENAI

    def __init__(self, http: Http) -> None:
        self._http = http

    @staticmethod
    def _headers(api_key: str) -> dict[str, str]:
        return {"authorization": f"Bearer {api_key}", "content-type": "application/json"}

    def list_models(self, api_key: str) -> list[ModelInfo]:
        page = self._http.get(f"{BASE_URL}/v1/models", headers=self._headers(api_key))
        models: list[ModelInfo] = []
        for item in page.get("data") or []:
            model_id = item.get("id") if isinstance(item, dict) else None
            if not isinstance(model_id, str) or not model_id:
                continue
            if any(word in model_id.lower() for word in _NOT_TEXT):
                continue
            models.append(ModelInfo(model_id, model_id))
        return models

    def generate_structured(self, api_key: str, request: StructuredRequest) -> StructuredResult:
        body: dict[str, Any] = {
            "model": request.model_id,
            "instructions": request.system,
            "input": request.user,
            "max_output_tokens": request.max_output_tokens,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": request.schema_name,
                    "schema": request.schema,
                    "strict": True,
                }
            },
            "store": False,
        }
        if request.temperature is not None:
            body["temperature"] = request.temperature
        answer = self._http.post(
            f"{BASE_URL}/v1/responses", headers=self._headers(api_key), body=body
        )
        if answer.get("status") not in (None, "completed"):
            raise ProviderError(ProviderErrorKind.BAD_OUTPUT)  # incomplete, failed or cancelled
        texts: list[str] = []
        for item in answer.get("output") or []:
            if not isinstance(item, dict) or item.get("type") != "message":
                continue
            for part in item.get("content") or []:
                if not isinstance(part, dict):
                    continue
                if part.get("type") == "refusal":
                    raise ProviderError(ProviderErrorKind.BAD_OUTPUT)
                if part.get("type") == "output_text" and isinstance(part.get("text"), str):
                    texts.append(part["text"])
        if not texts:
            raise bad_output()
        usage = answer.get("usage")
        usage = usage if isinstance(usage, dict) else {}
        return StructuredResult(
            data=json_object("".join(texts)),
            tokens_in=count(usage.get("input_tokens")),
            tokens_out=count(usage.get("output_tokens")),
        )
