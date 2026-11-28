"""OpenAI: the Responses API, the model list and the Batch API (ADR-0009, ADR-0023).

Written from OpenAI's published API reference and checked with recorded answers; not yet tried
against the live service (run ``qbank ai-smoke``, and ``--batch`` for Economy). The key goes in the
``Authorization`` header; the answer is asked for as JSON that matches the schema (``text.format``,
strict).

Economy (batch) runs, one request per batch: the request is written as the one line of a JSONL
file (``custom_id`` is the run's id), uploaded with purpose ``batch``, and a batch for
``/v1/responses`` is created from it. The run's id is also kept in the batch's ``metadata``, which
is how a batch whose creation was never confirmed is found again. Results are read from the
batch's output file (or, for a failed request, its error file); nothing is deleted at OpenAI: its
files expire by themselves.
"""

import json
import re
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
    jpeg_base64,
)
from qbank.modules.ai.providers.http import (
    Http,
    bad_output,
    count,
    json_object,
    kind_for_status,
)

BASE_URL = "https://api.openai.com"
_ENDPOINT = "/v1/responses"
# The key under which a batch carries our run id (metadata: up to 16 pairs, values up to 512 chars).
TAG_KEY = "qbank_run"
# How long OpenAI keeps the answer file: long enough to read it again after a restart, far shorter
# than its 30-day default. Allowed range is one hour to 30 days.
_OUTPUT_KEPT_SECONDS = 7 * 24 * 3600
_LIST_PAGE = 100
_MAX_LIST_PAGES = 10  # the 1,000 newest batches: a run is looked for soon after it was sent
# What OpenAI's ids look like (batch_abc123, file-abc123). Anything else is never put in an address.
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,99}")
# Where an unfinished batch can be: it ends only in one of the others.
_GOING = frozenset({"validating", "in_progress", "finalizing", "cancelling"})
# A batch that did not finish may still hold the answer of a request that did.
_MAYBE_ANSWERED = {"cancelled": BatchState.CANCELLED, "expired": BatchState.EXPIRED}
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


