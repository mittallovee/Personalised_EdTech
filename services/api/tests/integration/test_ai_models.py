"""M5 PR 5b-1: the coaching's AI model list (H-03, H-17; test T45).

A refresh runs as a background job with the coaching's stored key and copies the provider's list
into the coaching's rows. It never changes what an admin set (enabled, the overlay); a model that
disappears stays on record as unavailable; a failure is recorded as a kind, never retried by itself.
No real provider is called: the job is given a scripted fake.
"""

import base64
from collections.abc import Iterator
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from qbank.core.config import AppEnv, Settings
from qbank.core.db import Database
from qbank.core.jobs import JobRegistry, Worker
from qbank.core.secretbox import build_keyring
from qbank.core.tenancy import TenantContext
from qbank.main import create_app
from qbank.modules.ai import jobs as ai_jobs
from qbank.modules.ai.models import AiModel
from qbank.modules.ai.names import Provider
from qbank.modules.ai.providers.base import ModelInfo, ProviderError, ProviderErrorKind
from qbank.modules.ai.providers.fake import FakeProvider
from qbank.modules.audit.models import AuditEvent
from tests.integration.conftest import Member, MigratedDatabase, make_member, sign_in

KEYS = "/api/v1/ai/keys"
MODELS = "/api/v1/ai/models"
MASTER = base64.b64encode(bytes(range(32))).decode()
OTHER_MASTER = base64.b64encode(bytes(range(1, 33))).decode()
KEY = "fake-openai-" + "a" * 16 + "0001"

PRICED = ModelInfo(
    "gpt-priced",
    "GPT priced",
    supports_vision=True,
    supports_json=True,
    context_tokens=128000,
    price_in_per_mtok=Decimal("0.1"),
    price_out_per_mtok=Decimal("0.4"),
)
PLAIN = ModelInfo("gpt-plain", "GPT plain")
THIRD = ModelInfo("gpt-third", "GPT third", supports_json=False)


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


@pytest.fixture(autouse=True)
def empty_queue(owner_db: Database) -> None:
    """Jobs left by other tests must not be picked up by this test's worker."""
    with owner_db.transaction(TenantContext(is_platform=True)) as session:
        session.execute(
            text("UPDATE jobs SET state = 'FAILED' WHERE state IN ('QUEUED', 'RUNNING')")
        )


@pytest.fixture
def fake(monkeypatch: pytest.MonkeyPatch) -> FakeProvider:
    provider = FakeProvider(name=Provider.OPENAI, models=(PRICED, PLAIN))
    monkeypatch.setattr(ai_jobs, "provider_for", lambda _provider: provider)
    return provider


def run_jobs(worker_db: Database, master: str = MASTER) -> int:
    registry = JobRegistry()
    ai_jobs.register_jobs(registry, build_keyring(master, "k1", None))
    return Worker(worker_db, registry, worker_id="test").run_until_idle()


def refresh(client: TestClient, headers: dict[str, str], provider: str = "OPENAI"):  # type: ignore[no-untyped-def]
    return client.post(f"{MODELS}/refresh", json={"provider": provider}, headers=headers)


