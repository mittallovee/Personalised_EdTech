"""Which versions a person may read, as one query condition (M4 design note §5).

From submit on, every member may read a version; work in progress (a draft, a returned question)
stays with its author, admins and holders of the edit-others grant, and to anyone else it does not
exist. ``_open`` in ``service.py`` applies the same rule to one question; every list built from
queries uses this condition instead, so a hidden question is never found, counted or listed.
"""

from sqlalchemy import ColumnElement, false, or_, true

from qbank.core.auth import Principal
from qbank.core.permissions import Action, is_allowed, may_access_all_drafts
from qbank.modules.questions.domain.workflow import PRIVATE_STATES
from qbank.modules.questions.models import QuestionMaster, QuestionVersion

_PRIVATE = [state.value for state in PRIVATE_STATES]


def readable(principal: Principal) -> ColumnElement[bool]:
    """True for the rows of ``question_masters`` joined to ``question_versions`` that this person
    may read. Someone with no role in the coaching (removed, suspended) may read nothing."""
    if not is_allowed(principal, Action.CREATE_QUESTIONS):
        return false()
    if may_access_all_drafts(principal):
        return true()
    return or_(
        QuestionVersion.state.not_in(_PRIVATE), QuestionMaster.created_by == principal.user_id
    )
