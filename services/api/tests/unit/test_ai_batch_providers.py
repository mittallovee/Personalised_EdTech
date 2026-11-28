"""M5 PR 5h-2: the Economy (batch) adapters of OpenAI and Google (T44, T50 to T52 at the edge).

No network. Every call goes through a mock transport that plays the provider's service, so these
tests check what we send (addresses, the one header that carries the key, the one request in each
batch and the run id that makes it findable) and how every kind of answer is read. They prove the
adapters against the providers' published documents as written (OpenAI's Batch guide and reference,
Google's Batch Mode guide and reference), not against the live services: ``qbank ai-smoke --batch``
does that.
"""

import json
from collections.abc import Callable
from typing import Any

import httpx2
import pytest

from qbank.modules.ai.names import Provider
from qbank.modules.ai.providers.base import (
    BatchProvider,
    BatchState,
    ProviderError,
    ProviderErrorKind,
    StructuredRequest,
    StructuredResult,
)
from qbank.modules.ai.providers.fake import FakeProvider
from qbank.modules.ai.providers.google import GoogleProvider
from qbank.modules.ai.providers.http import Http
from qbank.modules.ai.providers.openai import OpenAIProvider
from qbank.modules.ai.providers.registry import provider_for
from qbank.modules.ai.providers.smoke import smoke_batch

KEY = "test-key-" + "x" * 16 + "0123"  # made up, and too plain to look like a real key
TAG = "01a2b3c4-0000-7000-8000-000000000001"  # a run's id
SCHEMA = {
    "type": "object",
    "properties": {"label": {"type": "string"}},
    "required": ["label"],
    "additionalProperties": False,
}
REQUEST = StructuredRequest(
    model_id="model-x",
    system="SYSTEM-TEXT",
    user="USER-TEXT",
    schema_name="tag",
    schema=SCHEMA,
    max_output_tokens=300,
    temperature=0.2,
)
ANSWER = {"label": "kinematics"}
Handler = Callable[[httpx2.Request], httpx2.Response]


class Service:
    """A provider's service, played by routes (method and path) to handlers. Keeps every request."""

    def __init__(self) -> None:
        self.routes: dict[tuple[str, str], Handler] = {}
        self.requests: list[httpx2.Request] = []

    def on(self, method: str, path: str, handler: Handler | Any, status: int = 200) -> None:
        if callable(handler):
            self.routes[(method, path)] = handler
        else:
            self.routes[(method, path)] = lambda _: httpx2.Response(status, json=handler)

    def text(self, path: str, body: str) -> None:
        self.routes[("GET", path)] = lambda _: httpx2.Response(200, content=body.encode())

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(request)
        handler = self.routes.get((request.method, request.url.path))
        if handler is None:
            return httpx2.Response(404, json={"error": "no such route"})
        return handler(request)

    def calls(self, method: str, path: str) -> list[httpx2.Request]:
        return [r for r in self.requests if (r.method, r.url.path) == (method, path)]

    def http(self) -> Http:
        return Http(httpx2.Client(transport=httpx2.MockTransport(self)))


def json_of(request: httpx2.Request) -> dict[str, Any]:
    body: dict[str, Any] = json.loads(request.content)
    return body


# --- OpenAI --------------------------------------------------------------------------------------

OPENAI_RESPONSE = {
    "status": "completed",
    "output": [
        {"type": "message", "content": [{"type": "output_text", "text": json.dumps(ANSWER)}]}
    ],
    "usage": {"input_tokens": 120, "output_tokens": 30},
}


def openai_line(custom_id: str = TAG, **changes: Any) -> str:
    line: dict[str, Any] = {
        "id": "batch_req_1",
        "custom_id": custom_id,
        "response": {"status_code": 200, "request_id": "req_1", "body": OPENAI_RESPONSE},
        "error": None,
    }
    line.update(changes)
    return json.dumps(line)


def openai_batch(status: str, **changes: Any) -> dict[str, Any]:
    batch: dict[str, Any] = {
        "id": "batch_abc123",
        "object": "batch",
        "status": status,
        "output_file_id": None,
        "error_file_id": None,
        "request_counts": {"total": 1, "completed": 0, "failed": 0},
        "metadata": {"qbank_run": TAG},
    }
    batch.update(changes)
    return batch


def openai() -> tuple[OpenAIProvider, Service]:
    service = Service()
    return OpenAIProvider(service.http()), service


