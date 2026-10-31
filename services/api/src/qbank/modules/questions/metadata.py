"""The labels on a question: class to concepts, difficulty, Bloom, past-year details (D-15).

Only the shape is checked here. That an id exists in this coaching's catalogue, that the topic
belongs to the chapter and so on, needs the database and is checked in a later pull request.
Nothing raises: every problem becomes a finding.
"""

import re
from datetime import date
from uuid import UUID

from qbank.modules.questions.blocks import as_dict
from qbank.modules.questions.findings import Findings, at_index, at_key

# The taxonomy module owns the Bloom list and this module may not import it: a test compares them.
BLOOM_KEYS = ("REMEMBER", "UNDERSTAND", "APPLY", "ANALYZE", "EVALUATE", "CREATE")
DIFFICULTY_MIN, DIFFICULTY_MAX = 1, 10
EXAM_YEAR_MIN, EXAM_YEAR_MAX = 1950, 2100
MAX_SECONDARY_CONCEPTS = 20
MAX_SHORT_TEXT = 50
MAX_NOTE = 500

_PATH = "metadata"
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_KNOWN = frozenset(
    {
        "class_id",
        "subject_id",
        "chapter_id",
        "topic_id",
        "subtopic_id",
        "primary_concept_id",
        "secondary_concept_ids",
        "difficulty",
        "bloom_level",
        "is_pyq",
        "exam_id",
        "exam_year",
        "exam_date",
        "exam_shift",
        "paper_code",
        "source_id",
        "source_note",
    }
)
# (field, code when missing, what the person must choose). All are needed before publishing.
_REQUIRED_IDS = (
    ("class_id", "CLASS_MISSING", "Choose the class."),
    ("subject_id", "SUBJECT_MISSING", "Choose the subject."),
    ("chapter_id", "CHAPTER_MISSING", "Choose the chapter."),
    ("topic_id", "TOPIC_MISSING", "Choose the topic."),
    ("primary_concept_id", "PRIMARY_CONCEPT_MISSING", "Choose the main concept."),
)
_PYQ_ONLY = ("exam_id", "exam_year", "exam_date", "exam_shift", "paper_code")


def check_metadata(value: object, out: Findings) -> None:
    if value is None:
        out.incomplete(
            _PATH, "METADATA_MISSING", "Add the labels: class, subject, chapter, topic and so on."
        )
        return
    meta = as_dict(value)
    if meta is None:
        out.error(_PATH, "METADATA_NOT_OBJECT", "The metadata must be an object of labels.")
        return
    for key in meta:
        if key not in _KNOWN:
            out.error(at_key(_PATH, str(key)), "UNKNOWN_FIELD", f"The metadata has no '{key}'.")

    for field, missing, ask in _REQUIRED_IDS:
        _id(meta, field, out, required=(missing, ask))
    _id(meta, "subtopic_id", out)
    _secondary_concepts(meta, out)
    _difficulty(meta.get("difficulty"), out)
    _bloom(meta.get("bloom_level"), out)
    _past_year(meta, out)
    _id(meta, "source_id", out)
    _text(meta, "source_note", MAX_NOTE, out)


def _id(
    meta: dict[str, object],
    field: str,
    out: Findings,
    required: tuple[str, str] | None = None,
) -> None:
    value = meta.get(field)
    where = at_key(_PATH, field)
    if value is None:
        if required is not None:
            out.incomplete(where, *required)
    elif not _is_uuid(value):
        out.error(where, "METADATA_ID_INVALID", "This id is not valid; choose it from the list.")


