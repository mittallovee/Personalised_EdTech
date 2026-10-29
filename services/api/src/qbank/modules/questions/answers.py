"""Options and answers for SCQ, multiple correct, integer, single digit and numerical (D-01, D-02).

Rules are spec-v1's question types; the numbers are defaults in ``Rules`` (D-03).

- No floats anywhere. Integers are JSON integers (a boolean is not one). Numerical values are
  decimal strings with exactly two decimals; more than two are *kept and flagged*, never rounded.
- No unit field on a numerical answer: units live in the stem, equations or solution.
"""

import re
from decimal import Decimal

from qbank.modules.questions.blocks import as_dict, check_blocks, has_content
from qbank.modules.questions.findings import Findings, at_index, at_key
from qbank.modules.questions.rules import Rules

_ID = re.compile(r"[A-Za-z0-9_-]{1,20}")
# Longest numerical text looked at, so a huge string is never turned into a number.
_MAX_NUMBER_CHARS = 30
_NUMBER = re.compile(r"(-?)(\d+)(?:\.(\d+))?")


def is_id(value: object) -> bool:
    """An option, item or statement id: 1 to 20 letters, digits, ``_`` or ``-``."""
    return isinstance(value, str) and _ID.fullmatch(value) is not None


def is_whole_number(value: object) -> bool:
    """A JSON integer. ``True`` and ``False`` are not numbers here, and neither is ``3.0``."""
    return isinstance(value, int) and not isinstance(value, bool)


def check_options(content: dict[str, object], rules: Rules, out: Findings) -> list[str] | None:
    """Check the four options of an SCQ or multiple-correct question.

    Returns the option ids that can be answered with, or ``None`` when there are no usable options
    yet (then an answer cannot be checked against them).
    """
    options = content.get("options")
    if options is None:
        out.incomplete(
            "options", "OPTIONS_MISSING", f"Add the {rules.option_count} answer options."
        )
        return None
    if not isinstance(options, list):
        out.error("options", "OPTIONS_NOT_LIST", "The options must be a list.")
        return None
    if len(options) < rules.option_count:
        out.incomplete(
            "options",
            "OPTIONS_COUNT",
            f"This needs exactly {rules.option_count} options; it has {len(options)}.",
        )
    elif len(options) > rules.option_count:
        out.error(
            "options",
            "OPTIONS_COUNT",
            f"This needs exactly {rules.option_count} options; it has {len(options)}.",
        )
    ids: list[str] = []
    for index, option in enumerate(options[: rules.option_count + 1]):
        where = at_index("options", index)
        obj = as_dict(option)
        if obj is None:
            out.error(
                where, "OPTION_NOT_OBJECT", "An option must be an object with an id and content."
            )
            continue
        for key in obj:
            if key not in ("id", "content"):
                out.error(at_key(where, str(key)), "UNKNOWN_FIELD", f"An option has no '{key}'.")
        option_id = obj.get("id")
        if not isinstance(option_id, str) or not is_id(option_id):
            out.error(
                at_key(where, "id"),
                "OPTION_ID_INVALID",
                "An option id is 1 to 20 letters, digits, '_' or '-' (for example A).",
            )
        elif option_id in ids:
            out.error(
                at_key(where, "id"), "OPTION_ID_DUPLICATE", f"Two options have the id {option_id}."
            )
        else:
            ids.append(option_id)
        content_where = at_key(where, "content")
        blocks = obj.get("content")
        if blocks is not None:
            check_blocks(blocks, content_where, rules, out)
        if blocks is None or (isinstance(blocks, list) and not has_content(blocks)):
            out.incomplete(content_where, "OPTION_EMPTY", "This option has no content yet.")
    return ids


def check_answer_fields(
    answer: dict[str, object], allowed: frozenset[str], out: Findings, message: str
) -> None:
    for key in answer:
        if key not in allowed:
            out.error(at_key("answer", str(key)), "ANSWER_FIELD_UNKNOWN", message.format(key=key))


def check_scq_answer(answer: object, option_ids: list[str] | None, out: Findings) -> None:
    obj = as_dict(answer)
    if obj is None:
        out.error("answer", "ANSWER_SHAPE", 'The answer must look like {"option_id": "B"}.')
        return
    check_answer_fields(
        obj, frozenset({"option_id"}), out, "A single-choice answer has no '{key}'."
    )
    chosen = obj.get("option_id")
    if not isinstance(chosen, str):
        out.error(
            at_key("answer", "option_id"),
            "ANSWER_SHAPE",
            "Name the correct option by its id, like B.",
        )
    elif option_ids is not None and chosen not in option_ids:
        out.error(
            at_key("answer", "option_id"),
            "ANSWER_OPTION_UNKNOWN",
            f"The answer names option {chosen}, which does not exist.",
        )


