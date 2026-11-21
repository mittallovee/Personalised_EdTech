"""Budgets and the usage ledger (M5 design note §7; H-05, H-06).

A person's spend in a month is the sum of their ledger entries of that month. A run first
**reserves** its estimated cost (refused if it would pass the person's budget), and when it ends it
gives the reservation back and **settles** the real cost, so a reservation counts only while it is
held. The check and the reservation happen in one transaction under a lock on that person, so two
runs started together cannot both pass a budget that has room for one.

- The window is the calendar month in India time (UTC+05:30, which has no daylight saving). A run
  belongs to the month it began in, however late it ends.
- Budgets are in rupees and providers bill in dollars: each entry keeps the rate in force when it
  was written. With no rate entered a budget cannot be applied, so it is off (the screens say so).
- An unknown price reserves nothing and is settled as ``UNKNOWN`` (zero): visible, but it adds no
  spend, so it is refused only once the budget is already used up. The admin can add an adjustment
  after reading the provider's invoice.
- At 80 % and at 100 % of a budget the person gets one in-app notice per month; the notice itself
  is a ledger marker, so "once" holds even when two runs cross the line together.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, ROUND_UP, Decimal
from typing import Literal
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from qbank.core.auth import Principal
from qbank.core.errors import Conflict, NotFound, PreconditionFailed
from qbank.core.permissions import Action, require
from qbank.modules.ai.models import AiBudget, AiSettings, LedgerEntry
from qbank.modules.audit.public import record_event
from qbank.modules.notifications.public import notify
from qbank.modules.organizations.public import find_active_membership

INDIA = timezone(timedelta(hours=5, minutes=30))
_RUPEE_PLACES = Decimal(
    "0.0001"
)  # entries keep four places, so many tiny costs are not rounded away
_WARN_AT = Decimal("0.8")
ADJUSTMENT_ENTITY = "ai_ledger"

State = Literal["NO_LIMIT", "OK", "WARNING", "REACHED", "OFF"]


def period_of(moment: datetime) -> date:
    """The first day of the month, in India time, that ``moment`` falls in."""
    local = moment.astimezone(INDIA)
    return date(local.year, local.month, 1)


def _rupees(usd: Decimal, rate: Decimal | None, *, up: bool = False) -> Decimal | None:
    if rate is None:
        return None
    return (usd * rate).quantize(_RUPEE_PLACES, rounding=ROUND_UP if up else ROUND_HALF_UP)


@dataclass(frozen=True, slots=True)
class Standing:
    """Where a person stands this month."""

    period: date
    spent_usd: Decimal
    spent_inr: Decimal
    limit_inr: Decimal | None  # what the admin set for them (their own, else the default)
    rate: Decimal | None
    state: State

    @property
    def remaining_inr(self) -> Decimal | None:
        if self.limit_inr is None or self.rate is None:
            return None
        return max(self.limit_inr - self.spent_inr, Decimal(0))


@dataclass(frozen=True, slots=True)
class Reserved:
    period: date
    usd: Decimal
    inr: Decimal | None
    cost_kind: Literal["ESTIMATED", "UNKNOWN"]


def _lock_person(session: Session, organization_id: UUID, user_id: UUID) -> None:
    """Hold this person's budget until the transaction ends, so checks and entries queue up."""
    session.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
        {"key": f"ai-budget:{organization_id}:{user_id}"},
    )


def _rate_and_default(
    session: Session, organization_id: UUID
) -> tuple[Decimal | None, Decimal | None]:
    row = session.scalars(
        select(AiSettings).where(AiSettings.organization_id == organization_id)
    ).first()
    return (row.usd_to_inr, row.default_budget_inr) if row is not None else (None, None)


def _limit(
    session: Session, organization_id: UUID, user_id: UUID, default: Decimal | None
) -> Decimal | None:
    own = session.scalars(
        select(AiBudget.monthly_inr).where(
            AiBudget.organization_id == organization_id, AiBudget.user_id == user_id
        )
    ).first()
    return own if own is not None else default


def _spent(
    session: Session, organization_id: UUID, user_id: UUID, period: date
) -> tuple[Decimal, Decimal]:
    usd, inr = session.execute(
        select(
            func.coalesce(func.sum(LedgerEntry.amount_usd), 0),
            func.coalesce(func.sum(LedgerEntry.amount_inr), 0),
        ).where(
            LedgerEntry.organization_id == organization_id,
            LedgerEntry.user_id == user_id,
            LedgerEntry.period == period,
        )
    ).one()
    return Decimal(str(usd)), Decimal(str(inr))


def _state(limit: Decimal | None, rate: Decimal | None, spent_inr: Decimal) -> State:
    if limit is None:
        return "NO_LIMIT"
    if rate is None:
        return "OFF"
    if limit == 0 or spent_inr >= limit:
        return "REACHED"
    if spent_inr >= limit * _WARN_AT:
        return "WARNING"
    return "OK"


