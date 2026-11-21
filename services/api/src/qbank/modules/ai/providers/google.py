"""Google (Gemini API): generateContent and the model list (ADR-0009, ADR-0023).

Written from Google's published API reference and checked with recorded answers; not yet tried
against the live service (run ``qbank ai-smoke``). The key goes in ``x-goog-api-key``, never in the
address; the answer is asked for as JSON that matches the schema (``responseJsonSchema``).
"""

import re
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

BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
_MAX_PAGES = 10
_PAGE = 1000
# What Google's model ids look like (gemini-2.5-pro, gemma-3-27b-it). Anything else is not put in
# an address.
_MODEL_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}")


class GoogleProvider:
    name = Provider.GOOGLE

    def __init__(self, http: Http) -> None:
        self._http = http

    @staticmethod
    def _headers(api_key: str) -> dict[str, str]:
        return {"x-goog-api-key": api_key, "content-type": "application/json"}

    def list_models(self, api_key: str) -> list[ModelInfo]:
        models: list[ModelInfo] = []
        token: str | None = None
        for _ in range(_MAX_PAGES):
            params: dict[str, Any] = {"pageSize": _PAGE}
            if token is not None:
                params["pageToken"] = token
            page = self._http.get(
                f"{BASE_URL}/models", headers=self._headers(api_key), params=params
            )
            for item in page.get("models") or []:
                if not isinstance(item, dict):
                    continue
                name = item.get("name")
                methods = item.get("supportedGenerationMethods")
                if not isinstance(name, str) or "generateContent" not in (methods or []):
                    continue
                model_id = name.removeprefix("models/")
                display = item.get("displayName")
                models.append(
                    ModelInfo(
                        model_id,
                        display if isinstance(display, str) and display else model_id,
                        context_tokens=count(item.get("inputTokenLimit")),
                    )
                )
            following = page.get("nextPageToken")
            if isinstance(following, str) and following:
                token = following
            else:
                break
        return models

    def generate_structured(self, api_key: str, request: StructuredRequest) -> StructuredResult:
        config: dict[str, Any] = {
            "responseMimeType": "application/json",
            "responseJsonSchema": request.schema,
            "maxOutputTokens": request.max_output_tokens,
        }
        if request.temperature is not None:
            config["temperature"] = request.temperature
        body: dict[str, Any] = {
            "systemInstruction": {"parts": [{"text": request.system}]},
            "contents": [{"role": "user", "parts": [{"text": request.user}]}],
            "generationConfig": config,
        }
        # The model id comes from the catalogue, but it goes into an address, so only the shape a
        # real id has is used: it can only ever be one path segment.
        if not _MODEL_ID.fullmatch(request.model_id) or ".." in request.model_id:
            raise ProviderError(ProviderErrorKind.BAD_REQUEST)
        url = f"{BASE_URL}/models/{request.model_id}:generateContent"
        answer = self._http.post(url, headers=self._headers(api_key), body=body)
        feedback = answer.get("promptFeedback")
        if isinstance(feedback, dict) and feedback.get("blockReason"):
            raise ProviderError(ProviderErrorKind.BAD_OUTPUT)
        candidates = answer.get("candidates")
        first = candidates[0] if isinstance(candidates, list) and candidates else None
        if not isinstance(first, dict) or first.get("finishReason") not in (None, "STOP"):
            raise ProviderError(ProviderErrorKind.BAD_OUTPUT)  # cut off, blocked or recitation
        content = first.get("content")
        parts = content.get("parts") if isinstance(content, dict) else None
        texts = [
            part["text"]
            for part in (parts if isinstance(parts, list) else [])
            if isinstance(part, dict)
            and isinstance(part.get("text"), str)
            and part.get("thought") is not True
        ]
        if not texts:
            raise bad_output()
        usage = answer.get("usageMetadata")
        usage = usage if isinstance(usage, dict) else {}
        out = count(usage.get("candidatesTokenCount"))
        thinking = count(usage.get("thoughtsTokenCount"))
        return StructuredResult(
            data=json_object("".join(texts)),
            tokens_in=count(usage.get("promptTokenCount")),
            tokens_out=None if out is None else out + (thinking or 0),
        )
