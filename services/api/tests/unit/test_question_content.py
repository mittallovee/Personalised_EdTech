"""T23 (part 1): the checks on a question's content: envelope, blocks, and the first five formats.

The fixtures are spec-v1's own examples (copied to ``tests/fixtures``): for each format the
incomplete draft saves with no error, the content-ready fixture has no findings at all, and the
invalid replacement answer produces exactly the finding the spec names.
"""

import copy
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from qbank.modules.questions.findings import Level
from qbank.modules.questions.public import DEFAULT_RULES, Rules, validate_content

FIXTURES: dict[str, Any] = json.loads(
    (Path(__file__).parent.parent / "fixtures" / "spec_v1_questions.json").read_text("utf-8")
)
FIRST_FIVE = ["SCQ", "MULTI_CORRECT", "INTEGER", "SINGLE_DIGIT", "NUMERICAL"]


def codes(content: object, rules: Rules = DEFAULT_RULES) -> list[str]:
    return [f.code for f in validate_content(content, rules)]


def ready(kind: str) -> dict[str, Any]:
    return copy.deepcopy(FIXTURES[kind]["ready"])


# --- spec-v1 fixtures ----------------------------------------------------------------------------


@pytest.mark.parametrize("kind", FIRST_FIVE)
def test_the_incomplete_draft_saves_with_no_error(kind: str) -> None:
    findings = validate_content(FIXTURES[kind]["draft"])
    assert findings, "an incomplete draft should say what is still missing"
    assert [f for f in findings if f.level == Level.ERROR] == []


@pytest.mark.parametrize("kind", FIRST_FIVE)
def test_the_content_ready_fixture_has_no_findings(kind: str) -> None:
    assert validate_content(FIXTURES[kind]["ready"]) == []


@pytest.mark.parametrize(
    ("kind", "expected"),
    [
        ("SCQ", ["ANSWER_OPTION_UNKNOWN"]),
        ("MULTI_CORRECT", ["ANSWER_EMPTY"]),
        ("INTEGER", ["ANSWER_OUT_OF_RANGE"]),
        ("SINGLE_DIGIT", ["ANSWER_OUT_OF_RANGE"]),
        ("NUMERICAL", ["NUMERIC_TOO_MANY_DECIMALS"]),
    ],
)
def test_the_invalid_replacement_answer_gives_exactly_the_named_finding(
    kind: str, expected: list[str]
) -> None:
    content = ready(kind)
    content["answer"] = FIXTURES[kind]["invalid_answer"]["answer"]
    assert codes(content) == expected


def test_the_draft_names_what_is_missing() -> None:
    assert codes(FIXTURES["SCQ"]["draft"]) == ["OPTIONS_MISSING", "ANSWER_MISSING"]
    assert codes(FIXTURES["INTEGER"]["draft"]) == ["ANSWER_MISSING"]


# --- the envelope --------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "junk", [None, [], "text", 5, True, {"stem": 5}, {"a": {"b": {"c": [{}]}}}]
)
def test_nothing_ever_raises(junk: object) -> None:
    assert isinstance(validate_content(junk), list)


def test_content_must_be_an_object() -> None:
    assert codes([1, 2]) == ["CONTENT_NOT_OBJECT"]


@pytest.mark.parametrize("version", [0, 2, "1", True, None])
def test_only_schema_version_one_is_understood(version: object) -> None:
    content = ready("SCQ")
    content["schema_version"] = version
    assert "SCHEMA_VERSION_UNSUPPORTED" in codes(content)


def test_unknown_question_type_is_an_error() -> None:
    content = ready("SCQ")
    content["question_type"] = "ESSAY"
    assert "QUESTION_TYPE_UNKNOWN" in codes(content)


def test_a_field_of_another_format_is_refused() -> None:
    content = ready("INTEGER")
    content["options"] = []
    assert codes(content) == ["FIELD_NOT_ALLOWED"]


def test_language_must_look_like_a_language_code() -> None:
    content = ready("SCQ")
    content["language"] = "English!"
    assert codes(content) == ["LANGUAGE_INVALID"]
    del content["language"]
    assert codes(content) == ["LANGUAGE_MISSING"]


def test_video_link_must_be_a_web_address() -> None:
    content = ready("SCQ")
    content["video_solution_url"] = "https://example.com/watch?v=1"
    assert codes(content) == []
    content["video_solution_url"] = "javascript:alert(1)"
    assert codes(content) == ["VIDEO_URL_INVALID"]


