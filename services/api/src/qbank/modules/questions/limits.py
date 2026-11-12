"""The answer limits a coaching can change (M3 design note §5.4, D-03).

Only the numbers that say what an answer may be are settings: how many items a matching or
multiple-statement question has, and the range of an integer, single-digit or numerical key. The
limits that keep storage and rendering safe (an equation's length, the size of a revision...) are
not settings: they stay in ``Rules`` for everyone.

A coaching sets its own values, and may override some of them for one exam (a JEE Advanced question
may allow what a JEE Main one does not). A question is checked with the built-in values, then the
coaching's, then those of the exam in its labels. A changed limit never rewrites old revisions; it
only changes what the findings say. All of this is pure: the service does the database reading.
"""

import re
from collections.abc import Mapping
from dataclasses import dataclass, replace
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from qbank.modules.questions.rules import Rules


@dataclass(frozen=True, slots=True)
class Field:
    kind: Literal["int", "decimal"]
    low: int | Decimal
    high: int | Decimal


_BIG = 999_999
_BIG_DECIMAL = Decimal("999999.99")

# The settings, and the widest range each may take. Both ends are bounds on the setting itself,
# not on a question's answer: a coaching may narrow or widen within them.
FIELDS: dict[str, Field] = {
    "matching_min_items": Field("int", 2, 10),
    "matching_max_items": Field("int", 2, 10),
    "statements_min": Field("int", 2, 10),
    "statements_max": Field("int", 2, 10),
    "integer_min": Field("int", -_BIG, _BIG),
    "integer_max": Field("int", -_BIG, _BIG),
    "digit_min": Field("int", 0, 9),
    "digit_max": Field("int", 0, 9),
    "numeric_min": Field("decimal", -_BIG_DECIMAL, _BIG_DECIMAL),
    "numeric_max": Field("decimal", -_BIG_DECIMAL, _BIG_DECIMAL),
}

# Pairs that must leave at least one allowed value.
_PAIRS = (
    ("matching_min_items", "matching_max_items"),
    ("statements_min", "statements_max"),
    ("integer_min", "integer_max"),
    ("digit_min", "digit_max"),
    ("numeric_min", "numeric_max"),
)

# A decimal is written as text with at most two decimals, never as a float: "999.00".
_DECIMAL = re.compile(r"-?[0-9]{1,6}(\.[0-9]{1,2})?")


@dataclass(frozen=True, slots=True)
class LimitProblem:
    path: str
    code: str
    message: str


@dataclass(frozen=True, slots=True)
class Overrides:
    """What a coaching changed: its own values, and the values of particular exams."""

    defaults: Mapping[str, Any]
    exams: Mapping[UUID, Mapping[str, Any]]


def _value(name: str, raw: object) -> int | Decimal | None:
    """The setting as a number, or None when ``raw`` is not a usable value for it."""
    field = FIELDS[name]
    if field.kind == "int":
        if not isinstance(raw, int) or isinstance(raw, bool):
            return None
        number: int | Decimal = raw
    else:
        if not isinstance(raw, str) or _DECIMAL.fullmatch(raw) is None:
            return None
        number = Decimal(raw)
    return number if field.low <= number <= field.high else None


def _usable(values: object) -> dict[str, int | Decimal]:
    """The settings in ``values`` that are known and valid, as numbers."""
    if not isinstance(values, Mapping):
        return {}
    found: dict[str, int | Decimal] = {}
    for name, raw in values.items():
        if isinstance(name, str) and name in FIELDS:
            number = _value(name, raw)
            if number is not None:
                found[name] = number
    return found


def _apply(base: Rules, values: Mapping[str, int | Decimal]) -> Rules:
    return replace(base, **values)  # type: ignore[arg-type]


def effective_rules(base: Rules, overrides: Overrides, exam: UUID | None) -> Rules:
    """The rules for a question: built-in, then the coaching's values, then its exam's."""
    rules = _apply(base, _usable(overrides.defaults))
    if exam is not None and exam in overrides.exams:
        rules = _apply(rules, _usable(overrides.exams[exam]))
    return rules


