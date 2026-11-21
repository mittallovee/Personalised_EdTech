from datetime import datetime

from pydantic import BaseModel, Field, SecretStr

from qbank.modules.ai.names import Provider


class SetKey(BaseModel):
    """The key as the provider gave it. Write-only: no response ever carries it."""

    key: SecretStr = Field(
        description="The provider's API key, as copied from the provider. It is sealed on the"
        " server and never shown again; only its last four characters are.",
    )


class ProviderKeyOut(BaseModel):
    provider: Provider
    configured: bool
    last4: str | None = Field(
        description="The last four characters, so a person can tell which key is stored."
    )
    updated_at: datetime | None


class KeysOut(BaseModel):
    encryption_ready: bool = Field(
        description="False when the server has no master encryption key: keys cannot be stored"
        " until whoever runs the server sets `AI_KEYS_MASTER_KEY`."
    )
    data: list[ProviderKeyOut]
