"""M5 PR 5b-2: what an admin sets for the AI features (H-03, H-05, H-06; part of test T45).

The rate and default budget, the model and mode offered first for each operation, and a person's
own budget. Each is saved under If-Match, audited, limited to the Owner and admins, and confined
to the coaching. No provider is called: models are rows written directly.
"""

import base64
from collections.abc import Iterator
from decimal import Decimal
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from qbank.core.config import AppEnv, Settings
from qbank.core.db import Database
from qbank.core.tenancy import TenantContext
from qbank.main import create_app
from qbank.modules.ai.models import AiModel
from qbank.modules.audit.models import AuditEvent
from tests.integration.conftest import Member, MigratedDatabase, make_member, sign_in

SETTINGS = "/api/v1/ai/settings"
OPERATIONS = "/api/v1/ai/operations"
BUDGETS = "/api/v1/ai/budgets"
MASTER = base64.b64encode(bytes(range(32))).decode()


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


def add_model(
    owner_db: Database,
    org_id: UUID,
    model_id: str,
    *,
    enabled: bool = True,
    available: bool = True,
    supports_json: bool | None = True,
    batch: bool | None = None,
) -> UUID:
    with owner_db.transaction(TenantContext(organization_id=org_id)) as session:
        row = AiModel(
            organization_id=org_id,
            provider="OPENAI",
            model_id=model_id,
            display_name=model_id.upper(),
            supports_json=supports_json,
            overlay_batch_supported=batch,
            enabled=enabled,
            available=available,
        )
        session.add(row)
        session.flush()
        return row.id


@pytest.fixture
def admin(client: TestClient, team: dict[str, Member]) -> dict[str, str]:
    return sign_in(client, team["admin"].email)


def tag(response_headers: dict[str, str]) -> dict[str, str]:
    return {"If-Match": response_headers["ETag"]}


# --- The rate and the default budget -----------------------------------------------------------


def test_nothing_is_set_to_begin_with(client: TestClient, admin: dict[str, str]) -> None:
    response = client.get(SETTINGS, headers=admin)
    assert response.status_code == 200
    assert response.json() == {"usd_to_inr": None, "default_budget_inr": None, "revision": 0}
    assert response.headers["ETag"] == '"rev-0"'


def test_the_rate_and_budget_are_saved_exactly_audited_and_need_the_current_etag(
    client: TestClient, admin: dict[str, str], team: dict[str, Member], owner_db: Database
) -> None:
    body = {"usd_to_inr": "83.5", "default_budget_inr": "500.50"}
    assert client.put(SETTINGS, json=body, headers=admin).status_code == 428
    stale = client.put(SETTINGS, json=body, headers={**admin, "If-Match": '"rev-7"'})
    assert stale.status_code == 412
    saved = client.put(SETTINGS, json=body, headers={**admin, "If-Match": '"rev-0"'})
    assert saved.status_code == 200, saved.text
    assert saved.json() == {"usd_to_inr": "83.5", "default_budget_inr": "500.5", "revision": 1}
    assert saved.headers["ETag"] == '"rev-1"'
    # The same stale tag now fails: the first save moved the revision on.
    again = client.put(SETTINGS, json=body, headers={**admin, "If-Match": '"rev-0"'})
    assert again.status_code == 412
    cleared = client.put(
        SETTINGS,
        json={"usd_to_inr": None, "default_budget_inr": None},
        headers={**admin, "If-Match": '"rev-1"'},
    )
    assert cleared.json() == {"usd_to_inr": None, "default_budget_inr": None, "revision": 2}

    with owner_db.transaction(TenantContext(organization_id=team["owner"].org_id)) as session:
        events = list(
            session.scalars(
                select(AuditEvent)
                .where(
                    AuditEvent.organization_id == team["owner"].org_id,
                    AuditEvent.entity_type == "ai_settings",
                )
                .order_by(AuditEvent.created_at)
            )
        )
    assert [e.action for e in events] == ["AI_SETTINGS_CHANGED", "AI_SETTINGS_CHANGED"]
    assert events[0].before == {"usd_to_inr": None, "default_budget_inr": None}
    assert events[0].after == {"usd_to_inr": "83.5", "default_budget_inr": "500.5"}
    assert events[0].actor_user_id == team["admin"].user_id


