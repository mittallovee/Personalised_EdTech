"""What every operation gives the orchestrator (M5 design note §9).

An operation knows its own variables, its locked output schema, how to check an answer against the
database's facts, and how (and whether) to apply it. The orchestrator knows nothing about any one
operation: it runs the same ten steps for each.
"""

import json
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from qbank.core.auth import Principal
from qbank.core.errors import ValidationFailed
from qbank.modules.questions.public import Applied


class BadOutput(Exception):
    """The model's answer is not usable: wrong shape, or it names something that does not exist.
    The message says what was wrong in our own words and never repeats the answer."""


MOST_QUESTION_CHARS = 30_000


@dataclass(frozen=True, slots=True)
class RunBase:
    """The exact working revision a run read: a result is applied to that revision or to none."""

    question_id: UUID
    revision_id: UUID
    revision: int


# (session, principal, what the run was based on, checked output) -> how it ended
ApplyStep = Callable[[Session, Principal, RunBase, dict[str, Any]], Applied]


def question_json(content: dict[str, Any], leave_out: Iterable[str]) -> str:
    """The question as JSON text for a prompt, without the parts the operation must not see (the
    labels always; for solving also the answer and solution). Refuses one too large to send."""
    hidden = set(leave_out)
    text = json.dumps(
        {key: value for key, value in content.items() if key not in hidden},
        ensure_ascii=False,
        sort_keys=True,
    )
    if len(text) > MOST_QUESTION_CHARS:
        raise ValidationFailed(
            "This question is too large to send to the AI.", code="AI_QUESTION_TOO_LARGE"
        )
    return text


@dataclass(frozen=True, slots=True)
class Prepared:
    """One run's operation-specific parts."""

    values: dict[str, str]  # placeholder name -> text, each put in the prompt as data
    schema_name: str
    schema: dict[str, Any]
    max_output_tokens: int
    check: Callable[
        [dict[str, Any]], dict[str, Any]
    ]  # the answer -> the checked output, or BadOutput
    before: dict[str, Any] = field(
        default_factory=dict
    )  # what the output would replace, for the screen
    apply: ApplyStep | None = None  # None: a suggestion, applied only by an explicit click
