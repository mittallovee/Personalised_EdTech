"""The demo provider (local trials and the browser tests): every operation gets an answer that
passes the real checks, and hosted environments refuse to switch it on."""

import pytest
from pydantic import ValidationError

from qbank.core.config import AppEnv, Settings
from qbank.modules.ai.names import Provider
from qbank.modules.ai.providers.demo import DemoProvider
from qbank.modules.ai.providers.registry import provider_factory, provider_for
from tests.integration.ai_support import QUESTIONS, World


@pytest.fixture
def demo(world: World) -> World:
    world.client.app.state.ai_providers = lambda _provider: DemoProvider()  # type: ignore[attr-defined]
    return world


def labels(world: World) -> dict[str, object]:
    return world.labels()


def test_tagging_fills_valid_labels_from_the_syllabus_it_was_shown(demo: World) -> None:
    run = demo.run().json()
    assert (run["status"], run["apply_status"]) == ("SUCCEEDED", "APPLIED"), run
    after = labels(demo)
    assert after["chapter_id"] == str(demo.catalogue.chapter_id)
    assert after["primary_concept_id"] == str(demo.catalogue.concept_id)
    assert (after["difficulty"], after["bloom_level"]) == (6, "APPLY")


def test_solving_suggests_an_option_that_exists_and_it_applies(demo: World) -> None:
    run = demo.run({"operation": "SOLVE"}).json()
    assert (run["status"], run["apply_status"]) == ("SUCCEEDED", "NOT_APPLIED"), run
    assert run["result"]["output"]["answer"] == {"option_id": "A"}
    applied = demo.client.post(f"/api/v1/ai/runs/{run['id']}/apply", headers=demo.author_headers)
    assert applied.json()["apply_status"] == "APPLIED"


def test_verifying_reports_a_note_and_offers_no_correction(demo: World) -> None:
    run = demo.run({"operation": "VERIFY"}).json()
    assert run["status"] == "SUCCEEDED", run
    assert [f["severity"] for f in run["result"]["output"]["findings"]] == ["note"]
    assert "corrected_content" not in run["result"]["output"]


def test_translating_keeps_the_structure_and_marks_the_words(demo: World) -> None:
    run = demo.run({"operation": "TRANSLATE", "target_language": "hi"}).json()
    assert run["status"] == "SUCCEEDED", run
    content = run["result"]["output"]["content"]
    assert content["stem"][0]["text"].startswith("[translated] ")
    done = demo.client.post(f"/api/v1/ai/runs/{run['id']}/apply", headers=demo.author_headers)
    created = done.json()["result"]["output"]["created_question"]
    fetched = demo.client.get(f"{QUESTIONS}/{created['id']}", headers=demo.author_headers)
    assert fetched.status_code == 200


def test_the_factory_gives_the_demo_provider_only_when_asked() -> None:
    assert provider_factory(False) is provider_for
    assert isinstance(provider_factory(True)(Provider.ANTHROPIC), DemoProvider)


@pytest.mark.parametrize("env", [AppEnv.STAGING, AppEnv.PRODUCTION])
def test_hosted_environments_refuse_the_demo_provider(env: AppEnv) -> None:
    with pytest.raises(ValidationError, match="AI_DEMO_PROVIDER"):
        Settings(
            app_env=env,
            database_url="postgresql+psycopg://u:p@localhost/db",
            session_cookie_secure=True,
            allowed_origins=["https://app.example.com"],
            ai_demo_provider=True,
        )


def test_local_development_accepts_it() -> None:
    settings = Settings(
        app_env=AppEnv.LOCAL,
        database_url="postgresql+psycopg://u:p@localhost/db",
        ai_demo_provider=True,
    )
    assert settings.ai_demo_provider is True
