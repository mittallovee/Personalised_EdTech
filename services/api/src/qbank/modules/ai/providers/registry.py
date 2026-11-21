"""The adapter for a provider, by name: the one place that knows which class serves which."""

from collections.abc import Callable

from qbank.modules.ai.names import Provider
from qbank.modules.ai.providers.anthropic import AnthropicProvider
from qbank.modules.ai.providers.base import AIProvider
from qbank.modules.ai.providers.demo import DemoProvider
from qbank.modules.ai.providers.google import GoogleProvider
from qbank.modules.ai.providers.http import Http
from qbank.modules.ai.providers.openai import OpenAIProvider
from qbank.modules.ai.providers.openrouter import OpenRouterProvider

_shared: Http | None = None


def shared_http() -> Http:
    """One connection pool for the whole process, made when first needed."""
    global _shared
    if _shared is None:
        _shared = Http()
    return _shared


def provider_for(provider: Provider, http: Http | None = None) -> AIProvider:
    shared = http or shared_http()
    adapters: dict[Provider, AIProvider] = {
        Provider.ANTHROPIC: AnthropicProvider(shared),
        Provider.OPENAI: OpenAIProvider(shared),
        Provider.GOOGLE: GoogleProvider(shared),
        Provider.OPENROUTER: OpenRouterProvider(shared),
    }
    return adapters[provider]


def provider_factory(demo: bool) -> Callable[[Provider], AIProvider]:
    """The adapters the app uses: the real ones, or (``demo``, local only) the stand-in for all."""
    if demo:
        stand_in = DemoProvider()
        return lambda _provider: stand_in
    return provider_for
