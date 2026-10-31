"""T23 (metadata): the checks on a question's labels (D-15), without a database.

Only the *shape* is checked here: ids look like ids, numbers are in range, the PYQ fields are
present when the question is a past-year question. Whether an id exists in this coaching's
catalogue, and whether chapter, topic and concepts form one valid branch, is checked with the
database (a later PR).
"""

import copy
from typing import Any

import pytest

from qbank.modules.questions.findings import Level
from qbank.modules.questions.metadata import BLOOM_KEYS
from qbank.modules.questions.public import validate_content
from qbank.modules.taxonomy.catalogues import BLOOM_LEVELS
from tests.unit.test_question_content import FIXTURES

EXAM = "00000000-0000-4000-8000-0000000000e1"
SOURCE = "00000000-0000-4000-8000-0000000000f1"
OTHER = "00000000-0000-4000-8000-000000000006"


def with_metadata(**changes: object) -> dict[str, Any]:
    content = copy.deepcopy(FIXTURES["SCQ"]["ready"])
    content["metadata"].update(changes)
    return content


def pyq(**changes: object) -> dict[str, Any]:
    return with_metadata(**{"is_pyq": True, "exam_id": EXAM, "exam_year": 2024, **changes})


def found(content: object) -> list[tuple[str, str, Level]]:
    return [(f.path, f.code, f.level) for f in validate_content(content)]


def codes(content: object) -> list[str]:
    return [f.code for f in validate_content(content)]


def test_a_draft_with_no_metadata_says_so_once() -> None:
    content = copy.deepcopy(FIXTURES["SCQ"]["ready"])
    del content["metadata"]
    assert found(content) == [("metadata", "METADATA_MISSING", Level.INCOMPLETE)]


def test_empty_metadata_names_every_required_label() -> None:
    content = with_metadata()
    content["metadata"] = {}
    assert found(content) == [
        ("metadata.class_id", "CLASS_MISSING", Level.INCOMPLETE),
        ("metadata.subject_id", "SUBJECT_MISSING", Level.INCOMPLETE),
        ("metadata.chapter_id", "CHAPTER_MISSING", Level.INCOMPLETE),
        ("metadata.topic_id", "TOPIC_MISSING", Level.INCOMPLETE),
        ("metadata.primary_concept_id", "PRIMARY_CONCEPT_MISSING", Level.INCOMPLETE),
        ("metadata.difficulty", "DIFFICULTY_MISSING", Level.INCOMPLETE),
        ("metadata.bloom_level", "BLOOM_MISSING", Level.INCOMPLETE),
    ]


def test_null_means_not_given() -> None:
    assert codes(with_metadata(subtopic_id=None, exam_date=None, source_id=None)) == []
    assert codes(with_metadata(class_id=None)) == ["CLASS_MISSING"]


def test_metadata_must_be_an_object_with_known_fields() -> None:
    for junk in ("x", 5, [], True):
        content = with_metadata()
        content["metadata"] = junk
        assert codes(content) == ["METADATA_NOT_OBJECT"], junk
    assert codes(with_metadata(colour="red")) == ["UNKNOWN_FIELD"]


@pytest.mark.parametrize(
    "field",
    ["class_id", "subject_id", "chapter_id", "topic_id", "subtopic_id", "primary_concept_id"],
)
def test_catalogue_ids_must_be_uuids(field: str) -> None:
    for bad in ("x", "", 7, True, ["a"], {"a": 1}):
        assert found(with_metadata(**{field: bad})) == [
            (f"metadata.{field}", "METADATA_ID_INVALID", Level.ERROR)
        ], bad


def test_secondary_concepts() -> None:
    assert codes(with_metadata(secondary_concept_ids=[OTHER])) == []
    assert codes(with_metadata(secondary_concept_ids="x")) == ["SECONDARY_CONCEPTS_NOT_LIST"]
    assert codes(with_metadata(secondary_concept_ids=[OTHER, OTHER])) == [
        "SECONDARY_CONCEPT_DUPLICATE"
    ]
    assert found(with_metadata(secondary_concept_ids=["nope"])) == [
        ("metadata.secondary_concept_ids[0]", "METADATA_ID_INVALID", Level.ERROR)
    ]
    primary = FIXTURES["SCQ"]["ready"]["metadata"]["primary_concept_id"]
    assert codes(with_metadata(secondary_concept_ids=[primary])) == ["SECONDARY_CONCEPT_IS_PRIMARY"]
    many = [f"00000000-0000-4000-8000-{i:012d}" for i in range(100, 121)]
    assert "SECONDARY_CONCEPTS_COUNT" in codes(with_metadata(secondary_concept_ids=many))