@pytest.mark.parametrize(
    "body",
    [
        {"usd_to_inr": "0", "default_budget_inr": None},
        {"usd_to_inr": "-1", "default_budget_inr": None},
        {"usd_to_inr": "10001", "default_budget_inr": None},
        {"usd_to_inr": None, "default_budget_inr": "-0.01"},
        {"usd_to_inr": None, "default_budget_inr": "1.234"},
        {"usd_to_inr": None},
        {"usd_to_inr": None, "default_budget_inr": None, "extra": 1},
    ],
)
def test_a_rate_or_budget_that_makes_no_sense_is_refused(
    client: TestClient, admin: dict[str, str], body: dict[str, object]
) -> None:
    response = client.put(SETTINGS, json=body, headers={**admin, "If-Match": '"rev-0"'})
    assert response.status_code in (400, 422)


def test_only_the_owner_and_admins_reach_these_settings(
    client: TestClient, team: dict[str, Member]
) -> None:
    faculty = sign_in(client, team["faculty"].email)
    for url in (SETTINGS, OPERATIONS, BUDGETS):
        assert client.get(url, headers=faculty).status_code == 403
    stale = {**faculty, "If-Match": '"rev-0"'}
    body = {"usd_to_inr": None, "default_budget_inr": None}
    assert client.put(SETTINGS, json=body, headers=stale).status_code == 403
    operation = client.put(f"{OPERATIONS}/TAG", json={"default_model_id": None}, headers=stale)
    assert operation.status_code == 403
    own = f"{BUDGETS}/{team['faculty'].user_id}"
    assert client.put(own, json={"monthly_inr": "10"}, headers=stale).status_code == 403
    assert client.delete(own, headers=stale).status_code == 403
    owner = sign_in(client, team["owner"].email)  # the client holds one session: this replaces it
    for url in (SETTINGS, OPERATIONS, BUDGETS):
        assert client.get(url, headers=owner).status_code == 200


# --- The model, mode and fallbacks of an operation ---------------------------------------------


def test_the_four_operations_are_always_listed_unset_at_first(
    client: TestClient, admin: dict[str, str]
) -> None:
    body = client.get(OPERATIONS, headers=admin).json()
    assert [o["operation"] for o in body["data"]] == ["TAG", "TRANSLATE", "SOLVE", "VERIFY"]
    for item in body["data"]:
        assert item["default_model"] is None
        assert item["mode"] == "NOW"
        assert item["fallbacks"] == []
        assert item["problem"] is None
        assert item["revision"] == 0


def test_an_operation_gets_a_model_and_fallbacks_and_it_is_audited(
    client: TestClient,
    admin: dict[str, str],
    team: dict[str, Member],
    owner_db: Database,
) -> None:
    org = team["owner"].org_id
    first = add_model(owner_db, org, "gpt-first")
    second = add_model(owner_db, org, "gpt-second")
    third = add_model(owner_db, org, "gpt-third")
    body = {
        "default_model_id": str(first),
        "mode": "NOW",
        "fallback_model_ids": [str(second), str(third)],
    }
    assert client.put(f"{OPERATIONS}/TAG", json=body, headers=admin).status_code == 428
    saved = client.put(f"{OPERATIONS}/TAG", json=body, headers={**admin, "If-Match": '"rev-0"'})
    assert saved.status_code == 200, saved.text
    result = saved.json()
    assert result["default_model"]["model_id"] == "gpt-first"
    assert [m["model_id"] for m in result["fallbacks"]] == ["gpt-second", "gpt-third"]
    assert result["revision"] == 1
    assert saved.headers["ETag"] == '"rev-1"'

    listing = client.get(OPERATIONS, headers=admin).json()["data"]
    assert listing[0]["default_model"]["model_id"] == "gpt-first"
    assert listing[1]["default_model"] is None  # the other operations are untouched

    changed = client.put(
        f"{OPERATIONS}/TAG",
        json={"default_model_id": str(second), "mode": "NOW", "fallback_model_ids": []},
        headers={**admin, "If-Match": '"rev-1"'},
    )
    assert changed.json()["fallbacks"] == []
    assert changed.json()["revision"] == 2

    with owner_db.transaction(TenantContext(organization_id=org)) as session:
        events = list(
            session.scalars(
                select(AuditEvent)
                .where(AuditEvent.organization_id == org, AuditEvent.entity_type == "ai_operation")
                .order_by(AuditEvent.created_at)
            )
        )
    assert [e.action for e in events] == ["AI_OPERATION_DEFAULT_CHANGED"] * 2
    assert events[0].before is not None and events[0].after is not None
    assert events[0].before["default_model_id"] is None
    assert events[0].after["default_model"] == "OPENAI/gpt-first"
    assert events[1].before["default_model"] is None  # names are kept for what is set, not before
    assert events[1].after["fallback_model_ids"] == []


