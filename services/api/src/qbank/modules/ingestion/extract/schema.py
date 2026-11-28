"""What the model must answer with for one page, and how it becomes question content (G-04).

The schema is locked in code (an edit to the prompt can never loosen it). Everything the model says
is untrusted: it is checked here for shape and size, converted into the same content the question
editor writes, and then checked by the same validators as a person's save. A printed answer that is
written with more precision than the answer rules allow is **flagged, never rounded**.
"""

import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any

from qbank.modules.questions.public import QUESTION_TYPES, Finding, Level, validate_content

MOST_QUESTIONS_PER_PAGE = 40
MOST_TEXT = 6000
OPTION_IDS = ("A", "B", "C", "D")
TYPES = (
    "SCQ",
    "MULTI_CORRECT",
    "INTEGER",
    "SINGLE_DIGIT",
    "NUMERICAL",
    "MATCHING",
    "ASSERTION_REASON",
    "MULTIPLE_STATEMENT",
)
_BOX = {
    "type": ["object", "null"],
    "additionalProperties": False,
    "required": ["x", "y", "w", "h"],
    "properties": {k: {"type": "number", "minimum": 0, "maximum": 1} for k in "xywh"},
}
_TEXT = {"type": "string", "maxLength": MOST_TEXT}
_OPT_TEXT = {"type": ["string", "null"], "maxLength": MOST_TEXT}
_LIST = {"type": "array", "maxItems": 12, "items": _TEXT}


def schema() -> dict[str, Any]:
    question = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "question_type",
            "language",
            "stem",
            "options",
            "statements",
            "assertion",
            "reason",
            "left",
            "right",
            "matching_options",
            "answer_text",
            "solution",
            "region",
            "confidence",
            "handwritten",
            "notes",
        ],
        "properties": {
            "question_type": {"type": "string", "enum": list(TYPES)},
            "language": {"type": "string", "pattern": "^[a-z]{2,3}$"},
            "stem": _TEXT,
            "options": _LIST,
            "statements": _LIST,
            "assertion": _OPT_TEXT,
            "reason": _OPT_TEXT,
            "left": _LIST,
            "right": _LIST,
            "matching_options": {
                "type": "array",
                "maxItems": 4,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["id", "pairs"],
                    "properties": {
                        "id": {"type": "string", "enum": list(OPTION_IDS)},
                        "pairs": {
                            "type": "array",
                            "maxItems": 12,
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "required": ["left", "right"],
                                "properties": {
                                    "left": {"type": "integer", "minimum": 1, "maximum": 12},
                                    "right": {
                                        "type": "array",
                                        "maxItems": 12,
                                        "items": {"type": "integer", "minimum": 1, "maximum": 12},
                                    },
                                },
                            },
                        },
                    },
                },
            },
            "answer_text": {"type": ["string", "null"], "maxLength": 200},
            "solution": _OPT_TEXT,
            "region": _BOX,
            "confidence": {"type": "string", "enum": ["HIGH", "MEDIUM", "LOW"]},
            "handwritten": {"type": "boolean"},
            "notes": {"type": ["string", "null"], "maxLength": 500},
        },
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["questions", "unreadable", "no_questions"],
        "properties": {
            "questions": {"type": "array", "maxItems": MOST_QUESTIONS_PER_PAGE, "items": question},
            "unreadable": {
                "type": "array",
                "maxItems": 20,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["reason", "region"],
                    "properties": {"reason": {"type": "string", "maxLength": 300}, "region": _BOX},
                },
            },
            "no_questions": {"type": "boolean"},
        },
    }


class BadPage(Exception):
    """The model's answer for a page is not usable at all (not the shape asked for)."""


@dataclass(frozen=True, slots=True)
class Candidate:
    ordinal: int
    region: dict[str, float] | None
    raw: dict[str, Any]
    content: dict[str, Any]
    findings: list[dict[str, str]]
    confidence: str
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class PageReading:
    candidates: list[Candidate]
    unreadable: list[dict[str, Any]]
    no_questions: bool


def _blocks(text: str | None) -> list[dict[str, str]]:
    """Paragraphs of plain text: a blank line starts a new one. Maths stays as the model wrote it
    between ``\\(`` and ``\\)``; a mistake in it is a finding, not something guessed at here."""
    parts = [part.strip() for part in re.split(r"\n\s*\n", text or "") if part.strip()]
    return [{"kind": "paragraph", "text": part} for part in parts] or [
        {"kind": "paragraph", "text": ""}
    ]


def _letters(text: str) -> list[str]:
    found = re.findall(r"\b([A-D])\b", text.upper())
    return list(dict.fromkeys(found))


def _two_places(raw: str) -> str | None:
    """A decimal exactly as printed with two places, or None if it needs more (never rounded)."""
    try:
        value = Decimal(raw.strip().replace(",", "."))
    except InvalidOperation:
        return None
    if value.as_tuple().exponent < -2:  # type: ignore[operator]
        return None
    return format(value.quantize(Decimal("0.01")), "f")