def _input(request: StructuredRequest) -> str | list[dict[str, Any]]:
    """The user text, or, with pictures, one message holding the text and the pictures."""
    if not request.images:
        return request.user
    content: list[dict[str, Any]] = [{"type": "input_text", "text": request.user}]
    content += [
        {"type": "input_image", "image_url": f"data:image/jpeg;base64,{jpeg_base64(data)}"}
        for data in request.images
    ]
    return [{"role": "user", "content": content}]


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
            "input": _input(request),
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

    @staticmethod
    def _result(answer: dict[str, Any]) -> StructuredResult:
        """The structured answer inside a Responses API object (a direct call or a batch line)."""
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

    def generate_structured(self, api_key: str, request: StructuredRequest) -> StructuredResult:
        answer = self._http.post(
            f"{BASE_URL}/v1/responses", headers=self._headers(api_key), body=self._body(request)
        )
        return self._result(answer)

    # --- Economy: the Batch API ----------------------------------------------------------------

    @staticmethod
    def _checked(identifier: str) -> str:
        if not _ID.fullmatch(identifier):
            raise ProviderError(ProviderErrorKind.BAD_REQUEST)
        return identifier

    def _upload(self, api_key: str, line: str) -> str:
        """The request, as a one-line JSONL file OpenAI keeps for the batch. A file sent twice is
        harmless (no batch exists yet), so one more try is made after a passing failure."""
        headers = {
            "authorization": f"Bearer {api_key}"
        }  # the multipart boundary is added by the sender
        for attempt in (1, 2):
            try:
                made = self._http.post_file(
                    f"{BASE_URL}/v1/files",
                    headers=headers,
                    fields={"purpose": "batch"},
                    file_name="run.jsonl",
                    content=line.encode("utf-8"),
                    content_type="application/jsonl",
                )
            except ProviderError as problem:
                if attempt == 1 and problem.retryable:
                    continue
                raise
            identifier = made.get("id")
            if not isinstance(identifier, str):
                raise bad_output()
            return self._checked(identifier)
        raise bad_output()  # not reached: the second attempt returns or raises

    def submit_batch(self, api_key: str, *, tag: str, request: StructuredRequest) -> str:
        line = json.dumps(
            {
                "custom_id": tag,
                "method": "POST",
                "url": _ENDPOINT,
                "body": self._body(request),
            },
            ensure_ascii=False,
        )
        file_id = self._upload(api_key, line)
        made = self._http.post(
            f"{BASE_URL}/v1/batches",
            headers=self._headers(api_key),
            body={
                "input_file_id": file_id,
                "endpoint": _ENDPOINT,
                "completion_window": "24h",
                "metadata": {TAG_KEY: tag},
                "output_expires_after": {"anchor": "created_at", "seconds": _OUTPUT_KEPT_SECONDS},
            },
        )
        batch_id = made.get("id")
        if not isinstance(batch_id, str):
            raise bad_output()
        return self._checked(batch_id)

    def _batch(self, api_key: str, batch_id: str) -> dict[str, Any]:
        return self._http.get(
            f"{BASE_URL}/v1/batches/{self._checked(batch_id)}", headers=self._headers(api_key)
        )

    @staticmethod
    def _answered(batch: dict[str, Any]) -> bool:
        """Whether the batch says at least one request was completed (so an output file exists)."""
        counts = batch.get("request_counts")
        done = counts.get("completed") if isinstance(counts, dict) else None
        return (
            isinstance(batch.get("output_file_id"), str)
            and isinstance(done, int)
            and not isinstance(done, bool)
            and done > 0
        )

    def batch_status(self, api_key: str, batch_id: str) -> BatchState:
        batch = self._batch(api_key, batch_id)
        status = batch.get("status")
        if status == "completed":
            return BatchState.DONE
        if status == "failed":
            return BatchState.FAILED
        if status in _MAYBE_ANSWERED:
            # Work finished before the end still counts, and is charged for: read it.
            return BatchState.DONE if self._answered(batch) else _MAYBE_ANSWERED[status]
        return BatchState.IN_PROGRESS  # validating, in progress, finalizing, cancelling, or new

    def _lines(self, api_key: str, file_id: object) -> list[dict[str, Any]]:
        """The lines of a results file that can be read. One that cannot is left out."""
        if not isinstance(file_id, str):
            return []
        text = self._http.get_text(
            f"{BASE_URL}/v1/files/{self._checked(file_id)}/content", headers=self._headers(api_key)
        )
        lines: list[dict[str, Any]] = []
        for raw in text.splitlines():
            try:
                parsed = json.loads(raw)
            except ValueError:
                continue
            if isinstance(parsed, dict):
                lines.append(parsed)
        return lines

    @staticmethod
    def _error_kind(code: object) -> ProviderErrorKind:
        if code == "batch_expired":
            return ProviderErrorKind.TIMEOUT
        if code == "rate_limit_exceeded":
            return ProviderErrorKind.RATE_LIMITED
        if code in ("server_error", "model_not_available"):
            return ProviderErrorKind.UNAVAILABLE
        if isinstance(code, str) and code.startswith("invalid"):
            return ProviderErrorKind.BAD_REQUEST
        return ProviderErrorKind.BAD_OUTPUT

    def fetch_batch_answer(self, api_key: str, batch_id: str, *, tag: str) -> BatchAnswer:
        batch = self._batch(api_key, batch_id)
        for file_key in ("output_file_id", "error_file_id"):
            for line in self._lines(api_key, batch.get(file_key)):
                if line.get("custom_id") != tag:
                    continue
                response = line.get("response")
                if not isinstance(response, dict):
                    error = line.get("error")
                    code = error.get("code") if isinstance(error, dict) else None
                    return BatchAnswer(error=self._error_kind(code))
                status = response.get("status_code")
                body = response.get("body")
                if status != 200 or not isinstance(body, dict):
                    kind = (
                        kind_for_status(status)
                        if isinstance(status, int) and status != 200
                        else ProviderErrorKind.BAD_OUTPUT
                    )
                    return BatchAnswer(error=kind)
                try:
                    return BatchAnswer(result=self._result(body))
                except ProviderError as problem:
                    return BatchAnswer(error=problem.kind)
        return BatchAnswer(error=ProviderErrorKind.BAD_OUTPUT)

    def cancel_batch(self, api_key: str, batch_id: str) -> None:
        self._http.post(
            f"{BASE_URL}/v1/batches/{self._checked(batch_id)}/cancel",
            headers=self._headers(api_key),
            body={},
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
            items = [item for item in page.get("data") or [] if isinstance(item, dict)]
            for item in items:
                meta = item.get("metadata")
                identifier = item.get("id")
                if (
                    isinstance(meta, dict)
                    and meta.get(TAG_KEY) == tag
                    and isinstance(identifier, str)
                    and _ID.fullmatch(identifier)
                ):
                    found.append(identifier)
            last = page.get("last_id")
            if found or page.get("has_more") is not True or not isinstance(last, str) or not items:
                break
            after = last
        return found
