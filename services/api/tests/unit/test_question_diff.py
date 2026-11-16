"""M4 PR 4d, test T40 (part 1): what changed between two texts of a question (E-08).

Examples first, then rules that must hold for *any* two JSON documents (Hypothesis tries hundreds of
generated ones and shrinks a failure): the diff of equal texts is empty, replaying the changes on
the old text gives the new one, and the word segments of an edited text add back up to both
versions. Deterministic in CI; try new random inputs locally with ``HYPOTHESIS_PROFILE=explore``.
"""

import copy
import json
import os
from itertools import pairwise
from typing import Any

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from qbank.modules.questions.domain import diff as diff_module
from qbank.modules.questions.domain.diff import (
    Change,
    Op,
    SegmentKind,
    apply_changes,
    diff_content,
    word_segments,
)

PROFILES: dict[str, dict[str, Any]] = {
    "ci": {"max_examples": 200, "derandomize": True},
    "explore": {"max_examples": 3_000, "derandomize": False},
}
PROFILE = PROFILES[os.environ.get("HYPOTHESIS_PROFILE", "ci")]
PROP = settings(
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
    max_examples=PROFILE["max_examples"],
    derandomize=PROFILE["derandomize"],
)


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def paragraph(text: str) -> dict[str, Any]:
    return {"kind": "paragraph", "text": text}


def equation(source: str) -> dict[str, Any]:
    return {"kind": "equation", "format": "latex", "source": source}


def question(
    stem: list[Any], options: list[str] | None = None, answer: str = "B"
) -> dict[str, Any]:
    return {
        "question_type": "SCQ",
        "language": "en",
        "stem": stem,
        "options": [
            {"id": chr(65 + at), "content": [paragraph(text)]}
            for at, text in enumerate(options or ["one", "two", "three", "four"])
        ],
        "answer": {"correct_option_id": answer},
        "metadata": {"difficulty": 3},
    }


# ---- examples ---------------------------------------------------------------------------------


def test_equal_texts_have_no_changes() -> None:
    content = question([paragraph("A body of mass \\(m\\) moves."), equation("v = u + at")])
    assert diff_content(content, copy.deepcopy(content)) == []


def test_an_edited_sentence_is_one_replace_with_word_segments() -> None:
    old = question([paragraph("A body moves with speed 5 m/s.")])
    new = question([paragraph("A body moves with speed 7 m/s.")])
    [change] = diff_content(old, new)
    assert change.op is Op.REPLACE
    assert change.path == ("stem", 0, "text")
    assert change.before == "A body moves with speed 5 m/s."
    assert change.after == "A body moves with speed 7 m/s."
    assert change.segments is not None
    changed = [(s.kind, s.text) for s in change.segments if s.kind is not SegmentKind.EQUAL]
    assert changed == [(SegmentKind.DELETE, "5 "), (SegmentKind.INSERT, "7 ")]


def test_an_edited_equation_is_one_item_removed_old_and_added_new() -> None:
    old = question([paragraph("Find v."), equation("v = u + at")])
    new = question([paragraph("Find v."), equation("v = u + 2at")])
    [change] = diff_content(old, new)
    assert change.op is Op.REPLACE
    assert change.path == ("stem", 1)  # the whole block, never its inside
    assert change.before == equation("v = u + at")
    assert change.after == equation("v = u + 2at")
    assert change.segments is None


def test_a_picture_that_changed_is_one_item() -> None:
    old = question([{"kind": "image", "asset_id": "a" * 8, "alt_text": "A graph"}])
    new = question([{"kind": "image", "asset_id": "b" * 8, "alt_text": "A graph"}])
    [change] = diff_content(old, new)
    assert (change.op, change.path) == (Op.REPLACE, ("stem", 0))


def test_an_option_edit_names_the_option_and_the_answer_change_is_separate() -> None:
    old = question([paragraph("Pick.")], ["one", "two", "three", "four"], answer="B")
    new = question([paragraph("Pick.")], ["one", "two", "THREE", "four"], answer="C")
    changes = diff_content(old, new)
    assert sorted(change.path for change in changes) == [
        ("answer", "correct_option_id"),
        ("options", 2, "content", 0, "text"),
    ]


