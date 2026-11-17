"""T39 (unit): the key two exact duplicates share, and what makes two questions different."""

import copy
from typing import Any

from hypothesis import given, settings
from hypothesis import strategies as st

from qbank.modules.questions.duplicate_key import duplicate_key

settings.register_profile("duplicate_key", max_examples=300, deadline=None)
settings.load_profile("duplicate_key")


def question() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "question_type": "SCQ",
        "language": "en",
        "stem": [
            {"kind": "paragraph", "text": "A block slides down a smooth incline. Find \\(a\\)."},
            {"kind": "equation", "format": "latex", "source": r"a = g \sin\theta"},
        ],
        "options": [
            {"id": "A", "content": [{"kind": "paragraph", "text": "5 m/s^2"}]},
            {"id": "B", "content": [{"kind": "paragraph", "text": "10 m/s^2"}]},
            {"id": "C", "content": [{"kind": "paragraph", "text": "2 m/s^2"}]},
            {"id": "D", "content": [{"kind": "paragraph", "text": "0"}]},
        ],
        "answer": {"option_id": "A"},
        "solution": [{"kind": "paragraph", "text": "Resolve gravity along the incline."}],
        "metadata": {"difficulty": 3},
    }


def changed(**edit: Any) -> dict[str, Any]:
    content = question()
    content.update(copy.deepcopy(edit))
    return content


KEY = duplicate_key(question())


def test_a_question_has_a_key_of_64_hex_characters() -> None:
    assert KEY is not None and len(KEY) == 64 and int(KEY, 16) >= 0


def test_case_and_spacing_of_the_prose_do_not_make_a_new_question() -> None:
    content = question()
    content["stem"][0]["text"] = "  a BLOCK   slides down a\nsmooth incline.  Find \\(a\\). "
    content["options"][1]["content"][0]["text"] = "10  M/S^2"
    assert duplicate_key(content) == KEY


def test_the_solution_the_video_and_the_labels_are_not_part_of_the_key() -> None:
    content = changed(
        solution=[{"kind": "paragraph", "text": "Another way."}],
        video_solution_url="https://example.com/v",
        metadata={"difficulty": 9, "subject_id": "x"},
        language="hi",
    )
    assert duplicate_key(content) == KEY


def test_an_equation_is_compared_as_written() -> None:
    capital = question()
    capital["stem"][1]["source"] = r"a = G \sin\theta"
    spaced = question()
    spaced["stem"][1]["source"] = r"a  =  g \sin\theta "
    assert duplicate_key(capital) != KEY  # a changed symbol is a different question
    assert duplicate_key(spaced) == KEY  # only the spacing changed


def test_an_equation_inside_a_paragraph_is_compared_as_written() -> None:
    content = question()
    content["stem"][0]["text"] = "A block slides down a smooth incline. Find \\(A\\)."
    assert duplicate_key(content) != KEY


def test_another_option_answer_or_format_is_a_different_question() -> None:
    option = question()
    option["options"][2]["content"][0]["text"] = "3 m/s^2"
    assert duplicate_key(option) != KEY
    assert duplicate_key(changed(answer={"option_id": "B"})) != KEY
    assert duplicate_key(changed(question_type="MULTI_CORRECT")) != KEY


def test_a_changed_word_is_a_different_question() -> None:
    content = question()
    content["stem"][0]["text"] = "A block slides down a rough incline. Find \\(a\\)."
    assert duplicate_key(content) != KEY


def test_a_picture_counts_by_the_stored_picture() -> None:
    def with_picture(asset: str) -> dict[str, Any]:
        content = question()
        content["stem"].append({"kind": "image", "asset_id": asset, "caption": "Ramp"})
        return content

    assert duplicate_key(with_picture("p1")) == duplicate_key(with_picture("p1"))
    assert duplicate_key(with_picture("p1")) != duplicate_key(with_picture("p2"))


def test_an_empty_stem_has_no_key() -> None:
    assert duplicate_key({"stem": []}) is None
    assert duplicate_key({"stem": [{"kind": "paragraph", "text": "   "}]}) is None
    assert duplicate_key(None) is None


json_values = st.recursive(
    st.none() | st.booleans() | st.integers() | st.text(max_size=12),
    lambda inner: (
        st.lists(inner, max_size=4)
        | st.dictionaries(
            st.sampled_from(
                [
                    "kind",
                    "text",
                    "source",
                    "stem",
                    "options",
                    "id",
                    "content",
                    "answer",
                    "rows",
                    "items",
                    "mapping",
                    "asset_id",
                    "question_type",
                ]
            ),
            inner,
            max_size=6,
        )
    ),
    max_leaves=30,
)


@given(json_values)
def test_any_content_gives_a_key_or_none_and_never_an_error(value: object) -> None:
    key = duplicate_key(value)
    assert key is None or len(key) == 64
    assert duplicate_key(value) == key  # the same content, the same key
