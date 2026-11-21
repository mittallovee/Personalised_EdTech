"""M5 PR 5a-2: the four provider adapters, the fake provider and the smoke check (T44).

No network: every call goes through a mock transport that returns a recorded-style answer and keeps
the request, so these tests check what we send (address, the one header that carries the key, the
schema), how each answer is read, and how each failure is reported. They prove the adapters against
the providers' documents as written, not against the live services (``qbank ai-smoke`` does that).
"""

import json
from collections.abc import Callable
from decimal import Decimal
from typing import Any

import httpx2
import pytest

from qbank.modules.ai.names import Provider
from qbank.modules.ai.providers.anthropic import AnthropicProvider
from qbank.modules.ai.providers.base import (
    AIProvider,
    ProviderError,
    ProviderErrorKind,
    StructuredRequest,
    StructuredResult,
)
from qbank.modules.ai.providers.fake import FakeProvider
from qbank.modules.ai.providers.google import GoogleProvider
from qbank.modules.ai.providers.http import MAX_RESPONSE_BYTES, Http
from qbank.modules.ai.providers.openai import OpenAIProvider
from qbank.modules.ai.providers.openrouter import OpenRouterProvider, per_million
from qbank.modules.ai.providers.registry import provider_for
from qbank.modules.ai.providers.smoke import smoke

KEY = "test-key-" + "x" * 16 + "0123"  # made up, and too plain to look like a real key
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
ANSWER_TEXT = json.dumps({"label": "kinematics"})

Handler = Callable[[httpx2.Request], httpx2.Response]


class Seen:
    """The requests an adapter sent."""

    def __init__(self) -> None:
        self.requests: list[httpx2.Request] = []

    @property
    def last(self) -> httpx2.Request:
        return self.requests[-1]

    def body(self) -> dict[str, Any]:
        parsed: dict[str, Any] = json.loads(self.last.content)
        return parsed


def make(handler: Handler) -> tuple[Http, Seen]:
    seen = Seen()

    def record(request: httpx2.Request) -> httpx2.Response:
        seen.requests.append(request)
        return handler(request)

    return Http(httpx2.Client(transport=httpx2.MockTransport(record))), seen


def reply(body: Any, status: int = 200, headers: dict[str, str] | None = None) -> Handler:
    def handler(_: httpx2.Request) -> httpx2.Response:
        if isinstance(body, bytes):
            return httpx2.Response(status, content=body, headers=headers)
        return httpx2.Response(status, json=body, headers=headers)

    return handler


# What each provider says when it answers well; the same ANSWER_TEXT in each one's own shape.
GOOD: dict[Provider, dict[str, Any]] = {
    Provider.ANTHROPIC: {
        "stop_reason": "end_turn",
        "content": [{"type": "text", "text": ANSWER_TEXT}],
        "usage": {"input_tokens": 120, "output_tokens": 30},
    },
    Provider.OPENAI: {
        "status": "completed",
        "output": [
            {"type": "reasoning", "summary": []},
            {"type": "message", "content": [{"type": "output_text", "text": ANSWER_TEXT}]},
        ],
        "usage": {"input_tokens": 120, "output_tokens": 30},
    },
    Provider.GOOGLE: {
        "candidates": [
            {"finishReason": "STOP", "content": {"parts": [{"text": ANSWER_TEXT}]}},
        ],
        "usageMetadata": {
            "promptTokenCount": 120,
            "candidatesTokenCount": 25,
            "thoughtsTokenCount": 5,
        },
    },
    Provider.OPENROUTER: {
        "choices": [
            {"finish_reason": "stop", "message": {"role": "assistant", "content": ANSWER_TEXT}}
        ],
        "usage": {"prompt_tokens": 120, "completion_tokens": 30, "cost": 0.00042},
    },
}
BUILD: dict[Provider, Callable[[Http], AIProvider]] = {
    Provider.ANTHROPIC: AnthropicProvider,
    Provider.OPENAI: OpenAIProvider,
    Provider.GOOGLE: GoogleProvider,
    Provider.OPENROUTER: OpenRouterProvider,
}
EVERY = list(Provider)


def adapter(provider: Provider, handler: Handler) -> tuple[AIProvider, Seen]:
    http, seen = make(handler)
    return BUILD[provider](http), seen


# --- Asking for an answer ---------------------------------------------------------------------


