"""Routes for AI usage and cost (M5 design note §7; H-05, H-06)."""

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request, status

from qbank.core.auth import CurrentPrincipal
from qbank.core.db import Database, get_database
from qbank.core.errors import PreconditionFailed
from qbank.core.permissions import Action, require
from qbank.modules.ai import budget
from qbank.modules.ai.schemas import (
    AdjustUsage,
    PersonUsageOut,
    UsageListOut,
    UsageOut,
)
from qbank.modules.identity.public import display_names

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])

_MONTH = Query(
    pattern=r"^\d{4}-(0[1-9]|1[0-2])$",
    description="A month, `YYYY-MM` (India time). Defaults to this month.",
)
_DENIED: dict[int | str, dict[str, Any]] = {
    403: {"description": "Only the Owner and admins (`PERMISSION_DENIED`)"}
}


def _month(value: str | None) -> date:
    if value is None:
        return budget.period_of(datetime.now(UTC))
    return date(int(value[:4]), int(value[5:7]), 1)


def _money(value: Decimal, places: str = "0.01") -> str:
    return format(value.quantize(Decimal(places)), "f")


def _out(standing: budget.Standing) -> UsageOut:
    remaining = standing.remaining_inr
    return UsageOut(
        period=standing.period.strftime("%Y-%m"),
        spent_usd=_money(standing.spent_usd, "0.000001"),
        spent_inr=_money(standing.spent_inr),
        limit_inr=None if standing.limit_inr is None else _money(standing.limit_inr),
        remaining_inr=None if remaining is None else _money(remaining),
        state=standing.state,
    )


@router.get(
    "/usage/me",
    summary="Your own AI usage and what is left of your budget this month (H-05)",
    description="Any member of the coaching. Costs are US dollars (what providers bill) and rupees"
    " at the rate in force when each was recorded; runs in progress count at their estimate.",
)
def my_usage(
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
    month: Annotated[str | None, _MONTH] = None,
) -> UsageOut:
    organization_id = principal.tenant_context.organization_id
    if organization_id is None:
        raise PreconditionFailed("Choose a coaching to see usage for.")
    with database.transaction(principal.tenant_context) as session:
        return _out(
            budget.standing(session, organization_id, principal.user_id, period=_month(month))
        )


@router.get(
    "/usage",
    summary="Everyone's AI usage for a month (H-05, H-06)",
    description="Owner and admins. One row per member who has usage or a budget of their own that"
    " month, with their budget and state.",
    responses=_DENIED,
)
def usage(
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
    month: Annotated[str | None, _MONTH] = None,
) -> UsageListOut:
    require(principal, Action.MANAGE_AI_SETTINGS)
    organization_id = principal.tenant_context.organization_id
    if organization_id is None:  # the permission check already refuses this
        raise PreconditionFailed("Choose a coaching to see usage for.")
    period = _month(month)
    with database.transaction(principal.tenant_context) as session:
        people = budget.people_with_usage(session, organization_id, period)
        names = display_names(session, people)
        rows = [
            PersonUsageOut(
                **_out(
                    budget.standing(session, organization_id, user_id, period=period)
                ).model_dump(),
                user_id=user_id,
                display_name=names.get(user_id),
            )
            for user_id in people
        ]
    return UsageListOut(period=period.strftime("%Y-%m"), data=rows)


@router.post(
    "/usage/adjustments",
    status_code=status.HTTP_201_CREATED,
    summary="Correct a member's usage this month after reading the provider's invoice (H-06)",
    description="Owner and admins. Adds an entry (positive or negative dollars) to this month; the"
    " ledger is never edited, so a mistake is corrected by another adjustment. Written to the audit"
    " log. Returns the member's new standing.",
    responses={**_DENIED, 404: {"description": "No such member in this coaching (`NOT_FOUND`)"}},
)
def adjust_usage(
    body: AdjustUsage,
    request: Request,
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
) -> UsageOut:
    with database.transaction(principal.tenant_context) as session:
        standing = budget.adjust(
            session,
            principal,
            body.user_id,
            amount_usd=body.amount_usd,
            note=body.note,
            request_id=request.state.request_id,
        )
        return _out(standing)
