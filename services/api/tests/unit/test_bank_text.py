"""F-03 (unit): the plain text of a question that the bank's search reads.

The extractor never raises and never trusts: whatever the author saved, the result is text, within
its cap, in a bounded amount of work.
"""

import time
import unicodedata

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from qbank.modules.questions.bank_text import MAX_TEXT, PREVIEW_LENGTH, bank_text

settings.register_profile("bank_text", max_examples=300, deadline=None)
settings.load_profile("bank_text")


def para(text: str) -> dict[str, str]:
    return {"kind": "paragraph", "text": text}


def test_the_text_is_the_stem_then_the_other_parts_then_the_solution() -> None:
    content = {
        "stem": [
            para("A block slides."),
            {"kind": "equation", "format": "latex", "source": "v=u+at"},
        ],
        "assertion": [para("Friction opposes motion.")],
        "reason": [para("It acts against the sliding.")],
        "statements": [{"id": "S1", "content": [para("Statement one")]}],
        "left": [{"id": "L1", "content": [para("Left item")]}],
        "right": [{"id": "R1", "content": [para("Right item")]}],
        "options": [
            {"id": "A", "content": [para("Option A text")]},
            {"id": "B", "mapping": {"L1": ["R1"]}},  # a matching option holds ids, not text
        ],
        "solution": [para("Use Newton's second law.")],
    }
    assert bank_text(content).stem_text == (
        "A block slides. v=u+at Friction opposes motion. It acts against the sliding."
        " Statement one Left item Right item Option A text Use Newton's second law."
    )


def test_a_picture_adds_its_caption_and_description_and_a_table_its_cells() -> None:
    content = {
        "stem": [
            {"kind": "image", "asset_id": "x", "caption": "Inclined plane", "alt_text": "A ramp"},
            {
                "kind": "table",
                "rows": [[[para("mass")], [para("2 kg")]], [[para("g")], [para("10")]]],
            },
            {"kind": "list", "ordered": False, "items": [[para("first")], [para("second")]]},
        ]
    }
    assert bank_text(content).stem_text == "Inclined plane A ramp mass 2 kg g 10 first second"


def test_the_preview_is_the_beginning_of_the_stem_only() -> None:
    content = {"stem": [para("x" * 500)], "solution": [para("hidden answer")]}
    result = bank_text(content)
    assert result.preview == "x" * PREVIEW_LENGTH
    assert "hidden answer" in result.stem_text and "hidden answer" not in result.preview


def test_whitespace_is_one_space_and_text_is_in_composed_form() -> None:
    decomposed = unicodedata.normalize("NFD", "café")
    result = bank_text({"stem": [para(f"  a\n\n b\t{decomposed}  "), para("")]})
    assert result.stem_text == "a b café"
    assert unicodedata.is_normalized("NFC", result.stem_text)


def test_a_nul_character_is_a_space() -> None:
    assert bank_text({"stem": [para("a\x00b")]}).stem_text == "a b"


def test_the_text_is_capped() -> None:
    content = {"stem": [para("word " * 10_000)], "solution": [para("tail")]}
    result = bank_text(content)
    assert len(result.stem_text) <= MAX_TEXT
    assert "tail" not in result.stem_text


@pytest.mark.parametrize("junk", [None, [], "text", 5, {"stem": "text"}, {"stem": [5, None, []]}])
def test_content_without_blocks_gives_no_text(junk: object) -> None:
    result = bank_text(junk)
    assert (result.stem_text, result.preview) == ("", "")


def test_blocks_nested_too_deep_are_ignored() -> None:
    inner: object = [para("deep")]
    for _ in range(6):
        inner = [{"kind": "list", "ordered": False, "items": [inner]}]
    assert bank_text({"stem": inner}).stem_text == ""


def test_a_huge_hostile_draft_is_read_in_bounded_time() -> None:
    empty_cell = [[[]] * 1000] * 1000  # a million empty cells
    started = time.monotonic()
    result = bank_text({"stem": [{"kind": "table", "rows": empty_cell}], "options": [None] * 10**6})
    assert time.monotonic() - started < 2
    assert result.stem_text == ""


json_values = st.recursive(
    st.none() | st.booleans() | st.integers() | st.floats(allow_nan=False) | st.text(max_size=20),
    lambda inner: (
        st.lists(inner, max_size=4)
        | st.dictionaries(
            st.sampled_from(
                [
                    "kind",
                    "text",
                    "source",
                    "caption",
                    "alt_text",
                    "rows",
                    "items",
                    "content",
                    "stem",
                    "options",
                    "solution",
                    "statements",
                    "left",
                    "right",
                    "assertion",
                    "reason",
                ]
            ),
            inner,
            max_size=6,
        )
    ),
    max_leaves=40,
)


@given(json_values)
def test_any_content_gives_text_within_the_cap_and_never_an_error(value: object) -> None:
    result = bank_text(value)
    assert len(result.stem_text) <= MAX_TEXT
    assert len(result.preview) <= PREVIEW_LENGTH
    assert "\x00" not in result.stem_text
    assert result.stem_text == " ".join(result.stem_text.split())
