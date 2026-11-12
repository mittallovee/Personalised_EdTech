from decimal import Decimal
from uuid import UUID

import pytest

from qbank.modules.questions.limits import (
    FIELDS,
    LimitProblem,
    Overrides,
    check_overrides,
    effective_rules,
    exam_of,
    normalise,
)
from qbank.modules.questions.rules import DEFAULT_RULES

EXAM = UUID("00000000-0000-4000-8000-0000000000e1")
OTHER = UUID("00000000-0000-4000-8000-0000000000e2")


def problems(defaults: object, exams: object = None) -> list[tuple[str, str]]:
    found = check_overrides(defaults, exams if exams is not None else {})
    return [(p.path, p.code) for p in found]


# --- Reading the values -------------------------------------------------------------------------


def test_every_setting_has_a_default_and_bounds_around_it() -> None:
    for name, field in FIELDS.items():
        built_in = getattr(DEFAULT_RULES, name)
        assert field.low <= built_in <= field.high, name


def test_nothing_set_means_the_built_in_limits() -> None:
    assert effective_rules(DEFAULT_RULES, Overrides({}, {}), None) == DEFAULT_RULES


def test_the_coachings_values_replace_the_built_in_ones_and_an_exam_replaces_those() -> None:
    overrides = Overrides(
        defaults={"integer_max": 9999, "numeric_max": "100.50"},
        exams={EXAM: {"integer_max": 99999}},
    )
    plain = effective_rules(DEFAULT_RULES, overrides, None)
    assert (plain.integer_max, plain.numeric_max) == (9999, Decimal("100.50"))
    assert plain.integer_min == DEFAULT_RULES.integer_min  # untouched
    exam = effective_rules(DEFAULT_RULES, overrides, EXAM)
    assert (exam.integer_max, exam.numeric_max) == (99999, Decimal("100.50"))
    other = effective_rules(DEFAULT_RULES, overrides, OTHER)  # an exam with no override
    assert other.integer_max == 9999


def test_numbers_in_the_safety_limits_are_never_changed_by_settings() -> None:
    overrides = Overrides({"integer_max": 5}, {})
    rules = effective_rules(DEFAULT_RULES, overrides, None)
    for name in ("equation_chars", "paragraph_chars", "blocks_per_list", "revision_bytes"):
        assert getattr(rules, name) == getattr(DEFAULT_RULES, name)


# --- Checking what an admin sends ---------------------------------------------------------------


def test_good_values_have_no_problems() -> None:
    assert problems({"integer_max": 9999, "numeric_min": "-5.5", "matching_max_items": 6}) == []
    assert problems({}, {str(EXAM): {"integer_max": 100}}) == []


def test_unknown_settings_are_refused_so_a_typo_is_not_silently_ignored() -> None:
    assert problems({"integr_max": 5}) == [("defaults.integr_max", "SETTING_UNKNOWN")]
    assert problems({"revision_bytes": 5}) == [("defaults.revision_bytes", "SETTING_UNKNOWN")]


@pytest.mark.parametrize("value", [True, None, 1.5, [], {}, "12", "x"])
def test_a_whole_number_setting_must_be_a_whole_number(value: object) -> None:
    assert problems({"integer_max": value}) == [("defaults.integer_max", "SETTING_NOT_A_NUMBER")]


@pytest.mark.parametrize("value", [True, None, 5, 1.5, "abc", "1e3", "1,5", "1.234", " 1", ""])
def test_a_decimal_setting_is_text_with_at_most_two_decimals(value: object) -> None:
    assert problems({"numeric_max": value}) == [("defaults.numeric_max", "SETTING_NOT_A_NUMBER")]


def test_a_value_outside_its_bounds_is_refused() -> None:
    field = FIELDS["integer_max"]
    assert problems({"integer_max": field.high + 1}) == [
        ("defaults.integer_max", "SETTING_OUT_OF_RANGE")
    ]
    assert problems({"integer_max": field.high}) == []
    assert problems({"matching_max_items": 11}) == [
        ("defaults.matching_max_items", "SETTING_OUT_OF_RANGE")
    ]
    assert problems({"digit_max": 10}) == [("defaults.digit_max", "SETTING_OUT_OF_RANGE")]
    assert problems({"numeric_max": "9999999.00"}) == [
        ("defaults.numeric_max", "SETTING_OUT_OF_RANGE")
    ]


def test_a_minimum_above_its_maximum_is_refused_where_the_two_meet() -> None:
    assert problems({"integer_min": 10, "integer_max": 5}) == [("defaults", "RANGE_EMPTY")]
    assert problems({"matching_min_items": 6, "matching_max_items": 3}) == [
        ("defaults", "RANGE_EMPTY")
    ]
    assert problems({"numeric_min": "5.00", "numeric_max": "4.99"}) == [("defaults", "RANGE_EMPTY")]
    assert problems({"integer_min": 5, "integer_max": 5}) == []  # one allowed value is fine


def test_an_exam_is_checked_on_top_of_the_coachings_values() -> None:
    # The exam alone is fine (max 100 > built-in min 0) but not with the coaching's own minimum.
    assert problems({"integer_min": 500}, {str(EXAM): {"integer_max": 100}}) == [
        (f"exams.{EXAM}", "RANGE_EMPTY")
    ]


def test_exam_keys_must_be_ids_and_values_must_be_objects() -> None:
    assert problems({}, {"not-an-id": {}}) == [("exams.not-an-id", "EXAM_ID_INVALID")]
    assert problems({}, {str(EXAM).upper(): {}}) == [
        (f"exams.{str(EXAM).upper()}", "EXAM_ID_INVALID")
    ]
    assert problems({}, {str(EXAM): [1]}) == [(f"exams.{EXAM}", "SETTINGS_NOT_AN_OBJECT")]
    assert problems([1], {}) == [("defaults", "SETTINGS_NOT_AN_OBJECT")]
    assert problems({}, [1]) == [("exams", "SETTINGS_NOT_AN_OBJECT")]


def test_problems_are_data_with_a_plain_message() -> None:
    (found,) = check_overrides({"integer_max": "x"}, {})
    assert isinstance(found, LimitProblem)
    assert "whole number" in found.message


# --- Turning what was stored into overrides -----------------------------------------------------


def test_normalise_reads_stored_values_and_drops_what_it_cannot_use() -> None:
    stored_exams = {str(EXAM): {"integer_max": 7}, "junk": {"integer_max": 1}, str(OTHER): "no"}
    overrides = normalise({"integer_min": -3, "bogus": 1}, stored_exams)
    assert overrides.defaults == {"integer_min": -3}
    assert overrides.exams == {EXAM: {"integer_max": 7}}


def test_normalise_copes_with_nothing_stored() -> None:
    assert normalise(None, None) == Overrides({}, {})
    assert normalise("x", [1]) == Overrides({}, {})


# --- Which exam a question is for ---------------------------------------------------------------


def test_the_exam_of_a_question_is_read_from_its_labels() -> None:
    assert exam_of({"metadata": {"exam_id": str(EXAM)}}) == EXAM


@pytest.mark.parametrize(
    "content",
    [
        None,
        [],
        {},
        {"metadata": None},
        {"metadata": {"exam_id": 5}},
        {"metadata": {"exam_id": "x"}},
    ],
)
def test_a_question_with_no_usable_exam_has_none(content: object) -> None:
    assert exam_of(content) is None
