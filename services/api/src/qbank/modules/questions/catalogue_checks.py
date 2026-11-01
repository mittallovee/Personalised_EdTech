"""The metadata checks that need this coaching's lists (M3 design note section 5.5, C-04).

``metadata.py`` checks the shape of the labels. Here each id is checked against what the lookup
found for it: it is this coaching's, it is the right kind of item, the syllabus levels form one
branch (the subject is under the class, the chapter under the subject...), and every concept
belongs to the chosen subject. A retired item is only a warning, so an old draft keeps working.
Choosing a retired item for the first time is stopped by the pickers, which list active items only.

A pure function of the content and the lookup: the service does the database reading. Ids that are
not ids, and everything else that is not metadata, are left to the shape checks.
"""

from collections.abc import Mapping
from uuid import UUID

from qbank.modules.questions.blocks import as_dict
from qbank.modules.questions.findings import Finding, Findings, at_index, at_key
from qbank.modules.questions.metadata import MAX_SECONDARY_CONCEPTS
from qbank.modules.taxonomy.public import CatalogueRef

_PATH = "metadata"
# field -> (kind it must be, what to call it in a message)
_SINGLE = {
    "class_id": ("CLASS", "class"),
    "subject_id": ("SUBJECT", "subject"),
    "chapter_id": ("CHAPTER", "chapter"),
    "topic_id": ("TOPIC", "topic"),
    "subtopic_id": ("SUBTOPIC", "subtopic"),
    "primary_concept_id": ("CONCEPT", "concept"),
    "exam_id": ("EXAM", "exam"),
    "source_id": ("SOURCE", "source"),
}
# child field -> the field of the level above it
_PARENT = {
    "subject_id": "class_id",
    "chapter_id": "subject_id",
    "topic_id": "chapter_id",
    "subtopic_id": "topic_id",
}


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


def _secondary(meta: dict[str, object]) -> list[object]:
    """The other concepts, only as many as the shape check looks at: a draft with thousands of
    them is saved with a count finding, and must not make the lookup (or a list page) huge."""
    value = meta.get("secondary_concept_ids")
    return value[: MAX_SECONDARY_CONCEPTS + 1] if isinstance(value, list) else []


def catalogue_ids(content: object) -> set[UUID]:
    """Every id in the metadata that looks like an id: what to ask the lookup about."""
    meta = _metadata(content)
    ids = {_uuid(meta.get(field)) for field in _SINGLE}
    ids |= {_uuid(value) for value in _secondary(meta)}
    return {i for i in ids if i is not None}


def check_catalogue(content: object, refs: Mapping[UUID, CatalogueRef]) -> list[Finding]:
    meta = _metadata(content)
    out = Findings()
    good: dict[str, UUID] = {}  # fields whose id is this coaching's and the right kind
    for field, (kind, noun) in _SINGLE.items():
        wanted = _uuid(meta.get(field))
        if wanted is not None and _known(wanted, kind, noun, at_key(_PATH, field), refs, out):
            good[field] = wanted
    secondary: list[tuple[int, UUID]] = []
    for index, value in enumerate(_secondary(meta)):
        wanted = _uuid(value)
        where = at_index(at_key(_PATH, "secondary_concept_ids"), index)
        if wanted is not None and _known(wanted, "CONCEPT", "concept", where, refs, out):
            secondary.append((index, wanted))

    for child, parent in _PARENT.items():
        if child in good and parent in good and refs[good[child]].parent_id != good[parent]:
            noun, above = _SINGLE[child][1], _SINGLE[parent][1]
            out.error(
                at_key(_PATH, child),
                "HIERARCHY_MISMATCH",
                f"This {noun} is not under the chosen {above}.",
            )
    if "subject_id" in good:  # every concept of a question is one of its subject (C-02)
        subject = good["subject_id"]
        concepts = [(at_key(_PATH, "primary_concept_id"), good.get("primary_concept_id"))]
        concepts += [
            (at_index(at_key(_PATH, "secondary_concept_ids"), index), concept)
            for index, concept in secondary
        ]
        for where, concept in concepts:
            if concept is not None and refs[concept].subject_id != subject:
                out.error(
                    where,
                    "CONCEPT_SUBJECT_MISMATCH",
                    "This concept belongs to another subject than the one chosen.",
                )
    return out.items


def _known(
    wanted: UUID,
    kind: str,
    noun: str,
    where: str,
    refs: Mapping[UUID, CatalogueRef],
    out: Findings,
) -> bool:
    """Whether ``wanted`` is this coaching's and the right kind (saying what is wrong if not)."""
    ref = refs.get(wanted)
    if ref is None:
        out.error(where, "CATALOGUE_ID_UNKNOWN", f"This {noun} is not in your coaching's lists.")
        return False
    if ref.kind != kind:
        out.error(where, "CATALOGUE_KIND_WRONG", f"This id is not a {noun}.")
        return False
    if ref.state == "DEPRECATED":
        out.warning(
            where,
            "DEPRECATED_REFERENCE",
            f"This {noun} has been retired; consider choosing another.",
        )
    return True
