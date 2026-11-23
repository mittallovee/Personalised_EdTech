"""M5 PR 5g: translating a question (H-08, D-13; part of test T49).

A translation is a suggestion until a person applies it; applying makes a new draft question of
that person, linked to its source, and never touches the source. The result must keep the exact
structure of the source (answer, option ids, number of blocks): only words may change.
"""

import copy
import json
from typing import Any
from uuid import UUID

import pytest
from sqlalchemy import select

from qbank.core.tenancy import TenantContext
from qbank.modules.ai.models import GlossaryEntry
from qbank.modules.ai.providers.base import StructuredResult
from qbank.modules.audit.models import AuditEvent
from tests.integration.ai_support import QUESTIONS, World

TRANSLATE = {"operation": "TRANSLATE", "target_language": "hi"}


def source_content(world: World) -> dict[str, Any]:
    response = world.client.get(f"{QUESTIONS}/{world.question['id']}", headers=world.author_headers)
    assert response.status_code == 200, response.text
    content: dict[str, Any] = response.json()["content"]
    return content


def hindi(world: World, change: Any = None) -> StructuredResult:
    """The source with its words 'translated' (marked), and ``change`` applied for bad cases."""
    content = copy.deepcopy(source_content(world))
    content["stem"][0]["text"] = "[hi] " + content["stem"][0]["text"]
    for option in content["options"]:
        for block in option["content"]:
            if block.get("kind") == "paragraph":
                block["text"] = "[hi] " + block["text"]
    if change is not None:
        change(content)
    return StructuredResult({"content_json": json.dumps(content)}, 1500, 900)


def apply(world: World, run: dict[str, Any]) -> Any:
    return world.client.post(f"/api/v1/ai/runs/{run['id']}/apply", headers=world.author_headers)


def get(world: World, question_id: str) -> Any:
    return world.client.get(f"{QUESTIONS}/{question_id}", headers=world.author_headers)


def test_a_translation_is_a_suggestion_until_applied_and_then_a_linked_new_draft(
    world: World,
) -> None:
    before = source_content(world)
    world.provider.script.append(hindi(world))
    run = world.run(TRANSLATE).json()
    assert (run["status"], run["apply_status"], run["error_code"]) == (
        "SUCCEEDED",
        "NOT_APPLIED",
        None,
    )
    output = run["result"]["output"]
    assert output["language"] == "hi" and output["content"]["language"] == "hi"
    assert output["content"]["stem"][0]["text"].startswith("[hi] ")
    assert output["content"]["metadata"] == before["metadata"]  # the labels are carried over
    assert source_content(world) == before  # nothing created or changed yet

    done = apply(world, run)
    assert done.status_code == 200, done.text
    assert done.json()["apply_status"] == "APPLIED"
    created = done.json()["result"]["output"]["created_question"]
    new = get(world, created["id"]).json()
    assert new["code"] == created["code"] and new["code"] != world.question["code"]
    assert (new["state"], new["created_by"]) == ("DRAFT", str(world.author.user_id))
    assert new["content"]["language"] == "hi"
    assert new["translation_of"] == {
        "source_id": world.question["id"],
        "source_code": world.question["code"],
        "source_version_number": 1,
        "language": "hi",
        "source_updated": False,
    }
    assert source_content(world) == before  # the source is never touched
    assert get(world, world.question["id"]).json()["translation_of"] is None
    again = apply(world, run)
    assert (again.status_code, again.json()["error"]["code"]) == (409, "AI_RUN_NOT_APPLICABLE")
    with world.owner_db.transaction(TenantContext(organization_id=world.org_id)) as session:
        linked = session.scalars(
            select(AuditEvent).where(
                AuditEvent.action == "QUESTION_TRANSLATION_LINKED",
                AuditEvent.entity_id == UUID(created["id"]),
            )
        ).all()
    assert len(linked) == 1


