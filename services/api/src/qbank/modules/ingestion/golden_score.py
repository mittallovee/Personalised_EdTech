"""Scoring what a model read from a page against what a person finished (M6 6j, G-11, K-14).

Pure functions: no database, no provider. A *case* is the content a person accepted for one question
on a page (the key). A model is asked to read the same page again; each key question is matched to
the closest question it read (by its text), and the pair is compared field by field:

- ``kind``: the question type;
- ``text``: the question text (stem, and assertion, reason, statements, lists where there are any);
- ``options``: the options, in order (for matching, which items each option pairs);
- ``answer``: the printed answer.

Words are compared after folding case and spaces, so a different line break is not an error. Nothing
is rounded or "close enough": a changed digit is a different answer. Questions the model read that
match no key question are counted as ``extra`` (they may be a missed key, or a mistake).
"""

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any

FIELDS = ("kind", "text", "options", "answer")
MATCH_AT_LEAST = 0.6  # how alike two question texts must be to count as the same question


def _plain(blocks: Any) -> str:
    """The words of a list of content blocks, folded for comparison (formulas as written)."""
    if not isinstance(blocks, list):
        return ""
    words = " ".join(
        str(b.get("text") or b.get("latex") or "") for b in blocks if isinstance(b, dict)
    )
    return re.sub(r"\s+", " ", words).strip().casefold()


def _items(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [f"{i.get('id')}:{_plain(i.get('content'))}" for i in value if isinstance(i, dict)]


def _text_of(content: dict[str, Any]) -> str:
    parts = [
        _plain(content.get("stem")),
        _plain(content.get("assertion")),
        _plain(content.get("reason")),
    ]
    for key in ("statements", "left", "right"):
        parts.extend(_items(content.get(key)))
    return " | ".join(p for p in parts if p)


def _options_of(content: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for option in content.get("options") or []:
        if not isinstance(option, dict):
            continue
        if "mapping" in option:
            mapping = option["mapping"]
            pairs = ",".join(f"{k}>{'+'.join(sorted(v))}" for k, v in sorted(mapping.items()))
            out.append(f"{option.get('id')}:{pairs}")
        else:
            out.append(f"{option.get('id')}:{_plain(option.get('content'))}")
    return out


@dataclass(frozen=True, slots=True)
class CaseResult:
    """How one key question fared. ``found`` is false when nothing like it was read."""

    found: bool
    right: dict[str, bool] = field(default_factory=dict)

    @property
    def perfect(self) -> bool:
        return self.found and all(self.right.values())


def compare(key: dict[str, Any], read: dict[str, Any]) -> CaseResult:
    return CaseResult(
        True,
        {
            "kind": key.get("question_type") == read.get("question_type"),
            "text": _text_of(key) == _text_of(read),
            "options": _options_of(key) == _options_of(read),
            "answer": key.get("answer") == read.get("answer"),
        },
    )


def _alike(key: dict[str, Any], read: dict[str, Any]) -> float:
    a, b = _text_of(key), _text_of(read)
    if not a or not b:
        return 0.0  # two blank texts are not "the same question"
    return SequenceMatcher(None, a, b).ratio()


def score_page(
    keys: list[dict[str, Any]], read: list[dict[str, Any]]
) -> tuple[list[CaseResult], int]:
    """Match each key to its closest unused read question; returns one result per key, in order,
    and how many read questions matched no key."""
    free = list(range(len(read)))
    results: list[CaseResult] = []
    for key in keys:
        best = max(free, key=lambda i: _alike(key, read[i]), default=None)
        if best is None or _alike(key, read[best]) < MATCH_AT_LEAST:
            results.append(CaseResult(False))
            continue
        free.remove(best)
        results.append(compare(key, read[best]))
    return results, len(free)


@dataclass(frozen=True, slots=True)
class Report:
    cases: int
    found: int
    perfect: int
    right: dict[str, int]  # per field: how many of the found questions got it right
    extra: int
    pages_failed: int
    tokens_in: int
    tokens_out: int

    def lines(self) -> list[str]:
        def pct(n: int, of: int) -> str:
            return f"{n}/{of} ({100 * n // of}%)" if of else "none to score"

        out = [
            f"Questions in the key: {self.cases}",
            f"Found by the model: {pct(self.found, self.cases)}",
            f"Entirely right (type, text, options, answer): {pct(self.perfect, self.cases)}",
        ]
        out += [f"  {name}: {pct(self.right[name], self.found)}" for name in FIELDS]
        out.append(f"Questions read that are not in the key: {self.extra}")
        if self.pages_failed:
            out.append(f"Pages the model could not read: {self.pages_failed}")
        out.append(f"Tokens used: {self.tokens_in} in, {self.tokens_out} out")
        return out


def summarise(
    results: list[CaseResult], *, extra: int, pages_failed: int, tokens_in: int, tokens_out: int
) -> Report:
    found = [r for r in results if r.found]
    return Report(
        cases=len(results),
        found=len(found),
        perfect=sum(1 for r in results if r.perfect),
        right={name: sum(1 for r in found if r.right[name]) for name in FIELDS},
        extra=extra,
        pages_failed=pages_failed,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
    )
