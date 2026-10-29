"""K-18: property-based tests for the question content checks (T23).

A normal test checks the cases someone thought of. A property test states a rule that must hold for
*every* input, and the Hypothesis library tries hundreds of generated inputs (and shrinks a
failure to the smallest example). The rules here:

- whatever it is given, ``validate_content`` returns findings and never raises, and gives the same
  answer twice;
- an integer key is accepted exactly when it is a whole JSON number from 0 to 999; anything else
  (a float, a string, a boolean...) is refused as "not an integer";
- a numerical key with exactly two decimals inside 0.00..999.00 is accepted, with more decimals
  it is flagged and never changed, and a range is accepted exactly when lower <= upper;
- the order of the options does not change the findings.

The last test proves the tests can fail: it breaks the integer check on purpose and expects the
property to catch it.

Deterministic in CI (``derandomize``); try new random inputs locally with
``HYPOTHESIS_PROFILE=explore``.
"""

import copy
import json
import os
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from qbank.modules.questions import answers
from qbank.modules.questions.findings import Finding, Level
from qbank.modules.questions.public import validate_content

PROFILES: dict[str, dict[str, Any]] = {
    "ci": {"max_examples": 150, "derandomize": True},
    "explore": {"max_examples": 2_000, "derandomize": False},
}
PROFILE = PROFILES[os.environ.get("HYPOTHESIS_PROFILE", "ci")]
PROP = settings(
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
    max_examples=PROFILE["max_examples"],
    derandomize=PROFILE["derandomize"],
)

FIXTURES: dict[str, Any] = json.loads(
    (Path(__file__).parent.parent / "fixtures" / "spec_v1_questions.json").read_text("utf-8")
)
FIRST_FIVE = ["SCQ", "MULTI_CORRECT", "INTEGER", "SINGLE_DIGIT", "NUMERICAL"]

JSON_VALUES = st.recursive(
    st.none()
    | st.booleans()
    | st.integers()
    | st.floats(allow_nan=False, allow_infinity=False)
    | st.text(max_size=20),
    lambda children: (
        st.lists(children, max_size=4) | st.dictionaries(st.text(max_size=8), children, max_size=4)
    ),
    max_leaves=30,
)


def codes(content: object) -> list[str]:
    return [f.code for f in validate_content(content)]


def integer_question(value: object) -> dict[str, Any]:
    content = copy.deepcopy(FIXTURES["INTEGER"]["ready"])
    content["answer"] = {"value": value}
    return content


def numerical_question(answer: object) -> dict[str, Any]:
    content = copy.deepcopy(FIXTURES["NUMERICAL"]["ready"])
    content["answer"] = answer
    return content


def two_decimals(number: Decimal) -> str:
    return f"{number:.2f}"


# --- the properties, as plain functions so the last test can run a broken checker ---------------


@PROP
@given(JSON_VALUES)
def prop_arbitrary_values_never_raise(value: object) -> None:
    findings = validate_content(value)
    assert findings == validate_content(value)  # a pure function of its input
    for finding in findings:
        assert isinstance(finding, Finding)
        assert finding.code == finding.code.upper() and finding.code
        assert finding.level in Level


@PROP
@given(
    st.sampled_from(FIRST_FIVE),
    st.sampled_from(
        ["stem", "options", "answer", "language", "question_type", "solution", "extra"]
    ),
    JSON_VALUES,
)
def prop_a_damaged_fixture_never_raises(kind: str, field: str, damage: object) -> None:
    content = copy.deepcopy(FIXTURES[kind]["ready"])
    content[field] = damage
    findings = validate_content(content)
    assert all(isinstance(f.path, str) and isinstance(f.message, str) for f in findings)


@PROP
@given(st.integers(min_value=-(10**6), max_value=10**6))
def prop_integer_key_is_accepted_exactly_inside_the_range(number: int) -> None:
    found = codes(integer_question(number))
    assert (found == []) if 0 <= number <= 999 else (found == ["ANSWER_OUT_OF_RANGE"])


@PROP
@given(
    st.booleans()
    | st.floats(allow_nan=False, allow_infinity=False)
    | st.text(max_size=10)
    | st.none()
    | st.lists(st.integers(), max_size=3)
)
def prop_anything_but_a_whole_number_is_not_an_integer(value: object) -> None:
    assert codes(integer_question(value)) == ["ANSWER_NOT_INTEGER"]


@PROP
@given(st.decimals(min_value=0, max_value=999, places=2))
def prop_two_decimal_keys_in_range_are_accepted(number: Decimal) -> None:
    text = two_decimals(number)
    assert codes(numerical_question({"mode": "exact", "value": text})) == []


@PROP
@given(st.decimals(min_value=0, max_value=998, places=2), st.integers(min_value=1, max_value=9999))
def prop_extra_decimals_are_flagged_and_never_rounded(number: Decimal, extra: int) -> None:
    text = f"{two_decimals(number)}{extra}"  # at least three decimals
    content = numerical_question({"mode": "exact", "value": text})
    assert "NUMERIC_TOO_MANY_DECIMALS" in codes(content)
    assert content["answer"]["value"] == text  # never rounded or changed


@PROP
@given(
    st.decimals(min_value=0, max_value=999, places=2),
    st.decimals(min_value=0, max_value=999, places=2),
)
def prop_a_range_is_accepted_exactly_when_lower_is_not_above_upper(
    first: Decimal, second: Decimal
) -> None:
    answer = {"mode": "range", "lower": two_decimals(first), "upper": two_decimals(second)}
    found = codes(numerical_question(answer))
    assert (found == []) if first <= second else (found == ["NUMERIC_RANGE_REVERSED"])


@PROP
@given(st.permutations(range(4)))
def prop_option_order_does_not_change_the_findings(order: list[int]) -> None:
    content = copy.deepcopy(FIXTURES["SCQ"]["ready"])
    content["options"][1]["content"] = []  # one finding to compare
    before = sorted((f.code, f.level) for f in validate_content(content))
    content["options"] = [content["options"][i] for i in order]
    after = sorted((f.code, f.level) for f in validate_content(content))
    assert [c for c, _ in before] == [c for c, _ in after]


# --- pytest runs the properties ------------------------------------------------------------------


def test_arbitrary_values_never_raise() -> None:
    prop_arbitrary_values_never_raise()


def test_a_damaged_fixture_never_raises() -> None:
    prop_a_damaged_fixture_never_raises()


def test_integer_keys_inside_the_range() -> None:
    prop_integer_key_is_accepted_exactly_inside_the_range()


def test_anything_but_a_whole_number_is_not_an_integer() -> None:
    prop_anything_but_a_whole_number_is_not_an_integer()


def test_two_decimal_keys_in_range() -> None:
    prop_two_decimal_keys_in_range_are_accepted()


def test_extra_decimals_are_flagged_and_never_rounded() -> None:
    prop_extra_decimals_are_flagged_and_never_rounded()


def test_ranges_follow_lower_not_above_upper() -> None:
    prop_a_range_is_accepted_exactly_when_lower_is_not_above_upper()


def test_option_order_does_not_change_the_findings() -> None:
    prop_option_order_does_not_change_the_findings()


def test_a_deliberately_broken_checker_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    """The properties are only worth anything if they fail on a wrong checker."""
    monkeypatch.setattr(answers, "is_whole_number", lambda value: True)  # accepts True and 3.5
    with pytest.raises(AssertionError):
        prop_anything_but_a_whole_number_is_not_an_integer()