def test_a_huge_document_is_refused_without_being_walked() -> None:
    content = ready("SCQ")
    content["solution"] = [{"kind": "paragraph", "text": "x" * 9_000}] * 40
    assert codes(content) == ["CONTENT_TOO_LARGE"]


# --- blocks --------------------------------------------------------------------------------------


def stem(*blocks: object) -> dict[str, Any]:
    content = ready("INTEGER")
    content["stem"] = list(blocks)
    return content


def test_text_is_never_treated_as_markup() -> None:
    # HTML in text is just characters: stored and shown as text, so there is nothing to refuse.
    assert codes(stem({"kind": "paragraph", "text": "<script>alert(1)</script> **bold**"})) == []


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (r"A body of mass \(m\) moves", []),
        (r"Two: \(a\) and \(b\)", []),
        (r"A literal backslash \\(not maths", []),
        (r"opened \(m never closed", ["INLINE_EQUATION_UNBALANCED"]),
        (r"closed \) never opened", ["INLINE_EQUATION_UNBALANCED"]),
        (r"nested \(a \(b\) c\)", ["INLINE_EQUATION_NESTED"]),
    ],
)
def test_inline_equations_must_balance(text: str, expected: list[str]) -> None:
    assert codes(stem({"kind": "paragraph", "text": text})) == expected


def test_block_kinds_and_fields_are_checked() -> None:
    assert codes(stem({"kind": "video"})) == ["BLOCK_KIND_UNKNOWN"]
    assert codes(stem({"text": "no kind"})) == ["BLOCK_KIND_UNKNOWN"]
    assert codes(stem("just text")) == ["BLOCK_NOT_OBJECT"]
    assert codes(stem({"kind": "paragraph", "text": "ok", "html": "<b>x</b>"})) == ["UNKNOWN_FIELD"]
    assert codes(stem({"kind": "paragraph", "text": 5})) == ["TEXT_NOT_STRING"]


def test_equations_are_latex_only() -> None:
    assert codes(stem({"kind": "equation", "format": "latex", "source": "E = mc^2"})) == []
    assert codes(stem({"kind": "equation", "format": "mathml", "source": "<math/>"})) == [
        "EQUATION_FORMAT_UNSUPPORTED"
    ]
    assert codes(stem({"kind": "equation", "format": "latex", "source": " "})) == ["EQUATION_EMPTY"]


def test_length_limits_are_applied_and_come_from_the_rules() -> None:
    long_text = {"kind": "paragraph", "text": "x" * 51}
    assert codes(stem(long_text)) == []
    assert codes(stem(long_text), replace(DEFAULT_RULES, paragraph_chars=50)) == [
        "PARAGRAPH_TOO_LONG"
    ]
    equation = {"kind": "equation", "format": "latex", "source": "x" * 2_001}
    assert codes(stem(equation)) == ["EQUATION_TOO_LONG"]
    assert codes(stem(*[{"kind": "paragraph", "text": "a"}] * 101)) == ["TOO_MANY_BLOCKS"]


def test_an_image_needs_a_picture_and_alt_text() -> None:
    image = {
        "kind": "image",
        "asset_id": "00000000-0000-4000-8000-0000000000aa",
        "alt_text": "A ramp",
    }
    assert codes(stem(image)) == []
    assert codes(stem({**image, "alt_text": ""})) == ["IMAGE_ALT_MISSING"]
    assert codes(stem({"kind": "image", "alt_text": "x"})) == ["IMAGE_ASSET_MISSING"]
    assert codes(stem({**image, "asset_id": "../../etc/passwd"})) == ["IMAGE_ASSET_ID_INVALID"]


def test_tables_are_rectangular_and_hold_only_text_and_equations() -> None:
    cell = [{"kind": "paragraph", "text": "1"}]
    assert codes(stem({"kind": "table", "rows": [[cell, cell], [cell, cell]]})) == []
    assert codes(stem({"kind": "table", "rows": [[cell, cell], [cell]]})) == [
        "TABLE_NOT_RECTANGULAR"
    ]
    assert codes(stem({"kind": "table", "rows": []})) == ["TABLE_EMPTY"]
    picture = [
        {"kind": "image", "asset_id": "00000000-0000-4000-8000-0000000000aa", "alt_text": "x"}
    ]
    assert codes(stem({"kind": "table", "rows": [[picture]]})) == ["BLOCK_KIND_NOT_ALLOWED"]


