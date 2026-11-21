"""The AI providers a coaching can bring its own key for (H-01)."""

from enum import StrEnum


class Provider(StrEnum):
    ANTHROPIC = "ANTHROPIC"
    OPENAI = "OPENAI"
    GOOGLE = "GOOGLE"
    OPENROUTER = "OPENROUTER"


class Operation(StrEnum):
    """What the AI can be asked to do to a question (M5 design note §8)."""

    TAG = "TAG"
    TRANSLATE = "TRANSLATE"
    SOLVE = "SOLVE"
    VERIFY = "VERIFY"


class Mode(StrEnum):
    """Now runs at once; Economy is a batch run at the provider's lower price, finished later."""

    NOW = "NOW"
    ECONOMY = "ECONOMY"


class Scope(StrEnum):
    """Whose prompt it is: the platform's, one coaching's, or one person's (prompt spec §4)."""

    PLATFORM = "PLATFORM"
    COACHING = "COACHING"
    PERSONAL = "PERSONAL"