def test_a_stale_operation_save_is_refused(
    client: TestClient, admin: dict[str, str], team: dict[str, Member], owner_db: Database
) -> None:
    model = add_model(owner_db, team["owner"].org_id, "gpt-first")
    body = {"default_model_id": str(model), "mode": "NOW", "fallback_model_ids": []}
    assert client.put(f"{OPERATIONS}/SOLVE", json=body, headers={**admin, "If-Match": '"rev-0"'})
    stale = client.put(f"{OPERATIONS}/SOLVE", json=body, headers={**admin, "If-Match": '"rev-0"'})
    assert stale.status_code == 412


def test_a_model_must_be_enabled_listed_and_able_to_return_json(
    client: TestClient, admin: dict[str, str], team: dict[str, Member], owner_db: Database
) -> None:
    org = team["owner"].org_id
    cases = {
        "AI_MODEL_NOT_ENABLED": add_model(owner_db, org, "off", enabled=False),
        "AI_MODEL_UNAVAILABLE": add_model(owner_db, org, "gone", available=False),
        "AI_MODEL_NO_JSON": add_model(owner_db, org, "nojson", supports_json=False),
    }
    for code, model in cases.items():
        response = client.put(
            f"{OPERATIONS}/TAG",
            json={"default_model_id": str(model), "fallback_model_ids": []},
            headers={**admin, "If-Match": '"rev-0"'},
        )
        assert response.status_code == 409, code
        assert response.json()["error"]["code"] == code
    # A fallback is held to the same rule as the first model.
    good = add_model(owner_db, org, "good")
    refused = client.put(
        f"{OPERATIONS}/TAG",
        json={
            "default_model_id": str(good),
            "fallback_model_ids": [str(cases["AI_MODEL_NOT_ENABLED"])],
        },
        headers={**admin, "If-Match": '"rev-0"'},
    )
    assert refused.json()["error"]["code"] == "AI_MODEL_NOT_ENABLED"
    # An unknown JSON ability (the provider does not say) is allowed.
    unknown = add_model(owner_db, org, "unknown", supports_json=None)
    ok = client.put(
        f"{OPERATIONS}/TAG",
        json={"default_model_id": str(unknown), "fallback_model_ids": []},
        headers={**admin, "If-Match": '"rev-0"'},
    )
    assert ok.status_code == 200


def test_economy_needs_a_model_the_admin_marked_for_batch_runs(
    client: TestClient, admin: dict[str, str], team: dict[str, Member], owner_db: Database
) -> None:
    org = team["owner"].org_id
    plain = add_model(owner_db, org, "plain")
    batch = add_model(owner_db, org, "batch", batch=True)
    refused = client.put(
        f"{OPERATIONS}/TRANSLATE",
        json={"default_model_id": str(plain), "mode": "ECONOMY", "fallback_model_ids": []},
        headers={**admin, "If-Match": '"rev-0"'},
    )
    assert refused.status_code == 409
    assert refused.json()["error"]["code"] == "AI_ECONOMY_UNAVAILABLE"
    none = client.put(
        f"{OPERATIONS}/TRANSLATE",
        json={"default_model_id": None, "mode": "ECONOMY", "fallback_model_ids": []},
        headers={**admin, "If-Match": '"rev-0"'},
    )
    assert none.status_code == 422
    done = client.put(
        f"{OPERATIONS}/TRANSLATE",
        json={"default_model_id": str(batch), "mode": "ECONOMY", "fallback_model_ids": []},
        headers={**admin, "If-Match": '"rev-0"'},
    )
    assert done.status_code == 200
    assert done.json()["mode"] == "ECONOMY"