@pytest.mark.parametrize("provider", EVERY)
def test_a_good_answer_is_read_the_same_way_for_every_provider(provider: Provider) -> None:
    adapter_, _ = adapter(provider, reply(GOOD[provider]))
    result = adapter_.generate_structured(KEY, REQUEST)
    assert result.data == {"label": "kinematics"}
    assert result.tokens_in == 120
    assert result.tokens_out == 30
    if provider is Provider.OPENROUTER:
        assert result.cost_usd == Decimal("0.00042")
    else:
        assert result.cost_usd is None


@pytest.mark.parametrize("provider", EVERY)
def test_the_key_travels_only_in_its_header_and_never_in_the_address_or_body(
    provider: Provider,
) -> None:
    adapter_, seen = adapter(provider, reply(GOOD[provider]))
    adapter_.generate_structured(KEY, REQUEST)
    request = seen.last
    assert request.method == "POST"
    assert request.url.scheme == "https"
    assert KEY not in str(request.url)
    assert KEY not in request.content.decode()
    carrying = [name for name, value in request.headers.items() if KEY in value]
    expected = {
        Provider.ANTHROPIC: "x-api-key",
        Provider.OPENAI: "authorization",
        Provider.GOOGLE: "x-goog-api-key",
        Provider.OPENROUTER: "authorization",
    }[provider]
    assert carrying == [expected]
    # The instructions and the data are sent apart, and the schema is the one given.
    text = request.content.decode()
    assert "SYSTEM-TEXT" in text
    assert "USER-TEXT" in text
    assert json.loads(text) != {}


def test_anthropic_request_shape() -> None:
    adapter_, seen = adapter(Provider.ANTHROPIC, reply(GOOD[Provider.ANTHROPIC]))
    adapter_.generate_structured(KEY, REQUEST)
    assert str(seen.last.url) == "https://api.anthropic.com/v1/messages"
    assert seen.last.headers["anthropic-version"] == "2023-06-01"
    body = seen.body()
    assert body["model"] == "model-x"
    assert body["max_tokens"] == 300
    assert body["system"] == "SYSTEM-TEXT"
    assert body["messages"] == [{"role": "user", "content": "USER-TEXT"}]
    assert body["output_config"] == {"format": {"type": "json_schema", "schema": SCHEMA}}
    assert body["temperature"] == 0.2


def test_openai_request_shape() -> None:
    adapter_, seen = adapter(Provider.OPENAI, reply(GOOD[Provider.OPENAI]))
    adapter_.generate_structured(KEY, REQUEST)
    assert str(seen.last.url) == "https://api.openai.com/v1/responses"
    body = seen.body()
    assert body["instructions"] == "SYSTEM-TEXT"
    assert body["input"] == "USER-TEXT"
    assert body["max_output_tokens"] == 300
    assert body["store"] is False
    assert body["text"]["format"] == {
        "type": "json_schema",
        "name": "tag",
        "schema": SCHEMA,
        "strict": True,
    }


def test_google_request_shape_and_a_model_id_cannot_change_the_path() -> None:
    adapter_, seen = adapter(Provider.GOOGLE, reply(GOOD[Provider.GOOGLE]))
    adapter_.generate_structured(KEY, REQUEST)
    assert str(seen.last.url) == (
        "https://generativelanguage.googleapis.com/v1beta/models/model-x:generateContent"
    )
    body = seen.body()
    assert body["systemInstruction"] == {"parts": [{"text": "SYSTEM-TEXT"}]}
    assert body["contents"] == [{"role": "user", "parts": [{"text": "USER-TEXT"}]}]
    assert body["generationConfig"]["responseMimeType"] == "application/json"
    assert body["generationConfig"]["responseJsonSchema"] == SCHEMA
    assert body["generationConfig"]["maxOutputTokens"] == 300
    hostile = StructuredRequest(
        model_id="../../v1/other?x=1",
        system="s",
        user="u",
        schema_name="tag",
        schema=SCHEMA,
        max_output_tokens=10,
    )
    requests_before = len(seen.requests)
    with pytest.raises(ProviderError) as refused:
        adapter_.generate_structured(KEY, hostile)
    assert refused.value.kind is ProviderErrorKind.BAD_REQUEST
    assert len(seen.requests) == requests_before  # nothing was sent for it


