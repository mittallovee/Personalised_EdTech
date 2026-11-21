"""M5 PR 5h: Economy (batch) runs (tests T50, T51, T52; H-18, ADR-0009).

A scripted fake provider with a batch service stands in for the real ones. Jobs are run by a real
``Worker`` on the worker database role, so what is proved here is what the background process does:
at-most-once submission, settlement of every ending, cancelling being final for applying, and the
requester being checked again when the result arrives.
"""

from decimal import Decimal
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from qbank.core.db import Database
from qbank.core.jobs import JobRegistry, Worker
from qbank.core.tenancy import TenantContext
from qbank.modules.ai.jobs import register_jobs
from qbank.modules.ai.models import AiRun, AiRunAttempt
from qbank.modules.ai.providers.base import (
    BatchState,
    ProviderError,
    ProviderErrorKind,
    StructuredResult,
)
from qbank.modules.notifications.models import Notification
from qbank.modules.organizations.models import Membership
from tests.integration.ai_support import QUESTIONS, D, World
from tests.integration.conftest import sign_in

ECONOMY = {"mode": "ECONOMY"}


class Plant:
    """A world whose model offers batch, plus a worker to run the background jobs."""

    def __init__(self, world: World, worker_db: Database) -> None:
        self.world = world
        self.model = world.add_model("fake-batch", batch=True, discount=D("0.5"))
        world.set_operation(self.model)
        registry = JobRegistry()
        register_jobs(registry, world.client.app.state.ai_keyring, lambda _p: world.provider)  # type: ignore[attr-defined]
        self.worker = Worker(worker_db, registry, worker_id="test-worker")

    def start(self, body: dict[str, Any] | None = None) -> dict[str, Any]:
        response = self.world.run({**ECONOMY, **(body or {})})
        assert response.status_code == 201, response.text
        run: dict[str, Any] = response.json()
        return run

    def jobs(self) -> int:
        """Run every job that is due, making the waiting ones due first (as if time had passed)."""
        done = 0
        for _ in range(10):
            with self.world.owner_db.transaction(
                TenantContext(organization_id=self.world.org_id)
            ) as session:
                session.execute(text("UPDATE jobs SET run_after = now() WHERE state = 'QUEUED'"))
            count = self.worker.run_until_idle()
            done += count
            if count == 0:
                break
        return done

    def one_round(self) -> int:
        """Run what is due now, without hurrying the waiting jobs."""
        return self.worker.run_until_idle()

    def run(self, run_id: str) -> AiRun:
        with self.world.owner_db.transaction(
            TenantContext(organization_id=self.world.org_id)
        ) as session:
            return session.scalars(select(AiRun).where(AiRun.id == UUID(run_id))).one()

    def kinds(self, run_id: str) -> list[str]:
        return [e.entry_kind for e in self.world.ledger(run_id)]

    def batch_of(self, run_id: str) -> str:
        found = self.world.provider.find_batches_by_tag("k", run_id)
        assert len(found) == 1, found
        return found[0]

    def api(self, method: str, path: str, **kwargs: Any) -> Any:
        return getattr(self.world.client, method)(path, headers=self.world.author_headers, **kwargs)


@pytest.fixture
def plant(world: World, worker_db: Database) -> Plant:
    return Plant(world, worker_db)


# --- T50: at most one submission ---------------------------------------------------------------


def test_an_economy_run_is_reserved_queued_and_then_handed_over_once(plant: Plant) -> None:
    run = plant.start()
    assert (run["mode"], run["phase"], run["attempts"]) == ("ECONOMY", "QUEUED", [])
    assert plant.kinds(run["id"]) == ["RESERVE"] and plant.world.provider.submit_calls == 0
    plant.one_round()  # claim, then submit (the collect job waits a minute)
    row = plant.run(run["id"])
    assert (row.status, row.provider_batch_id) == ("SUBMITTED", "fake-batch-1")
    assert plant.world.provider.submit_calls == 1
    batch = plant.world.provider.batches["fake-batch-1"]
    assert batch.tag == run["id"]  # the run's id is the tag the provider knows it by
    assert batch.request.model_id == "fake-batch" and '<data name="question">' in batch.request.user


