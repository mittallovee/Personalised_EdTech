"""T23 (catalogue): the metadata checks that need to know the coaching's lists (D-15, C-04).

The checks are a pure function of the metadata and of what a lookup found for each id, so they are
tested here with made-up lookups. The integration test uses the real tables.
"""

import copy
from collections.abc import Mapping
from typing import Any
from uuid import UUID

from qbank.modules.questions.catalogue_checks import catalogue_ids, check_catalogue
from qbank.modules.questions.findings import Level
from qbank.modules.taxonomy.public import CatalogueRef
from tests.unit.test_question_content import FIXTURES


def uid(n: int) -> str:
    return f"00000000-0000-4000-8000-{n:012d}"


CLASS, SUBJECT, CHAPTER, TOPIC, SUBTOPIC = (uid(n) for n in (1, 2, 3, 4, 10))
CONCEPT, OTHER_CONCEPT, EXAM, SOURCE = (uid(n) for n in (5, 6, 20, 30))


def good_refs() -> dict[UUID, CatalogueRef]:
    def ref(
        kind: str, parent: str | None = None, subject: str | None = None, state: str = "ACTIVE"
    ) -> CatalogueRef:
        return CatalogueRef(
            kind=kind,
            parent_id=UUID(parent) if parent else None,
            subject_id=UUID(subject) if subject else None,
            state=state,
        )

    return {
        UUID(CLASS): ref("CLASS"),
        UUID(SUBJECT): ref("SUBJECT", CLASS),
        UUID(CHAPTER): ref("CHAPTER", SUBJECT),
        UUID(TOPIC): ref("TOPIC", CHAPTER),
        UUID(SUBTOPIC): ref("SUBTOPIC", TOPIC),
        UUID(CONCEPT): ref("CONCEPT", subject=SUBJECT),
        UUID(OTHER_CONCEPT): ref("CONCEPT", subject=uid(99)),  # another subject's concept
        UUID(EXAM): ref("EXAM"),
        UUID(SOURCE): ref("SOURCE"),
    }


def content(**changes: object) -> dict[str, Any]:
    result = copy.deepcopy(FIXTURES["SCQ"]["ready"])
    result["metadata"].update(
        {
            "class_id": CLASS,
            "subject_id": SUBJECT,
            "chapter_id": CHAPTER,
            "topic_id": TOPIC,
            "primary_concept_id": CONCEPT,
        }
    )
    result["metadata"].update(changes)
    return result


def found(
    changes: Mapping[str, object], refs: dict[UUID, CatalogueRef] | None = None
) -> list[tuple[str, str, Level]]:
    findings = check_catalogue(content(**changes), refs if refs is not None else good_refs())
    return [(f.path, f.code, f.level) for f in findings]


def test_a_correct_branch_has_no_findings() -> None:
    full = {
        "subtopic_id": SUBTOPIC,
        "secondary_concept_ids": [OTHER_CONCEPT],
        "is_pyq": True,
        "exam_id": EXAM,
        "exam_year": 2024,
        "source_id": SOURCE,
    }
    assert found(full) == []
    assert found({}) == []


def test_an_id_the_coaching_does_not_have_is_an_error() -> None:
    refs = good_refs()
    del refs[UUID(TOPIC)]
    assert found({}, refs) == [("metadata.topic_id", "CATALOGUE_ID_UNKNOWN", Level.ERROR)]
    assert found({"exam_id": uid(77), "is_pyq": True, "exam_year": 2024}) == [
        ("metadata.exam_id", "CATALOGUE_ID_UNKNOWN", Level.ERROR)
    ]
    assert found({"secondary_concept_ids": [uid(78)]}) == [
        ("metadata.secondary_concept_ids[0]", "CATALOGUE_ID_UNKNOWN", Level.ERROR)
    ]


def test_an_id_of_the_wrong_kind_is_an_error() -> None:
    assert found({"class_id": SUBJECT}) == [
        ("metadata.class_id", "CATALOGUE_KIND_WRONG", Level.ERROR)
    ]
    assert found({"primary_concept_id": CHAPTER}) == [
        ("metadata.primary_concept_id", "CATALOGUE_KIND_WRONG", Level.ERROR)
    ]
    assert found({"source_id": EXAM}) == [
        ("metadata.source_id", "CATALOGUE_KIND_WRONG", Level.ERROR)
    ]


def test_each_level_must_sit_under_the_one_above() -> None:
    refs = good_refs()
    refs[UUID(CHAPTER)] = CatalogueRef("CHAPTER", UUID(uid(88)), None, "ACTIVE")  # other subject
    assert found({}, refs) == [("metadata.chapter_id", "HIERARCHY_MISMATCH", Level.ERROR)]
    refs = good_refs()
    refs[UUID(SUBTOPIC)] = CatalogueRef("SUBTOPIC", UUID(uid(89)), None, "ACTIVE")
    assert found({"subtopic_id": SUBTOPIC}, refs) == [
        ("metadata.subtopic_id", "HIERARCHY_MISMATCH", Level.ERROR)
    ]


def test_a_missing_parent_is_not_reported_twice() -> None:
    refs = good_refs()
    del refs[UUID(SUBJECT)]
    assert found({}, refs) == [("metadata.subject_id", "CATALOGUE_ID_UNKNOWN", Level.ERROR)]


def test_the_main_concept_belongs_to_the_chosen_subject_but_others_may_not() -> None:
    assert found({"primary_concept_id": OTHER_CONCEPT}) == [
        ("metadata.primary_concept_id", "CONCEPT_SUBJECT_MISMATCH", Level.ERROR)
    ]
    assert found({"secondary_concept_ids": [OTHER_CONCEPT]}) == []


def test_a_retired_item_is_a_warning_not_an_error() -> None:
    refs = good_refs()
    refs[UUID(CHAPTER)] = CatalogueRef("CHAPTER", UUID(SUBJECT), None, "DEPRECATED")
    refs[UUID(EXAM)] = CatalogueRef("EXAM", None, None, "DEPRECATED")
    changes = {"is_pyq": True, "exam_id": EXAM, "exam_year": 2024}
    assert found(changes, refs) == [
        ("metadata.chapter_id", "DEPRECATED_REFERENCE", Level.WARNING),
        ("metadata.exam_id", "DEPRECATED_REFERENCE", Level.WARNING),
    ]


def test_ids_that_are_not_ids_are_left_to_the_shape_checks() -> None:
    assert found({"class_id": "x", "secondary_concept_ids": ["y", 3]}) == []


def test_anything_but_metadata_is_ignored_and_nothing_raises() -> None:
    for junk in (None, [], "x", {"metadata": None}, {"metadata": []}, {"metadata": {"a": 1}}):
        assert check_catalogue(junk, good_refs()) == []
        assert catalogue_ids(junk) == set()


def test_every_valid_id_is_collected_once_for_the_lookup() -> None:
    meta = content(secondary_concept_ids=[OTHER_CONCEPT, "junk"], source_id=SOURCE)
    assert catalogue_ids(meta) == {
        UUID(x) for x in (CLASS, SUBJECT, CHAPTER, TOPIC, CONCEPT, OTHER_CONCEPT, SOURCE)
    }
