"""M6 PR 6e: each provider adapter puts the pictures of a request where its provider wants them.

A request with no pictures is sent exactly as before (so every existing operation is unchanged);
with pictures, the JPEGs go in as base64 in the provider's own shape, before or beside the text.
"""

import base64
from dataclasses import replace
from typing import Any

import pytest

from qbank.modules.ai.names import Provider
from qbank.modules.ai.providers.anthropic import AnthropicProvider
from qbank.modules.ai.providers.base import AIProvider
from qbank.modules.ai.providers.google import GoogleProvider
from qbank.modules.ai.providers.openai import OpenAIProvider
from qbank.modules.ai.providers.openrouter import OpenRouterProvider
from tests.unit.test_ai_providers import GOOD, KEY, REQUEST, make, reply

PICTURES = (b"\xff\xd8\xff-first", b"\xff\xd8\xff-second")
B64 = [base64.b64encode(p).decode() for p in PICTURES]
WITH = replace(REQUEST, images=PICTURES)

ADAPTERS: dict[Provider, type] = {
    Provider.ANTHROPIC: AnthropicProvider,
    Provider.OPENAI: OpenAIProvider,
    Provider.GOOGLE: GoogleProvider,
    Provider.OPENROUTER: OpenRouterProvider,
}


def sent(provider: Provider, request: Any) -> dict[str, Any]:
    http, seen = make(reply(GOOD[provider]))
    adapter: AIProvider = ADAPTERS[provider](http)
    adapter.generate_structured(KEY, request)
    return seen.body()


def test_openai_sends_text_and_pictures_as_one_message() -> None:
    body = sent(Provider.OPENAI, WITH)
    (message,) = body["input"]
    assert message["role"] == "user"
    assert message["content"][0] == {"type": "input_text", "text": "USER-TEXT"}
    assert [part["image_url"] for part in message["content"][1:]] == [
        f"data:image/jpeg;base64,{b}" for b in B64
    ]


def test_anthropic_sends_the_pictures_before_the_text() -> None:
    (message,) = sent(Provider.ANTHROPIC, WITH)["messages"]
    blocks = message["content"]
    assert [b["type"] for b in blocks] == ["image", "image", "text"]
    assert blocks[0]["source"] == {"type": "base64", "media_type": "image/jpeg", "data": B64[0]}
    assert blocks[2]["text"] == "USER-TEXT"


def test_google_sends_the_pictures_inline_before_the_text() -> None:
    (content,) = sent(Provider.GOOGLE, WITH)["contents"]
    parts = content["parts"]
    assert parts[0] == {"inlineData": {"mimeType": "image/jpeg", "data": B64[0]}}
    assert parts[-1] == {"text": "USER-TEXT"} and len(parts) == 3


def test_openrouter_sends_text_and_picture_urls_in_one_message() -> None:
    user = sent(Provider.OPENROUTER, WITH)["messages"][1]
    assert user["content"][0] == {"type": "text", "text": "USER-TEXT"}
    assert [p["image_url"]["url"] for p in user["content"][1:]] == [
        f"data:image/jpeg;base64,{b}" for b in B64
    ]


@pytest.mark.parametrize("provider", list(Provider))
def test_without_pictures_the_request_is_exactly_what_it_was(provider: Provider) -> None:
    body = sent(provider, REQUEST)
    text = repr(body)
    assert "base64" not in text and "inlineData" not in text and "image" not in text
    assert "USER-TEXT" in text


@pytest.mark.parametrize("provider", list(Provider))
def test_a_picture_never_appears_in_clear_outside_the_request_body(provider: Provider) -> None:
    http, seen = make(reply(GOOD[provider]))
    ADAPTERS[provider](http).generate_structured(KEY, WITH)
    assert all(KEY not in str(r.url) for r in seen.requests)