def openai_ready(service: Service) -> None:
    service.on("POST", "/v1/files", {"id": "file-in1", "object": "file", "purpose": "batch"})
    service.on("POST", "/v1/batches", openai_batch("validating"))


class TestOpenAISubmit:
    def test_uploads_one_line_then_creates_a_batch_tagged_with_the_run(self) -> None:
        adapter, service = openai()
        openai_ready(service)
        assert adapter.submit_batch(KEY, tag=TAG, request=REQUEST) == "batch_abc123"

        upload = service.calls("POST", "/v1/files")[0]
        assert upload.headers["authorization"] == f"Bearer {KEY}"
        assert upload.headers["content-type"].startswith("multipart/form-data; boundary=")
        raw = upload.content.decode()
        assert 'name="purpose"' in raw and "\r\n\r\nbatch\r\n" in raw
        sent = [part for part in raw.split("\r\n") if part.startswith("{")]
        assert len(sent) == 1
        line = json.loads(sent[0])
        assert (line["custom_id"], line["method"], line["url"]) == (TAG, "POST", "/v1/responses")
        body = line["body"]
        assert body["model"] == "model-x"
        assert body["instructions"] == "SYSTEM-TEXT" and body["input"] == "USER-TEXT"
        assert body["text"]["format"]["strict"] is True
        assert body["text"]["format"]["schema"] == SCHEMA
        assert body["max_output_tokens"] == 300 and body["temperature"] == 0.2

        create = service.calls("POST", "/v1/batches")[0]
        assert json_of(create) == {
            "input_file_id": "file-in1",
            "endpoint": "/v1/responses",
            "completion_window": "24h",
            "metadata": {"qbank_run": TAG},
            "output_expires_after": {"anchor": "created_at", "seconds": 7 * 24 * 3600},
        }

    def test_the_key_is_only_ever_in_the_authorization_header(self) -> None:
        adapter, service = openai()
        openai_ready(service)
        adapter.submit_batch(KEY, tag=TAG, request=REQUEST)
        for request in service.requests:
            assert KEY not in str(request.url)
            assert KEY.encode() not in request.content

    def test_a_passing_failure_of_the_upload_is_tried_once_more_and_nothing_is_created_twice(
        self,
    ) -> None:
        adapter, service = openai()
        outcomes = iter(
            [httpx2.Response(503, json={}), httpx2.Response(200, json={"id": "file-in2"})]
        )
        service.on("POST", "/v1/files", lambda _: next(outcomes))
        service.on("POST", "/v1/batches", openai_batch("validating"))
        assert adapter.submit_batch(KEY, tag=TAG, request=REQUEST) == "batch_abc123"
        assert len(service.calls("POST", "/v1/files")) == 2
        assert len(service.calls("POST", "/v1/batches")) == 1
        assert json_of(service.calls("POST", "/v1/batches")[0])["input_file_id"] == "file-in2"

    def test_an_upload_that_keeps_failing_ends_without_creating_a_batch(self) -> None:
        adapter, service = openai()
        service.on("POST", "/v1/files", {}, status=503)
        with pytest.raises(ProviderError) as caught:
            adapter.submit_batch(KEY, tag=TAG, request=REQUEST)
        assert caught.value.kind is ProviderErrorKind.UNAVAILABLE
        assert len(service.calls("POST", "/v1/files")) == 2
        assert service.calls("POST", "/v1/batches") == []

    def test_a_refused_key_is_not_retried(self) -> None:
        adapter, service = openai()
        service.on("POST", "/v1/files", {}, status=401)
        with pytest.raises(ProviderError) as caught:
            adapter.submit_batch(KEY, tag=TAG, request=REQUEST)
        assert caught.value.kind is ProviderErrorKind.AUTH
        assert len(service.calls("POST", "/v1/files")) == 1
        assert service.calls("POST", "/v1/batches") == []

    def test_creation_is_never_repeated_and_an_unconfirmed_one_is_reported_as_such(self) -> None:
        adapter, service = openai()
        service.on("POST", "/v1/files", {"id": "file-in1"})

        def lost(_: httpx2.Request) -> httpx2.Response:
            raise httpx2.ReadTimeout("slow")

        service.on("POST", "/v1/batches", lost)
        with pytest.raises(ProviderError) as caught:
            adapter.submit_batch(KEY, tag=TAG, request=REQUEST)
        assert caught.value.kind is ProviderErrorKind.TIMEOUT  # may exist: look it up, never resend
        assert len(service.calls("POST", "/v1/batches")) == 1

    def test_an_answer_without_ids_is_an_unusable_answer(self) -> None:
        adapter, service = openai()
        service.on("POST", "/v1/files", {"object": "file"})
        with pytest.raises(ProviderError) as caught:
            adapter.submit_batch(KEY, tag=TAG, request=REQUEST)
        assert caught.value.kind is ProviderErrorKind.BAD_OUTPUT


