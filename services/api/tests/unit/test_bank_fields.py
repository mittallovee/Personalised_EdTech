"""T37 part 1 (unit): what the bank index reads from a question's content.

The extractor never raises and never trusts: whatever the author saved, each field is either a
valid value or ``None``, so the index holds nothing that could break a filter.
"""

from typing import Any
from uuid import UUID, uuid4

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from qbank.modules.questions.bank_fields import bank_fields
from qbank.modules.questions.metadata import BLOOM_KEYS
from qbank.modules.questions.validate import QUESTION_TYPES

settings.register_profile("bank_fields", max_examples=300, deadline=None)
settings.load_profile("bank_fields")

IDS = [uuid4() for _ in range(6)]


def content(**meta: Any) -> dict[str, Any]:
    return {"question_type": "SCQ", "language": "en", "metadata": meta}


def test_the_labels_are_read_from_the_metadata() -> None:
    fields = bank_fields(
        {
            "question_type": "NUMERICAL",
            "language": "HI",
            "solution": [{"kind": "paragraph", "text": "Use v = u + at."}],
            "video_solution_url": "https://example.com/v",
            "metadata": {
                "class_id": str(IDS[0]),
                "subject_id": str(IDS[1]),
                "chapter_id": str(IDS[2]),
                "topic_id": str(IDS[3]),
                "primary_concept_id": str(IDS[4]),
                "secondary_concept_ids": [str(IDS[5]), str(IDS[4]), str(IDS[5])],
                "difficulty": 6,
                "bloom_level": "ANALYZE",
                "is_pyq": True,
                "exam_id": str(IDS[0]),
                "exam_year": 2024,
            },
        }
    )
    assert (fields.question_type, fields.language) == ("NUMERICAL", "hi")
    assert (fields.class_id, fields.subject_id, fields.chapter_id) == (IDS[0], IDS[1], IDS[2])
    assert (fields.topic_id, fields.primary_concept_id) == (IDS[3], IDS[4])
    assert fields.concept_ids == (IDS[4], IDS[5])  # main first, each once
    assert (fields.difficulty, fields.bloom_level, fields.is_pyq) == (6, "ANALYZE", True)
    assert (fields.exam_id, fields.exam_year) == (IDS[0], 2024)
    assert (fields.has_solution, fields.has_video) == (True, True)


def test_a_question_with_no_labels_has_none() -> None:
    fields = bank_fields({})
    assert fields.question_type is None and fields.language is None
    assert fields.concept_ids == ()
    assert (fields.is_pyq, fields.has_solution, fields.has_video) == (False, False, False)


@pytest.mark.parametrize("value", [0, 11, -1, True, 5.5, "5", None, [5]])
def test_a_difficulty_outside_one_to_ten_is_left_out(value: object) -> None:
    assert bank_fields(content(difficulty=value)).difficulty is None


@pytest.mark.parametrize("value", [1, 10])
def test_the_ends_of_the_difficulty_range_are_kept(value: int) -> None:
    assert bank_fields(content(difficulty=value)).difficulty == value


@pytest.mark.parametrize("value", ["yes", 1, "true", None])
def test_only_a_real_true_marks_a_past_year_question(value: object) -> None:
    assert bank_fields(content(is_pyq=value)).is_pyq is False


@pytest.mark.parametrize("blank", [[], [{"kind": "paragraph", "text": "   "}], "text", None])
def test_a_blank_solution_is_not_a_solution(blank: object) -> None:
    assert bank_fields({"solution": blank}).has_solution is False


@pytest.mark.parametrize("url", ["", "   ", None, 5, ["https://example.com"]])
def test_a_blank_video_link_is_not_a_video(url: object) -> None:
    assert bank_fields({"video_solution_url": url}).has_video is False


def test_a_language_is_a_code_in_lower_case_or_nothing() -> None:
    assert bank_fields({"language": "en-IN"}).language == "en-in"
    for bad in ("english language", "e", "", 5, None, "x" * 30):
        assert bank_fields({"language": bad}).language is None


def test_content_that_is_not_an_object_gives_empty_fields() -> None:
    for junk in (None, [], "text", 5, [{"metadata": {}}]):
        fields = bank_fields(junk)
        assert fields.subject_id is None and fields.concept_ids == ()


json_values = st.recursive(
    st.none()
    | st.booleans()
    | st.integers()
    | st.floats(allow_nan=False)
    | st.text(max_size=12)
    | st.uuids().map(str),
    lambda inner: (
        st.lists(inner, max_size=4)
        | st.dictionaries(
            st.sampled_from(
                [
                    "metadata",
                    "language",
                    "question_type",
                    "solution",
                    "video_solution_url",
                    "difficulty",
                    "bloom_level",
                    "is_pyq",
                    "exam_year",
                    "subject_id",
                    "primary_concept_id",
                    "secondary_concept_ids",
                ]
            ),
            inner,
            max_size=6,
        )
    ),
    max_leaves=25,
)


@given(json_values)
def test_any_content_gives_valid_values_and_never_an_error(value: object) -> None:
    fields = bank_fields(value)
    assert fields.question_type is None or fields.question_type in QUESTION_TYPES
    assert fields.bloom_level is None or fields.bloom_level in BLOOM_KEYS
    assert fields.difficulty is None or 1 <= fields.difficulty <= 10
    assert fields.exam_year is None or 1950 <= fields.exam_year <= 2100
    assert len(set(fields.concept_ids)) == len(fields.concept_ids)
    assert all(isinstance(c, UUID) for c in fields.concept_ids)
    if fields.primary_concept_id is not None:
        assert fields.concept_ids[0] == fields.primary_concept_id
