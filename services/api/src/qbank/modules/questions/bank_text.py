"""The plain text of a question that the bank's free-text search reads (F-03, design note §7.3).

Pure, and never raising: a content is whatever the author saved, so anything that is not text is
left out. The text is the stem, then the assertion, reason, statements and the left and right
columns, then each option, then the solution. Equations are kept as the LaTeX the author wrote,
because a search for ``\\frac`` or ``v^2`` should find them. Pictures add their caption and
description. The text is capped and the work is bounded, so one huge or hostile draft cannot make a
huge index row or take long to read.
"""

import unicodedata
from dataclasses import dataclass, field
from typing import Any

from qbank.modules.questions.blocks import as_dict

MAX_TEXT = 20_000  # characters kept per question; the rest is not searched
PREVIEW_LENGTH = 200
_MAX_DEPTH = 3  # blocks inside a table cell or a list item; deeper junk is ignored
_MAX_VISITS = 5_000  # blocks looked at per question, empty or not

# Fields holding a list of blocks, in the order they are read after the stem.
_BLOCK_FIELDS = ("assertion", "reason")
# Fields holding a list of ``{"id", "content": blocks}``.
_ITEM_FIELDS = ("statements", "left", "right", "options")


@dataclass(frozen=True, slots=True)
class BankText:
    stem_text: str  # everything searchable, one line
    preview: str  # the beginning of the stem, for the list


@dataclass(slots=True)
class _Reader:
    """Collects text until the cap or the work budget is reached."""

    parts: list[str] = field(default_factory=list)
    size: int = 0
    visits: int = 0

    @property
    def done(self) -> bool:
        return self.size >= MAX_TEXT or self.visits >= _MAX_VISITS

    def tick(self) -> bool:
        """Count one more look at something; true once the budget is spent."""
        self.visits += 1
        return self.done

    def add(self, value: object) -> None:
        if isinstance(value, str) and value:
            self.parts.append(value)
            self.size += len(value)

    def blocks(self, value: object, depth: int = 0) -> None:
        if not isinstance(value, list) or depth > _MAX_DEPTH:
            return
        for block in value:
            if self.tick():
                return
            obj = as_dict(block)
            if obj is None:
                continue
            kind = obj.get("kind")
            if kind == "paragraph":
                self.add(obj.get("text"))
            elif kind == "equation":
                self.add(obj.get("source"))
            elif kind == "image":
                self.add(obj.get("caption"))
                self.add(obj.get("alt_text"))
            elif kind == "table":
                for row in _list(obj.get("rows")):
                    for cell in _list(row):
                        self.blocks(cell, depth + 1)
                        if self.tick():
                            return
            elif kind == "list":
                for item in _list(obj.get("items")):
                    self.blocks(item, depth + 1)
                    if self.tick():
                        return


def _list(value: object) -> list[Any]:
    return value if isinstance(value, list) else []


def _clean(value: str) -> str:
    """One line, in Unicode's composed form (so a typed and a pasted Hindi word are the same)."""
    return " ".join(unicodedata.normalize("NFC", value).replace("\x00", " ").split())


def bank_text(content: object) -> BankText:
    """The searchable text of a question's content, and the beginning of its stem."""
    obj = as_dict(content) or {}
    stem = _Reader()
    stem.blocks(obj.get("stem"))
    rest = _Reader(parts=list(stem.parts), size=stem.size, visits=stem.visits)
    for name in _BLOCK_FIELDS:
        rest.blocks(obj.get(name))
    for name in _ITEM_FIELDS:
        for item in _list(obj.get(name)):
            if rest.tick():
                break
            item_obj = as_dict(item)
            if item_obj is not None:
                rest.blocks(item_obj.get("content"))
    rest.blocks(obj.get("solution"))
    return BankText(
        stem_text=_clean(" ".join(rest.parts))[:MAX_TEXT],
        preview=_clean(" ".join(stem.parts))[:PREVIEW_LENGTH],
    )
