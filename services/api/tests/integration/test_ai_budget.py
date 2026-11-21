"""M5 PR 5c: the usage ledger and budgets (H-05, H-06; test T48 and the budget half of T47).

A run reserves its estimated cost, is refused if that would pass the person's budget, and settles
the real cost when it ends. The ledger only ever grows; the month is the calendar month in India
time; the 80 % and 100 % notices go out once. No provider is called.
"""

import base64
import threading
from collections.abc import Iterator
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

import psycopg
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError

from qbank.core.config import AppEnv, Settings
from qbank.core.db import Database
from qbank.core.errors import AppError
from qbank.core.ids import new_id
from qbank.core.tenancy import TenantContext
from qbank.main import create_app
from qbank.modules.ai import budget
from qbank.modules.ai.models import AiBudget, AiSettings, LedgerEntry
from qbank.modules.audit.models import AuditEvent
from qbank.modules.notifications.models import Notification
from tests.integration.conftest import Member, MigratedDatabase, make_member, sign_in

USAGE = "/api/v1/ai/usage"
MASTER = base64.b64encode(bytes(range(32))).decode()
D = Decimal


@pytest.fixture
def client(migrated_database: MigratedDatabase) -> Iterator[TestClient]:
    settings = Settings(
        app_env=AppEnv.TEST,
        database_url=migrated_database.app_url,
        session_cookie_secure=False,
        ai_keys_master_key=MASTER,  # type: ignore[arg-type]
    )
    with TestClient(create_app(settings)) as test_client:
        yield test_client


@pytest.fixture
def team(owner_db: Database) -> dict[str, Member]:
    owner = make_member(owner_db, "OWNER")
    return {
        "owner": owner,
        "admin": make_member(owner_db, "ADMIN", org_id=owner.org_id),
        "faculty": make_member(owner_db, "FACULTY", org_id=owner.org_id),
    }


def context(member: Member) -> TenantContext:
    return TenantContext(organization_id=member.org_id, user_id=member.user_id)


def configure(
    owner_db: Database,
    member: Member,
    *,
    rate: str | None = "80",
    default: str | None = None,
    own: str | None = None,
) -> None:
    """Set the coaching's rate and default budget, and the member's own budget."""
    with owner_db.transaction(TenantContext(organization_id=member.org_id)) as session:
        session.add(
            AiSettings(
                organization_id=member.org_id,
                usd_to_inr=D(rate) if rate is not None else None,
                default_budget_inr=D(default) if default is not None else None,
                updated_by=member.user_id,
            )
        )
        if own is not None:
            session.add(
                AiBudget(
                    organization_id=member.org_id,
                    user_id=member.user_id,
                    monthly_inr=D(own),
                    updated_by=member.user_id,
                )
            )


def reserve(db: Database, member: Member, usd: str | None, *, now: datetime | None = None) -> UUID:
    run = new_id()
    with db.transaction(context(member)) as session:
        budget.reserve(
            session,
            organization_id=member.org_id,
            user_id=member.user_id,
            run_id=run,
            estimate_usd=D(usd) if usd is not None else None,
            now=now,
        )
    return run


def settle(db: Database, member: Member, run: UUID, usd: str | None) -> None:
    with db.transaction(context(member)) as session:
        budget.settle(
            session,
            organization_id=member.org_id,
            run_id=run,
            actual_usd=D(usd) if usd is not None else None,
        )


def standing(db: Database, member: Member, **kw: object) -> budget.Standing:
    with db.transaction(context(member)) as session:
        return budget.standing(session, member.org_id, member.user_id, **kw)  # type: ignore[arg-type]


def entries(owner_db: Database, member: Member) -> list[LedgerEntry]:
    with owner_db.transaction(TenantContext(organization_id=member.org_id)) as session:
        rows = list(
            session.scalars(
                select(LedgerEntry)
                .where(
                    LedgerEntry.organization_id == member.org_id,
                    LedgerEntry.user_id == member.user_id,
                )
                .order_by(LedgerEntry.created_at, LedgerEntry.id)
            )
        )
        session.expunge_all()
        return rows


