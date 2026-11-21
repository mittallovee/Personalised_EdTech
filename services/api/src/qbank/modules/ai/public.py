"""Public interface of the AI module: what other modules and the command line use."""

from qbank.core.secretbox import Keyring, KeyUnreadable
from qbank.modules.ai.keys import open_key, reseal_all
from qbank.modules.ai.names import Provider
from qbank.modules.ai.providers.base import (
    AIProvider,
    ModelInfo,
    ProviderError,
    ProviderErrorKind,
    StructuredRequest,
    StructuredResult,
)
from qbank.modules.ai.providers.registry import provider_for
from qbank.modules.ai.providers.smoke import smoke

__all__ = [
    "AIProvider",
    "KeyUnreadable",
    "Keyring",
    "ModelInfo",
    "Provider",
    "ProviderError",
    "ProviderErrorKind",
    "StructuredRequest",
    "StructuredResult",
    "open_key",
    "provider_for",
    "reseal_all",
    "smoke",
]