def test_the_prompt_gets_the_languages_and_only_the_glossary_terms_that_appear(
    world: World,
) -> None:
    with world.owner_db.transaction(TenantContext(organization_id=world.org_id)) as session:
        for source, target in (("What is", "Kya hai"), ("velocity", "veg")):
            session.add(
                GlossaryEntry(
                    organization_id=world.org_id,
                    language="hi",
                    source_term=source,
                    target_term=target,
                    created_by=world.admin.user_id,
                    updated_by=world.admin.user_id,
                )
            )
    world.provider.script.append(hindi(world))
    assert world.run(TRANSLATE).status_code == 201
    user = world.provider.calls[0][1].user
    assert '<data name="source_language">\nEnglish\n</data>' in user
    assert '<data name="target_language">\nHindi\n</data>' in user
    assert "What is = Kya hai" in user and "velocity" not in user
    assert '"metadata"' not in user  # the labels are not sent


@pytest.mark.parametrize(
    "change",
    [
        lambda c: c.update(answer={"option_id": "A"}),  # the key must not move
        lambda c: c["options"][0].update(id="Z"),  # option ids must not change
        lambda c: c.update(options=c["options"][:3]),  # an option was dropped
        lambda c: c.update(extra_field=1),  # a key was added
        lambda c: c.update(question_type="MULTI_CORRECT"),  # another kind of question
        lambda c: c["stem"].append({"kind": "paragraph", "text": "A hint."}),  # a block was added
        lambda c: c["stem"][0].update(kind="equation"),  # a block changed kind
    ],
)
def test_a_translation_that_changes_the_structure_is_stored_as_failed(
    world: World, change: Any
) -> None:
    world.provider.script.append(hindi(world, change))
    run = world.run(TRANSLATE).json()
    assert (run["status"], run["error_code"]) == ("FAILED", "AI_OUTPUT_INVALID")
    assert apply(world, run).status_code == 409


@pytest.mark.parametrize("text", ["{not json", "[1, 2]", "5"])
def test_a_translation_that_is_not_a_json_object_is_stored_as_failed(
    world: World, text: str
) -> None:
    world.provider.script.append(StructuredResult({"content_json": text}, 10, 10))
    assert world.run(TRANSLATE).json()["error_code"] == "AI_OUTPUT_INVALID"


def test_the_target_language_must_be_a_known_other_language(world: World) -> None:
    for language, code in (
        (None, "AI_TRANSLATE_LANGUAGE_INVALID"),
        ("zz", "AI_TRANSLATE_LANGUAGE_INVALID"),
        ("en", "AI_TRANSLATE_SAME_LANGUAGE"),
    ):
        body = {"operation": "TRANSLATE", **({"target_language": language} if language else {})}
        refused = world.run(body)
        assert (refused.status_code, refused.json()["error"]["code"]) == (422, code)
    assert world.provider.calls == []


def test_a_submitted_question_can_be_translated_and_stays_untouched(world: World) -> None:
    submitted = world.client.post(
        f"{QUESTIONS}/{world.question['id']}/submit",
        headers={**world.author_headers, "If-Match": f'"rev-{world.question["revision"]}"'},
    )
    assert submitted.status_code == 200, submitted.text
    world.provider.script.append(hindi(world))
    run = world.run(TRANSLATE).json()
    assert run["status"] == "SUCCEEDED", run
    done = apply(world, run)
    assert done.json()["apply_status"] == "APPLIED"
    assert get(world, world.question["id"]).json()["state"] == "IN_REVIEW"


def test_a_source_that_changed_before_applying_makes_no_translation(world: World) -> None:
    world.provider.script.append(hindi(world))
    run = world.run(TRANSLATE).json()
    current = get(world, world.question["id"])
    content = current.json()["content"]
    content["stem"][0]["text"] = "What is 3 + 3?"
    saved = world.client.put(
        f"{QUESTIONS}/{world.question['id']}/working-revision",
        json={"content": content},
        headers={**world.author_headers, "If-Match": current.headers["ETag"]},
    )
    assert saved.status_code == 200, saved.text
    done = apply(world, run)
    assert done.json()["apply_status"] == "OUT_OF_DATE"
    assert "created_question" not in done.json()["result"]["output"]