def money(owner_db: Database, member: Member) -> list[LedgerEntry]:
    """The entries that carry money (not the once-only notice markers)."""
    return [e for e in entries(owner_db, member) if not e.entry_kind.startswith("NOTICE")]


def notices(owner_db: Database, member: Member) -> list[str]:
    with owner_db.transaction(TenantContext(organization_id=member.org_id)) as session:
        return list(
            session.scalars(
                select(Notification.kind)
                .where(Notification.user_id == member.user_id)
                .order_by(Notification.created_at)
            )
        )


# --- The month -----------------------------------------------------------------------------------


def test_the_month_is_the_calendar_month_in_india_time() -> None:
    assert budget.period_of(datetime(2026, 1, 31, 18, 29, tzinfo=UTC)) == date(2026, 1, 1)
    assert budget.period_of(datetime(2026, 1, 31, 18, 30, tzinfo=UTC)) == date(2026, 2, 1)
    assert budget.period_of(datetime(2026, 12, 31, 20, 0, tzinfo=UTC)) == date(2027, 1, 1)


# --- Reserve, settle, release -------------------------------------------------------------


def test_a_reservation_counts_until_the_run_ends_and_is_replaced_by_the_real_cost(
    db: Database, owner_db: Database, team: dict[str, Member]
) -> None:
    person = team["faculty"]
    configure(owner_db, person, rate="80", default="100")
    run = reserve(db, person, "0.5")  # 40 rupees held
    held = standing(db, person)
    assert (held.spent_usd, held.spent_inr) == (D("0.5"), D("40"))
    assert held.state == "OK"
    assert held.remaining_inr == D("60")

    settle(db, person, run, "0.25")  # the provider billed half of that
    done = standing(db, person)
    assert (done.spent_usd, done.spent_inr) == (D("0.25"), D("20"))
    kinds = [(e.entry_kind, e.cost_kind) for e in entries(owner_db, person)]
    assert kinds == [("RESERVE", "ESTIMATED"), ("RELEASE", None), ("SETTLE", "ACTUAL")]

    settle(db, person, run, "9")  # a retried step charges nothing more
    assert standing(db, person).spent_usd == D("0.25")
    assert len(entries(owner_db, person)) == 3


def test_a_failed_run_gives_the_reservation_back_once(
    db: Database, owner_db: Database, team: dict[str, Member]
) -> None:
    person = team["faculty"]
    configure(owner_db, person, rate="80", default="100")
    run = reserve(db, person, "1")
    with db.transaction(context(person)) as session:
        budget.release(session, organization_id=person.org_id, run_id=run)
        budget.release(session, organization_id=person.org_id, run_id=run)
    after = standing(db, person)
    assert (after.spent_usd, after.spent_inr) == (D("0"), D("0"))
    assert [e.entry_kind for e in money(owner_db, person)] == ["RESERVE", "RELEASE"]
    settle(db, person, run, "5")  # a closed run cannot be settled afterwards
    assert standing(db, person).spent_usd == D("0")


def test_an_unknown_price_is_recorded_as_unknown_and_an_estimate_stands_in_when_there_is_one(
    db: Database, owner_db: Database, team: dict[str, Member]
) -> None:
    person = team["faculty"]
    configure(owner_db, person, rate="80", default="100")
    unknown = reserve(db, person, None)
    settle(db, person, unknown, None)
    priced = reserve(db, person, "0.1")
    settle(db, person, priced, None)  # no token counts came back: the estimate is used
    settled = [e for e in entries(owner_db, person) if e.entry_kind == "SETTLE"]
    assert [(e.cost_kind, e.amount_usd) for e in settled] == [
        ("UNKNOWN", D("0")),
        ("ESTIMATED", D("0.1")),
    ]
    assert standing(db, person).spent_inr == D("8")


# --- The budget -----------------------------------------------------------------------------------