def listed(client: TestClient, headers: dict[str, str], **params: str):  # type: ignore[no-untyped-def]
    response = client.get(MODELS, params=params, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def by_id(body: dict, model_id: str) -> dict:  # type: ignore[type-arg]
    return next(m for m in body["data"] if m["model_id"] == model_id)


def state(body: dict, provider: str = "OPENAI") -> dict:  # type: ignore[type-arg]
    return next(p for p in body["providers"] if p["provider"] == provider)


@pytest.fixture
def stocked(
    client: TestClient, team: dict[str, Member], worker_db: Database, fake: FakeProvider
) -> dict[str, str]:
    """An admin with an OpenAI key stored and the list fetched once."""
    headers = sign_in(client, team["admin"].email)
    assert client.put(f"{KEYS}/OPENAI", json={"key": KEY}, headers=headers).status_code == 200
    assert refresh(client, headers).status_code == 202
    assert run_jobs(worker_db) == 1
    return headers


# --- Refreshing --------------------------------------------------------------------------------


def test_a_refresh_fills_the_list_with_what_the_provider_said_and_enables_nothing(
    stocked: dict[str, str], client: TestClient, fake: FakeProvider
) -> None:
    body = listed(client, stocked)
    assert [m["model_id"] for m in body["data"]] == ["gpt-plain", "gpt-priced"]
    priced = by_id(body, "gpt-priced")
    assert priced["display_name"] == "GPT priced"
    assert priced["enabled"] is False
    assert priced["available"] is True
    assert (priced["price_in_per_mtok"], priced["price_out_per_mtok"]) == ("0.1", "0.4")
    assert priced["price_source"] == "PROVIDER"
    assert (priced["supports_vision"], priced["supports_json"]) == (True, True)
    assert priced["context_tokens"] == 128000
    assert priced["batch_supported"] is False  # only an admin can say a model supports batches
    plain = by_id(body, "gpt-plain")
    assert plain["price_in_per_mtok"] is None
    assert plain["price_source"] == "UNKNOWN"
    assert plain["supports_json"] is None
    openai = state(body)
    assert openai["configured"] is True
    assert openai["last_error"] is None
    assert openai["last_refreshed_at"] is not None
    assert state(body, "ANTHROPIC")["configured"] is False
    # The key the job used is the one the admin stored, and nothing else was sent anywhere.
    assert [call_key for call_key in fake.listed] == [KEY]


def test_pressing_refresh_twice_in_a_minute_starts_one_job(
    client: TestClient, team: dict[str, Member], fake: FakeProvider, worker_db: Database
) -> None:
    headers = sign_in(client, team["admin"].email)
    client.put(f"{KEYS}/OPENAI", json={"key": KEY}, headers=headers)
    first = refresh(client, headers)
    second = refresh(client, headers)
    assert first.status_code == second.status_code == 202
    assert first.json()["job_id"] == second.json()["job_id"]
    assert run_jobs(worker_db) == 1
    assert len(fake.listed) == 1


def test_a_second_refresh_keeps_what_the_admin_set_and_follows_the_provider(
    stocked: dict[str, str], client: TestClient, fake: FakeProvider, worker_db: Database
) -> None:
    model = by_id(listed(client, stocked), "gpt-priced")
    enabled = client.patch(
        f"{MODELS}/{model['id']}",
        json={"enabled": True, "overlay": {"price_in": "9.5", "batch_supported": True}},
        headers={**stocked, "If-Match": f'"rev-{model["revision"]}"'},
    )
    assert enabled.status_code == 200, enabled.text

    # The provider drops one model, changes the other's price and adds a third.
    changed = ModelInfo("gpt-priced", "GPT priced v2", price_in_per_mtok=Decimal("0.2"))
    fake.models = (changed, THIRD)
    assert refresh(client, stocked).status_code == 202
    # A new minute is a new job: make the previous one's key not collide.
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("qbank.modules.ai.models_api.time", lambda: 10**10)
        again = refresh(client, stocked)
    assert again.status_code == 202
    run_jobs(worker_db)

    body = listed(client, stocked)
    priced = by_id(body, "gpt-priced")
    assert priced["display_name"] == "GPT priced v2"
    assert priced["enabled"] is True  # untouched by the refresh
    assert priced["overlay"]["price_in"] == "9.5"
    assert priced["price_in_per_mtok"] == "9.5"  # the admin's price wins over 0.2
    assert priced["price_source"] == "ADMIN"
    assert priced["batch_supported"] is True
    assert priced["supports_vision"] is None  # the provider no longer says
    third = by_id(body, "gpt-third")
    assert (third["enabled"], third["available"], third["supports_json"]) == (False, True, False)
    gone = by_id(body, "gpt-plain")
    assert gone["available"] is False  # no longer listed, but still on record
    only_listed = listed(client, stocked, available="true")
    assert [m["model_id"] for m in only_listed["data"]] == ["gpt-priced", "gpt-third"]

    # It comes back when the provider lists it again.
    fake.models = (changed, THIRD, PLAIN)
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("qbank.modules.ai.models_api.time", lambda: 2 * 10**10)
        refresh(client, stocked)
    run_jobs(worker_db)
    assert by_id(listed(client, stocked), "gpt-plain")["available"] is True


def test_a_provider_failure_is_recorded_as_a_kind_and_changes_no_model(
    stocked: dict[str, str], client: TestClient, fake: FakeProvider, worker_db: Database
) -> None:
    before = listed(client, stocked)["data"]
    fake_failure = ProviderError(ProviderErrorKind.AUTH, status=401)

    def failing(_key: str) -> list[ModelInfo]:
        raise fake_failure

    fake.list_models = failing  # type: ignore[method-assign]
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("qbank.modules.ai.models_api.time", lambda: 3 * 10**10)
        refresh(client, stocked)
    assert run_jobs(worker_db) == 1  # the job itself finished: it is not retried
    body = listed(client, stocked)
    assert body["data"] == before
    assert state(body)["last_error"] == "AUTH"
    assert "401" not in str(state(body))  # only the kind, no text of the failure


def test_a_key_that_cannot_be_opened_is_recorded_not_retried(
    stocked: dict[str, str], client: TestClient, worker_db: Database
) -> None:
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("qbank.modules.ai.models_api.time", lambda: 4 * 10**10)
        refresh(client, stocked)
    run_jobs(worker_db, master=OTHER_MASTER)  # the worker was given a different master key
    assert state(listed(client, stocked))["last_error"] == "KEY_UNREADABLE"


def test_refresh_needs_a_stored_key_and_a_master_key(
    client: TestClient, team: dict[str, Member], migrated_database: MigratedDatabase
) -> None:
    headers = sign_in(client, team["admin"].email)
    missing = refresh(client, headers, "GOOGLE")
    assert missing.status_code == 409
    assert missing.json()["error"]["code"] == "AI_KEY_MISSING"
    settings = Settings(
        app_env=AppEnv.TEST, database_url=migrated_database.app_url, session_cookie_secure=False
    )
    with TestClient(create_app(settings)) as plain:
        refused = refresh(plain, sign_in(plain, team["admin"].email), "OPENAI")
    assert refused.status_code == 409
    assert refused.json()["error"]["code"] == "AI_NOT_CONFIGURED"


# --- Enabling and the admin's own facts --------------------------------------------------------


def test_enabling_a_model_is_audited_and_needs_the_current_etag(
    stocked: dict[str, str], client: TestClient, team: dict[str, Member], owner_db: Database
) -> None:
    model = by_id(listed(client, stocked), "gpt-priced")
    url = f"{MODELS}/{model['id']}"
    tag = f'"rev-{model["revision"]}"'
    assert client.patch(url, json={"enabled": True}, headers=stocked).status_code == 428
    stale = client.patch(url, json={"enabled": True}, headers={**stocked, "If-Match": '"rev-99"'})
    assert stale.status_code == 412
    done = client.patch(url, json={"enabled": True}, headers={**stocked, "If-Match": tag})
    assert done.status_code == 200
    assert done.json()["enabled"] is True
    assert done.headers["ETag"] == f'"rev-{model["revision"] + 1}"'
    # Doing it again with the new tag changes nothing and writes nothing.
    again = client.patch(
        url, json={"enabled": True}, headers={**stocked, "If-Match": done.headers["ETag"]}
    )
    assert again.json()["revision"] == done.json()["revision"]
    off = client.patch(
        url, json={"enabled": False}, headers={**stocked, "If-Match": done.headers["ETag"]}
    )
    assert off.json()["enabled"] is False

    with owner_db.transaction(TenantContext(organization_id=team["owner"].org_id)) as session:
        events = list(
            session.scalars(
                select(AuditEvent)
                .where(
                    AuditEvent.organization_id == team["owner"].org_id,
                    AuditEvent.entity_type == "ai_model",
                )
                .order_by(AuditEvent.created_at)
            )
        )
    assert [e.action for e in events] == ["AI_MODEL_ENABLED", "AI_MODEL_DISABLED"]
    assert events[0].after is not None
    assert events[0].after["model"] == "gpt-priced"
    assert events[0].actor_user_id == team["admin"].user_id


def test_a_model_the_provider_no_longer_lists_cannot_be_enabled(
    stocked: dict[str, str], client: TestClient, fake: FakeProvider, worker_db: Database
) -> None:
    fake.models = (PRICED,)
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("qbank.modules.ai.models_api.time", lambda: 5 * 10**10)
        refresh(client, stocked)
    run_jobs(worker_db)
    gone = by_id(listed(client, stocked), "gpt-plain")
    assert gone["available"] is False
    response = client.patch(
        f"{MODELS}/{gone['id']}",
        json={"enabled": True},
        headers={**stocked, "If-Match": f'"rev-{gone["revision"]}"'},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "AI_MODEL_UNAVAILABLE"


def test_the_overlay_wins_where_set_and_null_gives_the_provider_back(
    stocked: dict[str, str], client: TestClient
) -> None:
    plain = by_id(listed(client, stocked), "gpt-plain")
    url = f"{MODELS}/{plain['id']}"
    first = client.patch(
        url,
        json={"overlay": {"price_in": "3", "price_out": "15.5", "supports_json": True}},
        headers={**stocked, "If-Match": f'"rev-{plain["revision"]}"'},
    ).json()
    assert (first["price_in_per_mtok"], first["price_out_per_mtok"]) == ("3", "15.5")
    assert first["price_source"] == "ADMIN"
    assert first["supports_json"] is True
    assert first["overlay"]["price_in"] == "3"
    # Only what is sent changes: the price stays, the capability is removed.
    second = client.patch(
        url,
        json={"overlay": {"supports_json": None}},
        headers={**stocked, "If-Match": f'"rev-{first["revision"]}"'},
    ).json()
    assert second["price_in_per_mtok"] == "3"
    assert second["supports_json"] is None
    third = client.patch(
        url,
        json={"overlay": {"price_in": None, "price_out": None}},
        headers={**stocked, "If-Match": f'"rev-{second["revision"]}"'},
    ).json()
    assert third["price_source"] == "UNKNOWN"
    assert third["overlay"] == {
        "supports_vision": None,
        "supports_json": None,
        "price_in": None,
        "price_out": None,
        "batch_supported": None,
        "batch_discount": None,
    }


@pytest.mark.parametrize(
    "overlay",
    [
        {"price_in": "-1"},
        {"price_out": "100001"},
        {"price_in": "1.1234567"},
        {"batch_discount": "0"},
        {"batch_discount": "1.5"},
        {"unknown_fact": True},
    ],
)
def test_an_overlay_that_makes_no_sense_is_refused(
    stocked: dict[str, str], client: TestClient, overlay: dict[str, object]
) -> None:
    model = by_id(listed(client, stocked), "gpt-priced")
    response = client.patch(
        f"{MODELS}/{model['id']}",
        json={"overlay": overlay},
        headers={**stocked, "If-Match": f'"rev-{model["revision"]}"'},
    )
    assert response.status_code in (400, 422)
    assert by_id(listed(client, stocked), "gpt-priced")["revision"] == model["revision"]


def test_prices_are_exact_decimals_never_floats(
    stocked: dict[str, str], client: TestClient, team: dict[str, Member], owner_db: Database
) -> None:
    with owner_db.transaction(TenantContext(organization_id=team["owner"].org_id)) as session:
        row = session.scalars(
            select(AiModel).where(
                AiModel.organization_id == team["owner"].org_id, AiModel.model_id == "gpt-priced"
            )
        ).one()
        assert row.price_in == Decimal("0.100000")
        assert isinstance(row.price_in, Decimal)


# --- Who may and whose ---------------------------------------------------------------------------


def test_faculty_and_signed_out_visitors_cannot_use_the_model_routes(
    stocked: dict[str, str], client: TestClient, team: dict[str, Member]
) -> None:
    model = by_id(listed(client, stocked), "gpt-priced")
    faculty = sign_in(client, team["faculty"].email)
    assert client.get(MODELS, headers=faculty).status_code == 403
    assert refresh(client, faculty).status_code == 403
    patch = client.patch(
        f"{MODELS}/{model['id']}",
        json={"enabled": True},
        headers={**faculty, "If-Match": '"rev-1"'},
    )
    assert patch.status_code == 403
    client.cookies.clear()
    assert client.get(MODELS).status_code == 401


def test_one_coaching_never_sees_or_changes_anothers_models(
    stocked: dict[str, str], client: TestClient, owner_db: Database
) -> None:
    model = by_id(listed(client, stocked), "gpt-priced")
    stranger = make_member(owner_db, "ADMIN", coaching_name="Other Coaching")
    headers = sign_in(client, stranger.email)
    assert listed(client, headers)["data"] == []
    response = client.patch(
        f"{MODELS}/{model['id']}",
        json={"enabled": True},
        headers={**headers, "If-Match": f'"rev-{model["revision"]}"'},
    )
    assert response.status_code == 404
    assert state(listed(client, headers))["last_refreshed_at"] is None


def test_the_filters_narrow_the_list(stocked: dict[str, str], client: TestClient) -> None:
    model = by_id(listed(client, stocked), "gpt-priced")
    client.patch(
        f"{MODELS}/{model['id']}",
        json={"enabled": True},
        headers={**stocked, "If-Match": f'"rev-{model["revision"]}"'},
    )
    assert [m["model_id"] for m in listed(client, stocked, enabled="true")["data"]] == [
        "gpt-priced"
    ]
    assert [m["model_id"] for m in listed(client, stocked, enabled="false")["data"]] == [
        "gpt-plain"
    ]
    assert listed(client, stocked, provider="GOOGLE")["data"] == []