def _answer(kind: str, text: str | None, warnings: list[str]) -> dict[str, Any] | None:
    if text is None or not text.strip():
        return None
    printed = text.strip()
    if kind in ("SCQ", "MATCHING", "ASSERTION_REASON", "MULTIPLE_STATEMENT"):
        letters = _letters(printed)
        if len(letters) == 1:
            return {"option_id": letters[0]}
    elif kind == "MULTI_CORRECT":
        letters = _letters(printed)
        if letters:
            return {"option_ids": letters}
    elif kind in ("INTEGER", "SINGLE_DIGIT"):
        if re.fullmatch(r"-?\d{1,6}", printed):
            return {"value": int(printed)}
    elif kind == "NUMERICAL":
        pieces = re.split(r"\s*(?:to|\u2013|\u2014|-(?=\s))\s*", printed)
        if len(pieces) == 2:
            lower, upper = _two_places(pieces[0]), _two_places(pieces[1])
            if lower is not None and upper is not None:
                return {"mode": "range", "lower": lower, "upper": upper}
        elif len(pieces) == 1:
            exact = _two_places(printed)
            if exact is not None:
                return {"mode": "exact", "value": exact}
        if re.search(r"\d\.\d{3,}", printed):
            warnings.append("OVERPRECISE_ANSWER")  # more places than allowed: shown, never rounded
            return None
    warnings.append("ANSWER_NOT_READ")
    return None


def _items(texts: list[str], prefix: str) -> list[dict[str, Any]]:
    return [{"id": f"{prefix}{n}", "content": _blocks(t)} for n, t in enumerate(texts, start=1)]


def to_content(item: dict[str, Any], warnings: list[str]) -> dict[str, Any]:
    """One model-read question as the content the editor stores (labels are left for tagging)."""
    kind = item["question_type"]
    content: dict[str, Any] = {
        "schema_version": 1,
        "question_type": kind,
        "language": item["language"],
        "stem": _blocks(item["stem"]),
    }
    if kind in ("SCQ", "MULTI_CORRECT", "ASSERTION_REASON", "MULTIPLE_STATEMENT"):
        content["options"] = [
            {"id": OPTION_IDS[n], "content": _blocks(t)}
            for n, t in enumerate(item["options"][: len(OPTION_IDS)])
        ]
    if kind == "ASSERTION_REASON":
        content["assertion"] = _blocks(item["assertion"])
        content["reason"] = _blocks(item["reason"])
    if kind == "MULTIPLE_STATEMENT":
        content["statements"] = _items(item["statements"], "S")
    if kind == "MATCHING":
        content["left"] = _items(item["left"], "L")
        content["right"] = _items(item["right"], "R")
        content["options"] = [
            {
                "id": option["id"],
                "mapping": {
                    f"L{p['left']}": [f"R{r}" for r in p["right"]] for p in option["pairs"]
                },
            }
            for option in item["matching_options"]
        ]
    answer = _answer(kind, item["answer_text"], warnings)
    if answer is not None:
        content["answer"] = answer
    if item["solution"]:
        content["solution"] = _blocks(item["solution"])
    return content


def read_page(data: dict[str, Any]) -> PageReading:
    """The model's answer for one page as candidates. Raises ``BadPage`` for an answer that is not
    the shape asked for at all (the schema makes that rare); a single odd question is kept with its
    findings rather than dropped, so a person decides."""
    questions = data.get("questions")
    if not isinstance(questions, list) or len(questions) > MOST_QUESTIONS_PER_PAGE:
        raise BadPage("questions")
    out: list[Candidate] = []
    for ordinal, item in enumerate(questions, start=1):
        if not isinstance(item, dict) or item.get("question_type") not in QUESTION_TYPES:
            raise BadPage("question")
        warnings: list[str] = []
        if item.get("handwritten") is True:
            warnings.append("HANDWRITTEN")
        if item.get("confidence") == "LOW":
            warnings.append("LOW_CONFIDENCE")
        content = to_content(item, warnings)
        findings = [
            {"path": f.path, "code": f.code, "level": f.level.value, "message": f.message}
            for f in validate_content(content)
            if f.level in (Level.ERROR, Level.INCOMPLETE, Level.WARNING)
        ]
        region = item.get("region")
        out.append(
            Candidate(
                ordinal=ordinal,
                region=region if isinstance(region, dict) else None,
                raw=item,
                content=content,
                findings=findings,
                confidence=str(item.get("confidence", "LOW")),
                warnings=warnings,
            )
        )
    unreadable = [u for u in data.get("unreadable") or [] if isinstance(u, dict)]
    return PageReading(out, unreadable, bool(data.get("no_questions")))


__all__ = [
    "BadPage",
    "Candidate",
    "Finding",
    "PageReading",
    "read_page",
    "schema",
    "to_content",
]