def test_two_claims_for_one_run_hand_it_over_only_once(plant: Plant) -> None:
    run = plant.start()
    # A duplicate claim job (a second worker, a replayed message): only one can win the run.
    with plant.world.owner_db.transaction(TenantContext(organization_id=plant.world.org_id)) as s:
        s.execute(
            text(
                "INSERT INTO jobs (id, organization_id, type, payload, max_attempts)"
                " SELECT gen_random_uuid(), organization_id, type, payload, max_attempts"
                " FROM jobs WHERE type = 'ai.claim_submit'"
            )
        )
    plant.one_round()
    assert plant.world.provider.submit_calls == 1
    assert plant.run(run["id"]).status == "SUBMITTED"


def test_a_reply_lost_after_the_batch_was_created_is_reconciled_never_resent(
    plant: Plant,
) -> None:
    plant.world.provider.lose_submit_answer = True  # the provider takes it; we never hear back
    run = plant.start()
    plant.jobs()  # the first attempt times out; the retry looks the batch up
    row = plant.run(run["id"])
    assert (row.status, row.provider_batch_id) == ("SUBMITTED", "fake-batch-1")
    assert plant.world.provider.submit_calls == 1  # never sent a second time


def test_a_submission_that_never_shows_up_stays_unknown_and_reserved_until_an_admin_decides(
    plant: Plant,
) -> None:
    plant.world.provider.lose_submit_answer = True
    run = plant.start()
    plant.one_round()  # attempt 1: timeout (ambiguous)
    plant.world.provider.batches.clear()  # and it turns out the provider never had it
    plant.jobs()  # attempts 2 to 6 look for it; the last one gives up
    row = plant.run(run["id"])
    assert row.status == "SUBMISSION_UNKNOWN" and plant.world.provider.submit_calls == 1
    assert plant.kinds(run["id"]) == ["RESERVE"]  # the whole reservation is still held
    with plant.world.owner_db.transaction(TenantContext(organization_id=plant.world.org_id)) as s:
        told = s.scalars(select(Notification).where(Notification.kind == "AI_SUBMISSION_UNKNOWN"))
        assert plant.world.admin.user_id in {n.user_id for n in told}
    # A person cannot settle it; an admin can, with what the provider's billing says.
    assert plant.api("post", f"/api/v1/ai/runs/{run['id']}/resolve", json={}).status_code == 403
    admin = TestClient(plant.world.client.app)
    resolved = admin.post(
        f"/api/v1/ai/runs/{run['id']}/resolve",
        json={"actual_usd": "0.0123"},
        headers=sign_in(admin, plant.world.admin.email),
    )
    assert resolved.status_code == 200, resolved.text
    assert (resolved.json()["phase"], resolved.json()["error_code"]) == (
        "FAILED",
        "AI_SUBMISSION_UNKNOWN",
    )
    assert plant.world.ledger(run["id"])[-1].amount_usd == D("0.0123")
    again = admin.post(
        f"/api/v1/ai/runs/{run['id']}/resolve",
        json={},
        headers=sign_in(admin, plant.world.admin.email),
    )
    assert again.status_code == 409


def test_a_definite_refusal_fails_the_run_gives_the_budget_back_and_is_not_retried(
    plant: Plant,
) -> None:
    plant.world.provider.reject_submit = ProviderError(ProviderErrorKind.AUTH, status=401)
    run = plant.start()
    plant.jobs()
    row = plant.run(run["id"])
    assert (row.status, row.error_code) == ("FAILED", "AI_PROVIDER_AUTH")
    assert plant.world.provider.submit_calls == 1
    assert plant.kinds(run["id"]) == ["RESERVE", "RELEASE"]


# --- T51: every ending settles the reservation ---------------------------------------------------


def submitted(plant: Plant, body: dict[str, Any] | None = None) -> tuple[dict[str, Any], str]:
    run = plant.start(body)
    plant.one_round()
    return run, plant.batch_of(run["id"])


