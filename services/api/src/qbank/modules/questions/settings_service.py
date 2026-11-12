"""Reading and changing a coaching's answer limits (M3 design note §5.4, D-03).

The settings are one small document per coaching: only what it changed from the built-in values,
for the coaching as a whole and for particular exams. Saving replaces the whole document under
``If-Match``, so two admins cannot overwrite each other unseen. The findings of every question read
these settings each time, so a change shows on the next look and no saved revision is touched.
"""

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from qbank.core.auth import Principal
from qbank.core.errors import PreconditionFailed, ValidationFailed
from qbank.core.etag import etag, require_if_match
from qbank.core.permissions import Action, require
from qbank.modules.audit.public import record_event
from qbank.modules.questions.limits import (
    LimitProblem,
    Overrides,
    check_overrides,
    normalise,
)
from qbank.modules.questions.models import AnswerRuleSettings
from qbank.modules.taxonomy.public import look_up

ENTITY_TYPE = "answer_rules"


@dataclass(frozen=True, slots=True)
class SettingsView:
    revision: int  # 0 until the coaching first saves
    defaults: dict[str, Any]
    exams: dict[str, dict[str, Any]]


def load_overrides(session: Session) -> Overrides:
    """The coaching's settings as the findings use them (row-level security picks the coaching).

    Never raises on what is stored: a value that cannot be used is left out.
    """
    row = session.scalars(select(AnswerRuleSettings)).first()
    return normalise(row.defaults, row.exams) if row is not None else Overrides({}, {})


def _view(row: AnswerRuleSettings | None) -> SettingsView:
    if row is None:
        return SettingsView(0, {}, {})
    return SettingsView(
        row.revision, dict(row.defaults), {key: dict(v) for key, v in row.exams.items()}
    )


def get_settings(session: Session, principal: Principal) -> SettingsView:
    require(principal, Action.MANAGE_ANSWER_RULES)
    return _view(session.scalars(select(AnswerRuleSettings)).first())


def _refuse(problems: list[LimitProblem]) -> ValidationFailed:
    return ValidationFailed(
        "Some of these limits cannot be used.",
        code="ANSWER_RULES_INVALID",
        details={
            "problems": [{"path": p.path, "code": p.code, "message": p.message} for p in problems]
        },
    )


def _is_id(key: str) -> bool:
    try:
        return str(UUID(key)) == key
    except ValueError:
        return False


def save_settings(
    session: Session,
    principal: Principal,
    defaults: dict[str, Any],
    exams: dict[str, dict[str, Any]],
    *,
    if_match: str | None,
    request_id: str | None,
) -> SettingsView:
    """Replace the coaching's settings. ``if_match`` must be the ETag last read (``"rev-0"`` before
    the first save)."""
    require(principal, Action.MANAGE_ANSWER_RULES)
    organization_id = principal.tenant_context.organization_id
    if organization_id is None:  # the permission check already refuses this
        raise PreconditionFailed("No coaching to save settings for.")
    row = session.scalars(select(AnswerRuleSettings).with_for_update()).first()
    require_if_match(if_match, row.revision if row is not None else 0)

    problems = check_overrides(defaults, exams)
    known = look_up(session, [UUID(key) for key in exams if _is_id(key)])
    for key in exams:
        if _is_id(key) and (UUID(key) not in known or known[UUID(key)].kind != "EXAM"):
            problems.append(
                LimitProblem(f"exams.{key}", "EXAM_NOT_FOUND", "There is no such exam here.")
            )
    if problems:
        raise _refuse(problems)

    kept = {key: values for key, values in exams.items() if values}  # an empty layer says nothing
    before = _view(row)
    if row is None:
        row = AnswerRuleSettings(
            organization_id=organization_id,
            revision=1,
            defaults=defaults,
            exams=kept,
            updated_by=principal.user_id,
        )
        try:
            with session.begin_nested():
                session.add(row)
                session.flush()
        except IntegrityError:  # another admin saved the first version at the same moment
            raise PreconditionFailed(
                "Someone else changed this in the meantime. Reload it and try again.",
                details={"current_etag": etag(1)},
            ) from None
    else:
        row.defaults = defaults
        row.exams = kept
        row.revision += 1
        row.updated_by = principal.user_id
        session.flush()
    record_event(
        session,
        action="ANSWER_RULES_CHANGED",
        entity_type=ENTITY_TYPE,
        entity_id=organization_id,
        organization_id=organization_id,
        actor_user_id=principal.user_id,
        actor_is_platform=principal.acting_organization_id is not None,
        request_id=request_id,
        before={"defaults": before.defaults, "exams": before.exams},
        after={"defaults": defaults, "exams": kept},
    )
    return _view(row)