def standing(
    session: Session,
    organization_id: UUID,
    user_id: UUID,
    *,
    period: date | None = None,
    now: datetime | None = None,
) -> Standing:
    """Spend, budget and state of a person for a month (this one unless ``period`` is given)."""
    month = period or period_of(now or datetime.now(UTC))
    rate, default = _rate_and_default(session, organization_id)
    limit = _limit(session, organization_id, user_id, default)
    usd, inr = _spent(session, organization_id, user_id, month)
    return Standing(month, usd, inr, limit, rate, _state(limit, rate, inr))


def _notify_thresholds(
    session: Session,
    organization_id: UUID,
    user_id: UUID,
    period: date,
    *,
    limit: Decimal | None,
    rate: Decimal | None,
    spent_inr: Decimal,
) -> None:
    if limit is None or rate is None or limit <= 0:
        return
    steps = (
        ("NOTICE_80", limit * _WARN_AT, "AI_BUDGET_WARNING"),
        ("NOTICE_100", limit, "AI_BUDGET_REACHED"),
    )
    for entry_kind, line, kind in steps:
        if spent_inr < line:
            continue
        marker = session.execute(
            insert(LedgerEntry)
            .values(
                organization_id=organization_id,
                user_id=user_id,
                entry_kind=entry_kind,
                period=period,
                amount_usd=Decimal(0),
                amount_inr=Decimal(0),
            )
            .on_conflict_do_nothing()
            .returning(LedgerEntry.id)
        ).first()
        if marker is not None:  # not told yet this month
            notify(
                session,
                organization_id=organization_id,
                user_id=user_id,
                kind=kind,
                data={
                    "period": period.isoformat(),
                    "limit_inr": format(limit.normalize(), "f"),
                    "spent_inr": format(spent_inr.quantize(Decimal("0.01")), "f"),
                },
            )


def reserve(
    session: Session,
    *,
    organization_id: UUID,
    user_id: UUID,
    run_id: UUID,
    estimate_usd: Decimal | None,
    now: datetime | None = None,
) -> Reserved:
    """Set aside a run's estimated cost, or refuse (``AI_BUDGET_EXCEEDED``) if it would pass the
    person's budget. ``estimate_usd`` is ``None`` when the model's price is unknown."""
    _lock_person(session, organization_id, user_id)
    period = period_of(now or datetime.now(UTC))
    rate, default = _rate_and_default(session, organization_id)
    limit = _limit(session, organization_id, user_id, default)
    _, spent = _spent(session, organization_id, user_id, period)
    usd = estimate_usd if estimate_usd is not None else Decimal(0)
    inr = _rupees(usd, rate, up=True)  # rounded up: a reservation errs on the safe side
    kind: Literal["ESTIMATED", "UNKNOWN"] = "UNKNOWN" if estimate_usd is None else "ESTIMATED"
    if limit is not None and rate is not None:
        need = inr or Decimal(0)
        if limit == 0 or spent >= limit or spent + need > limit:
            raise Conflict(
                "This would pass your monthly AI budget.",
                code="AI_BUDGET_EXCEEDED",
                details={
                    "limit_inr": format(limit.normalize(), "f"),
                    "remaining_inr": format(
                        max(limit - spent, Decimal(0)).quantize(Decimal("0.01")), "f"
                    ),
                },
            )
    session.add(
        LedgerEntry(
            organization_id=organization_id,
            user_id=user_id,
            run_id=run_id,
            entry_kind="RESERVE",
            period=period,
            amount_usd=usd,
            amount_inr=inr,
            rate=rate,
            cost_kind=kind,
        )
    )
    session.flush()
    _notify_thresholds(
        session,
        organization_id,
        user_id,
        period,
        limit=limit,
        rate=rate,
        spent_inr=spent + (inr or Decimal(0)),
    )
    return Reserved(period, usd, inr, kind)


def _reservation(session: Session, organization_id: UUID, run_id: UUID) -> LedgerEntry:
    entry = session.scalars(
        select(LedgerEntry).where(
            LedgerEntry.organization_id == organization_id,
            LedgerEntry.run_id == run_id,
            LedgerEntry.entry_kind == "RESERVE",
        )
    ).first()
    if entry is None:
        raise NotFound("No reservation was made for this run.")
    return entry


def _already_closed(session: Session, organization_id: UUID, run_id: UUID) -> bool:
    return (
        session.scalars(
            select(LedgerEntry.id).where(
                LedgerEntry.organization_id == organization_id,
                LedgerEntry.run_id == run_id,
                LedgerEntry.entry_kind == "RELEASE",
            )
        ).first()
        is not None
    )


