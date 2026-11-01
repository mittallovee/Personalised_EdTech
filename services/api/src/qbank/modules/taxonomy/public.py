"""Public interface of the taxonomy module: what other modules may ask about the lists.

A question's metadata points at syllabus items, concepts, exams and sources. The questions module
asks here what each id is, and never reads these tables itself.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

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
