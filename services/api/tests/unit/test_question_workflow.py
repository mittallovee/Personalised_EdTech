"""M4 exit test T33 (unit part): the review workflow of a question version, as one table.

The expected values below are written out by hand from the M4 design note (§4.1 and §5), not
computed with the code under test, so a wrong edit to the state machine or to the access rules
shows up here.
The database trigger that repeats the allowed pairs is tested from this same table in PR 4a-2.
"""

from uuid import UUID

import pytest

from qbank.core.auth import Principal
from qbank.core.ids import new_id
from qbank.modules.questions.domain.workflow import (
    EDITABLE_STATES,
    PRIVATE_STATES,
    RETURN_REASON_LABELS,
    TRANSITIONS,
    Needs,
    ReturnReason,
    State,
    Step,
    allowed_steps,
    find_transition,
)
from qbank.modules.questions.domain.workflow_access import may_take_step

COACHING = new_id()
AUTHOR_ID = new_id()

S = State
T = Step
N = Needs

# (from state, step) -> (state of the version afterwards, what the person must hold, new version?)
EXPECTED = {
    (S.DRAFT, T.SUBMIT): (S.IN_REVIEW, N.EDIT, False),
    (S.CHANGES_REQUESTED, T.SUBMIT): (S.IN_REVIEW, N.EDIT, False),
    (S.IN_REVIEW, T.RETURN): (S.CHANGES_REQUESTED, N.QC, False),
    (S.IN_REVIEW, T.PASS_QC): (S.QC_PASSED, N.QC, False),
    (S.QC_PASSED, T.APPROVE): (S.APPROVED, N.APPROVE, False),
    (S.QC_PASSED, T.RETURN): (S.CHANGES_REQUESTED, N.APPROVE, False),
    (S.APPROVED, T.RETURN): (S.CHANGES_REQUESTED, N.PUBLISH, False),
    (S.APPROVED, T.PUBLISH): (S.PUBLISHED, N.PUBLISH, False),
    (S.IN_REVIEW, T.WITHDRAW): (S.DRAFT, N.EDIT, False),
    (S.QC_PASSED, T.WITHDRAW): (S.DRAFT, N.EDIT, False),
    (S.APPROVED, T.WITHDRAW): (S.DRAFT, N.EDIT, False),
    # The published version stays as it is; the step makes a new version in DRAFT.
    (S.PUBLISHED, T.START_CORRECTION): (S.DRAFT, N.EDIT, True),
}


def test_the_states_and_steps_are_the_ones_in_the_note() -> None:
    assert {s.value for s in State} == {
        "DRAFT",
        "IN_REVIEW",
        "CHANGES_REQUESTED",
        "QC_PASSED",
        "APPROVED",
        "PUBLISHED",
    }
    assert {s.value for s in Step} == {
        "SUBMIT",
        "RETURN",
        "PASS_QC",
        "APPROVE",
        "PUBLISH",
        "WITHDRAW",
        "START_CORRECTION",
    }


@pytest.mark.parametrize("state", list(State))
@pytest.mark.parametrize("step", list(Step))
def test_every_state_and_step_pair_is_allowed_exactly_as_the_note_says(
    state: State, step: Step
) -> None:
    found = find_transition(state, step)
    if (state, step) not in EXPECTED:
        assert found is None
        return
    result, needs, new_version = EXPECTED[(state, step)]
    assert found is not None
    assert (found.result, found.needs, found.new_version) == (result, needs, new_version)


def test_the_list_of_transitions_has_no_extra_or_repeated_pair() -> None:
    pairs = [(t.state, t.step) for t in TRANSITIONS]
    assert len(pairs) == len(set(pairs))
    assert set(pairs) == set(EXPECTED)


@pytest.mark.parametrize("state", list(State))
def test_allowed_steps_lists_what_the_state_permits(state: State) -> None:
    expected = {step for (s, step) in EXPECTED if s == state}
    assert set(allowed_steps(state)) == expected
    assert list(allowed_steps(state)) == sorted(allowed_steps(state), key=list(Step).index)


def test_a_published_version_can_only_be_corrected() -> None:
    assert allowed_steps(State.PUBLISHED) == (Step.START_CORRECTION,)


def test_nothing_leads_back_into_published_except_publish() -> None:
    into_published = {(t.state, t.step) for t in TRANSITIONS if t.result is State.PUBLISHED}
    assert into_published == {(State.APPROVED, Step.PUBLISH)}


