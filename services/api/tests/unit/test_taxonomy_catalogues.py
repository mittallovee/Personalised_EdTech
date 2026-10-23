"""M3 PR 2a: the fixed lists (languages, Bloom, difficulty guide) and how names are compared."""

import pytest

from qbank.core.errors import ValidationFailed
from qbank.modules.taxonomy.catalogues import (
    BLOOM_LEVELS,
    DIFFICULTY_GUIDE,
    LANGUAGE_TAGS,
    LANGUAGES,
    name_key,
)


def test_the_seven_question_languages_start_with_english() -> None:
    assert [language.tag for language in LANGUAGES] == ["en", "hi", "gu", "bn", "mr", "te", "ta"]
    assert {language.tag for language in LANGUAGES} == LANGUAGE_TAGS


def test_bloom_levels_are_the_six_in_order() -> None:
    assert [level.key for level in BLOOM_LEVELS] == [
        "REMEMBER",
        "UNDERSTAND",
        "APPLY",
        "ANALYZE",
        "EVALUATE",
        "CREATE",
    ]


def test_the_difficulty_guide_covers_one_to_ten_once() -> None:
    assert [item.level for item in DIFFICULTY_GUIDE] == list(range(1, 11))
    assert all(item.meaning for item in DIFFICULTY_GUIDE)


@pytest.mark.parametrize(
    ("a", "b"),
    [
        ("Newton's Laws", "newton's  laws"),
        ("  Kinematics ", "KINEMATICS"),
        ("Class\u00a011", "class 11"),  # a non-breaking space is a space
        ("\uff23\uff2c\uff21\uff33\uff33 \uff11\uff11", "class 11"),  # full-width forms fold
        ("Straße", "STRASSE"),
    ],
)
def test_names_that_differ_only_in_case_or_spacing_compare_equal(a: str, b: str) -> None:
    assert name_key(a) == name_key(b)


@pytest.mark.parametrize(
    ("a", "b"),
    [("Class 11", "Class 12"), ("Work, Energy", "Work Energy"), ("Optics 1", "Optics I")],
)
def test_names_that_differ_in_letters_or_digits_stay_different(a: str, b: str) -> None:
    assert name_key(a) != name_key(b)


def test_a_name_that_grows_too_long_once_normalised_is_refused_in_plain_words() -> None:
    """200 "ffi" ligatures are 200 characters, but 600 once expanded to letters."""
    ligatures = "\ufb03" * 200

    with pytest.raises(ValidationFailed) as raised:
        name_key(ligatures)

    assert raised.value.code == "NAME_TOO_LONG"


def test_a_long_name_that_stays_short_enough_is_accepted() -> None:
    assert len(name_key("x" * 200)) == 200
    assert len(name_key("\ufb03" * 133)) == 399  # 133 ligatures become 399 letters