def test_a_result_is_settled_at_the_discounted_cost_applied_and_the_person_told(
    plant: Plant,
) -> None:
    run, batch = submitted(plant)
    plant.world.provider.finish(batch, plant.world.answer())  # 1000 in, 200 out
    plant.jobs()
    done = plant.api("get", f"/api/v1/ai/runs/{run['id']}").json()
    assert (done["phase"], done["apply_status"], done["error_code"]) == (
        "SUCCEEDED",
        "APPLIED",
        None,
    )
    assert plant.world.labels()["difficulty"] == 7  # applied by the worker for the requester
    settle = plant.world.ledger(run["id"])[-1]
    # $1 and $2 per million tokens: 1000 in + 200 out = $0.0014, half price = $0.0007, ACTUAL.
    assert (settle.entry_kind, settle.cost_kind, settle.amount_usd) == (
        "SETTLE",
        "ACTUAL",
        D("0.0007"),
    )
    assert [a["outcome"] for a in done["attempts"]] == ["OK"]
    with plant.world.owner_db.transaction(TenantContext(organization_id=plant.world.org_id)) as s:
        told = s.scalars(
            select(Notification).where(
                Notification.kind == "AI_RUN_FINISHED",
                Notification.user_id == plant.world.author.user_id,
            )
        ).all()
    assert [n.data["run_id"] for n in told] == [run["id"]]


@pytest.mark.parametrize(
    ("state", "status", "code"),
    [
        (BatchState.FAILED, "FAILED", "AI_PROVIDER_BATCH_FAILED"),
        (BatchState.EXPIRED, "EXPIRED", "AI_PROVIDER_BATCH_EXPIRED"),
        (BatchState.CANCELLED, "CANCELLED", "AI_RUN_CANCELLED"),
    ],
)
def test_a_batch_that_ends_without_an_answer_gives_the_reservation_back(
    plant: Plant, state: BatchState, status: str, code: str
) -> None:
    run, batch = submitted(plant)
    plant.world.provider.end(batch, state)
    plant.jobs()
    row = plant.run(run["id"])
    assert (row.status, row.error_code, row.apply_status) == (status, code, "NOT_APPLIED")
    assert plant.kinds(run["id"]) == ["RESERVE", "RELEASE"]


def test_a_request_the_provider_failed_gives_the_reservation_back(plant: Plant) -> None:
    run, batch = submitted(plant)
    plant.world.provider.finish_with_error(batch, ProviderErrorKind.UNAVAILABLE)
    plant.jobs()
    row = plant.run(run["id"])
    assert (row.status, row.error_code) == ("FAILED", "AI_PROVIDER_UNAVAILABLE")
    assert plant.kinds(run["id"]) == ["RESERVE", "RELEASE"]


def test_an_unusable_answer_is_charged_and_applies_nothing(plant: Plant) -> None:
    run, batch = submitted(plant)
    before = plant.world.labels()
    plant.world.provider.finish(batch, plant.world.answer(difficulty=99))
    plant.jobs()
    row = plant.run(run["id"])
    assert (row.status, row.error_code) == ("FAILED", "AI_OUTPUT_INVALID")
    assert plant.world.ledger(run["id"])[-1].entry_kind == "SETTLE"
    assert plant.world.labels() == before


def test_a_batch_still_running_is_asked_about_again_later(plant: Plant) -> None:
    run, _ = submitted(plant)
    with plant.world.owner_db.transaction(TenantContext(organization_id=plant.world.org_id)) as s:
        s.execute(text("UPDATE jobs SET run_after = now() WHERE type = 'ai.collect_batch'"))
    plant.one_round()
    assert plant.run(run["id"]).status == "SUBMITTED"
    with plant.world.owner_db.transaction(TenantContext(organization_id=plant.world.org_id)) as s:
        waiting = s.execute(
            text(
                "SELECT count(*) FROM jobs WHERE type = 'ai.collect_batch' AND state = 'QUEUED'"
                " AND run_after > now()"
            )
        ).scalar()
    assert waiting == 1  # it came back to ask again, later