def _is_uuid(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        UUID(value)
    except ValueError:
        return False
    return True


def _secondary_concepts(meta: dict[str, object], out: Findings) -> None:
    value = meta.get("secondary_concept_ids")
    where = at_key(_PATH, "secondary_concept_ids")
    if value is None:
        return
    if not isinstance(value, list):
        out.error(where, "SECONDARY_CONCEPTS_NOT_LIST", "The other concepts must be a list of ids.")
        return
    if len(value) > MAX_SECONDARY_CONCEPTS:
        out.error(
            where,
            "SECONDARY_CONCEPTS_COUNT",
            f"At most {MAX_SECONDARY_CONCEPTS} other concepts are allowed.",
        )
    primary = meta.get("primary_concept_id")
    seen: set[str] = set()
    for index, concept in enumerate(value[: MAX_SECONDARY_CONCEPTS + 1]):
        here = at_index(where, index)
        if not _is_uuid(concept) or not isinstance(concept, str):
            out.error(here, "METADATA_ID_INVALID", "This id is not valid; choose it from the list.")
        elif concept == primary:
            out.error(
                here,
                "SECONDARY_CONCEPT_IS_PRIMARY",
                "The main concept is already chosen; leave it out of the other concepts.",
            )
        elif concept in seen:
            out.error(here, "SECONDARY_CONCEPT_DUPLICATE", "This concept is listed twice.")
        else:
            seen.add(concept)


def _difficulty(value: object, out: Findings) -> None:
    where = at_key(_PATH, "difficulty")
    if value is None:
        out.incomplete(where, "DIFFICULTY_MISSING", "Choose the difficulty, from 1 to 10.")
    elif (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not DIFFICULTY_MIN <= value <= DIFFICULTY_MAX
    ):
        out.error(
            where,
            "DIFFICULTY_INVALID",
            f"The difficulty is a whole number from {DIFFICULTY_MIN} to {DIFFICULTY_MAX}.",
        )


def _bloom(value: object, out: Findings) -> None:
    where = at_key(_PATH, "bloom_level")
    if value is None:
        out.incomplete(where, "BLOOM_MISSING", "Choose the Bloom level.")
    elif not isinstance(value, str) or value not in BLOOM_KEYS:
        out.error(
            where, "BLOOM_INVALID", "The Bloom level must be one of: " + ", ".join(BLOOM_KEYS)
        )


def _past_year(meta: dict[str, object], out: Findings) -> None:
    flag = meta.get("is_pyq")
    is_pyq = False
    if flag is not None:
        if isinstance(flag, bool):
            is_pyq = flag
        else:
            out.error(at_key(_PATH, "is_pyq"), "PYQ_FLAG_INVALID", "This must be true or false.")
    _id(meta, "exam_id", out, required=("PYQ_EXAM_MISSING", "Choose the exam.") if is_pyq else None)
    year = _exam_year(meta.get("exam_year"), is_pyq, out)
    _exam_date(meta.get("exam_date"), year, out)
    _text(meta, "exam_shift", MAX_SHORT_TEXT, out)
    _text(meta, "paper_code", MAX_SHORT_TEXT, out)
    if not is_pyq and any(meta.get(field) is not None for field in _PYQ_ONLY):
        out.warning(
            at_key(_PATH, "is_pyq"),
            "PYQ_FIELDS_IGNORED",
            "Exam details are filled in but this is not marked as a past-year question.",
        )


def _exam_year(value: object, is_pyq: bool, out: Findings) -> int | None:
    where = at_key(_PATH, "exam_year")
    if value is None:
        if is_pyq:
            out.incomplete(where, "PYQ_YEAR_MISSING", "Enter the year of the exam.")
        return None
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not EXAM_YEAR_MIN <= value <= EXAM_YEAR_MAX
    ):
        out.error(
            where,
            "PYQ_YEAR_INVALID",
            f"The year is a whole number from {EXAM_YEAR_MIN} to {EXAM_YEAR_MAX}.",
        )
        return None
    return value


def _exam_date(value: object, year: int | None, out: Findings) -> None:
    if value is None:
        return
    where = at_key(_PATH, "exam_date")
    parsed: date | None = None
    if isinstance(value, str) and _DATE.fullmatch(value):
        try:
            parsed = date.fromisoformat(value)
        except ValueError:
            parsed = None
    if parsed is None:
        out.error(where, "EXAM_DATE_INVALID", "The date is written like 2024-01-27.")
    elif year is not None and parsed.year != year:
        out.error(where, "EXAM_DATE_YEAR_MISMATCH", f"This date is not in the year {year}.")


def _text(meta: dict[str, object], field: str, longest: int, out: Findings) -> None:
    value = meta.get(field)
    if value is None:
        return
    if not isinstance(value, str) or not value.strip() or len(value) > longest:
        out.error(
            at_key(_PATH, field),
            "METADATA_TEXT_INVALID",
            f"This must be text of 1 to {longest} characters, or left out.",
        )