def test_difficulty_is_a_whole_number_from_1_to_10() -> None:
    for good in (1, 5, 10):
        assert codes(with_metadata(difficulty=good)) == []
    for bad in (0, 11, -1, 4.5, "4", True, [4]):
        assert codes(with_metadata(difficulty=bad)) == ["DIFFICULTY_INVALID"], bad


def test_bloom_level_is_one_of_the_catalogue_keys() -> None:
    for level in BLOOM_LEVELS:
        assert codes(with_metadata(bloom_level=level.key)) == []
    for bad in ("apply", "Apply", "SYNTHESIZE", "", 3, True):
        assert codes(with_metadata(bloom_level=bad)) == ["BLOOM_INVALID"], bad


def test_a_past_year_question_needs_an_exam_and_a_year() -> None:
    assert codes(pyq()) == []
    assert found(with_metadata(is_pyq=True)) == [
        ("metadata.exam_id", "PYQ_EXAM_MISSING", Level.INCOMPLETE),
        ("metadata.exam_year", "PYQ_YEAR_MISSING", Level.INCOMPLETE),
    ]
    assert codes(with_metadata(is_pyq=True, exam_id=EXAM)) == ["PYQ_YEAR_MISSING"]
    assert codes(with_metadata(is_pyq=True, exam_year=2024)) == ["PYQ_EXAM_MISSING"]


def test_pyq_flag_and_year_are_checked() -> None:
    for bad in ("yes", 1, 0, []):
        assert codes(with_metadata(is_pyq=bad)) == ["PYQ_FLAG_INVALID"], bad
    for good in (1950, 2024, 2100):
        assert codes(pyq(exam_year=good)) == []
    for bad in (1949, 2101, 20.5, "2024", True, 0):
        assert codes(pyq(exam_year=bad)) == ["PYQ_YEAR_INVALID"], bad
    assert found(pyq(exam_id="x")) == [("metadata.exam_id", "METADATA_ID_INVALID", Level.ERROR)]


def test_exam_date_shift_and_paper_code_are_optional_but_checked() -> None:
    assert codes(pyq(exam_date="2024-01-27", exam_shift="Shift 1", paper_code="A")) == []
    for bad in ("27-01-2024", "2024-13-01", "2024-02-30", "20240127", 5, True):
        assert codes(pyq(exam_date=bad)) == ["EXAM_DATE_INVALID"], bad
    assert codes(pyq(exam_date="2023-12-31")) == ["EXAM_DATE_YEAR_MISMATCH"]
    for field in ("exam_shift", "paper_code"):
        for bad in ("", "   ", 5, "x" * 51, ["a"]):
            assert codes(pyq(**{field: bad})) == ["METADATA_TEXT_INVALID"], (field, bad)


def test_exam_details_on_a_question_that_is_not_a_pyq_are_flagged_not_dropped() -> None:
    assert found(with_metadata(exam_id=EXAM, exam_year=2024)) == [
        ("metadata.is_pyq", "PYQ_FIELDS_IGNORED", Level.WARNING)
    ]
    assert codes(with_metadata(is_pyq=False, exam_shift="Shift 2")) == ["PYQ_FIELDS_IGNORED"]
    assert codes(with_metadata(is_pyq=False)) == []


def test_source_and_note() -> None:
    assert codes(with_metadata(source_id=SOURCE, source_note="p. 42, Q7")) == []
    assert found(with_metadata(source_id="x")) == [
        ("metadata.source_id", "METADATA_ID_INVALID", Level.ERROR)
    ]
    for bad in ("", 5, "n" * 501):
        assert codes(with_metadata(source_note=bad)) == ["METADATA_TEXT_INVALID"], bad


def test_the_bloom_keys_match_the_catalogue_exactly() -> None:
    assert tuple(level.key for level in BLOOM_LEVELS) == BLOOM_KEYS


def test_metadata_nested_junk_never_raises() -> None:
    for junk in ({"a": {"b": [{}]}}, {"difficulty": {"x": 1}}, {"secondary_concept_ids": [[], {}]}):
        content = with_metadata()
        content["metadata"] = junk
        assert isinstance(validate_content(content), list)