def test_openrouter_request_shape() -> None:
    adapter_, seen = adapter(Provider.OPENROUTER, reply(GOOD[Provider.OPENROUTER]))
    adapter_.generate_structured(KEY, REQUEST)
    assert str(seen.last.url) == "https://openrouter.ai/api/v1/chat/completions"
    body = seen.body()
    assert body["messages"] == [
        {"role": "system", "content": "SYSTEM-TEXT"},
        {"role": "user", "content": "USER-TEXT"},
    ]
    assert body["max_tokens"] == 300
    assert body["response_format"] == {
        "type": "json_schema",
        "json_schema": {"name": "tag", "strict": True, "schema": SCHEMA},
    }


def test_no_temperature_is_sent_when_none_is_asked_for() -> None:
    plain = StructuredRequest(
        model_id="m", system="s", user="u", schema_name="t", schema=SCHEMA, max_output_tokens=10
    )
    for provider in EVERY:
        adapter_, seen = adapter(provider, reply(GOOD[provider]))
        adapter_.generate_structured(KEY, plain)
        assert "temperature" not in seen.last.content.decode(), provider


def test_a_code_fence_around_the_json_is_tolerated_but_nothing_else() -> None:
    fenced = json.loads(json.dumps(GOOD[Provider.ANTHROPIC]))
    fenced["content"][0]["text"] = f"```json\n{ANSWER_TEXT}\n```"
    adapter_, _ = adapter(Provider.ANTHROPIC, reply(fenced))
    assert adapter_.generate_structured(KEY, REQUEST).data == {"label": "kinematics"}
    chatty = json.loads(json.dumps(GOOD[Provider.ANTHROPIC]))
    chatty["content"][0]["text"] = f"Sure! Here it is: {ANSWER_TEXT}"
    adapter_, _ = adapter(Provider.ANTHROPIC, reply(chatty))
    with pytest.raises(ProviderError) as problem:
        adapter_.generate_structured(KEY, REQUEST)
    assert problem.value.kind is ProviderErrorKind.BAD_OUTPUT


# Each provider's own ways of answering without an answer we can use.
UNUSABLE: list[tuple[Provider, dict[str, Any]]] = [
    (Provider.ANTHROPIC, {**GOOD[Provider.ANTHROPIC], "stop_reason": "max_tokens"}),
    (Provider.ANTHROPIC, {**GOOD[Provider.ANTHROPIC], "stop_reason": "refusal"}),
    (Provider.ANTHROPIC, {"stop_reason": "end_turn", "content": []}),
    (Provider.ANTHROPIC, {"stop_reason": "end_turn", "content": [{"type": "text", "text": "[1]"}]}),
    (Provider.OPENAI, {**GOOD[Provider.OPENAI], "status": "incomplete"}),
    (
        Provider.OPENAI,
        {
            "status": "completed",
            "output": [{"type": "message", "content": [{"type": "refusal", "refusal": "no"}]}],
        },
    ),
    (Provider.OPENAI, {"status": "completed", "output": []}),
    (Provider.GOOGLE, {"promptFeedback": {"blockReason": "SAFETY"}}),
    (
        Provider.GOOGLE,
        {"candidates": [{"finishReason": "MAX_TOKENS", "content": {"parts": [{"text": "{"}]}}]},
    ),
    (
        Provider.GOOGLE,
        {
            "candidates": [
                {"finishReason": "STOP", "content": {"parts": [{"text": "x", "thought": True}]}}
            ]
        },
    ),
    (Provider.GOOGLE, {"candidates": []}),
    (Provider.OPENROUTER, {"choices": [{"finish_reason": "length", "message": {"content": "{"}}]}),
    (Provider.OPENROUTER, {"choices": [{"finish_reason": "stop", "message": {"content": "  "}}]}),
    (Provider.OPENROUTER, {"choices": []}),
]


@pytest.mark.parametrize(("provider", "body"), UNUSABLE)
def test_an_answer_that_is_cut_off_refused_empty_or_not_json_is_bad_output(
    provider: Provider, body: dict[str, Any]
) -> None:
    adapter_, _ = adapter(provider, reply(body))
    with pytest.raises(ProviderError) as problem:
        adapter_.generate_structured(KEY, REQUEST)
    assert problem.value.kind is ProviderErrorKind.BAD_OUTPUT
    assert not problem.value.retryable