def check_multi_answer(answer: object, option_ids: list[str] | None, out: Findings) -> None:
    obj = as_dict(answer)
    if obj is None:
        out.error("answer", "ANSWER_SHAPE", 'The answer must look like {"option_ids": ["A", "C"]}.')
        return
    check_answer_fields(
        obj, frozenset({"option_ids"}), out, "A multiple-correct answer has no '{key}'."
    )
    chosen = obj.get("option_ids")
    where = at_key("answer", "option_ids")
    if not isinstance(chosen, list):
        out.error(where, "ANSWER_SHAPE", "Name the correct options as a list of ids, like [A, C].")
        return
    if not chosen:
        out.error(where, "ANSWER_EMPTY", "At least one correct option is required.")
        return
    seen: set[str] = set()
    for index, item in enumerate(chosen):
        item_path = at_index(where, index)
        if not isinstance(item, str):
            out.error(item_path, "ANSWER_SHAPE", "Each correct option is named by its id, like A.")
        elif item in seen:
            out.error(item_path, "ANSWER_OPTION_DUPLICATE", f"Option {item} is named twice.")
        else:
            seen.add(item)
            if option_ids is not None and item not in option_ids:
                out.error(
                    item_path,
                    "ANSWER_OPTION_UNKNOWN",
                    f"The answer names option {item}, which does not exist.",
                )


def check_whole_number_answer(
    answer: object, low: int, high: int, label: str, out: Findings
) -> None:
    obj = as_dict(answer)
    if obj is None:
        out.error("answer", "ANSWER_SHAPE", 'The answer must look like {"value": 5}.')
        return
    check_answer_fields(obj, frozenset({"value"}), out, f"A {label} answer has no '{{key}}'.")
    value = obj.get("value")
    where = at_key("answer", "value")
    if not is_whole_number(value):
        out.error(
            where, "ANSWER_NOT_INTEGER", f"The {label} key must be a whole number, no fraction."
        )
    elif not isinstance(value, int) or not low <= value <= high:
        out.error(where, "ANSWER_OUT_OF_RANGE", f"The {label} key must be from {low} to {high}.")


def _number(value: object, path: str, rules: Rules, out: Findings) -> Decimal | None:
    """Read a numerical key written as text; ``None`` when it cannot be read as a number."""
    if not isinstance(value, str):
        out.error(
            path, "NUMERIC_NOT_TEXT", 'Write the number as text with two decimals, like "9.80".'
        )
        return None
    match = _NUMBER.fullmatch(value) if len(value) <= _MAX_NUMBER_CHARS else None
    if match is None:
        out.error(
            path, "NUMERIC_FORMAT_INVALID", 'Write the number with two decimals, like "9.80".'
        )
        return None
    decimals = match.group(3) or ""
    if len(decimals) < 2:
        out.error(path, "NUMERIC_FORMAT_INVALID", 'Write exactly two decimals, like "9.80".')
        return None
    number = Decimal(value)
    if match.group(1) and number == 0:
        out.error(path, "NUMERIC_FORMAT_INVALID", 'Write zero as "0.00", without a minus sign.')
        return None
    if len(decimals) > 2:
        # Kept as written, never rounded: the draft saves and publication stays blocked.
        out.error(
            path,
            "NUMERIC_TOO_MANY_DECIMALS",
            "More than two decimal places. The value is kept as written (not rounded) until "
            "someone decides what the key should be.",
        )
    if number < rules.numeric_min or number > rules.numeric_max:
        out.error(
            path,
            "ANSWER_OUT_OF_RANGE",
            f"The numerical key must be from {rules.numeric_min} to {rules.numeric_max}.",
        )
    return number


def check_numerical_answer(answer: object, rules: Rules, out: Findings) -> None:
    obj = as_dict(answer)
    if obj is None:
        out.error(
            "answer",
            "ANSWER_SHAPE",
            'The answer must look like {"mode": "exact", "value": "9.80"} or '
            '{"mode": "range", "lower": "9.79", "upper": "9.81"}.',
        )
        return
    mode = obj.get("mode")
    if mode == "exact":
        fields = frozenset({"mode", "value"})
    elif mode == "range":
        fields = frozenset({"mode", "lower", "upper"})
    else:
        out.error(
            at_key("answer", "mode"),
            "NUMERIC_MODE_INVALID",
            "Say whether the key is an exact value or one range: mode 'exact' or 'range'.",
        )
        return
    for key in obj:
        if key in fields:
            continue
        if str(key).lower() in ("unit", "units"):
            out.error(
                at_key("answer", str(key)),
                "ANSWER_UNIT_NOT_ALLOWED",
                "A numerical answer has no unit field. Write the unit in the question or solution.",
            )
        else:
            out.error(
                at_key("answer", str(key)),
                "ANSWER_FIELD_UNKNOWN",
                f"A {mode} numerical answer has no '{key}'.",
            )
    if mode == "exact":
        if "value" not in obj:
            out.incomplete(
                at_key("answer", "value"), "NUMERIC_VALUE_MISSING", "Give the exact value."
            )
        else:
            _number(obj["value"], at_key("answer", "value"), rules, out)
        return
    ends: list[Decimal | None] = []
    for end in ("lower", "upper"):
        if end not in obj:
            out.incomplete(
                at_key("answer", end), "NUMERIC_VALUE_MISSING", f"Give the {end} end of the range."
            )
            ends.append(None)
        else:
            ends.append(_number(obj[end], at_key("answer", end), rules, out))
    lower, upper = ends
    if lower is not None and upper is not None and lower > upper:
        out.error(
            "answer",
            "NUMERIC_RANGE_REVERSED",
            "The lower end of the range must not be above the upper end.",
        )