def test_a_run_that_would_pass_the_budget_is_refused_with_what_is_left(
    db: Database, owner_db: Database, team: dict[str, Member]
) -> None:
    person = team["faculty"]
    configure(owner_db, person, rate="80", default="100")
    first = reserve(db, person, "1")  # 80 of 100
    with pytest.raises(AppError) as refused:
        reserve(db, person, "0.5")  # +40 would be 120
    assert refused.value.code == "AI_BUDGET_EXCEEDED"
    assert refused.value.details == {"limit_inr": "100", "remaining_inr": "20.00"}
    assert len(money(owner_db, person)) == 1  # a refusal leaves nothing behind
    settle(db, person, first, "0.1")  # it cost far less: 8 rupees
    reserve(db, person, "0.5")  # now there is room


def test_at_the_limit_new_runs_are_refused_even_when_their_price_is_unknown(
    db: Database, owner_db: Database, team: dict[str, Member]
) -> None:
    person = team["faculty"]
    configure(owner_db, person, rate="80", default="100")
    run = reserve(db, person, "1.25")  # exactly 100
    settle(db, person, run, "1.25")
    assert standing(db, person).state == "REACHED"
    for estimate in (None, "0.000001"):
        with pytest.raises(AppError) as refused:
            reserve(db, person, estimate)
        assert refused.value.code == "AI_BUDGET_EXCEEDED"


def test_a_budget_of_zero_means_no_ai_at_all(
    db: Database, owner_db: Database, team: dict[str, Member]
) -> None:
    person = team["faculty"]
    configure(owner_db, person, rate="80", default="100", own="0")
    with pytest.raises(AppError) as refused:
        reserve(db, person, None)
    assert refused.value.code == "AI_BUDGET_EXCEEDED"
    assert standing(db, person).state == "REACHED"


def test_a_persons_own_budget_beats_the_default(
    db: Database, owner_db: Database, team: dict[str, Member]
) -> None:
    person = team["faculty"]
    configure(owner_db, person, rate="80", default="10", own="1000")
    reserve(db, person, "5")  # 400 rupees: far over the default, inside their own
    assert standing(db, person).limit_inr == D("1000")


def test_without_a_rate_a_budget_is_off_and_without_a_budget_nothing_is_limited(
    db: Database, owner_db: Database, team: dict[str, Member]
) -> None:
    person = team["faculty"]
    configure(owner_db, person, rate=None, default="1")
    reserve(db, person, "50")  # the limit cannot be applied without a rate
    off = standing(db, person)
    assert off.state == "OFF"
    assert off.spent_inr == D("0")  # no rate, so no rupee amounts
    assert off.spent_usd == D("50")
    assert off.remaining_inr is None
    stranger = make_member(owner_db, "FACULTY", coaching_name="Another Coaching")
    assert standing(db, stranger).state == "NO_LIMIT"  # a coaching that set nothing: no limit


# --- Notices --------------------------------------------------------------------------------------


def test_the_80_and_100_percent_notices_go_out_once_each(
    db: Database, owner_db: Database, team: dict[str, Member]
) -> None:
    person = team["faculty"]
    configure(owner_db, person, rate="100", default="100")
    first = reserve(db, person, "0.5")  # 50: nothing yet
    assert notices(owner_db, person) == []
    settle(db, person, first, "0.5")
    second = reserve(db, person, "0.3")  # 80: warning
    assert notices(owner_db, person) == ["AI_BUDGET_WARNING"]
    settle(db, person, second, "0.3")
    third = reserve(db, person, "0.05")  # 85: still the same month, no second warning
    assert notices(owner_db, person) == ["AI_BUDGET_WARNING"]
    settle(db, person, third, "0.05")
    fourth = reserve(db, person, "0.15")  # 100: reached
    assert notices(owner_db, person) == ["AI_BUDGET_WARNING", "AI_BUDGET_REACHED"]
    settle(db, person, fourth, "0.15")
    with pytest.raises(AppError):
        reserve(db, person, "0.01")
    assert notices(owner_db, person) == ["AI_BUDGET_WARNING", "AI_BUDGET_REACHED"]
    markers = [e.entry_kind for e in entries(owner_db, person) if e.entry_kind.startswith("NOTICE")]
    assert markers == ["NOTICE_80", "NOTICE_100"]


def test_a_cost_that_turns_out_higher_than_estimated_still_triggers_the_notice(
    db: Database, owner_db: Database, team: dict[str, Member]
) -> None:
    person = team["faculty"]
    configure(owner_db, person, rate="100", default="100")
    run = reserve(db, person, "0.1")  # 10 estimated
    settle(db, person, run, "0.9")  # 90 billed
    assert notices(owner_db, person) == ["AI_BUDGET_WARNING"]


