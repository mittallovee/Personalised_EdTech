"""M5 PR 5l: the demo provider, run through the whole orchestrator for every question format.

The browser journey (T55) runs against a stack that answers AI calls with this provider, so its
answers must be accepted by the same checks as a real model's, for every format: the answer
validator, the structure check of a translation, the correction check of a verification. These tests
prove that, and that the settings refuse it outside local development.
"""

from typing import Any

import pytest
from pydantic import ValidationError

from qbank.core.config import AppEnv, Settings
from qbank.modules.ai.providers.demo import DemoProvider
from tests.integration.ai_support import QUESTIONS, World
from tests.integration.question_support import ready_for
from tests.unit.test_question_content import FIXTURES

KINDS = sorted(
    kind for kind, fixture in FIXTURES.items() if isinstance(fixture, dict) and "ready" in fixture
)


@pytest.fixture
def demo(world: World) -> World:
    world.client.app.state.ai_providers = lambda provider: DemoProvider(provider)  # type: ignore[attr-defined]
    return world


def question_of(world: World, kind: str) -> str:
    created = world.client.post(
        QUESTIONS, json={"content": ready_for(world.catalogue, kind)}, headers=world.author_headers
    )
    assert created.status_code == 201, created.text
    return str(created.json()["id"])


def run(world: World, question_id: str, body: dict[str, Any]) -> dict[str, Any]:
    response = world.client.post(
        f"{QUESTIONS}/{question_id}/ai/runs", json=body, headers=world.author_headers
    )
    assert response.status_code == 201, response.text
    answer: dict[str, Any] = response.json()
    return answer


@pytest.mark.parametrize("kind", KINDS)
def test_every_operation_gives_an_answer_the_checks_accept(demo: World, kind: str) -> None:
    question_id = question_of(demo, kind)
    for operation in ("SOLVE", "VERIFY"):
        result = run(demo, question_id, {"operation": operation})
        assert result["status"] == "SUCCEEDED", (kind, operation, result["error_code"])
    solved = run(demo, question_id, {"operation": "SOLVE"})
    applied = demo.client.post(f"/api/v1/ai/runs/{solved['id']}/apply", headers=demo.author_headers)
    assert applied.status_code == 200 and applied.json()["apply_status"] == "APPLIED"
    translated = run(demo, question_id, {"operation": "TRANSLATE", "target_language": "hi"})
    assert translated["status"] == "SUCCEEDED", (kind, translated["error_code"])


@pytest.mark.parametrize("kind", KINDS)
def test_tagging_fills_the_labels_from_the_subject_syllabus(demo: World, kind: str) -> None:
    question_id = question_of(demo, kind)
    result = run(demo, question_id, {"operation": "TAG"})
    assert result["status"] == "SUCCEEDED", (kind, result["error_code"])
    assert result["apply_status"] == "APPLIED"
    assert result["result"]["output"]["chapter_id"] == str(demo.catalogue.chapter_id)


def test_a_verification_offers_a_correction_that_can_be_applied(demo: World) -> None:
    question_id = question_of(demo, "SCQ")
    verified = run(demo, question_id, {"operation": "VERIFY"})
    assert verified["result"]["output"]["corrected_content"] is not None
    applied = demo.client.post(
        f"/api/v1/ai/runs/{verified['id']}/apply", headers=demo.author_headers
    )
    assert applied.status_code == 200 and applied.json()["apply_status"] == "APPLIED"


def test_a_translation_keeps_the_structure_and_marks_the_words(demo: World) -> None:
    question_id = question_of(demo, "SCQ")
    translated = run(demo, question_id, {"operation": "TRANSLATE", "target_language": "hi"})
    content = translated["result"]["output"]["content"]
    assert content["language"] == "hi"
    assert "[Hindi]" in content["stem"][0]["text"]


def test_the_demo_models_are_listed_with_prices() -> None:
    models = {m.model_id: m for m in DemoProvider().list_models("any-key")}
    assert set(models) == {"demo-small", "demo-large"}
    assert all(m.supports_json and m.price_in_per_mtok is not None for m in models.values())


def test_the_demo_is_refused_outside_local_development() -> None:
    base: dict[str, Any] = {"database_url": "postgresql://x", "ai_demo_provider": True}
    Settings(app_env=AppEnv.LOCAL, **base)
    Settings(app_env=AppEnv.TEST, **base)
    for env in (AppEnv.STAGING, AppEnv.PRODUCTION):
        with pytest.raises(ValidationError, match="AI_DEMO_PROVIDER"):
            Settings(
                app_env=env,
                allowed_origins=["https://app.example.com"],
                session_cookie_secure=True,
                **base,
            )


def test_a_demo_batch_is_done_after_a_few_seconds_and_answers_a_verification() -> None:
    from qbank.modules.ai.providers.base import BatchState, StructuredRequest

    adapter = DemoProvider()
    request = StructuredRequest("demo-small", "s", "u", "question_review", {}, 100)
    batch = adapter.submit_batch("key", tag="run-1", request=request)
    assert adapter.batch_status("key", batch) is BatchState.IN_PROGRESS
    old = batch.replace(batch.split("-")[1], "1000")  # sent long ago
    assert adapter.batch_status("key", old) is BatchState.DONE
    answer = adapter.fetch_batch_answer("key", old, tag="run-1")
    assert answer.result is not None and answer.result.data["corrected_content_json"] is None
    assert adapter.fetch_batch_answer("key", old, tag="other").error is not None
