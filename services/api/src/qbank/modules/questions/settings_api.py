"""Routes for the answer limits of a coaching (M3 design note §5.4, D-03)."""

from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response

from qbank.core.auth import CurrentPrincipal
from qbank.core.db import Database, get_database
from qbank.core.etag import IfMatchHeader, etag
from qbank.modules.questions import settings_service as service
from qbank.modules.questions.limits import FIELDS
from qbank.modules.questions.rules import DEFAULT_RULES
from qbank.modules.questions.schemas import (
    AnswerRulesOut,
    ExamLimits,
    SaveAnswerRules,
    SettingBounds,
)

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])

_DENIED: dict[int | str, dict[str, Any]] = {
    403: {"description": "Only the Owner and admins (`PERMISSION_DENIED`)"}
}


def _text(value: int | Decimal) -> int | str:
    """A whole number as it is; a decimal as text with two decimals, never as a float."""
    return value if isinstance(value, int) else f"{value:.2f}"


def _out(view: service.SettingsView) -> AnswerRulesOut:
    return AnswerRulesOut(
        revision=view.revision,
        built_in={name: _text(getattr(DEFAULT_RULES, name)) for name in FIELDS},
        bounds={
            name: SettingBounds(kind=field.kind, low=_text(field.low), high=_text(field.high))
            for name, field in FIELDS.items()
        },
        defaults=view.defaults,
        exams=[ExamLimits(exam_id=UUID(key), values=values) for key, values in view.exams.items()],
    )


@router.get(
    "/answer-rules",
    summary="The answer limits of the coaching",
    description="Owner and admins. The built-in values, the widest range each setting may take,"
    " and what this coaching changed (for itself and for particular exams). The ETag is for the"
    " save. A changed limit never rewrites a saved revision; it only changes what the findings"
    " say.",
    responses=_DENIED,
)
def get_answer_rules(
    principal: CurrentPrincipal,
    response: Response,
    database: Annotated[Database, Depends(get_database)],
) -> AnswerRulesOut:
    with database.transaction(principal.tenant_context) as session:
        result = _out(service.get_settings(session, principal))
    response.headers["ETag"] = etag(result.revision)
    return result


@router.put(
    "/answer-rules",
    summary="Change the answer limits of the coaching",
    description="Owner and admins. Send everything that differs from the built-in values, with the"
    ' ETag you last read in `If-Match` (`"rev-0"` before the first save); a save from a stale'
    " screen is refused (412). A minimum above its maximum, a value outside its bounds, an unknown"
    " setting or an exam that is not this coaching's is refused with every problem listed"
    " (`ANSWER_RULES_INVALID`). The change is written to the audit log.",
    responses={
        **_DENIED,
        412: {"description": "Changed since you read it; reload (`REVISION_STALE`)"},
        422: {"description": "Some limits cannot be used; `details.problems` lists them"},
        428: {"description": "`If-Match` is missing (`IF_MATCH_REQUIRED`)"},
    },
)
def save_answer_rules(
    body: SaveAnswerRules,
    principal: CurrentPrincipal,
    request: Request,
    response: Response,
    database: Annotated[Database, Depends(get_database)],
    if_match: Annotated[str | None, IfMatchHeader] = None,
) -> AnswerRulesOut:
    with database.transaction(principal.tenant_context) as session:
        view = service.save_settings(
            session,
            principal,
            body.defaults,
            body.exams,
            if_match=if_match,
            request_id=request.state.request_id,
        )
        result = _out(view)
    response.headers["ETag"] = etag(result.revision)
    return result