def test_a_batch_older_than_the_providers_promise_is_given_up_on(plant: Plant) -> None:
    run, _ = submitted(plant)
    with plant.world.owner_db.transaction(TenantContext(organization_id=plant.world.org_id)) as s:
        s.execute(
            text(
                "UPDATE ai_runs SET submit_started_at = now() - interval '49 hours' WHERE id = :i"
            ),
            {"i": run["id"]},
        )
    plant.jobs()
    row = plant.run(run["id"])
    assert (row.status, row.error_code) == ("EXPIRED", "AI_PROVIDER_BATCH_EXPIRED")
    assert plant.kinds(run["id"]) == ["RESERVE", "RELEASE"]


# --- T52: cancelling is final for applying -------------------------------------------------------


def test_cancelling_before_it_is_handed_over_ends_it_and_is_never_submitted(plant: Plant) -> None:
    run = plant.start()
    cancelled = plant.api("post", f"/api/v1/ai/runs/{run['id']}/cancel")
    assert cancelled.status_code == 200, cancelled.text
    assert (cancelled.json()["phase"], cancelled.json()["cancel_requested"]) == ("CANCELLED", True)
    plant.jobs()
    assert plant.world.provider.submit_calls == 0
    assert plant.kinds(run["id"]) == ["RESERVE", "RELEASE"]


def test_a_result_that_arrives_after_cancelling_is_kept_and_charged_but_never_applied(
    plant: Plant,
) -> None:
    run, batch = submitted(plant)
    before = plant.world.labels()
    cancelled = plant.api("post", f"/api/v1/ai/runs/{run['id']}/cancel")
    assert cancelled.status_code == 200 and cancelled.json()["phase"] == "SUBMITTED"
    assert plant.world.provider.cancelled == [batch]  # the provider was asked to stop...
    plant.world.provider.finish(batch, plant.world.answer())  # ...but it was too late
    plant.jobs()
    done = plant.run(run["id"])
    assert (done.status, done.apply_status) == ("CANCELLED", "NOT_APPLIED")
    assert done.result is not None and done.result["output"]["difficulty"] == 7  # kept
    assert plant.world.labels() == before  # never applied
    assert plant.world.ledger(run["id"])[-1].entry_kind == "SETTLE"  # charged


def test_cancelling_while_it_is_being_handed_over_cancels_the_batch_when_it_exists(
    plant: Plant,
) -> None:
    run = plant.start()
    plant.worker.run_next()  # only the claim: the run is SUBMITTING, the submit job waits
    assert plant.run(run["id"]).status == "SUBMITTING"
    cancelled = plant.api("post", f"/api/v1/ai/runs/{run['id']}/cancel")
    assert cancelled.status_code == 200 and cancelled.json()["cancel_requested"] is True
    plant.one_round()
    assert plant.world.provider.cancelled == ["fake-batch-1"]  # asked as soon as it existed


def test_only_a_waiting_economy_run_can_be_cancelled(plant: Plant) -> None:
    plant.world.provider.script.append(plant.world.answer())
    now_run = plant.world.run({"mode": "NOW"}).json()  # a Now run is never "waiting"
    refused = plant.api("post", f"/api/v1/ai/runs/{now_run['id']}/cancel")
    assert (refused.status_code, refused.json()["error"]["code"]) == (409, "AI_RUN_NOT_CANCELLABLE")
    run, batch = submitted(plant)
    plant.world.provider.finish(batch, plant.world.answer())
    plant.jobs()
    late = plant.api("post", f"/api/v1/ai/runs/{run['id']}/cancel")
    assert (late.status_code, late.json()["error"]["code"]) == (409, "AI_RUN_NOT_CANCELLABLE")


# --- B-10: checked again when the result arrives ----------------------------------------------