def test_lists_hold_items_of_text_and_equations() -> None:
    item = [{"kind": "paragraph", "text": "one"}]
    assert codes(stem({"kind": "list", "ordered": True, "items": [item, item]})) == []
    assert codes(stem({"kind": "list", "ordered": "yes", "items": [item]})) == [
        "LIST_ORDERED_NOT_BOOLEAN"
    ]
    assert codes(stem({"kind": "list", "items": []})) == ["LIST_EMPTY"]


def test_a_finding_names_the_field_it_is_about() -> None:
    content = ready("SCQ")
    content["options"][2]["content"] = [{"kind": "paragraph", "text": r"broken \("}]
    [finding] = validate_content(content)
    assert finding.path == "options[2].content[0].text"
    assert finding.level == Level.ERROR


# --- SCQ and multiple correct --------------------------------------------------------------------


def test_scq_needs_exactly_four_distinct_options() -> None:
    content = ready("SCQ")
    content["options"] = content["options"][:3]
    assert codes(content) == ["OPTIONS_COUNT"]  # three: still being written
    [finding] = validate_content(content)
    assert finding.level == Level.INCOMPLETE
    content = ready("SCQ")
    content["options"].append({"id": "E", "content": [{"kind": "paragraph", "text": "8"}]})
    [finding] = validate_content(content)
    assert (finding.code, finding.level) == ("OPTIONS_COUNT", Level.ERROR)
    content = ready("SCQ")
    content["options"][1]["id"] = "A"
    assert "OPTION_ID_DUPLICATE" in codes(content)
    content["options"][1]["id"] = "has space"
    assert "OPTION_ID_INVALID" in codes(content)


def test_an_empty_option_is_incomplete_not_wrong() -> None:
    content = ready("SCQ")
    content["options"][3]["content"] = []
    [finding] = validate_content(content)
    assert (finding.code, finding.level) == ("OPTION_EMPTY", Level.INCOMPLETE)


def test_scq_answer_shapes() -> None:
    for bad in ({"option_ids": ["A"]}, {"option_id": 1}, "B", ["B"], {"option_id": "B", "x": 1}):
        content = ready("SCQ")
        content["answer"] = bad
        assert validate_content(content), bad
    content = ready("SCQ")
    content["answer"] = {"option_id": "D"}
    assert codes(content) == []


def test_multiple_correct_allows_one_to_four_distinct_options() -> None:
    for chosen in (["A"], ["A", "C"], ["A", "B", "C", "D"]):
        content = ready("MULTI_CORRECT")
        content["answer"] = {"option_ids": chosen}
        assert codes(content) == [], chosen
    for bad, expected in (
        ([], "ANSWER_EMPTY"),
        (["A", "A"], "ANSWER_OPTION_DUPLICATE"),
        (["Z"], "ANSWER_OPTION_UNKNOWN"),
        ([1], "ANSWER_SHAPE"),
        ("A", "ANSWER_SHAPE"),
    ):
        content = ready("MULTI_CORRECT")
        content["answer"] = {"option_ids": bad}
        assert codes(content) == [expected], bad


def test_an_answer_cannot_be_checked_while_options_are_missing() -> None:
    content = ready("SCQ")
    del content["options"]
    assert codes(content) == ["OPTIONS_MISSING"]  # no second finding about the answer


# --- integer and single digit --------------------------------------------------------------------


@pytest.mark.parametrize("value", [0, 1, 500, 999])
def test_integer_keys_inside_the_range(value: int) -> None:
    content = ready("INTEGER")
    content["answer"] = {"value": value}
    assert codes(content) == []


@pytest.mark.parametrize(
    ("value", "expected"),
    [(-1, "ANSWER_OUT_OF_RANGE"), (1000, "ANSWER_OUT_OF_RANGE"), (2**70, "ANSWER_OUT_OF_RANGE")],
)
def test_integer_keys_outside_the_range(value: int, expected: str) -> None:
    content = ready("INTEGER")
    content["answer"] = {"value": value}
    assert codes(content) == [expected]


@pytest.mark.parametrize("value", [3.5, 3.0, "7", True, False, None, [3], {"v": 3}])
def test_integer_keys_must_be_whole_json_numbers(value: object) -> None:
    content = ready("INTEGER")
    content["answer"] = {"value": value}
    assert codes(content) == ["ANSWER_NOT_INTEGER"]


@pytest.mark.parametrize(("value", "ok"), [(0, True), (9, True), (-1, False), (10, False)])
def test_single_digit_range(value: int, ok: bool) -> None:
    content = ready("SINGLE_DIGIT")
    content["answer"] = {"value": value}
    assert (codes(content) == []) is ok