def _layer_problems(path: str, values: object) -> list[LimitProblem]:
    if not isinstance(values, Mapping):
        return [LimitProblem(path, "SETTINGS_NOT_AN_OBJECT", "These settings must be an object.")]
    problems: list[LimitProblem] = []
    for name, raw in values.items():
        where = f"{path}.{name}"
        if not isinstance(name, str) or name not in FIELDS:
            problems.append(
                LimitProblem(where, "SETTING_UNKNOWN", f"There is no setting '{name}'.")
            )
            continue
        field = FIELDS[name]
        if _value(name, raw) is not None:
            continue
        number = _read(name, raw)
        if number is None:
            what = (
                "a whole number"
                if field.kind == "int"
                else 'a number written as text with at most two decimals, like "999.00"'
            )
            problems.append(LimitProblem(where, "SETTING_NOT_A_NUMBER", f"{name} must be {what}."))
        else:
            problems.append(
                LimitProblem(
                    where,
                    "SETTING_OUT_OF_RANGE",
                    f"{name} must be from {field.low} to {field.high}.",
                )
            )
    return problems


def _read(name: str, raw: object) -> int | Decimal | None:
    """The number in ``raw`` whether or not it is within the bounds (None if it is not a number)."""
    if FIELDS[name].kind == "int":
        return raw if isinstance(raw, int) and not isinstance(raw, bool) else None
    if isinstance(raw, str) and re.fullmatch(r"-?[0-9]{1,12}(\.[0-9]{1,2})?", raw):
        return Decimal(raw)
    return None


def _empty_range(rules: Rules) -> str | None:
    for low, high in _PAIRS:
        if getattr(rules, low) > getattr(rules, high):
            return f"{low} is above {high}, so nothing would be allowed."
    return None


def check_overrides(defaults: object, exams: object) -> list[LimitProblem]:
    """What is wrong with the settings an admin sent (an empty list means they can be saved)."""
    from qbank.modules.questions.rules import DEFAULT_RULES

    problems = _layer_problems("defaults", defaults)
    base = _apply(DEFAULT_RULES, _usable(defaults))
    message = _empty_range(base)
    if message is not None:
        problems.append(LimitProblem("defaults", "RANGE_EMPTY", message))
    if not isinstance(exams, Mapping):
        problems.append(
            LimitProblem("exams", "SETTINGS_NOT_AN_OBJECT", "The exam settings must be an object.")
        )
        return problems
    for key, values in exams.items():
        path = f"exams.{key}"
        if not isinstance(key, str) or _exam_id(key) is None:
            problems.append(LimitProblem(path, "EXAM_ID_INVALID", "This is not an exam's id."))
            continue
        layer = _layer_problems(path, values)
        problems.extend(layer)
        message = _empty_range(_apply(base, _usable(values)))
        if message is not None and not layer:
            problems.append(LimitProblem(path, "RANGE_EMPTY", message))
    return problems


def _exam_id(text: str) -> UUID | None:
    """An exam id in its standard spelling (lower case, with dashes), else None."""
    try:
        parsed = UUID(text)
    except ValueError:
        return None
    return parsed if str(parsed) == text else None


def normalise(defaults: object, exams: object) -> Overrides:
    """Overrides from stored JSON, leaving out whatever cannot be used (never raises)."""
    layers: dict[UUID, Mapping[str, Any]] = {}
    if isinstance(exams, Mapping):
        for key, values in exams.items():
            exam = _exam_id(key) if isinstance(key, str) else None
            if exam is not None and isinstance(values, Mapping):
                layers[exam] = _raw(values)
    return Overrides(_raw(defaults), layers)


def _raw(values: object) -> Mapping[str, Any]:
    """The valid entries of ``values``, kept as the JSON values they were stored as."""
    if not isinstance(values, Mapping):
        return {}
    return {
        name: raw
        for name, raw in values.items()
        if isinstance(name, str) and name in FIELDS and _value(name, raw) is not None
    }


def exam_of(content: object) -> UUID | None:
    """The exam named in a question's labels, if it is a readable id."""
    if not isinstance(content, Mapping):
        return None
    metadata = content.get("metadata")
    exam = metadata.get("exam_id") if isinstance(metadata, Mapping) else None
    if not isinstance(exam, str):
        return None
    try:
        return UUID(exam)
    except ValueError:
        return None
