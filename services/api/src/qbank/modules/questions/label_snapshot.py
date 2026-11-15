"""The names of a question's labels as they were on the day it was published (M4 design note §4.5).

A published question must read the same in history even after a syllabus item is renamed, so the
publication keeps the English name of every label next to its id. Pure functions of the content
and the names found: the service does the database reading.
"""

from collections.abc import Mapping
from typing import Any
from uuid import UUID

from qbank.modules.questions.blocks import as_dict

_SINGLE = (
    "class_id",
    "subject_id",
    "chapter_id",
    "topic_id",
    "subtopic_id",
    "primary_concept_id",
    "exam_id",
    "source_id",
)
_LIST = "secondary_concept_ids"


def _uuid(value: object) -> UUID | None:
    if not isinstance(value, str):
        return None
    try:
        return UUID(value)
    except ValueError:
        return None


def _metadata(content: object) -> dict[str, object]:
    obj = as_dict(content)
    meta = as_dict(obj.get("metadata")) if obj is not None else None
    return meta if meta is not None else {}


def label_ids(content: object) -> set[UUID]:
    """Every label id in the metadata: what to ask for the names of."""
    meta = _metadata(content)
    found = {_uuid(meta.get(field)) for field in _SINGLE}
    secondary = meta.get(_LIST)
    if isinstance(secondary, list):
        found |= {_uuid(value) for value in secondary}
    return {i for i in found if i is not None}


def snapshot_labels(content: object, names: Mapping[UUID, str]) -> dict[str, Any]:
    """``{"chapter_id": {"id": ..., "name": ...}, ..., "secondary_concept_ids": [...]}`` for each
    label the content has and ``names`` knows. An id with no name is left out, never invented."""
    meta = _metadata(content)
    out: dict[str, Any] = {}
    for field in _SINGLE:
        label = _uuid(meta.get(field))
        if label is not None and label in names:
            out[field] = {"id": str(label), "name": names[label]}
    secondary = meta.get(_LIST)
    if isinstance(secondary, list):
        listed = [_uuid(value) for value in secondary]
        out[_LIST] = [
            {"id": str(i), "name": names[i]} for i in listed if i is not None and i in names
        ]
    return out
