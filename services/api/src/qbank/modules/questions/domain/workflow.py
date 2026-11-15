"""The review workflow of a question version, as one pure table (M4 design note §4, ADR-0020).

This is the only definition of which step may follow which state. It knows nothing about the
database, HTTP or people: the service asks it "may this state take this step, and what must the
person hold?", and the database trigger added in PR 4a-2 repeats the same pairs so a bug in code
cannot skip a step. Who holds what is decided in ``workflow_access.py``.
"""

from dataclasses import dataclass
from enum import StrEnum


class State(StrEnum):
    DRAFT = "DRAFT"
    IN_REVIEW = "IN_REVIEW"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"
    QC_PASSED = "QC_PASSED"
    APPROVED = "APPROVED"
    PUBLISHED = "PUBLISHED"


class Step(StrEnum):
    SUBMIT = "SUBMIT"
    RETURN = "RETURN"
    PASS_QC = "PASS_QC"  # noqa: S105 (a step name, not a password)
    APPROVE = "APPROVE"
    PUBLISH = "PUBLISH"
    WITHDRAW = "WITHDRAW"
    START_CORRECTION = "START_CORRECTION"


class Needs(StrEnum):
    """What a person must hold to take a step (a right, not a role: see ``workflow_access``)."""

    EDIT = "EDIT"  # may edit this question: its author, an admin, or the edit-others grant
    QC = "QC"
    APPROVE = "APPROVE"
    PUBLISH = "PUBLISH"


@dataclass(frozen=True, slots=True)
class Transition:
    state: State  # the state the version is in before the step
    step: Step
    result: State  # the state of the version that results (of the NEW version when new_version)
    needs: Needs
    new_version: bool = False  # True: the step leaves this version alone and starts version n+1


TRANSITIONS: tuple[Transition, ...] = (
    Transition(State.DRAFT, Step.SUBMIT, State.IN_REVIEW, Needs.EDIT),
    Transition(State.CHANGES_REQUESTED, Step.SUBMIT, State.IN_REVIEW, Needs.EDIT),
    Transition(State.IN_REVIEW, Step.RETURN, State.CHANGES_REQUESTED, Needs.QC),
    Transition(State.IN_REVIEW, Step.PASS_QC, State.QC_PASSED, Needs.QC),
    Transition(State.QC_PASSED, Step.APPROVE, State.APPROVED, Needs.APPROVE),
    # A late error has a way back without waiting for the author to withdraw (decision 3).
    Transition(State.QC_PASSED, Step.RETURN, State.CHANGES_REQUESTED, Needs.APPROVE),
    Transition(State.APPROVED, Step.RETURN, State.CHANGES_REQUESTED, Needs.PUBLISH),
    Transition(State.APPROVED, Step.PUBLISH, State.PUBLISHED, Needs.PUBLISH),
    Transition(State.IN_REVIEW, Step.WITHDRAW, State.DRAFT, Needs.EDIT),
    Transition(State.QC_PASSED, Step.WITHDRAW, State.DRAFT, Needs.EDIT),
    Transition(State.APPROVED, Step.WITHDRAW, State.DRAFT, Needs.EDIT),
    Transition(State.PUBLISHED, Step.START_CORRECTION, State.DRAFT, Needs.EDIT, new_version=True),
)

_BY_PAIR: dict[tuple[State, Step], Transition] = {(t.state, t.step): t for t in TRANSITIONS}
_STEP_ORDER = {step: position for position, step in enumerate(Step)}

# While a version is in review the text is frozen: the editor is read-only and the server refuses a
# save (QUESTION_NOT_EDITABLE). Editing during review means Withdraw first (decision 2).
EDITABLE_STATES = frozenset({State.DRAFT, State.CHANGES_REQUESTED})
# Work in progress is private to its author, admins and the edit-others grant; from submit on, every
# member of the coaching may read it (decision 4).
PRIVATE_STATES = frozenset({State.DRAFT, State.CHANGES_REQUESTED})


def find_transition(state: State, step: Step) -> Transition | None:
    """The transition a step makes from a state, or None when the state does not allow the step."""
    return _BY_PAIR.get((state, step))


def allowed_steps(state: State) -> tuple[Step, ...]:
    """The steps a state allows, in ``Step`` order (the API reports them as ``details.allowed``)."""
    steps = [t.step for t in TRANSITIONS if t.state is state]
    return tuple(sorted(steps, key=_STEP_ORDER.__getitem__))


class ReturnReason(StrEnum):
    """Why a question is sent back. Stable codes, so the web can show them and later count them."""

    ANSWER_WRONG = "ANSWER_WRONG"
    STATEMENT_UNCLEAR = "STATEMENT_UNCLEAR"
    OPTIONS_FLAWED = "OPTIONS_FLAWED"
    SOLUTION_WRONG = "SOLUTION_WRONG"
    LABELS_WRONG = "LABELS_WRONG"
    DIFFICULTY_OR_BLOOM_WRONG = "DIFFICULTY_OR_BLOOM_WRONG"
    DUPLICATE = "DUPLICATE"
    FORMATTING = "FORMATTING"
    OTHER = "OTHER"


# Plain text, shown to the author as text and never as markup (§4.3).
RETURN_REASON_LABELS: dict[ReturnReason, str] = {
    ReturnReason.ANSWER_WRONG: "The answer is wrong or does not match the question",
    ReturnReason.STATEMENT_UNCLEAR: "The question text is unclear, incomplete or ambiguous",
    ReturnReason.OPTIONS_FLAWED: "An option is wrong, repeated, or gives the answer away",
    ReturnReason.SOLUTION_WRONG: "The solution is wrong or skips steps",
    ReturnReason.LABELS_WRONG: "Class, subject, chapter, topic or concept is wrong",
    ReturnReason.DIFFICULTY_OR_BLOOM_WRONG: "The difficulty or Bloom level does not fit",
    ReturnReason.DUPLICATE: "This looks like a copy of another question",
    ReturnReason.FORMATTING: "Equations, pictures or layout need fixing",
    ReturnReason.OTHER: "Something else (explained in the note)",
}