def test_google_counts_thinking_tokens_as_output_and_missing_counts_are_unknown() -> None:
    adapter_, _ = adapter(Provider.GOOGLE, reply(GOOD[Provider.GOOGLE]))
    assert adapter_.generate_structured(KEY, REQUEST).tokens_out == 30
    bare = {"candidates": GOOD[Provider.GOOGLE]["candidates"]}
    adapter_, _ = adapter(Provider.GOOGLE, reply(bare))
    result = adapter_.generate_structured(KEY, REQUEST)
    assert (result.tokens_in, result.tokens_out) == (None, None)


# --- Failures ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("status", "kind", "retryable"),
    [
        (401, ProviderErrorKind.AUTH, False),
        (403, ProviderErrorKind.AUTH, False),
        (429, ProviderErrorKind.RATE_LIMITED, True),
        (400, ProviderErrorKind.BAD_REQUEST, False),
        (404, ProviderErrorKind.BAD_REQUEST, False),
        (413, ProviderErrorKind.TOO_LARGE, False),
        (408, ProviderErrorKind.UNAVAILABLE, True),
        (500, ProviderErrorKind.UNAVAILABLE, True),
        (503, ProviderErrorKind.UNAVAILABLE, True),
        (529, ProviderErrorKind.UNAVAILABLE, True),
    ],
)
@pytest.mark.parametrize("provider", EVERY)
def test_an_http_failure_becomes_one_kind_of_error_that_says_nothing_of_the_call(
    provider: Provider, status: int, kind: ProviderErrorKind, retryable: bool
) -> None:
    echo = {"error": {"message": f"bad key {KEY} and prompt USER-TEXT"}}
    adapter_, _ = adapter(provider, reply(echo, status=status, headers={"retry-after": "7"}))
    for call in (
        lambda: adapter_.generate_structured(KEY, REQUEST),
        lambda: adapter_.list_models(KEY),
    ):
        with pytest.raises(ProviderError) as problem:
            call()
        error = problem.value
        assert (error.kind, error.status, error.retryable) == (kind, status, retryable)
        assert KEY not in str(error)
        assert "USER-TEXT" not in str(error)
        assert KEY not in repr(error.__dict__)
    assert problem.value.retry_after_seconds == 7.0


def test_a_retry_after_that_is_not_a_sensible_number_is_ignored() -> None:
    for header in ("soon", "-5", "99999"):
        adapter_, _ = adapter(
            Provider.OPENAI, reply({}, status=429, headers={"retry-after": header})
        )
        with pytest.raises(ProviderError) as problem:
            adapter_.generate_structured(KEY, REQUEST)
        assert problem.value.retry_after_seconds is None


