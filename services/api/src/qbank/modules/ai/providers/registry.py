"""The adapter for a provider, by name: the one place that knows which class serves which."""

from qbank.modules.ai.names import Provider
from qbank.modules.ai.providers.anthropic import AnthropicProvider
from qbank.modules.ai.providers.base import AIProvider
from qbank.modules.ai.providers.google import GoogleProvider
from qbank.modules.ai.providers.http import Http
from qbank.modules.ai.providers.openai import OpenAIProvider
from qbank.modules.ai.providers.openrouter import OpenRouterProvider


def provider_for(provider: Provider, http: Http | None = None) -> AIProvider:
    shared = http or Http()
    adapters: dict[Provider, AIProvider] = {
        Provider.ANTHROPIC: AnthropicProvider(shared),
        Provider.OPENAI: OpenAIProvider(shared),
        Provider.GOOGLE: GoogleProvider(shared),
        Provider.OPENROUTER: OpenRouterProvider(shared),
    }
    return adapters[provider]
