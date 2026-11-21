"""Public interface of the taxonomy module: what other modules may ask about the lists.

A question's metadata points at syllabus items, concepts, exams and sources. The questions module
asks here what each id is, and never reads these tables itself.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from qbank.modules.taxonomy.catalogues import BLOOM_LEVELS, LANGUAGES
from qbank.modules.taxonomy.models import Concept, Exam, Source, TaxonomyNode


@dataclass(frozen=True, slots=True)
class CatalogueRef:
    """What an id stands for in this coaching.

    ``kind`` is the syllabus kind (CLASS, SUBJECT, CHAPTER, TOPIC, SUBTOPIC) or CONCEPT, EXAM or
    SOURCE. ``parent_id`` is the syllabus parent; ``subject_id`` is a concept's subject.
    ``state`` is ACTIVE or DEPRECATED (retired).
    """

    kind: str
    parent_id: UUID | None
    subject_id: UUID | None
    state: str


def look_up(session: Session, ids: Iterable[UUID]) -> dict[UUID, CatalogueRef]:
    """What each of ``ids`` is. Ids that are not in the caller's coaching are left out (row-level
    security hides other coachings' rows), so "missing" covers both "no such id" and "not yours"."""
    wanted = set(ids)
    found: dict[UUID, CatalogueRef] = {}
    if not wanted:
        return found
    for node in session.scalars(select(TaxonomyNode).where(TaxonomyNode.id.in_(wanted))):
        found[node.id] = CatalogueRef(node.kind, node.parent_id, None, node.state)
    for concept in session.scalars(select(Concept).where(Concept.id.in_(wanted))):
        found[concept.id] = CatalogueRef("CONCEPT", None, concept.subject_id, concept.state)
    for exam in session.scalars(select(Exam).where(Exam.id.in_(wanted))):
        found[exam.id] = CatalogueRef("EXAM", None, None, exam.state)
    for source in session.scalars(select(Source).where(Source.id.in_(wanted))):
        found[source.id] = CatalogueRef("SOURCE", None, None, source.state)
    return found


def names_of(session: Session, ids: Iterable[UUID]) -> dict[UUID, str]:
    """The English name of each of ``ids`` that is in the caller's coaching (others are left out),
    for a record that must keep how an item was called on a given day."""
    wanted = set(ids)
    names: dict[UUID, str] = {}
    if not wanted:
        return names
    for node in session.scalars(select(TaxonomyNode).where(TaxonomyNode.id.in_(wanted))):
        names[node.id] = node.name
    for concept in session.scalars(select(Concept).where(Concept.id.in_(wanted))):
        names[concept.id] = concept.name
    for exam in session.scalars(select(Exam).where(Exam.id.in_(wanted))):
        names[exam.id] = exam.name
    for source in session.scalars(select(Source).where(Source.id.in_(wanted))):
        names[source.id] = source.name
    return names


def language_names() -> dict[str, str]:
    """The question languages (tag to English name), the same for every coaching."""
    return {language.tag: language.english_name for language in LANGUAGES}


@dataclass(frozen=True, slots=True)
class SyllabusItem:
    id: UUID
    name: str
    parent_id: UUID | None = None  # a topic's chapter; None for a chapter or a concept


@dataclass(frozen=True, slots=True)
class SubjectSyllabus:
    """The active chapters, topics and concepts under one subject, for the AI to choose from."""

    chapters: list[SyllabusItem]
    topics: list[SyllabusItem]
    concepts: list[SyllabusItem]


def syllabus_of(session: Session, subject_id: UUID) -> SubjectSyllabus | None:
    """The choices under ``subject_id``, or ``None`` when it is not an active subject of the
    caller's coaching. Retired items are left out. Ordered as the syllabus screens order them."""
    subject = session.get(TaxonomyNode, subject_id)
    if subject is None or subject.kind != "SUBJECT" or subject.state != "ACTIVE":
        return None
    nodes = list(
        session.scalars(
            select(TaxonomyNode)
            .where(TaxonomyNode.parent_id == subject_id, TaxonomyNode.state == "ACTIVE")
            .order_by(TaxonomyNode.sort_order, TaxonomyNode.name)
        )
    )
    chapters = [SyllabusItem(node.id, node.name) for node in nodes if node.kind == "CHAPTER"]
    chapter_ids = {item.id for item in chapters}
    topics = [
        SyllabusItem(node.id, node.name, node.parent_id)
        for node in session.scalars(
            select(TaxonomyNode)
            .where(
                TaxonomyNode.parent_id.in_(chapter_ids),
                TaxonomyNode.kind == "TOPIC",
                TaxonomyNode.state == "ACTIVE",
            )
            .order_by(TaxonomyNode.sort_order, TaxonomyNode.name)
        )
    ]
    concepts = [
        SyllabusItem(concept.id, concept.name)
        for concept in session.scalars(
            select(Concept)
            .where(Concept.subject_id == subject_id, Concept.state == "ACTIVE")
            .order_by(Concept.name)
        )
    ]
    return SubjectSyllabus(chapters, topics, concepts)


def bloom_keys() -> tuple[str, ...]:
    """The Bloom levels a question may carry, from lowest to highest."""
    return tuple(level.key for level in BLOOM_LEVELS)
