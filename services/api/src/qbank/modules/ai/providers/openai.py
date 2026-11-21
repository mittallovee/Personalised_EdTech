"""OpenAI: the Responses API, the model list and the Batch API (ADR-0009, ADR-0023).

Written from OpenAI's published API reference and checked with recorded answers; not yet tried
against the live service (run ``qbank ai-smoke``). The key goes in the ``Authorization`` header; the
answer is asked for as JSON that matches the schema (``text.format``, strict).

Economy (batch) runs: a run is one request in its own batch. The request is uploaded as a one-line
JSONL file, and the batch is created with the run's id in its ``metadata``. OpenAI's list of batches
shows each batch's metadata, so a batch whose creation we never heard back about can be found again
by that id: this is what lets Economy be offered for OpenAI (ADR-0009). The documents do not say how
structured output is written inside a batch request body; it is written as in the Responses API
above, which is the documented meaning of ``body``. Unverified until ``qbank ai-smoke`` has run.
"""

import json
from typing import Any

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
from qbank.modules.ai.providers.http import Http, _kind_for, bad_output, count, json_object

BASE_URL = "https://api.openai.com"
TAG_KEY = "qbank_run"  # the batch metadata key that carries the run id
_LIST_PAGE = 100
_MAX_LIST_PAGES = 10
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

    @staticmethod
    def _body(request: StructuredRequest) -> dict[str, Any]:
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
        return body

    def generate_structured(self, api_key: str, request: StructuredRequest) -> StructuredResult:
        answer = self._http.post(
            f"{BASE_URL}/v1/responses", headers=self._headers(api_key), body=self._body(request)
        )
        return self._read(answer)

    @staticmethod
    def _read(answer: dict[str, Any]) -> StructuredResult:
        """The structured answer in a Responses API object (a direct answer or a batch's)."""
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

    # --- the Batch API -------------------------------------------------------------------------

    def submit_batch(self, api_key: str, *, tag: str, request: StructuredRequest) -> str:
        line = json.dumps(
            {
                "custom_id": tag,
                "method": "POST",
                "url": "/v1/responses",
                "body": self._body(request),
            },
            ensure_ascii=False,
        )
        uploaded = self._http.post_file(
            f"{BASE_URL}/v1/files",
            headers={"authorization": f"Bearer {api_key}"},
            fields={"purpose": "batch"},
            file_name="request.jsonl",
            content=(line + "\n").encode("utf-8"),
        )
        file_id = uploaded.get("id")
        if not isinstance(file_id, str) or not file_id:
            raise bad_output()
        created = self._http.post(
            f"{BASE_URL}/v1/batches",
            headers=self._headers(api_key),
            body={
                "input_file_id": file_id,
                "endpoint": "/v1/responses",
                "completion_window": "24h",
                "metadata": {TAG_KEY: tag},
            },
        )
        batch_id = created.get("id")
        if not isinstance(batch_id, str) or not batch_id:
            raise bad_output()
        return batch_id

    def _batch(self, api_key: str, batch_id: str) -> dict[str, Any]:
        return self._http.get(f"{BASE_URL}/v1/batches/{batch_id}", headers=self._headers(api_key))

    def batch_status(self, api_key: str, batch_id: str) -> BatchState:
        status = self._batch(api_key, batch_id).get("status")
        if status == "completed":
            return BatchState.DONE
        if status == "failed":
            return BatchState.FAILED
        if status == "expired":
            return BatchState.EXPIRED
        if status == "cancelled":
            return BatchState.CANCELLED
        # validating, in_progress, finalizing, cancelling, and anything new: not ended yet
        return BatchState.IN_PROGRESS

    def _lines(self, api_key: str, file_id: object) -> list[dict[str, Any]]:
        if not isinstance(file_id, str) or not file_id:
            return []
        text = self._http.get_text(
            f"{BASE_URL}/v1/files/{file_id}/content", headers=self._headers(api_key)
        )
        lines: list[dict[str, Any]] = []
        for raw in text.splitlines():
            if not raw.strip():
                continue
            try:
                parsed = json.loads(raw)
            except ValueError:
                continue
            if isinstance(parsed, dict):
                lines.append(parsed)
        return lines

    def fetch_batch_answer(self, api_key: str, batch_id: str, *, tag: str) -> BatchAnswer:
        batch = self._batch(api_key, batch_id)
        for file_key in ("output_file_id", "error_file_id"):
            for line in self._lines(api_key, batch.get(file_key)):
                if line.get("custom_id") != tag:
                    continue
                response = line.get("response")
                if isinstance(response, dict):
                    status = response.get("status_code")
                    body = response.get("body")
                    if status == 200 and isinstance(body, dict):
                        try:
                            return BatchAnswer(result=self._read(body))
                        except ProviderError as problem:
                            return BatchAnswer(error=problem.kind)
                    if isinstance(status, int):
                        return BatchAnswer(error=_kind_for(status))
                return BatchAnswer(error=ProviderErrorKind.UNAVAILABLE)  # an error line
        return BatchAnswer(error=ProviderErrorKind.BAD_OUTPUT)  # ended, but no line for the run

    def cancel_batch(self, api_key: str, batch_id: str) -> None:
        self._http.post(
            f"{BASE_URL}/v1/batches/{batch_id}/cancel", headers=self._headers(api_key), body={}
        )

    def find_batches_by_tag(self, api_key: str, tag: str) -> list[str]:
        found: list[str] = []
        after: str | None = None
        for _ in range(_MAX_LIST_PAGES):
            params: dict[str, Any] = {"limit": _LIST_PAGE}
            if after is not None:
                params["after"] = after
            page = self._http.get(
                f"{BASE_URL}/v1/batches", headers=self._headers(api_key), params=params
            )
            for item in page.get("data") or []:
                if not isinstance(item, dict):
                    continue
                meta = item.get("metadata")
                if isinstance(meta, dict) and meta.get(TAG_KEY) == tag:
                    batch_id = item.get("id")
                    if isinstance(batch_id, str):
                        found.append(batch_id)
            last = page.get("last_id")
            if page.get("has_more") is True and isinstance(last, str) and last:
                after = last
            else:
                break
        return found