def test_a_requester_who_has_left_gets_the_result_kept_for_review(plant: Plant) -> None:
    run, batch = submitted(plant)
    before = plant.world.labels()
    plant.world.provider.finish(batch, plant.world.answer())
    with plant.world.owner_db.transaction(TenantContext(organization_id=plant.world.org_id)) as s:
        for member in s.scalars(
            select(Membership).where(Membership.user_id == plant.world.author.user_id)
        ):
            member.status = "REMOVED"
    plant.jobs()
    row = plant.run(run["id"])
    assert (row.status, row.apply_status) == ("SUCCEEDED", "NEEDS_REVIEW")
    with plant.world.owner_db.transaction(TenantContext(organization_id=plant.world.org_id)) as s:
        member = s.scalars(
            select(Membership).where(Membership.user_id == plant.world.author.user_id)
        ).one()
        member.status = "ACTIVE"
    assert plant.world.labels() == before


def test_a_question_that_changed_while_waiting_keeps_the_result_out_of_date(plant: Plant) -> None:
    run, batch = submitted(plant)
    current = plant.api("get", f"{QUESTIONS}/{plant.world.question['id']}")
    content = current.json()["content"]
    content["metadata"]["difficulty"] = 2
    saved = plant.world.client.put(
        f"{QUESTIONS}/{plant.world.question['id']}/working-revision",
        json={"content": content},
        headers={**plant.world.author_headers, "If-Match": current.headers["ETag"]},
    )
    assert saved.status_code == 200, saved.text
    plant.world.provider.finish(batch, plant.world.answer())
    plant.jobs()
    row = plant.run(run["id"])
    assert (row.status, row.apply_status) == ("SUCCEEDED", "OUT_OF_DATE")
    assert plant.world.labels()["difficulty"] == 2


def test_an_economy_solve_is_still_a_suggestion_applied_by_a_click(plant: Plant) -> None:
    plant.world.set_operation(plant.model)
    run, batch = submitted(plant, {"operation": "SOLVE"})
    plant.world.provider.finish(
        batch, StructuredResult({"answer": {"option_id": "C"}, "solution": "Because."}, 900, 100)
    )
    plant.jobs()
    done = plant.api("get", f"/api/v1/ai/runs/{run['id']}").json()
    assert (done["phase"], done["apply_status"]) == ("SUCCEEDED", "NOT_APPLIED")
    applied = plant.api("post", f"/api/v1/ai/runs/{run['id']}/apply")
    assert applied.status_code == 200 and applied.json()["apply_status"] == "APPLIED"


# --- Who may use Economy ----------------------------------------------------------------------


def test_economy_needs_a_model_marked_as_batch_and_a_known_price(
    world: World, worker_db: Database
) -> None:
    plain = world.add_model("fake-plain")
    world.set_operation(plain)
    refused = world.run(ECONOMY)
    assert (refused.status_code, refused.json()["error"]["code"]) == (409, "AI_ECONOMY_UNAVAILABLE")
    unpriced = world.add_model("fake-unpriced", batch=True, priced=False)
    world.set_operation(unpriced)
    refused = world.run(ECONOMY)
    assert (refused.status_code, refused.json()["error"]["code"]) == (409, "AI_ECONOMY_NEEDS_PRICE")
    assert world.provider.submit_calls == 0


def test_the_operations_default_mode_applies_when_none_is_asked_for(plant: Plant) -> None:
    plant.world.set_operation(plant.model, mode="ECONOMY")
    response = plant.world.run()
    assert response.status_code == 201, response.text
    assert (response.json()["mode"], response.json()["phase"]) == ("ECONOMY", "QUEUED")
    assert plant.world.run({"mode": "NOW"}).json()["mode"] == "NOW"


def test_attempt_rows_are_written_for_the_batch_answer(plant: Plant) -> None:
    run, batch = submitted(plant)
    plant.world.provider.finish(batch, plant.world.answer())
    plant.jobs()
    with plant.world.owner_db.transaction(TenantContext(organization_id=plant.world.org_id)) as s:
        attempts = s.scalars(
            select(AiRunAttempt).where(AiRunAttempt.run_id == UUID(run["id"]))
        ).all()
    assert [(a.position, a.provider_model, a.outcome, a.tokens_in) for a in attempts] == [
        (1, "fake-batch", "OK", 1000)
    ]
    assert Decimal(plant.world.ledger(run["id"])[-1].amount_usd) > 0
