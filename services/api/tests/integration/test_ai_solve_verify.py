"""M5 PR 5f: solving a question and verifying one (test T49 for solve and verify).

Both only suggest. Nothing is written to the question until a person applies the suggestion, and
then only to the exact revision the run read. Answers are untrusted: they go through the same
validator as a person's save.
"""

import copy
import json
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from qbank.core.tenancy import TenantContext
from qbank.modules.ai.models import AiRun
from qbank.modules.ai.providers.base import StructuredResult
from qbank.modules.audit.models import AuditEvent
from tests.integration.ai_support import QUESTIONS, World
from tests.integration.conftest import make_member, sign_in
from tests.integration.question_support import ready_for

SOLVE = {"operation": "SOLVE"}
VERIFY = {"operation": "VERIFY"}


def content_of(world: World) -> dict[str, Any]:
    response = world.client.get(f"{QUESTIONS}/{world.question['id']}", headers=world.author_headers)
    assert response.status_code == 200, response.text
    content: dict[str, Any] = response.json()["content"]
    return content


def apply(world: World, run: dict[str, Any], headers: dict[str, str] | None = None) -> Any:
    return world.client.post(
        f"/api/v1/ai/runs/{run['id']}/apply", headers=headers or world.author_headers
    )


def solved(option: str = "C", solution: str = "Because 2 + 3 = 5.\n\nSo C.") -> StructuredResult:
    return StructuredResult({"answer": {"option_id": option}, "solution": solution}, 800, 300)


def edit_stem(world: World, text: str) -> None:
    current = world.client.get(f"{QUESTIONS}/{world.question['id']}", headers=world.author_headers)
    content = current.json()["content"]
    content["stem"] = [{"kind": "paragraph", "text": text}]
    saved = world.client.put(
        f"{QUESTIONS}/{world.question['id']}/working-revision",
        json={"content": content},
        headers={**world.author_headers, "If-Match": current.headers["ETag"]},
    )
    assert saved.status_code == 200, saved.text


def applied_events(world: World) -> list[AuditEvent]:
    with world.owner_db.transaction(TenantContext(organization_id=world.org_id)) as session:
        return list(
            session.scalars(
                select(AuditEvent).where(
                    AuditEvent.action == "AI_RUN_APPLIED",
                    AuditEvent.entity_id == UUID(world.question["id"]),
                )
            )
        )


# --- Solve ---------------------------------------------------------------------------------------


def test_solve_only_suggests_and_the_model_never_sees_the_answer_or_labels(world: World) -> None:
    before = content_of(world)
    world.provider.script.append(solved())
    run = world.run(SOLVE).json()
    assert (run["status"], run["apply_status"]) == ("SUCCEEDED", "NOT_APPLIED")
    assert run["result"]["output"]["answer"] == {"option_id": "C"}
    assert run["result"]["output"]["solution"][0] == {
        "kind": "paragraph",
        "text": "Because 2 + 3 = 5.",
    }
    assert run["result"]["before"]["answer"] == before["answer"]
    assert content_of(world) == before  # nothing written
    _, request = world.provider.calls[0]
    assert '"answer"' not in request.user and '"metadata"' not in request.user
    assert str(world.catalogue.subject_id) not in request.user
    assert request.schema["properties"]["answer"]["properties"]["option_id"]["enum"] == [
        "A",
        "B",
        "C",
        "D",
    ]


def test_applying_a_solution_changes_the_question_once_and_is_audited(world: World) -> None:
    world.provider.script.append(solved())
    run = world.run(SOLVE).json()
    done = apply(world, run)
    assert done.status_code == 200, done.text
    assert done.json()["apply_status"] == "APPLIED"
    content = content_of(world)
    assert content["answer"] == {"option_id": "C"}
    assert content["solution"][-1]["text"] == "So C."
    assert len(applied_events(world)) == 1
    again = apply(world, run)
    assert (again.status_code, again.json()["error"]["code"]) == (409, "AI_RUN_NOT_APPLICABLE")


