"""M5 PR 5h-2: OpenAI's Batch API as the adapter uses it (part of T44), and Economy's gate.

No network: a mock transport plays OpenAI. These prove the adapter against OpenAI's published
documents as written (the shapes were read from them), not against the live service; the structured
output inside a batch body is the one detail the documents do not show, so ``qbank ai-smoke`` must
confirm it before real use.
"""

import json
from typing import Any

import httpx2
import pytest

from qbank.modules.ai.providers.anthropic import AnthropicProvider
from qbank.modules.ai.providers.base import (
    BatchProvider,
    BatchState,
    ProviderError,
    ProviderErrorKind,
)
from qbank.modules.ai.providers.google import GoogleProvider
from qbank.modules.ai.providers.openai import OpenAIProvider
from qbank.modules.ai.providers.openrouter import OpenRouterProvider
from tests.unit.test_ai_providers import ANSWER_TEXT, KEY, REQUEST, make, reply

TAG = "0190c0de-0000-7000-8000-000000000001"
RESPONSE_BODY = {
    "status": "completed",
    "output": [{"type": "message", "content": [{"type": "output_text", "text": ANSWER_TEXT}]}],
    "usage": {"input_tokens": 120, "output_tokens": 30},
}


def line(custom_id: str, status: int = 200, body: Any = None) -> str:
    return json.dumps(
        {
            "id": "batch_req_1",
            "custom_id": custom_id,
            "response": {"status_code": status, "request_id": "r", "body": body or RESPONSE_BODY},
            "error": None,
        }
    )


def test_only_openai_offers_batch_because_only_it_can_find_a_batch_by_tag() -> None:
    http, _ = make(reply({}))
    assert isinstance(OpenAIProvider(http), BatchProvider)
    for other in (GoogleProvider(http), AnthropicProvider(http), OpenRouterProvider(http)):
        assert not isinstance(other, BatchProvider)


def test_submit_uploads_one_jsonl_line_then_creates_the_batch_tagged_with_the_run() -> None:
    calls: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        calls.append(request)
        if request.url.path == "/v1/files":
            return httpx2.Response(200, json={"id": "file-1", "object": "file"})
        return httpx2.Response(200, json={"id": "batch_9", "status": "validating"})

    http, _ = make(handler)
    assert OpenAIProvider(http).submit_batch(KEY, tag=TAG, request=REQUEST) == "batch_9"
    upload, create = calls
    assert str(upload.url) == "https://api.openai.com/v1/files"
    assert upload.headers["content-type"].startswith("multipart/form-data")
    raw = upload.content.decode()
    assert 'name="purpose"' in raw and "batch" in raw and 'filename="request.jsonl"' in raw
    jsonl = raw.split("\r\n\r\n", 2)[-1].split("\r\n--")[0].strip()
    sent = json.loads(jsonl.splitlines()[-1])
    assert (sent["custom_id"], sent["method"], sent["url"]) == (TAG, "POST", "/v1/responses")
    assert sent["body"]["model"] == "model-x" and sent["body"]["text"]["format"]["strict"] is True
    assert "SYSTEM-TEXT" in sent["body"]["instructions"] and sent["body"]["input"] == "USER-TEXT"
    assert upload.headers["authorization"] == f"Bearer {KEY}"
    made = json.loads(create.content)
    assert str(create.url) == "https://api.openai.com/v1/batches"
    assert made == {
        "input_file_id": "file-1",
        "endpoint": "/v1/responses",
        "completion_window": "24h",
        "metadata": {"qbank_run": TAG},
    }


@pytest.mark.parametrize(
    ("status", "state"),
    [
        ("validating", BatchState.IN_PROGRESS),
        ("in_progress", BatchState.IN_PROGRESS),
        ("finalizing", BatchState.IN_PROGRESS),
        ("cancelling", BatchState.IN_PROGRESS),
        ("completed", BatchState.DONE),
        ("failed", BatchState.FAILED),
        ("expired", BatchState.EXPIRED),
        ("cancelled", BatchState.CANCELLED),
        ("something_new", BatchState.IN_PROGRESS),
    ],
)
def test_batch_states_map_to_ours_and_an_unknown_one_means_keep_waiting(
    status: str, state: BatchState
) -> None:
    http, seen = make(reply({"id": "batch_9", "status": status}))
    assert OpenAIProvider(http).batch_status(KEY, "batch_9") == state
    assert str(seen.last.url) == "https://api.openai.com/v1/batches/batch_9"


