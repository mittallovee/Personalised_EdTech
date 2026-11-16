"""What the bank index keeps of a question's content: the labels, pulled out into plain values.

Pure, and never raising: a content is whatever the author saved, a draft may hold anything, so a
value that is not valid (an id that is not an id, a difficulty of 99) is simply left out of the
index, as ``None``. That the content is right is the validators' job (``metadata.py``); the index
only has to find what is there.
"""

import re
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from qbank.modules.questions.blocks import as_dict, has_content
from qbank.modules.questions.metadata import (
    BLOOM_KEYS,
    DIFFICULTY_MAX,
    DIFFICULTY_MIN,
    EXAM_YEAR_MAX,
    EXAM_YEAR_MIN,
)
from qbank.modules.questions.validate import QUESTION_TYPES

_LANGUAGE = re.compile(r"[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8})*")
_MAX_LANGUAGE = 20


@dataclass(frozen=True, slots=True)
class BankFields:
    question_type: str | None
    language: str | None
    class_id: UUID | None
    subject_id: UUID | None
    chapter_id: UUID | None
    topic_id: UUID | None
    primary_concept_id: UUID | None
    concept_ids: tuple[UUID, ...]
    difficulty: int | None
    bloom_level: str | None
    is_pyq: bool
    exam_id: UUID | None
    exam_year: int | None
    has_solution: bool
    has_video: bool


def _uuid(value: object) -> UUID | None:
    if not isinstance(value, str):
        return None
    try:
        return UUID(value)
    except ValueError:
        return None


def _whole_number(value: object, low: int, high: int) -> int | None:
    # ``bool`` is an ``int`` in Python, and ``true`` is not a difficulty.
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        return None
    return value


def _concepts(primary: UUID | None, others: object) -> tuple[UUID, ...]:
    """The main concept first, then the others, each once."""
    found: list[UUID] = [primary] if primary is not None else []
    for item in others if isinstance(others, list) else []:
        concept = _uuid(item)
        if concept is not None and concept not in found:
            found.append(concept)
    return tuple(found)


def _language(value: object) -> str | None:
    if (
        isinstance(value, str)
        and len(value) <= _MAX_LANGUAGE
        and _LANGUAGE.fullmatch(value) is not None
    ):
        return value.lower()
    return None


def _one_of(value: object, allowed: tuple[str, ...]) -> str | None:
    return value if isinstance(value, str) and value in allowed else None


def bank_fields(content: Any) -> BankFields:
    """The index fields of a question's content."""
    obj = as_dict(content) or {}
    meta = as_dict(obj.get("metadata")) or {}
    video = obj.get("video_solution_url")
    primary = _uuid(meta.get("primary_concept_id"))
    return BankFields(
        question_type=_one_of(obj.get("question_type"), QUESTION_TYPES),
        language=_language(obj.get("language")),
        class_id=_uuid(meta.get("class_id")),
        subject_id=_uuid(meta.get("subject_id")),
        chapter_id=_uuid(meta.get("chapter_id")),
        topic_id=_uuid(meta.get("topic_id")),
        primary_concept_id=primary,
        concept_ids=_concepts(primary, meta.get("secondary_concept_ids")),
        difficulty=_whole_number(meta.get("difficulty"), DIFFICULTY_MIN, DIFFICULTY_MAX),
        bloom_level=_one_of(meta.get("bloom_level"), BLOOM_KEYS),
        is_pyq=meta.get("is_pyq") is True,
        exam_id=_uuid(meta.get("exam_id")),
        exam_year=_whole_number(meta.get("exam_year"), EXAM_YEAR_MIN, EXAM_YEAR_MAX),
        has_solution=has_content(obj.get("solution")),
        has_video=isinstance(video, str) and bool(video.strip()),
    )
