"""Check a question's content and return findings (M3 design note §5.2 to §5.4).

``validate_content`` never raises: whatever it is given, the answer is a list of findings, so an
incomplete or mistaken draft can always be saved and the person sees what to fix.

This pull request checks the envelope, the blocks, and the formats SCQ, multiple correct, integer,
single digit and numerical. The parts of matching, assertion-reason and multiple-statement
questions, the metadata and the passage context are checked in the next pull request.
"""

import json
import re

from qbank.modules.questions.answers import (
    check_multi_answer,
    check_numerical_answer,
    check_options,
    check_scq_answer,
    check_whole_number_answer,
)
from qbank.modules.questions.blocks import as_dict, check_blocks
from qbank.modules.questions.findings import Finding, Findings, at_key
from qbank.modules.questions.rules import DEFAULT_RULES, Rules

SCHEMA_VERSION = 1

SCQ = "SCQ"
MULTI_CORRECT = "MULTI_CORRECT"
INTEGER = "INTEGER"
SINGLE_DIGIT = "SINGLE_DIGIT"
NUMERICAL = "NUMERICAL"
MATCHING = "MATCHING"
ASSERTION_REASON = "ASSERTION_REASON"
MULTIPLE_STATEMENT = "MULTIPLE_STATEMENT"

# The eight concrete formats. The ninth, passage-based, is shared context pinned by a child
# question (``context``), not a format of its own.
QUESTION_TYPES = (
    SCQ,
    MULTI_CORRECT,
    INTEGER,
    SINGLE_DIGIT,
    NUMERICAL,
    MATCHING,
    ASSERTION_REASON,
    MULTIPLE_STATEMENT,
)

_COMMON_FIELDS = frozenset(
    {
        "schema_version",
        "question_type",
        "language",
        "stem",
        "answer",
        "solution",
        "video_solution_url",
        "metadata",
        "context",
    }
)
_OWN_FIELDS: dict[str, frozenset[str]] = {
    SCQ: frozenset({"options"}),
    MULTI_CORRECT: frozenset({"options"}),
    INTEGER: frozenset(),
    SINGLE_DIGIT: frozenset(),
    NUMERICAL: frozenset(),
    MATCHING: frozenset({"left", "right", "options"}),
    ASSERTION_REASON: frozenset({"assertion", "reason", "options"}),
    MULTIPLE_STATEMENT: frozenset({"statements", "options"}),
}
_LANGUAGE = re.compile(r"[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8})*")
_MAX_VIDEO_URL = 2_000


def validate_content(content: object, rules: Rules = DEFAULT_RULES) -> list[Finding]:
    """The findings for a question's content (an empty list means nothing is wrong)."""
    out = Findings()
    obj = as_dict(content)
    if obj is None:
        out.error("", "CONTENT_NOT_OBJECT", "The question content must be an object.")
        return out.items
    try:
        size = len(json.dumps(obj, ensure_ascii=False).encode("utf-8"))
    except TypeError, ValueError:
        out.error(
            "", "CONTENT_NOT_JSON", "The question content has a value that is not plain data."
        )
        return out.items
    if size > rules.revision_bytes:
        out.error(
            "",
            "CONTENT_TOO_LARGE",
            f"This question is {size // 1024} KB; the limit is {rules.revision_bytes // 1024} KB.",
        )
        return out.items  # a huge document is not walked further

    question_type = _check_envelope(obj, rules, out)
    if question_type is not None:
        _check_type(question_type, obj, rules, out)
    return out.items


def _check_envelope(obj: dict[str, object], rules: Rules, out: Findings) -> str | None:
    version = obj.get("schema_version")
    if version != SCHEMA_VERSION or isinstance(version, bool):
        out.error(
            "schema_version",
            "SCHEMA_VERSION_UNSUPPORTED",
            f"The content must have schema_version {SCHEMA_VERSION}.",
        )
    question_type = obj.get("question_type")
    if not isinstance(question_type, str) or question_type not in QUESTION_TYPES:
        out.error(
            "question_type",
            "QUESTION_TYPE_UNKNOWN",
            "The question type must be one of: " + ", ".join(QUESTION_TYPES) + ".",
        )
        known: str | None = None
    else:
        known = question_type

    allowed = _COMMON_FIELDS | _OWN_FIELDS.get(known or "", frozenset())
    if known is not None:
        for key in obj:
            if key not in allowed:
                out.error(
                    str(key),
                    "FIELD_NOT_ALLOWED",
                    f"A {known} question has no '{key}'.",
                )

    language = obj.get("language")
    if language is None:
        out.incomplete("language", "LANGUAGE_MISSING", "Choose the language of the question.")
    elif not isinstance(language, str) or _LANGUAGE.fullmatch(language) is None:
        out.error("language", "LANGUAGE_INVALID", "The language must be a code like en or hi.")

    stem = obj.get("stem")
    if stem is None or stem == []:
        out.incomplete("stem", "STEM_EMPTY", "Write the question.")
    else:
        check_blocks(stem, "stem", rules, out)

    solution = obj.get("solution")
    if solution is not None:
        check_blocks(solution, "solution", rules, out)

    video = obj.get("video_solution_url")
    if video is not None:
        _check_video_url(video, out)
    return known


def _check_video_url(video: object, out: Findings) -> None:
    where = at_key("", "video_solution_url")
    ok = (
        isinstance(video, str)
        and len(video) <= _MAX_VIDEO_URL
        and video.startswith(("https://", "http://"))
        and " " not in video
    )
    if not ok:
        out.error(
            where,
            "VIDEO_URL_INVALID",
            "The video link must be a web address starting with https://.",
        )


def _check_type(question_type: str, obj: dict[str, object], rules: Rules, out: Findings) -> None:
    option_ids: list[str] | None = None
    if question_type in (SCQ, MULTI_CORRECT):
        option_ids = check_options(obj, rules, out)

    answer = obj.get("answer")
    if answer is None:
        out.incomplete("answer", "ANSWER_MISSING", "Choose the correct answer.")
        return
    if question_type == SCQ:
        check_scq_answer(answer, option_ids, out)
    elif question_type == MULTI_CORRECT:
        check_multi_answer(answer, option_ids, out)
    elif question_type == INTEGER:
        check_whole_number_answer(answer, rules.integer_min, rules.integer_max, "integer", out)
    elif question_type == SINGLE_DIGIT:
        check_whole_number_answer(answer, rules.digit_min, rules.digit_max, "single-digit", out)
    elif question_type == NUMERICAL:
        check_numerical_answer(answer, rules, out)
    # MATCHING, ASSERTION_REASON and MULTIPLE_STATEMENT: checked in the next pull request.
