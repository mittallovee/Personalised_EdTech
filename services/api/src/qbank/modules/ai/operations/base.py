"""What every operation gives the orchestrator (M5 design note §9).

An operation knows its own variables, its locked output schema, how to check an answer against the
database's facts, and how (and whether) to apply it. The orchestrator knows nothing about any one
operation: it runs the same ten steps for each.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from qbank.core.auth import Principal
from qbank.modules.questions.public import Applied, QuestionForAi


class BadOutput(Exception):
    """The model's answer is not usable: wrong shape, or it names something that does not exist.
    The message says what was wrong in our own words and never repeats the answer."""


# (session, principal, question, checked output) -> how it ended
ApplyStep = Callable[[Session, Principal, QuestionForAi, dict[str, Any]], Applied]


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
    apply: ApplyStep | None = None  # None: the result is only ever a suggestion