def test_only_draft_and_returned_questions_can_be_edited_and_are_private() -> None:
    in_progress = frozenset({State.DRAFT, State.CHANGES_REQUESTED})
    assert in_progress == EDITABLE_STATES
    assert in_progress == PRIVATE_STATES


# ---- Who may take a step (§5) -----------------------------------------------------------------


def person(
    role: str | None,
    *,
    user_id: UUID | None = None,
    grants: frozenset[str] = frozenset(),
    platform: bool = False,
    acting: bool = False,
) -> Principal:
    return Principal(
        user_id=user_id or new_id(),
        display_name="Someone",
        is_platform_admin=platform,
        organization_id=COACHING if role else None,
        role=role,
        acting_organization_id=COACHING if acting else None,
        grants=grants,
    )


# What each kind of person holds on a question written by AUTHOR_ID.
HOLDS = {
    "author, no grants": (person("FACULTY", user_id=AUTHOR_ID), {N.EDIT}),
    "other faculty, no grants": (person("FACULTY"), set()),
    "faculty with EDIT_OTHERS": (person("FACULTY", grants=frozenset({"EDIT_OTHERS"})), {N.EDIT}),
    "faculty with QC": (person("FACULTY", grants=frozenset({"QC"})), {N.QC}),
    "faculty with APPROVE": (person("FACULTY", grants=frozenset({"APPROVE"})), {N.APPROVE}),
    "faculty with PUBLISH": (person("FACULTY", grants=frozenset({"PUBLISH"})), {N.PUBLISH}),
    "author with every review grant": (
        person("FACULTY", user_id=AUTHOR_ID, grants=frozenset({"QC", "APPROVE", "PUBLISH"})),
        {N.EDIT, N.QC, N.APPROVE, N.PUBLISH},
    ),
    "admin": (person("ADMIN"), set(Needs)),
    "owner": (person("OWNER"), set(Needs)),
    "platform admin acting in the coaching": (
        person(None, platform=True, acting=True),
        set(Needs),
    ),
    "platform admin not acting": (person(None, platform=True), set()),
    "removed member (no role), stale grants": (
        person(None, user_id=AUTHOR_ID, grants=frozenset({"QC", "APPROVE", "PUBLISH"})),
        set(),
    ),
}


@pytest.mark.parametrize("who", sorted(HOLDS))
@pytest.mark.parametrize("state, step", sorted(EXPECTED, key=lambda k: (k[0], k[1])))
def test_who_may_take_each_step(who: str, state: State, step: Step) -> None:
    principal, holds = HOLDS[who]
    needs = EXPECTED[(state, step)][1]
    assert may_take_step(principal, state, step, author_id=AUTHOR_ID) == (needs in holds)


@pytest.mark.parametrize("who", sorted(HOLDS))
@pytest.mark.parametrize(
    "state, step", [(s, t) for s in State for t in Step if (s, t) not in EXPECTED]
)
def test_nobody_may_take_a_step_the_state_does_not_allow(
    who: str, state: State, step: Step
) -> None:
    principal, _ = HOLDS[who]
    assert may_take_step(principal, state, step, author_id=AUTHOR_ID) is False


def test_the_author_with_review_grants_is_not_stopped_from_reviewing_their_own_question() -> None:
    # "Reviewer must differ from the author" is E-03, priority P2, outside M4 (§16). When it is
    # built, this test changes with it; until then the rule must not appear by accident.
    principal, _ = HOLDS["author with every review grant"]
    assert may_take_step(principal, State.IN_REVIEW, Step.PASS_QC, author_id=AUTHOR_ID)


# ---- Reasons for returning a question (§4.3, appendix) ------------------------------------------


def test_the_return_reasons_are_the_ones_in_the_appendix() -> None:
    assert [r.value for r in ReturnReason] == [
        "ANSWER_WRONG",
        "STATEMENT_UNCLEAR",
        "OPTIONS_FLAWED",
        "SOLUTION_WRONG",
        "LABELS_WRONG",
        "DIFFICULTY_OR_BLOOM_WRONG",
        "DUPLICATE",
        "FORMATTING",
        "OTHER",
    ]


def test_every_reason_has_a_plain_label_for_the_author() -> None:
    assert set(RETURN_REASON_LABELS) == set(ReturnReason)
    for label in RETURN_REASON_LABELS.values():
        assert label and label == label.strip() and "<" not in label