def test_the_chain_is_at_most_three_models_each_once_and_starts_with_a_first(
    client: TestClient, admin: dict[str, str], team: dict[str, Member], owner_db: Database
) -> None:
    org = team["owner"].org_id
    ids = [str(add_model(owner_db, org, f"m{n}")) for n in range(4)]
    headers = {**admin, "If-Match": '"rev-0"'}

    def put(body: dict[str, object]):  # type: ignore[no-untyped-def]
        return client.put(f"{OPERATIONS}/VERIFY", json=body, headers=headers)

    assert put({"default_model_id": ids[0], "fallback_model_ids": ids[1:]}).status_code in (
        400,
        422,
    )
    repeated = put({"default_model_id": ids[0], "fallback_model_ids": [ids[1], ids[0]]})
    assert repeated.json()["error"]["code"] == "AI_MODEL_REPEATED"
    twice = put({"default_model_id": ids[0], "fallback_model_ids": [ids[1], ids[1]]})
    assert twice.json()["error"]["code"] == "AI_MODEL_REPEATED"
    lonely = put({"default_model_id": None, "fallback_model_ids": [ids[1]]})
    assert lonely.json()["error"]["code"] == "AI_FALLBACK_WITHOUT_DEFAULT"
    unknown = put({"default_model_id": "00000000-0000-4000-8000-000000000000"})
    assert unknown.json()["error"]["code"] == "AI_MODEL_NOT_FOUND"