class TestOpenAIStatus:
    @pytest.mark.parametrize(
        ("status", "expected"),
        [
            ("validating", BatchState.IN_PROGRESS),
            ("in_progress", BatchState.IN_PROGRESS),
            ("finalizing", BatchState.IN_PROGRESS),
            ("cancelling", BatchState.IN_PROGRESS),
            ("something_new", BatchState.IN_PROGRESS),
            ("completed", BatchState.DONE),
            ("failed", BatchState.FAILED),
            ("expired", BatchState.EXPIRED),
            ("cancelled", BatchState.CANCELLED),
        ],
    )
    def test_each_status(self, status: str, expected: BatchState) -> None:
        adapter, service = openai()
        service.on("GET", "/v1/batches/batch_abc123", openai_batch(status))
        assert adapter.batch_status(KEY, "batch_abc123") is expected

    @pytest.mark.parametrize("status", ["cancelled", "expired"])
    def test_work_finished_before_the_end_is_still_read_and_charged(self, status: str) -> None:
        adapter, service = openai()
        service.on(
            "GET",
            "/v1/batches/batch_abc123",
            openai_batch(
                status,
                output_file_id="file-out1",
                request_counts={"total": 1, "completed": 1, "failed": 0},
            ),
        )
        assert adapter.batch_status(KEY, "batch_abc123") is BatchState.DONE

    def test_an_ended_batch_with_nothing_completed_stays_ended(self) -> None:
        adapter, service = openai()
        service.on(
            "GET",
            "/v1/batches/batch_abc123",
            openai_batch(
                "expired",
                output_file_id="file-out1",
                request_counts={"total": 1, "completed": 0, "failed": 1},
            ),
        )
        assert adapter.batch_status(KEY, "batch_abc123") is BatchState.EXPIRED