def test_an_inserted_block_does_not_make_the_later_ones_look_edited() -> None:
    old = question([paragraph("First."), paragraph("Second."), paragraph("Third.")])
    new = question(
        [paragraph("First."), paragraph("Inserted."), paragraph("Second."), paragraph("Third.")]
    )
    [change] = diff_content(old, new)
    assert (change.op, change.path, change.after) == (Op.ADD, ("stem", 1), paragraph("Inserted."))


def test_a_removed_block_and_a_removed_key() -> None:
    old = question([paragraph("First."), paragraph("Second.")])
    old["solution"] = [paragraph("Because.")]
    new = question([paragraph("First.")])
    changes = diff_content(old, new)
    assert {(c.op, c.path) for c in changes} == {
        (Op.REMOVE, ("stem", 1)),
        (Op.REMOVE, ("solution",)),
    }
    assert canonical(apply_changes(old, changes)) == canonical(new)


def test_a_changed_label_in_the_metadata() -> None:
    old = question([paragraph("x")])
    new = copy.deepcopy(old)
    new["metadata"]["difficulty"] = 8
    new["metadata"]["bloom"] = "APPLY"
    changes = diff_content(old, new)
    assert {(c.op, c.path) for c in changes} == {
        (Op.REPLACE, ("metadata", "difficulty")),
        (Op.ADD, ("metadata", "bloom")),
    }


def test_null_is_a_value_like_any_other() -> None:
    changes = diff_content({"a": None}, {"a": 0})
    assert [(c.op, c.before, c.after) for c in changes] == [(Op.REPLACE, None, 0)]
    assert apply_changes({"a": None}, changes) == {"a": 0}


def test_true_and_one_are_different_values() -> None:
    assert diff_content({"a": True}, {"a": 1}) != []


def test_a_very_long_list_is_compared_as_one_piece_not_item_by_item() -> None:
    old = {"stem": [paragraph(str(n)) for n in range(600)]}
    new = {"stem": [paragraph(str(n + 1)) for n in range(600)]}
    [change] = diff_content(old, new)
    assert (change.op, change.path) == (Op.REPLACE, ("stem",))