def test_another_coachings_model_cannot_be_chosen(
    client: TestClient, admin: dict[str, str], owner_db: Database
) -> None:
    stranger = make_member(owner_db, "OWNER", coaching_name="Another Coaching")
    theirs = add_model(owner_db, stranger.org_id, "theirs")
    response = client.put(
        f"{OPERATIONS}/TAG",
        json={"default_model_id": str(theirs), "fallback_model_ids": []},
        headers={**admin, "If-Match": '"rev-0"'},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "AI_MODEL_NOT_FOUND"


def test_a_default_that_was_disabled_later_is_shown_with_its_problem(
    client: TestClient, admin: dict[str, str], team: dict[str, Member], owner_db: Database
) -> None:
    org = team["owner"].org_id
    model = add_model(owner_db, org, "later-off")
    client.put(
        f"{OPERATIONS}/TAG",
        json={"default_model_id": str(model), "fallback_model_ids": []},
        headers={**admin, "If-Match": '"rev-0"'},
    )
    with owner_db.transaction(TenantContext(organization_id=org)) as session:
        row = session.get(AiModel, model)
        assert row is not None
        row.enabled = False
    first = client.get(OPERATIONS, headers=admin).json()["data"][0]
    assert first["problem"] == "MODEL_DISABLED"
    assert first["default_model"]["enabled"] is False
    with owner_db.transaction(TenantContext(organization_id=org)) as session:
        row = session.get(AiModel, model)
        assert row is not None
        row.available = False
    assert client.get(OPERATIONS, headers=admin).json()["data"][0]["problem"] == "MODEL_UNAVAILABLE"


def test_the_operation_name_is_checked(client: TestClient, admin: dict[str, str]) -> None:
    response = client.put(
        f"{OPERATIONS}/DANCE",
        json={"default_model_id": None},
        headers={**admin, "If-Match": '"rev-0"'},
    )
    assert response.status_code in (400, 422)


# --- A person's own budget -----------------------------------------------------------------------


def test_a_member_gets_a_budget_of_their_own_and_loses_it_again(
    client: TestClient, admin: dict[str, str], team: dict[str, Member], owner_db: Database
) -> None:
    faculty = team["faculty"]
    url = f"{BUDGETS}/{faculty.user_id}"
    assert client.get(BUDGETS, headers=admin).json() == {"data": []}
    assert client.put(url, json={"monthly_inr": "250"}, headers=admin).status_code == 428
    saved = client.put(url, json={"monthly_inr": "250"}, headers={**admin, "If-Match": '"rev-0"'})
    assert saved.status_code == 200, saved.text
    assert saved.json()["monthly_inr"] == "250"
    assert saved.json()["revision"] == 1
    assert saved.json()["display_name"]
    stale = client.put(url, json={"monthly_inr": "1"}, headers={**admin, "If-Match": '"rev-0"'})
    assert stale.status_code == 412
    zero = client.put(url, json={"monthly_inr": "0"}, headers={**admin, **tag(saved.headers)})
    assert zero.json()["monthly_inr"] == "0"  # zero means no AI use, and is allowed
    listing = client.get(BUDGETS, headers=admin).json()["data"]
    assert [(b["user_id"], b["monthly_inr"]) for b in listing] == [(str(faculty.user_id), "0")]

    no_tag = client.delete(url, headers=admin)
    assert no_tag.status_code == 428
    gone = client.delete(url, headers={**admin, **tag(zero.headers)})
    assert gone.status_code == 204
    assert client.get(BUDGETS, headers=admin).json() == {"data": []}
    assert client.delete(url, headers={**admin, "If-Match": '"rev-3"'}).status_code == 404

    with owner_db.transaction(TenantContext(organization_id=faculty.org_id)) as session:
        events = list(
            session.scalars(
                select(AuditEvent)
                .where(
                    AuditEvent.organization_id == faculty.org_id,
                    AuditEvent.entity_type == "ai_budget",
                )
                .order_by(AuditEvent.created_at)
            )
        )
    assert [e.action for e in events] == [
        "AI_BUDGET_CHANGED",
        "AI_BUDGET_CHANGED",
        "AI_BUDGET_CLEARED",
    ]
    assert events[0].after == {"user_id": str(faculty.user_id), "monthly_inr": "250"}
    assert events[2].before == {"user_id": str(faculty.user_id), "monthly_inr": "0"}


def test_a_budget_goes_only_to_a_member_of_this_coaching(
    client: TestClient, admin: dict[str, str], owner_db: Database
) -> None:
    stranger = make_member(owner_db, "FACULTY", coaching_name="Another Coaching")
    response = client.put(
        f"{BUDGETS}/{stranger.user_id}",
        json={"monthly_inr": "10"},
        headers={**admin, "If-Match": '"rev-0"'},
    )
    assert response.status_code == 404
    unknown = client.put(
        f"{BUDGETS}/00000000-0000-4000-8000-000000000000",
        json={"monthly_inr": "10"},
        headers={**admin, "If-Match": '"rev-0"'},
    )
    assert unknown.status_code == 404


def test_budgets_are_exact_and_refuse_nonsense(
    client: TestClient, admin: dict[str, str], team: dict[str, Member]
) -> None:
    url = f"{BUDGETS}/{team['faculty'].user_id}"
    headers = {**admin, "If-Match": '"rev-0"'}
    for bad in ("-1", "1.005", "abc", "1000000001"):
        assert client.put(url, json={"monthly_inr": bad}, headers=headers).status_code in (400, 422)
    ok = client.put(url, json={"monthly_inr": "0.10"}, headers=headers)
    assert Decimal(ok.json()["monthly_inr"]) == Decimal("0.1")


def test_settings_of_one_coaching_are_not_seen_by_another(
    client: TestClient, admin: dict[str, str], owner_db: Database
) -> None:
    client.put(
        SETTINGS,
        json={"usd_to_inr": "90", "default_budget_inr": "100"},
        headers={**admin, "If-Match": '"rev-0"'},
    )
    other = make_member(owner_db, "ADMIN", coaching_name="Another Coaching")
    theirs = sign_in(client, other.email)
    assert client.get(SETTINGS, headers=theirs).json()["revision"] == 0
    assert client.get(BUDGETS, headers=theirs).json() == {"data": []}