class TestOpenAIAnswer:
    def answer(self, service: Service, adapter: OpenAIProvider) -> Any:
        return adapter.fetch_batch_answer(KEY, "batch_abc123", tag=TAG)

    def batch(self, service: Service, **files: str | None) -> None:
        service.on(
            "GET",
            "/v1/batches/batch_abc123",
            openai_batch(
                "completed",
                output_file_id=files.get("output"),
                error_file_id=files.get("error"),
                request_counts={"total": 1, "completed": 1, "failed": 0},
            ),
        )

    def test_reads_the_answer_of_this_run_with_its_token_counts(self) -> None:
        adapter, service = openai()
        self.batch(service, output="file-out1")
        service.text("/v1/files/file-out1/content", openai_line() + "\n")
        found = self.answer(service, adapter)
        assert found.error is None
        assert found.result.data == ANSWER
        assert (found.result.tokens_in, found.result.tokens_out) == (120, 30)
        assert found.result.cost_usd is None  # the ledger works it out, less the batch discount
        assert service.calls("GET", "/v1/files/file-out1/content")[0].headers["authorization"] == (
            f"Bearer {KEY}"
        )

    def test_skips_other_runs_and_lines_it_cannot_read(self) -> None:
        adapter, service = openai()
        self.batch(service, output="file-out1")
        service.text(
            "/v1/files/file-out1/content",
            "\n".join(["not json", "[1, 2]", openai_line("someone-else"), openai_line()]),
        )
        assert self.answer(service, adapter).result.data == ANSWER

    def test_a_request_that_failed_is_found_in_the_error_file(self) -> None:
        adapter, service = openai()
        self.batch(service, output=None, error="file-err1")
        failed = json.dumps(
            {
                "id": "batch_req_1",
                "custom_id": TAG,
                "response": None,
                "error": {"code": "batch_expired", "message": "ignored text"},
            }
        )
        service.text("/v1/files/file-err1/content", failed)
        found = self.answer(service, adapter)
        assert found.result is None and found.error is ProviderErrorKind.TIMEOUT

    @pytest.mark.parametrize(
        ("code", "kind"),
        [
            ("rate_limit_exceeded", ProviderErrorKind.RATE_LIMITED),
            ("server_error", ProviderErrorKind.UNAVAILABLE),
            ("invalid_request", ProviderErrorKind.BAD_REQUEST),
            ("something_odd", ProviderErrorKind.BAD_OUTPUT),
            (None, ProviderErrorKind.BAD_OUTPUT),
        ],
    )
    def test_the_error_code_of_a_request_becomes_a_failure_kind(
        self, code: str | None, kind: ProviderErrorKind
    ) -> None:
        adapter, service = openai()
        self.batch(service, error="file-err1")
        service.text(
            "/v1/files/file-err1/content",
            json.dumps({"custom_id": TAG, "response": None, "error": {"code": code}}),
        )
        assert self.answer(service, adapter).error is kind

    def test_a_status_other_than_200_inside_the_output_is_a_failure(self) -> None:
        adapter, service = openai()
        self.batch(service, output="file-out1")
        line = openai_line(response={"status_code": 429, "request_id": "r", "body": {"error": {}}})
        service.text("/v1/files/file-out1/content", line)
        assert self.answer(service, adapter).error is ProviderErrorKind.RATE_LIMITED

    def test_a_refusal_or_an_unfinished_answer_is_an_unusable_answer(self) -> None:
        adapter, service = openai()
        self.batch(service, output="file-out1")
        refusal = {
            "status": "completed",
            "output": [{"type": "message", "content": [{"type": "refusal", "refusal": "no"}]}],
        }
        line = openai_line(response={"status_code": 200, "request_id": "r", "body": refusal})
        service.text("/v1/files/file-out1/content", line)
        assert self.answer(service, adapter).error is ProviderErrorKind.BAD_OUTPUT

    def test_an_answer_that_is_not_the_schema_json_is_an_unusable_answer(self) -> None:
        adapter, service = openai()
        self.batch(service, output="file-out1")
        body = {
            "status": "completed",
            "output": [{"type": "message", "content": [{"type": "output_text", "text": "hello"}]}],
        }
        line = openai_line(response={"status_code": 200, "request_id": "r", "body": body})
        service.text("/v1/files/file-out1/content", line)
        assert self.answer(service, adapter).error is ProviderErrorKind.BAD_OUTPUT

    def test_nothing_for_this_run_is_an_unusable_answer(self) -> None:
        adapter, service = openai()
        self.batch(service, output="file-out1")
        service.text("/v1/files/file-out1/content", openai_line("someone-else"))
        assert self.answer(service, adapter).error is ProviderErrorKind.BAD_OUTPUT


class TestOpenAICancelAndFind:
    def test_cancel_asks_the_provider_to_stop(self) -> None:
        adapter, service = openai()
        service.on("POST", "/v1/batches/batch_abc123/cancel", openai_batch("cancelling"))
        adapter.cancel_batch(KEY, "batch_abc123")
        assert len(service.calls("POST", "/v1/batches/batch_abc123/cancel")) == 1

    def test_finds_a_batch_by_the_run_id_in_its_metadata(self) -> None:
        adapter, service = openai()
        service.on(
            "GET",
            "/v1/batches",
            {
                "object": "list",
                "data": [
                    openai_batch("in_progress", id="batch_other", metadata={"qbank_run": "other"}),
                    openai_batch("in_progress", id="batch_none", metadata=None),
                    openai_batch("in_progress", id="batch_mine"),
                ],
                "has_more": False,
            },
        )
        assert adapter.find_batches_by_tag(KEY, TAG) == ["batch_mine"]
        assert adapter.find_batches_by_tag(KEY, "unknown") == []

    def test_looks_through_more_pages_until_it_is_found(self) -> None:
        adapter, service = openai()
        pages = {
            None: {
                "data": [openai_batch("in_progress", id="batch_a", metadata={})],
                "has_more": True,
                "last_id": "batch_a",
            },
            "batch_a": {
                "data": [openai_batch("in_progress", id="batch_mine")],
                "has_more": True,
                "last_id": "batch_mine",
            },
        }

        def page(request: httpx2.Request) -> httpx2.Response:
            assert request.url.params["limit"] == "100"
            return httpx2.Response(200, json=pages[request.url.params.get("after")])

        service.on("GET", "/v1/batches", page)
        assert adapter.find_batches_by_tag(KEY, TAG) == ["batch_mine"]
        assert len(service.calls("GET", "/v1/batches")) == 2  # stops once it has found it

    def test_gives_up_after_a_bounded_number_of_pages(self) -> None:
        adapter, service = openai()
        service.on(
            "GET",
            "/v1/batches",
            {"data": [openai_batch("in_progress", metadata={})], "has_more": True, "last_id": "x"},
        )
        assert adapter.find_batches_by_tag(KEY, TAG) == []
        assert len(service.calls("GET", "/v1/batches")) == 10

    @pytest.mark.parametrize("bad", ["../v1/models", "batch/../x", "", "a b", "x" * 200])
    def test_an_id_that_is_not_the_shape_of_a_real_one_is_never_put_in_an_address(
        self, bad: str
    ) -> None:
        adapter, service = openai()
        for call in (adapter.batch_status, adapter.cancel_batch):
            with pytest.raises(ProviderError) as caught:
                call(KEY, bad)
            assert caught.value.kind is ProviderErrorKind.BAD_REQUEST
        assert service.requests == []