def test_a_huge_text_is_compared_as_one_piece(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(diff_module, "_MAX_TOKEN_PAIRS", 10)
    segments = word_segments("one two three four five six", "one two three four five seven")
    assert [(s.kind, s.text) for s in segments] == [
        (SegmentKind.DELETE, "one two three four five six"),
        (SegmentKind.INSERT, "one two three four five seven"),
    ]


def test_a_value_nested_thousands_deep_is_one_change_not_an_error() -> None:
    deep: Any = "end"
    for _ in range(5_000):
        deep = [deep]
    changes = diff_content(deep, ["other"])
    assert len(changes) == 1 and changes[0].op is Op.REPLACE


def test_nesting_beyond_the_depth_limit_is_replaced_whole() -> None:
    def nested(leaf: str) -> Any:
        value: Any = leaf
        for _ in range(40):
            value = {"k": value}
        return value

    old, new = nested("a"), nested("b")
    changes = diff_content(old, new)
    assert len(changes) == 1
    assert canonical(apply_changes(old, changes)) == canonical(new)


# ---- the rules, for any input -----------------------------------------------------------------

LETTERS = st.text(alphabet="ab c.", max_size=14)
SCALARS = st.none() | st.booleans() | st.integers(-3, 3) | LETTERS
JSON_VALUES = st.recursive(
    SCALARS,
    lambda inner: (
        st.lists(inner, max_size=5) | st.dictionaries(st.sampled_from("abcd"), inner, max_size=4)
    ),
    max_leaves=25,
)
BLOCKS = st.one_of(
    LETTERS.map(paragraph),
    LETTERS.map(equation),
    st.sampled_from(["x", "y"]).map(
        lambda asset: {"kind": "image", "asset_id": asset, "alt_text": "a"}
    ),
)
OPTIONS = st.lists(
    st.builds(
        lambda i, blocks: {"id": i, "content": blocks},
        st.sampled_from("ABCDE"),
        st.lists(BLOCKS, max_size=3),
    ),
    max_size=5,
)
QUESTIONS = st.builds(
    lambda stem, options, solution: {
        "question_type": "SCQ",
        "stem": stem,
        "options": options,
        "solution": solution,
    },
    st.lists(BLOCKS, max_size=6),
    OPTIONS,
    st.lists(BLOCKS, max_size=3),
)


@st.composite
def edited(draw: st.DrawFn, content: dict[str, Any]) -> dict[str, Any]:
    """``content`` after a few random edits: a block inserted, removed or reworded."""
    result = copy.deepcopy(content)
    for _ in range(draw(st.integers(0, 4))):
        stem: list[Any] = result["stem"]
        kind = draw(st.sampled_from(["insert", "remove", "reword", "option"]))
        if kind == "insert":
            stem.insert(draw(st.integers(0, len(stem))), draw(BLOCKS))
        elif kind == "remove" and stem:
            stem.pop(draw(st.integers(0, len(stem) - 1)))
        elif kind == "reword" and stem and stem[0].get("kind") == "paragraph":
            stem[0] = paragraph(stem[0]["text"] + draw(LETTERS))
        elif kind == "option" and result["options"]:
            result["options"][0]["content"] = draw(st.lists(BLOCKS, max_size=3))
    return result


@PROP
@given(JSON_VALUES)
def test_property_equal_texts_have_no_changes(value: Any) -> None:
    assert diff_content(value, copy.deepcopy(value)) == []


@PROP
@given(JSON_VALUES, JSON_VALUES)
def test_property_replaying_the_changes_gives_the_new_text(old: Any, new: Any) -> None:
    changes = diff_content(old, new)
    assert canonical(apply_changes(old, changes)) == canonical(new)
    assert bool(changes) == (canonical(old) != canonical(new))


@PROP
@given(QUESTIONS, st.data())
def test_property_replaying_the_changes_on_an_edited_question(
    old: dict[str, Any], data: st.DataObject
) -> None:
    new = data.draw(edited(old))
    changes = diff_content(old, new)
    assert canonical(apply_changes(old, changes)) == canonical(new)
    assert all(isinstance(change, Change) for change in changes)


@PROP
@given(QUESTIONS, QUESTIONS)
def test_property_replaying_the_changes_on_two_unrelated_questions(
    old: dict[str, Any], new: dict[str, Any]
) -> None:
    assert canonical(apply_changes(old, diff_content(old, new))) == canonical(new)


@PROP
@given(st.text(max_size=60), st.text(max_size=60))
def test_property_segments_add_back_up_to_both_texts(old: str, new: str) -> None:
    segments = word_segments(old, new)
    assert "".join(s.text for s in segments if s.kind is not SegmentKind.INSERT) == old
    assert "".join(s.text for s in segments if s.kind is not SegmentKind.DELETE) == new
    assert all(s.text for s in segments)
    assert all(a.kind is not b.kind for a, b in pairwise(segments))


@PROP
@given(st.text(max_size=60))
def test_property_equal_texts_are_one_equal_segment(text: str) -> None:
    segments = word_segments(text, text)
    assert [(s.kind, s.text) for s in segments] == ([(SegmentKind.EQUAL, text)] if text else [])


# ---- the tests can fail -----------------------------------------------------------------------


def test_the_round_trip_rule_catches_a_diff_that_forgets_removals(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Break the diff on purpose (drop every REMOVE) and the rule must notice."""
    real = diff_module.diff_content

    def forgetful(old: Any, new: Any) -> list[Change]:
        return [change for change in real(old, new) if change.op is not Op.REMOVE]

    monkeypatch.setattr(diff_module, "diff_content", forgetful)
    old, new = (
        question([paragraph("First."), paragraph("Second.")]),
        question([paragraph("First.")]),
    )
    assert canonical(apply_changes(old, diff_module.diff_content(old, new))) != canonical(new)