def test_a_suggestion_is_not_applied_to_a_question_that_changed_meanwhile(world: World) -> None:
    world.provider.script.append(solved())
    run = world.run(SOLVE).json()
    edit_stem(world, "What is 3 + 3?")
    done = apply(world, run)
    assert done.status_code == 200 and done.json()["apply_status"] == "OUT_OF_DATE"
    assert content_of(world)["answer"] == {"option_id": "B"}  # still the person's
    assert applied_events(world) == []


@pytest.mark.parametrize(
    "result",
    [
        {"answer": {"option_id": "Z"}, "solution": "x"},
        {"answer": {"option_ids": ["A"]}, "solution": "x"},
        {"answer": "C", "solution": "x"},
        {"answer": {"option_id": "C"}, "solution": ""},
        {"answer": {"option_id": "C"}},
        {"answer": {"option_id": "C"}, "solution": 5},
    ],
)
def test_an_unusable_solution_is_stored_as_failed(world: World, result: dict[str, Any]) -> None:
    world.provider.script.append(StructuredResult(result, 10, 10))
    run = world.run(SOLVE).json()
    assert (run["status"], run["error_code"]) == ("FAILED", "AI_OUTPUT_INVALID")
    assert apply(world, run).status_code == 409


def test_a_test_run_of_solve_can_never_be_applied(world: World) -> None:
    world.provider.script.append(solved())
    run = world.run({**SOLVE, "test": True}).json()
    assert apply(world, run).status_code == 409
    assert content_of(world)["answer"] == {"option_id": "B"}


def test_a_colleague_cannot_apply_someone_elses_run_but_an_admin_can(world: World) -> None:
    world.provider.script.append(solved())
    run = world.run(SOLVE).json()
    colleague = make_member(world.owner_db, "FACULTY", org_id=world.org_id)
    other = TestClient(world.client.app)
    refused = other.post(
        f"/api/v1/ai/runs/{run['id']}/apply", headers=sign_in(other, colleague.email)
    )
    assert refused.status_code == 404
    admin = TestClient(world.client.app)
    ok = admin.post(f"/api/v1/ai/runs/{run['id']}/apply", headers=sign_in(admin, world.admin.email))
    assert ok.status_code == 200 and ok.json()["apply_status"] == "APPLIED"


def test_a_numerical_range_is_cleaned_and_applied(world: World) -> None:
    created = world.client.post(
        QUESTIONS,
        json={"content": ready_for(world.catalogue, "NUMERICAL")},
        headers=world.author_headers,
    )
    assert created.status_code == 201, created.text
    world.question = created.json()
    answer = {"mode": "range", "value": None, "lower": "9.70", "upper": "9.90"}
    world.provider.script.append(StructuredResult({"answer": answer, "solution": "g"}, 10, 10))
    run = world.run(SOLVE).json()
    assert run["status"] == "SUCCEEDED", run
    assert run["result"]["output"]["answer"] == {"mode": "range", "lower": "9.70", "upper": "9.90"}
    assert apply(world, run).json()["apply_status"] == "APPLIED"
    assert content_of(world)["answer"] == {"mode": "range", "lower": "9.70", "upper": "9.90"}


def test_an_integer_answer_must_be_a_whole_number(world: World) -> None:
    created = world.client.post(
        QUESTIONS,
        json={"content": ready_for(world.catalogue, "INTEGER")},
        headers=world.author_headers,
    )
    world.question = created.json()
    world.provider.script.append(StructuredResult({"answer": {"value": 7}, "solution": "s"}, 5, 5))
    assert world.run(SOLVE).json()["status"] == "SUCCEEDED"
    world.provider.script.append(
        StructuredResult({"answer": {"value": 7.5}, "solution": "s"}, 5, 5)
    )
    assert world.run(SOLVE).json()["error_code"] == "AI_OUTPUT_INVALID"


# --- Verify --------------------------------------------------------------------------------------


def findings_only(*items: dict[str, str]) -> StructuredResult:
    return StructuredResult({"findings": list(items), "corrected_content_json": None}, 900, 200)


def corrected(world: World, change: Any) -> StructuredResult:
    content = copy.deepcopy(content_of(world))
    change(content)
    finding = {"path": "stem", "severity": "error", "message": "The stem is wrong."}
    return StructuredResult(
        {"findings": [finding], "corrected_content_json": json.dumps(content)}, 900, 400
    )


