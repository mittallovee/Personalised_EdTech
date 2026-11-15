"""Who may take a workflow step (M4 design note §5). The only place these rules live.

The pure table in ``workflow.py`` says which step a state allows and which right it needs. This
file turns a right into a yes or no for one person. It uses the ``Principal``, reloaded from the
database on every request, so a grant that was just removed stops working on the next request
(B-10); nothing a client sends is consulted.

Two things stay out on purpose. The author may review their own question, because "reviewer must
differ from the author" is E-03 (priority P2), outside M4. And the *Read* rules (§5) are not here:
they belong to the queries, where a hidden question must not be found at all.
"""

from uuid import UUID

from qbank.core.auth import Principal
from qbank.core.permissions import Action, Grant, has_grant, is_allowed, may_access_draft
from qbank.modules.questions.domain.workflow import Needs, State, Step, find_transition

_GRANT_FOR: dict[Needs, Grant] = {
    Needs.QC: Grant.QC,
    Needs.APPROVE: Grant.APPROVE,
    Needs.PUBLISH: Grant.PUBLISH,
}


def holds(principal: Principal, needs: Needs, *, author_id: UUID) -> bool:
    """Does this person hold the right a step needs, on a question written by ``author_id``?"""
    # Someone with no role in the coaching (removed or suspended) holds nothing, whatever grants
    # a stale record still lists; a platform admin holds everything only while acting in it.
    if not is_allowed(principal, Action.CREATE_QUESTIONS):
        return False
    if needs is Needs.EDIT:
        return may_access_draft(principal, author_id)
    return has_grant(principal, _GRANT_FOR[needs])


def may_take_step(principal: Principal, state: State, step: Step, *, author_id: UUID) -> bool:
    """May this person take this step on a version that is in this state?"""
    transition = find_transition(state, step)
    if transition is None:
        return False
    return holds(principal, transition.needs, author_id=author_id)