def _give_back(session: Session, reserved: LedgerEntry) -> None:
    session.add(
        LedgerEntry(
            organization_id=reserved.organization_id,
            user_id=reserved.user_id,
            run_id=reserved.run_id,
            entry_kind="RELEASE",
            period=reserved.period,
            amount_usd=-reserved.amount_usd,
            amount_inr=-reserved.amount_inr if reserved.amount_inr is not None else None,
            rate=reserved.rate,
        )
    )


def settle(
    session: Session,
    *,
    organization_id: UUID,
    run_id: UUID,
    actual_usd: Decimal | None,
) -> None:
    """Give the reservation back and record what the run cost: ``actual_usd`` from the provider's
    token counts, else the estimate (``ESTIMATED``), else nothing (``UNKNOWN``). Settling a run
    that is already closed does nothing, so a retried step cannot charge twice."""
    reserved = _reservation(session, organization_id, run_id)
    _lock_person(session, organization_id, reserved.user_id)
    if _already_closed(session, organization_id, run_id):
        return
    rate, default = _rate_and_default(session, organization_id)
    if actual_usd is not None:
        usd, kind = actual_usd, "ACTUAL"
    elif reserved.cost_kind == "ESTIMATED":
        usd, kind = reserved.amount_usd, "ESTIMATED"
    else:
        usd, kind = Decimal(0), "UNKNOWN"
    _give_back(session, reserved)
    session.add(
        LedgerEntry(
            organization_id=organization_id,
            user_id=reserved.user_id,
            run_id=run_id,
            entry_kind="SETTLE",
            period=reserved.period,
            amount_usd=usd,
            amount_inr=_rupees(usd, rate),
            rate=rate,
            cost_kind=kind,
        )
    )
    session.flush()
    _after_entry(session, organization_id, reserved.user_id, reserved.period, rate, default)


def release(session: Session, *, organization_id: UUID, run_id: UUID) -> None:
    """Give the reservation back and charge nothing (the run failed before the provider billed)."""
    reserved = _reservation(session, organization_id, run_id)
    _lock_person(session, organization_id, reserved.user_id)
    if _already_closed(session, organization_id, run_id):
        return
    _give_back(session, reserved)
    session.flush()


def _after_entry(
    session: Session,
    organization_id: UUID,
    user_id: UUID,
    period: date,
    rate: Decimal | None,
    default: Decimal | None,
) -> None:
    limit = _limit(session, organization_id, user_id, default)
    _, spent = _spent(session, organization_id, user_id, period)
    _notify_thresholds(
        session, organization_id, user_id, period, limit=limit, rate=rate, spent_inr=spent
    )


def adjust(
    session: Session,
    principal: Principal,
    user_id: UUID,
    *,
    amount_usd: Decimal,
    note: str,
    request_id: str | None,
    now: datetime | None = None,
) -> Standing:
    """An admin's correction (either sign) after reading the provider's invoice, added to this
    month. The ledger is never edited, so a mistake is corrected by another adjustment."""
    require(principal, Action.MANAGE_AI_SETTINGS)
    organization_id = principal.tenant_context.organization_id
    if organization_id is None:  # the permission check already refuses this
        raise PreconditionFailed("No coaching to adjust usage for.")
    membership = find_active_membership(session, user_id)
    if membership is None or membership.organization_id != organization_id:
        raise NotFound("There is no such member here.")
    _lock_person(session, organization_id, user_id)
    period = period_of(now or datetime.now(UTC))
    rate, default = _rate_and_default(session, organization_id)
    entry = LedgerEntry(
        organization_id=organization_id,
        user_id=user_id,
        entry_kind="ADJUST",
        period=period,
        amount_usd=amount_usd,
        amount_inr=_rupees(amount_usd, rate),
        rate=rate,
        cost_kind="ACTUAL",
        note=note,
        created_by=principal.user_id,
    )
    session.add(entry)
    session.flush()
    record_event(
        session,
        action="AI_USAGE_ADJUSTED",
        entity_type=ADJUSTMENT_ENTITY,
        entity_id=entry.id,
        organization_id=organization_id,
        actor_user_id=principal.user_id,
        actor_is_platform=principal.acting_organization_id is not None,
        request_id=request_id,
        before=None,
        after={
            "user_id": str(user_id),
            "amount_usd": format(amount_usd.normalize(), "f"),
            "period": period.isoformat(),
        },
    )
    _after_entry(session, organization_id, user_id, period, rate, default)
    return standing(session, organization_id, user_id, period=period)


def people_with_usage(session: Session, organization_id: UUID, period: date) -> list[UUID]:
    """Members who have entries this month or a budget of their own, for the admin's table."""
    spent = select(LedgerEntry.user_id).where(
        LedgerEntry.organization_id == organization_id, LedgerEntry.period == period
    )
    own = select(AiBudget.user_id).where(AiBudget.organization_id == organization_id)
    return sorted(set(session.scalars(spent.union(own))), key=str)
