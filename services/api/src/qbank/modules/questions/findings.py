"""Findings: what is wrong with a question's content, in plain words (M3 design note §5.4).

A finding names the field (``path``), a stable ``code`` that clients branch on (never the message),
and a level:

- ``error``: something supplied is malformed (an answer naming an option that does not exist).
- ``incomplete``: something needed for publishing is missing. A draft may still be saved.
- ``warning``: allowed, but worth a look.

Findings are computed from the content each time and never stored.
"""

from dataclasses import dataclass
from enum import StrEnum


class Level(StrEnum):
    ERROR = "error"
    INCOMPLETE = "incomplete"
    WARNING = "warning"


@dataclass(frozen=True, slots=True)
class Finding:
    path: str
    code: str
    level: Level
    message: str


def at_key(path: str, key: str) -> str:
    """The path of a field inside an object: ``answer`` + ``option_id`` -> ``answer.option_id``."""
    return f"{path}.{key}" if path else key


def at_index(path: str, index: int) -> str:
    """The path of an entry in a list: ``options`` + 2 -> ``options[2]``."""
    return f"{path}[{index}]"


class Findings:
    """Collects findings while the content is checked."""

    def __init__(self) -> None:
        self.items: list[Finding] = []

    def error(self, path: str, code: str, message: str) -> None:
        self.items.append(Finding(path, code, Level.ERROR, message))

    def incomplete(self, path: str, code: str, message: str) -> None:
        self.items.append(Finding(path, code, Level.INCOMPLETE, message))

    def warning(self, path: str, code: str, message: str) -> None:
        self.items.append(Finding(path, code, Level.WARNING, message))
