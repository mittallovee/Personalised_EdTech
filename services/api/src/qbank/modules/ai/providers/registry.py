"""The adapter for a provider, by name: the one place that knows which class serves which."""

from qbank.modules.ai.names import Provider
from qbank.modules.ai.providers.anthropic import AnthropicProvider
from qbank.modules.ai.providers.base import AIProvider
from qbank.modules.ai.providers.demo import DemoProvider
from qbank.modules.ai.providers.google import GoogleProvider
from qbank.modules.ai.providers.http import Http
from qbank.modules.ai.providers.openai import OpenAIProvider
from qbank.modules.ai.providers.openrouter import OpenRouterProvider

_shared: Http | None = None
_demo = False


def use_demo_provider() -> None:
    """From now on every provider is the demo one (no network, no real key). Called once at start
    when the settings say so; the settings refuse that outside local development and tests."""
    global _demo
    _demo = True


def shared_http() -> Http:
    """One connection pool for the whole process, made when first needed."""
    global _shared
    if _shared is None:
        _shared = Http()
    return _shared


def provider_for(provider: Provider, http: Http | None = None) -> AIProvider:
    if _demo:
        return DemoProvider(provider)
    shared = http or shared_http()
    adapters: dict[Provider, AIProvider] = {
        Provider.ANTHROPIC: AnthropicProvider(shared),
        Provider.OPENAI: OpenAIProvider(shared),
        Provider.GOOGLE: GoogleProvider(shared),
        Provider.OPENROUTER: OpenRouterProvider(shared),
    }
    return adapters[provider]