# --- The month rolls over -------------------------------------------------------------------------


def test_a_new_month_starts_from_zero_and_a_run_belongs_to_the_month_it_began_in(
    db: Database, owner_db: Database, team: dict[str, Member]
) -> None:
    person = team["faculty"]
    configure(owner_db, person, rate="100", default="100")
    january = datetime(2026, 1, 31, 18, 20, tzinfo=UTC)  # 23:50 on the 31st in India
    run = reserve(db, person, "0.9", now=january)
    settle(db, person, run, "0.9")  # finished after midnight, but it began in January
    assert standing(db, person, period=date(2026, 1, 1)).spent_inr == D("90")
    assert standing(db, person, period=date(2026, 2, 1)).spent_inr == D("0")
    assert [e.period for e in entries(owner_db, person) if e.entry_kind == "SETTLE"] == [
        date(2026, 1, 1)
    ]
    # In February there is room again, and the warning can be sent again.
    reserve(db, person, "0.85", now=datetime(2026, 1, 31, 18, 40, tzinfo=UTC))
    assert notices(owner_db, person) == ["AI_BUDGET_WARNING", "AI_BUDGET_WARNING"]


# --- The ledger only grows ------------------------------------------------------------------


def test_the_ledger_refuses_to_be_changed_even_by_its_owner(
    db: Database, owner_db: Database, team: dict[str, Member]
) -> None:
    person = team["faculty"]
    configure(owner_db, person, rate="80", default="100")
    reserve(db, person, "0.1")
    for statement in (
        "UPDATE ai_ledger SET amount_usd = 0",
        "DELETE FROM ai_ledger",
        "TRUNCATE ai_ledger",
    ):
        with (
            pytest.raises(DBAPIError, match="append-only"),
            owner_db.transaction(TenantContext(is_platform=True)) as session,
        ):
            session.execute(text(statement))
    assert standing(db, person).spent_usd == D("0.1")


def test_the_app_role_can_only_read_and_add_entries(
    migrated_database: MigratedDatabase,
) -> None:
    url = make_url(migrated_database.owner_url).set(drivername="postgresql")
    with psycopg.connect(url.render_as_string(hide_password=False)) as conn:
        grants = conn.execute(
            "SELECT privilege_type FROM information_schema.role_table_grants "
            "WHERE table_name = 'ai_ledger' AND grantee = 'qbank_app' ORDER BY 1"
        ).fetchall()
    assert [g[0] for g in grants] == ["INSERT", "SELECT"]


# --- Two runs at once -----------------------------------------------------------------------------


