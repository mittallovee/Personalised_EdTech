"""Public interface of the AI module: what other modules and the command line use."""

from qbank.core.secretbox import Keyring, KeyUnreadable
from qbank.modules.ai.keys import open_key, reseal_all
from qbank.modules.ai.metered import (
    CallOutcome,
    MeteredCall,
    check_model,
    make_call,
    release_reservation,
    reserve_call,
    settle_call,
)
from qbank.modules.ai.names import Provider
from qbank.modules.ai.orchestrator import ProviderFactory
from qbank.modules.ai.providers.base import (
    AIProvider,
    BatchProvider,
    ModelInfo,
    ProviderError,
    ProviderErrorKind,
    StructuredRequest,
    StructuredResult,
)
from qbank.modules.ai.providers.registry import provider_for
from qbank.modules.ai.providers.smoke import smoke, smoke_batch

__all__ = [
    "AIProvider",
    "BatchProvider",
    "CallOutcome",
    "KeyUnreadable",
    "Keyring",
    "MeteredCall",
    "ModelInfo",
    "Provider",
    "ProviderError",
    "ProviderErrorKind",
    "ProviderFactory",
    "StructuredRequest",
    "StructuredResult",
    "check_model",
    "make_call",
    "open_key",
    "provider_for",
    "release_reservation",
    "reseal_all",
    "reserve_call",
    "settle_call",
    "smoke",
    "smoke_batch",
]