# --- Google --------------------------------------------------------------------------------------

GOOGLE_RESPONSE = {
    "candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": json.dumps(ANSWER)}]}}],
    "usageMetadata": {
        "promptTokenCount": 120,
        "candidatesTokenCount": 25,
        "thoughtsTokenCount": 5,
    },
}


def google_op(state: str | None = "BATCH_STATE_PENDING", **changes: Any) -> dict[str, Any]:
    metadata: dict[str, Any] = {"displayName": TAG, "model": "models/model-x"}
    if state is not None:
        metadata["state"] = state
    operation: dict[str, Any] = {"name": "batches/abc123", "metadata": metadata, "done": False}
    operation.update(changes)
    return operation


def inlined(entry: dict[str, Any] | None = None, *, shape: str = "reference") -> dict[str, Any]:
    """The response of a finished batch, in each place Google's documents put the answers."""
    entry = entry or {"metadata": {"key": TAG}, "response": GOOGLE_RESPONSE}
    if shape == "reference":
        return {"output": {"inlinedResponses": {"inlinedResponses": [entry]}}}
    if shape == "guide-object":
        return {"inlinedResponses": {"inlinedResponses": [entry]}}
    return {"inlinedResponses": [entry]}


def google() -> tuple[GoogleProvider, Service]:
    service = Service()
    return GoogleProvider(service.http()), service


PATH = "/v1beta/batches/abc123"


class TestGoogleSubmit:
    def test_sends_the_request_inline_and_names_the_batch_after_the_run(self) -> None:
        adapter, service = google()
        service.on(
            "POST",
            "/v1beta/models/model-x:batchGenerateContent",
            {"name": "batches/abc123", "metadata": {}},
        )
        assert adapter.submit_batch(KEY, tag=TAG, request=REQUEST) == "batches/abc123"
        sent = service.requests[0]
        assert sent.headers["x-goog-api-key"] == KEY
        assert KEY not in str(sent.url) and KEY.encode() not in sent.content
        batch = json_of(sent)["batch"]
        assert batch["displayName"] == TAG
        (entry,) = batch["inputConfig"]["requests"]["requests"]
        assert entry["metadata"] == {"key": TAG}
        request = entry["request"]
        assert request["systemInstruction"] == {"parts": [{"text": "SYSTEM-TEXT"}]}
        assert request["contents"] == [{"role": "user", "parts": [{"text": "USER-TEXT"}]}]
        config = request["generationConfig"]
        assert config["responseMimeType"] == "application/json"
        assert config["responseJsonSchema"] == SCHEMA
        assert (config["maxOutputTokens"], config["temperature"]) == (300, 0.2)

    def test_a_model_id_that_is_not_the_shape_of_a_real_one_is_never_put_in_an_address(
        self,
    ) -> None:
        adapter, service = google()
        bad = StructuredRequest("../x", "s", "u", "n", SCHEMA, 10)
        with pytest.raises(ProviderError) as caught:
            adapter.submit_batch(KEY, tag=TAG, request=bad)
        assert caught.value.kind is ProviderErrorKind.BAD_REQUEST
        assert service.requests == []

    def test_a_name_that_is_not_a_batch_name_is_an_unusable_answer_or_refused(self) -> None:
        adapter, service = google()
        service.on("POST", "/v1beta/models/model-x:batchGenerateContent", {"done": False})
        with pytest.raises(ProviderError) as caught:
            adapter.submit_batch(KEY, tag=TAG, request=REQUEST)
        assert caught.value.kind is ProviderErrorKind.BAD_OUTPUT
        service.on(
            "POST",
            "/v1beta/models/model-x:batchGenerateContent",
            {"name": "operations/../../x"},
        )
        with pytest.raises(ProviderError) as other:
            adapter.submit_batch(KEY, tag=TAG, request=REQUEST)
        assert other.value.kind is ProviderErrorKind.BAD_REQUEST

    def test_a_timeout_is_reported_as_unconfirmed_and_not_repeated(self) -> None:
        adapter, service = google()

        def lost(_: httpx2.Request) -> httpx2.Response:
            raise httpx2.ReadTimeout("slow")

        service.on("POST", "/v1beta/models/model-x:batchGenerateContent", lost)
        with pytest.raises(ProviderError) as caught:
            adapter.submit_batch(KEY, tag=TAG, request=REQUEST)
        assert caught.value.kind is ProviderErrorKind.TIMEOUT
        assert len(service.requests) == 1


