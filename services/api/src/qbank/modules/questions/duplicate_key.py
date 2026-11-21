"""The key two exact duplicates share (D-16, M4 design note §7.4).

Two questions are exact duplicates when they ask the same thing with the same options and answer:
the key is a hash of the format, the stem (with the assertion, reason, statements and columns), the
options and the answer. The worked solution, the video and the labels are not part of it (the same
question with a better solution or another chapter is still the same question). A question under a
passage includes the passage checkpoint it is pinned to: the same child text under another passage
asks about another scenario.

Before hashing, prose is put in one form: Unicode composed, spaces collapsed, letter case folded.
**Equations are compared as written** (only their spacing is collapsed): in LaTeX a changed letter,
case, power or sign is a different question, so ``x^2`` and ``X^2`` are not duplicates. The same
holds for the parts of a paragraph between ``\\(`` and ``\\)``. A picture counts by the stored
picture it shows.

Pure, and never raising. A question with nothing in its stem has no key (two empty drafts are not
duplicates of each other).
"""

import hashlib
import json
import re
import unicodedata
from typing import Any

from qbank.modules.questions.blocks import as_dict, has_content
from qbank.modules.questions.context_checks import passage_pin

_INLINE_EQUATION = re.compile(r"(\\\(.*?\\\))", re.DOTALL)
_MAX_DEPTH = 3
_BLOCK_FIELDS = ("stem", "assertion", "reason")
_ITEM_FIELDS = ("statements", "left", "right", "options")


def _spaces(value: str) -> str:
    return " ".join(unicodedata.normalize("NFC", value).split())


def _prose(value: object) -> str:
    """Prose without case or spacing differences; inline equations inside it as written."""
    if not isinstance(value, str):
        return ""
    parts = _INLINE_EQUATION.split(value)
    return " ".join(
        _spaces(part) if part.startswith("\\(") else _spaces(part).casefold() for part in parts
    ).strip()


def _blocks(value: object, depth: int = 0) -> list[Any]:
    if not isinstance(value, list) or depth > _MAX_DEPTH:
        return []
    out: list[Any] = []
    for block in value:
        obj = as_dict(block)
        if obj is None:
            continue
        kind = obj.get("kind")
        if kind == "paragraph":
            text = _prose(obj.get("text"))
            if text:
                out.append(["p", text])
        elif kind == "equation":
            source = obj.get("source")
            if isinstance(source, str) and source.strip():
                out.append(["e", _spaces(source)])
        elif kind == "image":
            out.append(["i", str(obj.get("asset_id")), _prose(obj.get("caption"))])
        elif kind == "table":
            rows = obj.get("rows")
            out.append(
                [
                    "t",
                    [
                        [_blocks(cell, depth + 1) for cell in row] if isinstance(row, list) else []
                        for row in (rows if isinstance(rows, list) else [])
                    ],
                ]
            )
        elif kind == "list":
            items = obj.get("items")
            out.append(
                [
                    "l",
                    obj.get("ordered") is True,
                    [
                        _blocks(item, depth + 1)
                        for item in (items if isinstance(items, list) else [])
                    ],
                ]
            )
    return out


def _answer(value: object) -> object:
    """The answer with selections that have no order put in one order: ``["C", "A"]`` is the same
    set of correct options as ``["A", "C"]``."""
    obj = as_dict(value)
    if obj is None:
        return value
    ids = obj.get("option_ids")
    if isinstance(ids, list) and all(isinstance(i, str) for i in ids):
        return {**obj, "option_ids": sorted(set(ids))}
    return value


def _mapping(value: object) -> object:
    """A matching option: which right items go with each left item, in one order."""
    obj = as_dict(value)
    if obj is None:
        return value
    return {
        str(left): sorted(set(rights)) if all(isinstance(r, str) for r in rights) else rights
        for left, rights in obj.items()
        if isinstance(rights, list)
    }


def _items(value: object) -> list[Any]:
    out: list[Any] = []
    for item in value if isinstance(value, list) else []:
        obj = as_dict(item)
        if obj is None:
            continue
        entry: list[Any] = [str(obj.get("id")), _blocks(obj.get("content"))]
        if "mapping" in obj:  # a matching option: which left goes with which right
            entry.append(_mapping(obj.get("mapping")))
        out.append(entry)
    return out


def duplicate_key(content: object) -> str | None:
    """The 64-character hex key, or ``None`` when the stem is empty."""
    obj = as_dict(content) or {}
    if not has_content(obj.get("stem")):
        return None
    meaning = {
        "type": obj.get("question_type"),
        **{field: _blocks(obj.get(field)) for field in _BLOCK_FIELDS},
        **{field: _items(obj.get(field)) for field in _ITEM_FIELDS},
        "answer": _answer(obj.get("answer")),
        "passage": str(passage_pin(obj)) if passage_pin(obj) is not None else None,
    }
    try:
        canonical = json.dumps(meaning, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    except TypeError, ValueError, RecursionError:  # not plain data: no key, not an error
        return None
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
