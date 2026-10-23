"""The fixed lists a question refers to (M3 design note §4.3).

They are the same for every coaching and live in code, not in the database: the languages of the
first release, the Bloom levels and the written guide to the 1-10 difficulty scale. Questions store
the stable ``key`` or ``tag``; the labels here are for people and may be reworded without touching
saved questions.
"""

import re
import unicodedata
from dataclasses import dataclass

from qbank.core.errors import ValidationFailed


@dataclass(frozen=True, slots=True)
class Language:
    tag: str  # BCP 47 primary language subtag
    english_name: str
    native_name: str


# The question languages of the first release (spec-v1 LANGUAGE_SUPPORT). English comes first
# because every syllabus item has an English name.
LANGUAGES: tuple[Language, ...] = (
    Language("en", "English", "English"),
    Language("hi", "Hindi", "हिन्दी"),
    Language("gu", "Gujarati", "ગુજરાતી"),
    Language("bn", "Bengali", "বাংলা"),
    Language("mr", "Marathi", "मराठी"),
    Language("te", "Telugu", "తెలుగు"),
    Language("ta", "Tamil", "தமிழ்"),
)
LANGUAGE_TAGS = frozenset(language.tag for language in LANGUAGES)


@dataclass(frozen=True, slots=True)
class BloomLevel:
    key: str
    label: str


BLOOM_LEVELS: tuple[BloomLevel, ...] = (
    BloomLevel("REMEMBER", "Remember"),
    BloomLevel("UNDERSTAND", "Understand"),
    BloomLevel("APPLY", "Apply"),
    BloomLevel("ANALYZE", "Analyze"),
    BloomLevel("EVALUATE", "Evaluate"),
    BloomLevel("CREATE", "Create"),
)


@dataclass(frozen=True, slots=True)
class DifficultyLevel:
    level: int
    meaning: str


# Draft wording for the owner's approval (M3 design note, appendix).
DIFFICULTY_GUIDE: tuple[DifficultyLevel, ...] = (
    DifficultyLevel(1, "Direct recall of a definition, unit or formula; no calculation"),
    DifficultyLevel(2, "One formula, one step, numbers given directly"),
    DifficultyLevel(3, "One concept, simple calculation, standard textbook example"),
    DifficultyLevel(4, "One concept with a short derivation or unit conversion"),
    DifficultyLevel(
        5, "Two linked ideas or a multi-step calculation; typical board-exam difficulty"
    ),
    DifficultyLevel(6, "Typical JEE Main / NEET question: two concepts, a diagram, some algebra"),
    DifficultyLevel(7, "Hard JEE Main: three steps or a less familiar situation"),
    DifficultyLevel(
        8, "Easy JEE Advanced: several concepts, careful reasoning or non-obvious setup"
    ),
    DifficultyLevel(
        9, "Hard JEE Advanced: long chain of reasoning, edge cases, heavy algebra or calculus"
    ),
    DifficultyLevel(
        10, "Olympiad level: novel situation, deep insight needed; very few students solve it"
    ),
)

_SPACES = re.compile(r"\s+")


# The most a normalised name may be (the database column holds this many characters).
MAX_NAME_KEY_LENGTH = 400


def name_key(name: str) -> str:
    """A name in the form used to compare names: Unicode-normalised, case-folded, single spaces.

    "Newton's  Laws" and "newton's laws" compare equal; it never merges names that differ in
    letters or digits. Normalising can make a name longer (a ligature becomes three letters), so
    a name that is short enough as typed can still be refused here, with a clear message.
    """
    key = _SPACES.sub(" ", unicodedata.normalize("NFKC", name)).strip().casefold()
    if len(key) > MAX_NAME_KEY_LENGTH:
        raise ValidationFailed(
            "This name is too long once its special characters are written out in full."
            " Please shorten it.",
            code="NAME_TOO_LONG",
        )
    return key