class TestGoogleStatus:
    @pytest.mark.parametrize("prefix", ["BATCH_STATE_", "JOB_STATE_"])
    @pytest.mark.parametrize(
        ("word", "expected"),
        [
            ("UNSPECIFIED", BatchState.IN_PROGRESS),
            ("PENDING", BatchState.IN_PROGRESS),
            ("RUNNING", BatchState.IN_PROGRESS),
            ("SOMETHING_NEW", BatchState.IN_PROGRESS),
            ("SUCCEEDED", BatchState.DONE),
            ("FAILED", BatchState.FAILED),
            ("CANCELLED", BatchState.CANCELLED),
            ("EXPIRED", BatchState.EXPIRED),
        ],
    )
    def test_each_state_in_either_spelling(
        self, prefix: str, word: str, expected: BatchState
    ) -> None:
        adapter, service = google()
        service.on("GET", PATH, google_op(prefix + word))
        assert adapter.batch_status(KEY, "batches/abc123") is expected

    @pytest.mark.parametrize("word", ["CANCELLED", "EXPIRED"])
    def test_work_finished_before_the_end_is_still_read_and_charged(self, word: str) -> None:
        adapter, service = google()
        service.on("GET", PATH, google_op("BATCH_STATE_" + word, response=inlined()))
        assert adapter.batch_status(KEY, "batches/abc123") is BatchState.DONE

    def test_a_failed_batch_stays_failed(self) -> None:
        adapter, service = google()
        service.on("GET", PATH, google_op("BATCH_STATE_FAILED", response=inlined()))
        assert adapter.batch_status(KEY, "batches/abc123") is BatchState.FAILED

    def test_without_a_state_the_operation_itself_says_how_it_ended(self) -> None:
        adapter, service = google()
        cases: list[tuple[dict[str, Any], BatchState]] = [
            ({"done": False}, BatchState.IN_PROGRESS),
            ({"done": True, "response": inlined()}, BatchState.DONE),
            ({"done": True, "error": {"code": 1}}, BatchState.CANCELLED),
            ({"done": True, "error": {"code": 13}}, BatchState.FAILED),
        ]
        for changes, expected in cases:
            service.on("GET", PATH, google_op(None, **changes))
            assert adapter.batch_status(KEY, "batches/abc123") is expected