def serve(batch: dict[str, Any], files: dict[str, str]) -> Any:
    def handler(request: httpx2.Request) -> httpx2.Response:
        if request.url.path == "/v1/batches/batch_9":
            return httpx2.Response(200, json=batch)
        file_id = request.url.path.split("/")[3]
        return httpx2.Response(200, content=files[file_id].encode())

    return handler


def test_the_answer_is_read_from_the_output_file_by_the_runs_id() -> None:
    other = line("someone-else", body={"status": "failed"})
    handler = serve(
        {"status": "completed", "output_file_id": "out-1"}, {"out-1": f"{other}\n{line(TAG)}\n"}
    )
    http, _ = make(handler)
    answer = OpenAIProvider(http).fetch_batch_answer(KEY, "batch_9", tag=TAG)
    assert answer.error is None and answer.result is not None
    assert (answer.result.data, answer.result.tokens_in, answer.result.tokens_out) == (
        {"label": "kinematics"},
        120,
        30,
    )


def test_a_failed_request_is_an_error_kind_not_a_result() -> None:
    bad = line(TAG, status=429, body={"error": {}})
    http, _ = make(serve({"status": "completed", "output_file_id": "out-1"}, {"out-1": bad}))
    answer = OpenAIProvider(http).fetch_batch_answer(KEY, "batch_9", tag=TAG)
    assert (answer.result, answer.error) == (None, ProviderErrorKind.RATE_LIMITED)


def test_an_error_file_line_and_a_missing_line_are_errors_too() -> None:
    error_line = json.dumps(
        {"custom_id": TAG, "response": None, "error": {"code": "batch_expired", "message": "x"}}
    )
    http, _ = make(
        serve({"status": "expired", "error_file_id": "err-1"}, {"err-1": error_line + "\n"})
    )
    assert (
        OpenAIProvider(http).fetch_batch_answer(KEY, "batch_9", tag=TAG).error
        is ProviderErrorKind.UNAVAILABLE
    )
    http, _ = make(serve({"status": "completed", "output_file_id": "out-1"}, {"out-1": "\n"}))
    assert (
        OpenAIProvider(http).fetch_batch_answer(KEY, "batch_9", tag=TAG).error
        is ProviderErrorKind.BAD_OUTPUT
    )


def test_an_answer_that_is_not_json_for_the_schema_is_bad_output() -> None:
    body = {**RESPONSE_BODY, "output": [{"type": "message", "content": [{"type": "refusal"}]}]}
    http, _ = make(
        serve({"status": "completed", "output_file_id": "out-1"}, {"out-1": line(TAG, body=body)})
    )
    answer = OpenAIProvider(http).fetch_batch_answer(KEY, "batch_9", tag=TAG)
    assert answer.error is ProviderErrorKind.BAD_OUTPUT


def test_cancel_posts_to_the_batch_cancel_address() -> None:
    http, seen = make(reply({"id": "batch_9", "status": "cancelling"}))
    OpenAIProvider(http).cancel_batch(KEY, "batch_9")
    assert (seen.last.method, str(seen.last.url)) == (
        "POST",
        "https://api.openai.com/v1/batches/batch_9/cancel",
    )


def test_a_batch_is_found_again_by_the_tag_in_its_metadata_across_pages() -> None:
    pages = {
        None: {
            "data": [
                {"id": "b1", "metadata": {"qbank_run": "other"}},
                {"id": "b2", "metadata": None},
            ],
            "has_more": True,
            "last_id": "b2",
        },
        "b2": {"data": [{"id": "b3", "metadata": {"qbank_run": TAG}}], "has_more": False},
    }

    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, json=pages[request.url.params.get("after")])

    http, seen = make(handler)
    assert OpenAIProvider(http).find_batches_by_tag(KEY, TAG) == ["b3"]
    assert len(seen.requests) == 2
    assert (
        OpenAIProvider(make(reply({"data": [], "has_more": False}))[0]).find_batches_by_tag(
            KEY, TAG
        )
        == []
    )


def test_a_failure_while_uploading_is_a_provider_error_without_the_key_or_the_text() -> None:
    http, _ = make(reply({"error": {}}, status=401))
    with pytest.raises(ProviderError) as caught:
        OpenAIProvider(http).submit_batch(KEY, tag=TAG, request=REQUEST)
    assert caught.value.kind is ProviderErrorKind.AUTH
    assert KEY not in str(caught.value) and "USER-TEXT" not in str(caught.value)