def test_a_changed_limit_changes_what_is_accepted() -> None:
    content = ready("INTEGER")
    content["answer"] = {"value": 1000}
    assert codes(content, replace(DEFAULT_RULES, integer_max=1500)) == []
    content["answer"] = {"value": -5}
    assert codes(content, replace(DEFAULT_RULES, integer_min=-10)) == []


# --- numerical -----------------------------------------------------------------------------------


def numerical(answer: object) -> dict[str, Any]:
    content = ready("NUMERICAL")
    content["answer"] = answer
    return content


@pytest.mark.parametrize("value", ["0.00", "0.01", "9.80", "123.45", "999.00"])
def test_exact_values_inside_the_range(value: str) -> None:
    assert codes(numerical({"mode": "exact", "value": value})) == []


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("999.01", ["ANSWER_OUT_OF_RANGE"]),
        ("-0.01", ["ANSWER_OUT_OF_RANGE"]),
        ("-5.00", ["ANSWER_OUT_OF_RANGE"]),
        ("-0.00", ["NUMERIC_FORMAT_INVALID"]),
        ("9.8", ["NUMERIC_FORMAT_INVALID"]),
        ("9", ["NUMERIC_FORMAT_INVALID"]),
        ("abc", ["NUMERIC_FORMAT_INVALID"]),
        ("1e3", ["NUMERIC_FORMAT_INVALID"]),
        (" 9.80", ["NUMERIC_FORMAT_INVALID"]),
        ("9." + "0" * 40, ["NUMERIC_FORMAT_INVALID"]),
        (9.8, ["NUMERIC_NOT_TEXT"]),
        (9, ["NUMERIC_NOT_TEXT"]),
        (None, ["NUMERIC_NOT_TEXT"]),
    ],
)
def test_exact_values_outside_the_rules(value: object, expected: list[str]) -> None:
    assert codes(numerical({"mode": "exact", "value": value})) == expected


def test_extra_decimals_are_kept_and_flagged_not_rounded() -> None:
    content = numerical({"mode": "exact", "value": "9.805"})
    assert codes(content) == ["NUMERIC_TOO_MANY_DECIMALS"]
    assert content["answer"]["value"] == "9.805"  # the content itself is never changed
    # Still flagged for range when it is also out of range.
    assert codes(numerical({"mode": "exact", "value": "999.005"})) == [
        "NUMERIC_TOO_MANY_DECIMALS",
        "ANSWER_OUT_OF_RANGE",
    ]


def test_ranges_are_inclusive_and_ordered() -> None:
    assert codes(numerical({"mode": "range", "lower": "9.79", "upper": "9.81"})) == []
    assert codes(numerical({"mode": "range", "lower": "5.00", "upper": "5.00"})) == []
    assert codes(numerical({"mode": "range", "lower": "0.00", "upper": "999.00"})) == []
    assert codes(numerical({"mode": "range", "lower": "9.81", "upper": "9.79"})) == [
        "NUMERIC_RANGE_REVERSED"
    ]
    assert codes(numerical({"mode": "range", "lower": "1.00", "upper": "999.01"})) == [
        "ANSWER_OUT_OF_RANGE"
    ]


def test_a_range_needs_both_ends() -> None:
    assert codes(numerical({"mode": "range", "lower": "1.00"})) == ["NUMERIC_VALUE_MISSING"]
    assert codes(numerical({"mode": "exact"})) == ["NUMERIC_VALUE_MISSING"]


@pytest.mark.parametrize(
    ("answer", "expected"),
    [
        ({"mode": "exact", "value": "5.00", "unit": "m"}, ["ANSWER_UNIT_NOT_ALLOWED"]),
        (
            {"mode": "range", "lower": "1.00", "upper": "2.00", "Units": "m"},
            ["ANSWER_UNIT_NOT_ALLOWED"],
        ),
        (
            {"mode": "range", "ranges": [["1.00", "2.00"], ["5.00", "6.00"]]},
            ["ANSWER_FIELD_UNKNOWN"],
        ),
        ({"mode": "exact", "lower": "1.00", "value": "2.00"}, ["ANSWER_FIELD_UNKNOWN"]),
        ({"mode": "approx", "value": "5.00"}, ["NUMERIC_MODE_INVALID"]),
        ({"value": "5.00"}, ["NUMERIC_MODE_INVALID"]),
        ("5.00", ["ANSWER_SHAPE"]),
    ],
)
def test_numerical_answer_shapes(answer: object, expected: list[str]) -> None:
    found = codes(numerical(answer))
    assert expected[0] in found
