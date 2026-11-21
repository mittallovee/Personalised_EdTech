"""The AI providers a coaching can bring its own key for (H-01)."""

from enum import StrEnum


class Provider(StrEnum):
    ANTHROPIC = "ANTHROPIC"
    OPENAI = "OPENAI"
    GOOGLE = "GOOGLE"
    OPENROUTER = "OPENROUTER"