def test_a_timeout_and_a_connection_failure_are_retryable_and_say_nothing_of_the_call() -> None:
    def slow(_: httpx2.Request) -> httpx2.Response:
        raise httpx2.ReadTimeout(f"timed out talking with {KEY}")

    def down(_: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError(f"cannot reach {KEY}")

    for handler, kind in ((slow, ProviderErrorKind.TIMEOUT), (down, ProviderErrorKind.UNAVAILABLE)):
        adapter_, _ = adapter(Provider.ANTHROPIC, handler)
        with pytest.raises(ProviderError) as problem:
            adapter_.generate_structured(KEY, REQUEST)
        assert problem.value.kind is kind
        assert problem.value.retryable
        assert KEY not in str(problem.value)
        assert problem.value.__cause__ is None  # the original message is not kept


def test_an_answer_that_is_not_json_or_not_an_object_is_bad_output() -> None:
    for body in (b"<html>gateway</html>", b"[1, 2]", b"null"):
        adapter_, _ = adapter(Provider.OPENAI, reply(body))
        with pytest.raises(ProviderError) as problem:
            adapter_.generate_structured(KEY, REQUEST)
        assert problem.value.kind is ProviderErrorKind.BAD_OUTPUT


def test_an_answer_bigger_than_we_read_is_refused_without_parsing_it() -> None:
    huge = b'{"x": "' + b"a" * (MAX_RESPONSE_BYTES + 10) + b'"}'
    adapter_, _ = adapter(Provider.OPENAI, reply(huge))
    with pytest.raises(ProviderError) as problem:
        adapter_.generate_structured(KEY, REQUEST)
    assert problem.value.kind is ProviderErrorKind.TOO_LARGE
    declared = reply(b"{}", headers={"content-length": str(MAX_RESPONSE_BYTES + 1)})
    adapter_, _ = adapter(Provider.OPENAI, declared)
    with pytest.raises(ProviderError) as again:
        adapter_.list_models(KEY)
    assert again.value.kind is ProviderErrorKind.TOO_LARGE


def test_redirects_are_not_followed() -> None:
    def moved(_: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(302, headers={"location": "https://evil.example/steal"})

    adapter_, seen = adapter(Provider.OPENAI, moved)
    with pytest.raises(ProviderError) as problem:
        adapter_.list_models(KEY)
    assert problem.value.kind is ProviderErrorKind.BAD_REQUEST
    assert [r.url.host for r in seen.requests] == ["api.openai.com"]


# --- The model lists --------------------------------------------------------------------------


def test_anthropic_models_are_listed_across_pages() -> None:
    pages = [
        {
            "data": [
                {"id": "claude-a", "display_name": "Claude A"},
                {"id": "claude-b"},
                {"nope": 1},
            ],
            "has_more": True,
            "last_id": "claude-b",
        },
        {
            "data": [{"id": "claude-c", "display_name": "Claude C"}],
            "has_more": False,
            "last_id": "claude-c",
        },
    ]

    def handler(request: httpx2.Request) -> httpx2.Response:
        after = request.url.params.get("after_id")
        return httpx2.Response(200, json=pages[0] if after is None else pages[1])

    adapter_, seen = adapter(Provider.ANTHROPIC, handler)
    models = adapter_.list_models(KEY)
    assert [(m.model_id, m.display_name) for m in models] == [
        ("claude-a", "Claude A"),
        ("claude-b", "claude-b"),
        ("claude-c", "Claude C"),
    ]
    assert all(m.price_in_per_mtok is None for m in models)  # Anthropic's list gives no prices
    assert [r.url.params.get("after_id") for r in seen.requests] == [None, "claude-b"]
    assert all(r.method == "GET" and r.url.params["limit"] == "1000" for r in seen.requests)


def test_a_provider_that_always_says_there_is_more_is_read_a_bounded_number_of_times() -> None:
    forever = {"data": [{"id": "m"}], "has_more": True, "last_id": "m"}
    adapter_, seen = adapter(Provider.ANTHROPIC, reply(forever))
    adapter_.list_models(KEY)
    assert len(seen.requests) == 10


def test_openai_models_leave_out_the_ones_that_do_not_write_text() -> None:
    body = {
        "data": [
            {"id": "gpt-x"},
            {"id": "text-embedding-3-large"},
            {"id": "whisper-1"},
            {"id": "gpt-image-1"},
            {"id": "gpt-x-mini"},
            {"id": "tts-1-hd"},
        ]
    }
    adapter_, seen = adapter(Provider.OPENAI, reply(body))
    assert [m.model_id for m in adapter_.list_models(KEY)] == ["gpt-x", "gpt-x-mini"]
    assert str(seen.last.url) == "https://api.openai.com/v1/models"


def test_google_models_keep_only_the_ones_that_generate_content_and_follow_pages() -> None:
    pages = {
        None: {
            "models": [
                {
                    "name": "models/gemini-a",
                    "displayName": "Gemini A",
                    "supportedGenerationMethods": ["generateContent", "countTokens"],
                    "inputTokenLimit": 1048576,
                },
                {"name": "models/embed-x", "supportedGenerationMethods": ["embedContent"]},
            ],
            "nextPageToken": "page-2",
        },
        "page-2": {
            "models": [
                {"name": "models/gemini-b", "supportedGenerationMethods": ["generateContent"]}
            ]
        },
    }

    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, json=pages[request.url.params.get("pageToken")])

    adapter_, seen = adapter(Provider.GOOGLE, handler)
    models = adapter_.list_models(KEY)
    assert [(m.model_id, m.display_name, m.context_tokens) for m in models] == [
        ("gemini-a", "Gemini A", 1048576),
        ("gemini-b", "gemini-b", None),
    ]
    assert KEY not in str(seen.requests[0].url)


def test_openrouter_models_carry_prices_per_million_tokens_and_capabilities() -> None:
    body = {
        "data": [
            {
                "id": "vendor/model-a",
                "name": "Vendor: Model A",
                "context_length": 200000,
                "pricing": {"prompt": "0.000003", "completion": "0.000015"},
                "architecture": {"input_modalities": ["text", "image"]},
                "supported_parameters": ["max_tokens", "structured_outputs"],
            },
            {
                "id": "vendor/router",
                "pricing": {"prompt": "-1", "completion": "-1"},
                "architecture": {"input_modalities": ["text"]},
                "supported_parameters": ["temperature"],
            },
            {"id": "vendor/free", "pricing": {"prompt": "0", "completion": "0"}},
        ]
    }
    adapter_, _ = adapter(Provider.OPENROUTER, reply(body))
    a, router, free = adapter_.list_models(KEY)
    assert (a.price_in_per_mtok, a.price_out_per_mtok) == (Decimal("3"), Decimal("15"))
    assert (a.supports_vision, a.supports_json, a.context_tokens) == (True, True, 200000)
    assert a.display_name == "Vendor: Model A"
    assert (router.price_in_per_mtok, router.price_out_per_mtok) == (None, None)
    assert (router.supports_vision, router.supports_json) == (False, False)
    assert (free.price_in_per_mtok, free.supports_vision, free.supports_json) == (
        Decimal("0"),
        None,
        None,
    )


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        ("0.000003", Decimal("3")),
        ("0.0000001", Decimal("0.1")),
        (0, Decimal("0")),
        ("0", Decimal("0")),
        ("-1", None),
        ("free", None),
        ("NaN", None),
        (None, None),
        (True, None),
        (1.5, None),
    ],
)
def test_prices_are_exact_decimals_in_dollars_per_million_and_unknown_when_odd(
    given: object, expected: Decimal | None
) -> None:
    assert per_million(given) == expected