def test_two_runs_started_together_cannot_both_pass_a_budget_with_room_for_one(
    db: Database, owner_db: Database, team: dict[str, Member]
) -> None:
    person = team["faculty"]
    configure(owner_db, person, rate="100", default="100")
    ready = threading.Barrier(2)
    outcomes: list[str] = []

    def attempt() -> None:
        run = new_id()
        try:
            with db.transaction(context(person)) as session:
                ready.wait(timeout=10)
                budget.reserve(
                    session,
                    organization_id=person.org_id,
                    user_id=person.user_id,
                    run_id=run,
                    estimate_usd=D("0.7"),
                )
            outcomes.append("reserved")
        except AppError as problem:
            outcomes.append(problem.code)

    threads = [threading.Thread(target=attempt) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    assert sorted(outcomes) == ["AI_BUDGET_EXCEEDED", "reserved"]
    assert standing(db, person).spent_inr == D("70")


# --- Another coaching is another ledger ----------------------------------------------------------


def test_one_coachings_spend_is_invisible_to_another(
    db: Database, owner_db: Database, team: dict[str, Member]
) -> None:
    person = team["faculty"]
    configure(owner_db, person, rate="80", default="100")
    reserve(db, person, "0.5")
    stranger = make_member(owner_db, "FACULTY", coaching_name="Another Coaching")
    assert standing(db, stranger).spent_usd == D("0")
    with db.transaction(context(stranger)) as session:
        seen = session.scalars(select(LedgerEntry)).all()
    assert all(entry.organization_id == stranger.org_id for entry in seen)


# --- Usage over the API ---------------------------------------------------------------------------


def test_a_member_sees_their_own_standing_and_an_admin_sees_everyones(
    client: TestClient, db: Database, owner_db: Database, team: dict[str, Member]
) -> None:
    person = team["faculty"]
    configure(owner_db, person, rate="80", default="100")
    run = reserve(db, person, "0.5")
    settle(db, person, run, "0.25")

    faculty = sign_in(client, person.email)
    mine = client.get(f"{USAGE}/me", headers=faculty)
    assert mine.status_code == 200
    assert mine.json()["spent_inr"] == "20.00"
    assert mine.json()["spent_usd"] == "0.250000"
    assert mine.json()["limit_inr"] == "100.00"
    assert mine.json()["remaining_inr"] == "80.00"
    assert mine.json()["state"] == "OK"
    assert client.get(USAGE, headers=faculty).status_code == 403  # not everyone's

    admin = sign_in(client, team["admin"].email)
    everyone = client.get(USAGE, headers=admin)
    assert everyone.status_code == 200
    rows = {row["user_id"]: row for row in everyone.json()["data"]}
    assert rows[str(person.user_id)]["spent_inr"] == "20.00"
    assert rows[str(person.user_id)]["display_name"]
    assert str(team["owner"].user_id) not in rows  # nobody lists someone with no usage
    assert client.get(USAGE, params={"month": "2020-01"}, headers=admin).json()["data"] == []
    assert client.get(USAGE, params={"month": "2020-13"}, headers=admin).status_code in (400, 422)


def test_an_admin_corrects_usage_and_it_is_audited(
    client: TestClient, db: Database, owner_db: Database, team: dict[str, Member]
) -> None:
    person = team["faculty"]
    configure(owner_db, person, rate="100", default="100")
    admin = sign_in(client, team["admin"].email)
    body = {"user_id": str(person.user_id), "amount_usd": "0.85", "note": "October invoice"}
    done = client.post(f"{USAGE}/adjustments", json=body, headers=admin)
    assert done.status_code == 201, done.text
    assert done.json()["spent_inr"] == "85.00"
    assert done.json()["state"] == "WARNING"
    assert notices(owner_db, person) == ["AI_BUDGET_WARNING"]
    back = client.post(
        f"{USAGE}/adjustments",
        json={**body, "amount_usd": "-0.5", "note": "Entered twice"},
        headers=admin,
    )
    assert back.json()["spent_inr"] == "35.00"

    kinds = [e.entry_kind for e in entries(owner_db, person)]
    assert kinds.count("ADJUST") == 2
    with owner_db.transaction(TenantContext(organization_id=person.org_id)) as session:
        events = list(
            session.scalars(
                select(AuditEvent).where(
                    AuditEvent.organization_id == person.org_id,
                    AuditEvent.action == "AI_USAGE_ADJUSTED",
                )
            )
        )
    assert len(events) == 2
    assert events[0].actor_user_id == team["admin"].user_id


def test_adjustments_need_an_admin_a_member_and_a_reason(
    client: TestClient, owner_db: Database, team: dict[str, Member]
) -> None:
    person = team["faculty"]
    body = {"user_id": str(person.user_id), "amount_usd": "1", "note": "x"}
    faculty = sign_in(client, person.email)
    assert client.post(f"{USAGE}/adjustments", json=body, headers=faculty).status_code == 403
    admin = sign_in(client, team["admin"].email)
    stranger = make_member(owner_db, "FACULTY", coaching_name="Another Coaching")
    outsider = client.post(
        f"{USAGE}/adjustments", json={**body, "user_id": str(stranger.user_id)}, headers=admin
    )
    assert outsider.status_code == 404
    for bad in (
        {"note": ""},
        {"note": "n" * 301},
        {"amount_usd": "abc"},
        {"amount_usd": "1.0000001"},
    ):
        sent = client.post(f"{USAGE}/adjustments", json={**body, **bad}, headers=admin)
        assert sent.status_code in (400, 422)