class TestGoogleAnswer:
    @pytest.mark.parametrize("shape", ["reference", "guide-object", "guide-list"])
    def test_reads_the_answer_wherever_the_documents_put_it(self, shape: str) -> None:
        adapter, service = google()
        service.on("GET", PATH, google_op("BATCH_STATE_SUCCEEDED", response=inlined(shape=shape)))
        found = adapter.fetch_batch_answer(KEY, "batches/abc123", tag=TAG)
        assert found.error is None
        assert found.result is not None and found.result.data == ANSWER
        # Thinking tokens are output tokens too (25 + 5).
        assert (found.result.tokens_in, found.result.tokens_out) == (120, 30)

    def test_an_entry_for_another_key_is_not_this_runs_answer(self) -> None:
        adapter, service = google()
        entry = {"metadata": {"key": "someone-else"}, "response": GOOGLE_RESPONSE}
        service.on("GET", PATH, google_op("BATCH_STATE_SUCCEEDED", response=inlined(entry)))
        assert adapter.fetch_batch_answer(KEY, "batches/abc123", tag=TAG).error is (
            ProviderErrorKind.BAD_OUTPUT
        )

    @pytest.mark.parametrize(
        ("code", "kind"),
        [
            (3, ProviderErrorKind.BAD_REQUEST),
            (4, ProviderErrorKind.TIMEOUT),
            (8, ProviderErrorKind.RATE_LIMITED),
            (14, ProviderErrorKind.UNAVAILABLE),
            (16, ProviderErrorKind.AUTH),
            (2, ProviderErrorKind.BAD_OUTPUT),
        ],
    )
    def test_the_status_code_of_a_failed_request_becomes_a_failure_kind(
        self, code: int, kind: ProviderErrorKind
    ) -> None:
        adapter, service = google()
        entry = {"metadata": {"key": TAG}, "error": {"code": code, "message": "ignored text"}}
        service.on("GET", PATH, google_op("BATCH_STATE_SUCCEEDED", response=inlined(entry)))
        found = adapter.fetch_batch_answer(KEY, "batches/abc123", tag=TAG)
        assert found.result is None and found.error is kind

    def test_a_blocked_or_cut_off_answer_is_an_unusable_answer(self) -> None:
        adapter, service = google()
        cut = {"candidates": [{"finishReason": "MAX_TOKENS", "content": {"parts": []}}]}
        entry = {"metadata": {"key": TAG}, "response": cut}
        service.on("GET", PATH, google_op("BATCH_STATE_SUCCEEDED", response=inlined(entry)))
        assert adapter.fetch_batch_answer(KEY, "batches/abc123", tag=TAG).error is (
            ProviderErrorKind.BAD_OUTPUT
        )

    def test_no_answer_at_all_is_an_unusable_answer(self) -> None:
        adapter, service = google()
        service.on("GET", PATH, google_op("BATCH_STATE_SUCCEEDED", response={}))
        assert adapter.fetch_batch_answer(KEY, "batches/abc123", tag=TAG).error is (
            ProviderErrorKind.BAD_OUTPUT
        )


class TestGoogleCancelAndFind:
    def test_cancel_asks_the_provider_to_stop(self) -> None:
        adapter, service = google()
        service.on("POST", "/v1beta/batches/abc123:cancel", {})
        adapter.cancel_batch(KEY, "batches/abc123")
        assert service.requests[0].headers["x-goog-api-key"] == KEY

    def test_finds_a_batch_by_its_display_name_across_pages(self) -> None:
        adapter, service = google()
        pages = {
            None: {
                "operations": [google_op(name="batches/other", metadata={"displayName": "other"})],
                "nextPageToken": "next",
            },
            "next": {"operations": [google_op(name="batches/mine")]},
        }

        def page(request: httpx2.Request) -> httpx2.Response:
            assert request.url.params["pageSize"] == "100"
            return httpx2.Response(200, json=pages[request.url.params.get("pageToken")])

        service.on("GET", "/v1beta/batches", page)
        assert adapter.find_batches_by_tag(KEY, TAG) == ["batches/mine"]
        assert adapter.find_batches_by_tag(KEY, "unknown") == []

    def test_gives_up_after_a_bounded_number_of_pages(self) -> None:
        adapter, service = google()
        service.on(
            "GET",
            "/v1beta/batches",
            {"operations": [google_op(metadata={"displayName": "x"})], "nextPageToken": "more"},
        )
        assert adapter.find_batches_by_tag(KEY, TAG) == []
        assert len(service.calls("GET", "/v1beta/batches")) == 10

    @pytest.mark.parametrize("bad", ["../models", "operations/abc", "batches/", "batches/../x", ""])
    def test_a_name_that_is_not_the_shape_of_a_real_one_is_never_put_in_an_address(
        self, bad: str
    ) -> None:
        adapter, service = google()
        for call in (adapter.batch_status, adapter.cancel_batch):
            with pytest.raises(ProviderError) as caught:
                call(KEY, bad)
            assert caught.value.kind is ProviderErrorKind.BAD_REQUEST
        assert service.requests == []


# --- Who offers Economy --------------------------------------------------------------------------


def test_only_the_providers_with_a_batch_service_that_can_be_searched_by_tag_offer_economy() -> (
    None
):
    offers = {p: isinstance(provider_for(p), BatchProvider) for p in Provider}
    assert offers == {
        Provider.OPENAI: True,
        Provider.GOOGLE: True,
        Provider.ANTHROPIC: False,
        Provider.OPENROUTER: False,
    }