def test_an_unexpected_shape_in_a_model_list_is_skipped_not_fatal() -> None:
    for provider, body in (
        (Provider.ANTHROPIC, {"data": "nonsense"}),
        (Provider.OPENAI, {"data": [None, 5, {"id": 7}]}),
        (Provider.GOOGLE, {"models": [None, {"name": 3}]}),
        (Provider.OPENROUTER, {"data": [{"id": ""}, None]}),
    ):
        adapter_, _ = adapter(provider, reply(body))
        assert adapter_.list_models(KEY) == []


# --- The registry, the fake and the smoke check -----------------------------------------------


def test_the_registry_gives_the_adapter_for_each_provider() -> None:
    http, _ = make(reply({}))
    for provider in Provider:
        assert provider_for(provider, http).name is provider


def test_the_fake_provider_answers_from_its_script_and_records_what_it_was_asked() -> None:
    fake = FakeProvider()
    fake.script.extend(
        [
            StructuredResult({"label": "a"}, 5, 6, Decimal("0.01")),
            ProviderError(ProviderErrorKind.RATE_LIMITED, status=429),
        ]
    )
    assert fake.generate_structured("k1", REQUEST).data == {"label": "a"}
    with pytest.raises(ProviderError):
        fake.generate_structured("k2", REQUEST)
    assert fake.generate_structured("k3", REQUEST).data == {"ok": True}  # script empty
    assert [key for key, _ in fake.calls] == ["k1", "k2", "k3"]
    assert [m.model_id for m in fake.list_models("k4")] == ["fake-small", "fake-unpriced"]


def test_the_smoke_check_reports_each_step_and_never_the_key() -> None:
    fake = FakeProvider()
    worked, lines = smoke(fake, KEY, None)
    assert worked
    assert lines == [
        "List models: 2 found, 1 with a price.",
        "Ask a model: skipped (name one with --model to try a request).",
    ]
    worked, lines = smoke(fake, KEY, "fake-small")
    assert worked
    assert lines[1].startswith("Ask a model: worked (10 tokens in, 5 out)")
    fake.script.append(StructuredResult({"ok": False}, 1, 1))
    worked, lines = smoke(fake, KEY, "fake-small")
    assert not worked
    assert "not what was asked for" in lines[-1]
    fake.script.append(ProviderError(ProviderErrorKind.AUTH, status=401))
    worked, lines = smoke(fake, KEY, "fake-small")
    assert not worked
    assert lines[-1] == "Ask a model: FAILED (provider call failed: AUTH (HTTP 401))"
    assert all(KEY not in line for line in lines)


def test_the_smoke_check_stops_at_a_list_that_fails() -> None:
    http, _ = make(reply({}, status=401))
    worked, lines = smoke(OpenAIProvider(http), KEY, "gpt-x")
    assert not worked
    assert lines == ["List models: FAILED (provider call failed: AUTH (HTTP 401))"]