def test_verify_shows_findings_as_plain_text_and_has_nothing_to_apply(world: World) -> None:
    hostile = "<img src=x onerror=alert(1)> see javascript:void(0)"
    world.provider.script.append(
        findings_only({"path": "options[1]", "severity": "warning", "message": hostile})
    )
    run = world.run(VERIFY).json()
    assert (run["status"], run["apply_status"]) == ("SUCCEEDED", "NOT_APPLIED")
    assert run["result"]["output"]["findings"][0]["message"] == hostile  # kept as text
    assert "corrected_content" not in run["result"]["output"]
    refused = apply(world, run)
    assert (refused.status_code, refused.json()["error"]["code"]) == (409, "AI_RUN_NOT_APPLICABLE")


def test_a_correction_replaces_the_content_but_never_the_labels(world: World) -> None:
    labels = content_of(world)["metadata"]

    def fix(content: dict[str, Any]) -> None:
        content["stem"] = [{"kind": "paragraph", "text": "What is 2 + 3? Choose one."}]
        content["metadata"]["difficulty"] = 10  # an attempt to change the labels

    world.provider.script.append(corrected(world, fix))
    run = world.run(VERIFY).json()
    assert run["status"] == "SUCCEEDED", run
    assert run["result"]["before"]["content"]["stem"][0]["text"] == "What is 2 + 3?"
    assert content_of(world)["stem"][0]["text"] == "What is 2 + 3?"  # not yet
    done = apply(world, run)
    assert done.json()["apply_status"] == "APPLIED"
    after = content_of(world)
    assert after["stem"][0]["text"] == "What is 2 + 3? Choose one."
    assert after["metadata"] == labels
    assert len(applied_events(world)) == 1


@pytest.mark.parametrize(
    "change",
    [
        lambda c: c.update(question_type="INTEGER"),  # another kind of question
        lambda c: c.update(options=c["options"][:3]),  # three options: fails the validator
        lambda c: c.update(answer={"option_id": "Z"}),  # keys an option that does not exist
    ],
)
def test_a_correction_that_fails_the_validator_is_stored_as_failed(
    world: World, change: Any
) -> None:
    world.provider.script.append(corrected(world, change))
    run = world.run(VERIFY).json()
    assert (run["status"], run["error_code"]) == ("FAILED", "AI_OUTPUT_INVALID")
    assert content_of(world)["answer"] == {"option_id": "B"}


@pytest.mark.parametrize(
    "result",
    [
        {"findings": [], "corrected_content_json": "{not json"},
        {"findings": [], "corrected_content_json": "[1, 2]"},
        {"findings": [{"path": "stem", "severity": "fatal", "message": "x"}]},
        {"findings": [{"path": "stem", "severity": "error", "message": ""}]},
        {"findings": "none"},
        {"findings": [{"path": "p", "severity": "note", "message": "m"}] * 31},
    ],
)
def test_unusable_findings_are_stored_as_failed(world: World, result: dict[str, Any]) -> None:
    world.provider.script.append(StructuredResult(result, 10, 10))
    run = world.run(VERIFY).json()
    assert (run["status"], run["error_code"]) == ("FAILED", "AI_OUTPUT_INVALID")


def test_a_run_on_a_submitted_question_can_be_tested_but_not_run_for_real(world: World) -> None:
    submitted = world.client.post(
        f"{QUESTIONS}/{world.question['id']}/submit",
        headers={**world.author_headers, "If-Match": f'"rev-{world.question["revision"]}"'},
    )
    assert submitted.status_code == 200, submitted.text
    assert world.run(VERIFY).json()["error"]["code"] == "AI_QUESTION_NOT_EDITABLE"
    world.provider.script.append(findings_only())
    assert world.run({**VERIFY, "test": True}).json()["status"] == "SUCCEEDED"


def test_the_run_record_keeps_who_what_and_the_revision(world: World) -> None:
    world.provider.script.append(findings_only())
    run = world.run(VERIFY).json()
    with world.owner_db.transaction(TenantContext(organization_id=world.org_id)) as session:
        row = session.get(AiRun, UUID(run["id"]))
        assert row is not None
        assert (row.operation, row.user_id) == ("VERIFY", world.author.user_id)
        assert row.question_revision == world.question["revision"]