def test_an_error_never_carries_the_key_or_any_text_of_the_answer() -> None:
    adapter, service = openai()
    service.on("GET", "/v1/batches/batch_abc123", {"error": f"secret {KEY} text"}, status=500)
    with pytest.raises(ProviderError) as caught:
        adapter.batch_status(KEY, "batch_abc123")
    assert KEY not in str(caught.value) and "secret" not in str(caught.value)


def test_a_results_file_larger_than_the_cap_is_refused() -> None:
    adapter, service = openai()
    service.on(
        "GET",
        "/v1/batches/batch_abc123",
        openai_batch("completed", output_file_id="file-out1"),
    )
    service.text("/v1/files/file-out1/content", "x" * (4 * 1024 * 1024 + 1))
    with pytest.raises(ProviderError) as caught:
        adapter.fetch_batch_answer(KEY, "batch_abc123", tag=TAG)
    assert caught.value.kind is ProviderErrorKind.TOO_LARGE


# --- The batch smoke check ------------------------------------------------------------------------


class TestBatchSmoke:
    def test_proves_send_find_state_and_cancel_without_waiting_for_an_answer(self) -> None:

        fake = FakeProvider()
        worked, lines = smoke_batch(fake, KEY, "fake-small", sleep=lambda _: None)
        assert worked
        assert lines == [
            "Send a batch: worked.",
            "Find it again by its tag: worked.",
            "Ask its state: worked (IN_PROGRESS).",
            "Cancel it: worked (asked the provider to stop).",
        ]
        assert fake.cancelled == ["fake-batch-1"]
        assert all(KEY not in line for line in lines)

    def test_waits_for_the_answer_when_asked_and_does_not_cancel_a_finished_batch(self) -> None:

        fake = FakeProvider()
        pauses: list[float] = []

        def sleep(seconds: float) -> None:
            pauses.append(seconds)
            for batch_id in fake.batches:
                fake.finish(batch_id, StructuredResult({"ok": True}, 10, 5))

        clock = iter(range(0, 1000, 5))
        worked, lines = smoke_batch(
            fake, KEY, "fake-small", wait_seconds=60, sleep=sleep, clock=lambda: float(next(clock))
        )
        assert worked
        assert "After waiting: DONE." in lines
        assert lines[-1] == "Read its answer: worked (10 tokens in, 5 out)."
        assert fake.cancelled == []

    def test_a_batch_not_done_in_time_is_cancelled(self) -> None:

        fake = FakeProvider()
        clock = iter(range(0, 1000, 30))
        worked, lines = smoke_batch(
            fake,
            KEY,
            "fake-small",
            wait_seconds=60,
            sleep=lambda _: None,
            clock=lambda: float(next(clock)),
        )
        assert worked
        assert "After waiting: IN_PROGRESS." in lines
        assert fake.cancelled == ["fake-batch-1"]

    def test_a_failed_send_stops_there(self) -> None:

        fake = FakeProvider()
        fake.reject_submit = ProviderError(ProviderErrorKind.AUTH, status=401)
        worked, lines = smoke_batch(fake, KEY, "fake-small", sleep=lambda _: None)
        assert not worked
        assert lines == ["Send a batch: FAILED (provider call failed: AUTH (HTTP 401))"]

    def test_a_batch_that_cannot_be_found_by_its_tag_is_a_failure_that_is_still_cancelled(
        self,
    ) -> None:

        fake = FakeProvider()
        fake.find_batches_by_tag = lambda _key, _tag: []  # type: ignore[method-assign]
        pauses: list[float] = []
        worked, lines = smoke_batch(fake, KEY, "fake-small", sleep=pauses.append)
        assert not worked
        assert "Find it again by its tag: FAILED (it was not in the provider's list)." in lines
        assert len(pauses) == 4  # it looked five times, a little apart
        assert fake.cancelled == ["fake-batch-1"]  # nothing is left running

    def test_works_against_a_real_adapter_over_the_mock_service(self) -> None:

        adapter, service = openai()
        openai_ready(service)
        service.on(
            "GET",
            "/v1/batches",
            {"data": [openai_batch("validating", metadata={})], "has_more": False},
        )
        service.on("POST", "/v1/batches/batch_abc123/cancel", openai_batch("cancelling"))
        worked, lines = smoke_batch(adapter, KEY, "model-x", sleep=lambda _: None)
        assert not worked  # the list never showed the batch: the smoke check says so
        assert lines[0] == "Send a batch: worked."
        assert all(KEY not in line for line in lines)
