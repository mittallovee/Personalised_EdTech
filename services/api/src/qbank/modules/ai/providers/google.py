"""Google (Gemini API): generateContent, the model list and Batch Mode (ADR-0009, ADR-0023).

Written from Google's published API reference and checked with recorded answers; not yet tried
against the live service (run ``qbank ai-smoke``, and ``--batch`` for Economy). The key goes in
``x-goog-api-key``, never in the address; the answer is asked for as JSON that matches the schema
(``responseJsonSchema``).

Economy (batch) runs, one request per batch: ``models/{model}:batchGenerateContent`` with the
request inline. The run's id is the batch's ``displayName`` (and the request's ``metadata.key``),
which is how a batch whose creation was never confirmed is found again in the list of batches. A
batch is an Operation: its state is in ``metadata.state`` and, once it has succeeded, the answer is
in ``response`` (Google's reference and guide differ in where exactly, so every documented place is
read, and in the state names, so both ``BATCH_STATE_*`` and ``JOB_STATE_*`` are understood).
"""

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
)
from qbank.modules.ai.providers.http import Http, bad_output, count, json_object

BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
_MAX_PAGES = 10
_PAGE = 1000
# What Google's model ids look like (gemini-2.5-pro, gemma-3-27b-it). Anything else is not put in
# an address.
_MODEL_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}")
# A batch's name, as Google gives it (batches/123456); only this shape is put in an address.
_BATCH_NAME = re.compile(r"batches/[A-Za-z0-9][A-Za-z0-9_-]{0,99}")
_LIST_PAGE = 100
_MAX_LIST_PAGES = 10  # the newest 1,000 batches: a run is looked for soon after it was sent
_CANCELLED_CODE = 1  # google.rpc.Code.CANCELLED
# google.rpc.Code values a single request in a batch can fail with, as our failure kinds.
_RPC_KINDS = {
    3: ProviderErrorKind.BAD_REQUEST,  # INVALID_ARGUMENT
    4: ProviderErrorKind.TIMEOUT,  # DEADLINE_EXCEEDED
    7: ProviderErrorKind.AUTH,  # PERMISSION_DENIED
    8: ProviderErrorKind.RATE_LIMITED,  # RESOURCE_EXHAUSTED
    13: ProviderErrorKind.UNAVAILABLE,  # INTERNAL
    14: ProviderErrorKind.UNAVAILABLE,  # UNAVAILABLE
    16: ProviderErrorKind.AUTH,  # UNAUTHENTICATED
}
_ENDED = {
    "FAILED": BatchState.FAILED,
    "CANCELLED": BatchState.CANCELLED,
    "EXPIRED": BatchState.EXPIRED,
}


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

    @staticmethod
    def _request_body(request: StructuredRequest) -> dict[str, Any]:
        config: dict[str, Any] = {
            "responseMimeType": "application/json",
            "responseJsonSchema": request.schema,
            "maxOutputTokens": request.max_output_tokens,
        }
        if request.temperature is not None:
            config["temperature"] = request.temperature
        return {
            "systemInstruction": {"parts": [{"text": request.system}]},
            "contents": [{"role": "user", "parts": [{"text": request.user}]}],
            "generationConfig": config,
        }

    @staticmethod
    def _model_path(model_id: str) -> str:
        # The model id comes from the catalogue, but it goes into an address, so only the shape a
        # real id has is used: it can only ever be one path segment.
        if not _MODEL_ID.fullmatch(model_id) or ".." in model_id:
            raise ProviderError(ProviderErrorKind.BAD_REQUEST)
        return f"{BASE_URL}/models/{model_id}"

    @staticmethod
    def _result(answer: dict[str, Any]) -> StructuredResult:
        """The structured answer inside a GenerateContentResponse (a direct call or a batch one)."""
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

    def generate_structured(self, api_key: str, request: StructuredRequest) -> StructuredResult:
        url = f"{self._model_path(request.model_id)}:generateContent"
        answer = self._http.post(
            url, headers=self._headers(api_key), body=self._request_body(request)
        )
        return self._result(answer)

    # --- Economy: Batch Mode -------------------------------------------------------------------

    @staticmethod
    def _checked(name: str) -> str:
        if not _BATCH_NAME.fullmatch(name):
            raise ProviderError(ProviderErrorKind.BAD_REQUEST)
        return name

    def submit_batch(self, api_key: str, *, tag: str, request: StructuredRequest) -> str:
        url = f"{self._model_path(request.model_id)}:batchGenerateContent"
        made = self._http.post(
            url,
            headers=self._headers(api_key),
            body={
                "batch": {
                    "displayName": tag,
                    "inputConfig": {
                        "requests": {
                            "requests": [
                                {
                                    "request": self._request_body(request),
                                    "metadata": {"key": tag},
                                }
                            ]
                        }
                    },
                }
            },
        )
        name = made.get("name")
        if not isinstance(name, str):
            raise bad_output()
        return self._checked(name)

    def _batch(self, api_key: str, name: str) -> dict[str, Any]:
        return self._http.get(f"{BASE_URL}/{self._checked(name)}", headers=self._headers(api_key))

    @staticmethod
    def _entries(batch: dict[str, Any]) -> list[dict[str, Any]]:
        """The answers of the batch's requests, wherever Google's documents put them: under
        ``response.output.inlinedResponses.inlinedResponses`` (the reference), or
        ``response.inlinedResponses`` as a list or the same object (the guide)."""
        places: list[object] = []
        response = batch.get("response")
        if isinstance(response, dict):
            places.append(response.get("inlinedResponses"))
            output = response.get("output")
            if isinstance(output, dict):
                places.append(output.get("inlinedResponses"))
        for place in places:
            if isinstance(place, dict):
                place = place.get("inlinedResponses")
            if isinstance(place, list):
                return [entry for entry in place if isinstance(entry, dict)]
        return []

    @staticmethod
    def _state_word(batch: dict[str, Any]) -> str | None:
        """``SUCCEEDED``, ``RUNNING`` and so on, whichever prefix Google uses for the state."""
        meta = batch.get("metadata")
        state = meta.get("state") if isinstance(meta, dict) else None
        if not isinstance(state, str):
            return None
        return state.removeprefix("BATCH_STATE_").removeprefix("JOB_STATE_")

    def batch_status(self, api_key: str, batch_id: str) -> BatchState:
        batch = self._batch(api_key, batch_id)
        word = self._state_word(batch)
        if word is None:  # no state given: the Operation's own fields say how it ended
            if batch.get("done") is not True:
                return BatchState.IN_PROGRESS
            error = batch.get("error")
            if not isinstance(error, dict):
                return BatchState.DONE
            return (
                BatchState.CANCELLED if error.get("code") == _CANCELLED_CODE else BatchState.FAILED
            )
        if word == "SUCCEEDED":
            return BatchState.DONE
        if word in _ENDED:
            # Work finished before the end still counts, and is charged for: read it.
            answered = any(
                isinstance(entry.get("response"), dict) for entry in self._entries(batch)
            )
            return BatchState.DONE if answered and word != "FAILED" else _ENDED[word]
        return BatchState.IN_PROGRESS  # pending, running, unspecified, or a state not known yet

    def fetch_batch_answer(self, api_key: str, batch_id: str, *, tag: str) -> BatchAnswer:
        entries = self._entries(self._batch(api_key, batch_id))
        for entry in entries:
            meta = entry.get("metadata")
            key = meta.get("key") if isinstance(meta, dict) else None
            if key not in (None, tag):
                continue
            response = entry.get("response")
            if isinstance(response, dict):
                try:
                    return BatchAnswer(result=self._result(response))
                except ProviderError as problem:
                    return BatchAnswer(error=problem.kind)
            error = entry.get("error")
            code = error.get("code") if isinstance(error, dict) else None
            kind = _RPC_KINDS.get(code) if isinstance(code, int) else None
            return BatchAnswer(error=kind or ProviderErrorKind.BAD_OUTPUT)
        return BatchAnswer(error=ProviderErrorKind.BAD_OUTPUT)

    def cancel_batch(self, api_key: str, batch_id: str) -> None:
        self._http.post(
            f"{BASE_URL}/{self._checked(batch_id)}:cancel", headers=self._headers(api_key), body={}
        )

    def find_batches_by_tag(self, api_key: str, tag: str) -> list[str]:
        found: list[str] = []
        token: str | None = None
        for _ in range(_MAX_LIST_PAGES):
            params: dict[str, Any] = {"pageSize": _LIST_PAGE}
            if token is not None:
                params["pageToken"] = token
            page = self._http.get(
                f"{BASE_URL}/batches", headers=self._headers(api_key), params=params
            )
            for item in page.get("operations") or []:
                if not isinstance(item, dict):
                    continue
                meta = item.get("metadata")
                name = item.get("name")
                if (
                    isinstance(meta, dict)
                    and meta.get("displayName") == tag
                    and isinstance(name, str)
                    and _BATCH_NAME.fullmatch(name)
                ):
                    found.append(name)
            following = page.get("nextPageToken")
            if found or not isinstance(following, str) or not following:
                break
            token = following
        return found
