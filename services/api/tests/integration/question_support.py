"""Test helper: a small real catalogue, so a "ready" question can have no findings at all.

A question's labels must be this coaching's own ids, so the spec-v1 fixtures' made-up ids are
swapped for the ones of a catalogue seeded into the coaching under test.
"""

import copy
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from qbank.core.db import Database
from qbank.core.ids import new_id
from qbank.core.tenancy import TenantContext
from qbank.modules.taxonomy.models import Concept, Exam, TaxonomyNode
from tests.unit.test_question_content import FIXTURES


@dataclass(frozen=True)
class Catalogue:
    class_id: UUID
    subject_id: UUID
    chapter_id: UUID
    topic_id: UUID
    concept_id: UUID


def seed_catalogue(owner_db: Database, organization_id: UUID) -> Catalogue:
    """Class 11 > Physics > Kinematics > Motion in a line, and a concept of Physics."""
    ids = {name: new_id() for name in ("class", "subject", "chapter", "topic", "concept")}
    chain = [
        ("class", "CLASS", None, "Class 11"),
        ("subject", "SUBJECT", "class", "Physics"),
        ("chapter", "CHAPTER", "subject", "Kinematics"),
        ("topic", "TOPIC", "chapter", "Motion in a line"),
    ]
    kinds = {"class": "CLASS", "subject": "SUBJECT", "chapter": "CHAPTER", "topic": "TOPIC"}
    with owner_db.transaction(TenantContext(organization_id=organization_id)) as session:
        for name, kind, parent, label in chain:
            session.add(
                TaxonomyNode(
                    id=ids[name],
                    organization_id=organization_id,
                    kind=kind,
                    parent_id=ids[parent] if parent else None,
                    parent_kind=kinds[parent] if parent else None,
                    name=label,
                    name_key=label.lower(),
                )
            )
            session.flush()
        session.add(
            Concept(
                id=ids["concept"],
                organization_id=organization_id,
                subject_id=ids["subject"],
                name="Velocity",
                name_key="velocity",
            )
        )
    return Catalogue(ids["class"], ids["subject"], ids["chapter"], ids["topic"], ids["concept"])


def ready_for(catalogue: Catalogue, kind: str = "SCQ") -> dict[str, Any]:
    """The spec-v1 content-ready fixture of ``kind``, labelled with the catalogue's own ids."""
    content = copy.deepcopy(FIXTURES[kind]["ready"])
    content["metadata"].update(
        {
            "class_id": str(catalogue.class_id),
            "subject_id": str(catalogue.subject_id),
            "chapter_id": str(catalogue.chapter_id),
            "topic_id": str(catalogue.topic_id),
            "primary_concept_id": str(catalogue.concept_id),
        }
    )
    return content


def seed_exam(owner_db: Database, organization_id: UUID, name: str = "JEE Main") -> UUID:
    exam_id = new_id()
    with owner_db.transaction(TenantContext(organization_id=organization_id)) as session:
        session.add(
            Exam(id=exam_id, organization_id=organization_id, name=name, name_key=name.lower())
        )
    return exam_id
