"""M3 PR 3h-2: the questions under a passage (D-14; test T28).

A child question pins one exact checkpoint of a passage. The pin must be a checkpoint of the
coaching, and the passage lists its children with which sit on an older checkpoint.
"""

import copy
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from qbank.core.config import AppEnv, Settings
from qbank.core.db import Database
from qbank.main import create_app
from tests.integration.conftest import Member, MigratedDatabase, make_member, sign_in
from tests.unit.test_question_content import FIXTURES

PASSAGES = "/api/v1/passages"
QUESTIONS = "/api/v1/questions"
DRAFT = FIXTURES["SCQ"]["draft"]
READY = {
    "schema_version": 1,
    "title": "Free fall",
    "body": [{"kind": "paragraph", "text": "A stone is dropped from a tower."}],
}
UNAVAILABLE = "CONTEXT_PASSAGE_NOT_AVAILABLE"


@pytest.fixture
def client(migrated_database: MigratedDatabase, tmp_path: Path) -> Iterator[TestClient]:
    settings = Settings(
        app_env=AppEnv.TEST,
        database_url=migrated_database.app_url,
        session_cookie_secure=False,
        storage_dir=tmp_path / "storage",
    )
    with TestClient(create_app(settings)) as test_client:
        yield test_client


@pytest.fixture
def team(owner_db: Database) -> dict[str, Member]:
    owner = make_member(owner_db, "OWNER")
    return {
        "owner": owner,
        "author": make_member(owner_db, "FACULTY", org_id=owner.org_id),
        "other": make_member(owner_db, "FACULTY", org_id=owner.org_id),
        "editor": make_member(owner_db, "FACULTY", org_id=owner.org_id, grants=["EDIT_OTHERS"]),
    }


@pytest.fixture
def headers(client: TestClient, team: dict[str, Member]) -> dict[str, str]:
    return sign_in(client, team["author"].email)


def tag(item: dict[str, Any]) -> dict[str, str]:
    return {"If-Match": f'"rev-{item["revision"]}"'}


def passage_with_checkpoint(
    client: TestClient, headers: dict[str, str]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """A passage with one checkpoint: returns the passage (working copy) and the checkpoint."""
    started = client.post(PASSAGES, json={"content": READY}, headers=headers).json()
    after = client.post(
        f"{PASSAGES}/{started['id']}/checkpoints", headers={**headers, **tag(started)}
    ).json()
    return after, after["latest_checkpoint"]


def child_content(pin: object, ordinal: object = 1) -> dict[str, Any]:
    content = copy.deepcopy(DRAFT)
    content["context"] = {"passage_revision_id": pin, "ordinal": ordinal}
    return content


def start_child(
    client: TestClient, headers: dict[str, str], pin: object, ordinal: object = 1
) -> dict[str, Any]:
    response = client.post(
        QUESTIONS, json={"content": child_content(pin, ordinal)}, headers=headers
    )
    assert response.status_code == 201, response.text
    return dict(response.json())


def pin_codes(question: dict[str, Any]) -> list[str]:
    return [f["code"] for f in question["findings"] if f["code"] == UNAVAILABLE]


def children(client: TestClient, passage_id: str) -> dict[str, Any]:
    response = client.get(f"{PASSAGES}/{passage_id}/children")
    assert response.status_code == 200, response.text
    return dict(response.json())


# --- The pin ------------------------------------------------------------------------------------


def test_a_child_may_pin_a_checkpoint_of_a_passage_in_its_coaching(
    client: TestClient, headers: dict[str, str]
) -> None:
    _, checkpoint = passage_with_checkpoint(client, headers)
    child = start_child(client, headers, checkpoint["id"])
    assert pin_codes(child) == []
    assert client.get(f"{QUESTIONS}/{child['id']}").json()["findings"] == child["findings"]


def test_a_pin_to_the_passages_draft_is_refused_by_a_finding(
    client: TestClient, headers: dict[str, str]
) -> None:
    # A draft changes underneath its children, so only a checkpoint can be pinned.
    passage, _ = passage_with_checkpoint(client, headers)
    child = start_child(client, headers, passage["working_revision_id"])
    assert [f["path"] for f in child["findings"] if f["code"] == UNAVAILABLE] == [
        "context.passage_revision_id"
    ]


def test_a_pin_to_another_coachings_checkpoint_or_to_nothing_is_a_finding(
    client: TestClient, headers: dict[str, str], owner_db: Database
) -> None:
    outsider = TestClient(client.app)
    outsider_headers = sign_in(outsider, make_member(owner_db, "OWNER").email)
    _, foreign = passage_with_checkpoint(outsider, outsider_headers)
    assert pin_codes(start_child(client, headers, foreign["id"])) == [UNAVAILABLE]
    unknown = "6f1c2a9e-0000-4000-8000-000000000009"
    assert pin_codes(start_child(client, headers, unknown)) == [UNAVAILABLE]


def test_a_pin_that_is_not_an_id_is_left_to_the_shape_checks(
    client: TestClient, headers: dict[str, str]
) -> None:
    child = start_child(client, headers, "not-an-id")
    codes = [f["code"] for f in child["findings"]]
    assert "CONTEXT_PASSAGE_INVALID" in codes
    assert UNAVAILABLE not in codes


def test_saving_a_new_pin_changes_the_finding(client: TestClient, headers: dict[str, str]) -> None:
    _, checkpoint = passage_with_checkpoint(client, headers)
    child = start_child(client, headers, "6f1c2a9e-0000-4000-8000-000000000009")
    assert pin_codes(child) == [UNAVAILABLE]
    saved = client.put(
        f"{QUESTIONS}/{child['id']}/working-revision",
        json={"content": child_content(checkpoint["id"])},
        headers={**headers, **tag(child)},
    ).json()
    assert pin_codes(saved) == []


def test_a_passage_cannot_sit_under_another_passage(
    client: TestClient, headers: dict[str, str]
) -> None:
    _, checkpoint = passage_with_checkpoint(client, headers)
    nested = client.post(
        PASSAGES,
        json={"content": {**READY, "context": {"passage_revision_id": checkpoint["id"]}}},
        headers=headers,
    )
    assert nested.status_code == 201
    assert ("context", "FIELD_NOT_ALLOWED") in [
        (f["path"], f["code"]) for f in nested.json()["findings"]
    ]


# --- The child list -----------------------------------------------------------------------------


def test_a_passage_with_no_checkpoint_has_no_children(
    client: TestClient, headers: dict[str, str]
) -> None:
    started = client.post(PASSAGES, json={}, headers=headers).json()
    assert children(client, started["id"]) == {
        "data": [],
        "latest_checkpoint_number": None,
        "hidden_count": 0,
        "truncated": False,
    }


def test_children_are_listed_in_order_with_the_checkpoint_each_was_written_with(
    client: TestClient, headers: dict[str, str]
) -> None:
    passage, first = passage_with_checkpoint(client, headers)
    second_child = start_child(client, headers, first["id"], ordinal=2)
    first_child = start_child(client, headers, first["id"], ordinal=1)
    start_child(client, headers, "6f1c2a9e-0000-4000-8000-000000000009")  # not under this passage

    listed = children(client, passage["id"])
    assert listed["latest_checkpoint_number"] == 1
    assert [(c["question_id"], c["ordinal"], c["is_current"]) for c in listed["data"]] == [
        (first_child["id"], 1, True),
        (second_child["id"], 2, True),
    ]
    assert listed["data"][0]["code"] == first_child["code"]
    assert listed["data"][0]["pinned_checkpoint_number"] == 1
    assert listed["data"][0]["question_type"] == DRAFT["question_type"]
    assert listed["data"][0]["archived"] is False


def test_a_new_checkpoint_leaves_existing_children_on_the_old_one_until_moved(
    client: TestClient, headers: dict[str, str]
) -> None:
    passage, first = passage_with_checkpoint(client, headers)
    old = start_child(client, headers, first["id"], ordinal=1)
    changed = client.put(
        f"{PASSAGES}/{passage['id']}/working-revision",
        json={"content": {**READY, "title": "Free fall, revised"}},
        headers={**headers, **tag(passage)},
    ).json()
    second = client.post(
        f"{PASSAGES}/{passage['id']}/checkpoints", headers={**headers, **tag(changed)}
    ).json()["latest_checkpoint"]
    assert second["number"] == 2
    fresh = start_child(client, headers, second["id"], ordinal=2)

    listed = children(client, passage["id"])
    assert listed["latest_checkpoint_number"] == 2
    assert [
        (c["question_id"], c["pinned_checkpoint_number"], c["is_current"]) for c in listed["data"]
    ] == [
        (old["id"], 1, False),
        (fresh["id"], 2, True),
    ]
    # The old child still renders against the text it was written with.
    assert (
        client.get(f"/api/v1/passage-revisions/{first['id']}").json()["content"]["title"]
        == "Free fall"
    )

    # Moving the child to the new checkpoint makes it current.
    client.put(
        f"{QUESTIONS}/{old['id']}/working-revision",
        json={"content": child_content(second["id"], 1)},
        headers={**headers, **tag(old)},
    )
    assert [c["is_current"] for c in children(client, passage["id"])["data"]] == [True, True]


def test_archived_children_are_listed_and_marked(
    client: TestClient, headers: dict[str, str]
) -> None:
    passage, checkpoint = passage_with_checkpoint(client, headers)
    child = start_child(client, headers, checkpoint["id"])
    archived = client.post(f"{QUESTIONS}/{child['id']}/archive", headers=headers)
    assert archived.status_code in (200, 204), archived.text
    assert [c["archived"] for c in children(client, passage["id"])["data"]] == [True]


def test_other_peoples_draft_children_are_counted_not_shown_to_those_who_may_not_open_them(
    client: TestClient, headers: dict[str, str], team: dict[str, Member]
) -> None:
    passage, checkpoint = passage_with_checkpoint(client, headers)
    mine = start_child(client, headers, checkpoint["id"], ordinal=1)
    other = TestClient(client.app)
    other_headers = sign_in(other, team["other"].email)
    # Any member may read the checkpoint, so another author can write a child under it.
    theirs = start_child(other, other_headers, checkpoint["id"], ordinal=2)

    seen = children(client, passage["id"])
    assert [c["question_id"] for c in seen["data"]] == [mine["id"]]
    assert seen["hidden_count"] == 1

    editor = TestClient(client.app)
    sign_in(editor, team["editor"].email)
    # The edit-others grant opens drafts, but the passage itself is the author's draft too.
    assert editor.get(f"{PASSAGES}/{passage['id']}").status_code == 200
    everything = children(editor, passage["id"])
    assert [c["question_id"] for c in everything["data"]] == [mine["id"], theirs["id"]]
    assert everything["hidden_count"] == 0


def test_the_child_list_is_not_open_to_other_coachings_or_to_other_peoples_passage_drafts(
    client: TestClient, headers: dict[str, str], team: dict[str, Member], owner_db: Database
) -> None:
    passage, _ = passage_with_checkpoint(client, headers)
    other = TestClient(client.app)
    sign_in(other, team["other"].email)
    assert other.get(f"{PASSAGES}/{passage['id']}/children").status_code == 404
    outsider = TestClient(client.app)
    sign_in(outsider, make_member(owner_db, "OWNER").email)
    assert outsider.get(f"{PASSAGES}/{passage['id']}/children").status_code == 404
    assert TestClient(client.app).get(f"{PASSAGES}/{passage['id']}/children").status_code == 401


# --- A long list is never passed off as complete ------------------------------------------------


def test_a_list_longer_than_the_limit_says_so_and_still_shows_what_the_caller_may_open(
    client: TestClient,
    headers: dict[str, str],
    team: dict[str, Member],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from qbank.modules.questions import passage_service

    monkeypatch.setattr(passage_service, "MAX_CHILDREN", 2)
    passage, checkpoint = passage_with_checkpoint(client, headers)
    other = TestClient(client.app)
    other_headers = sign_in(other, team["other"].email)
    for ordinal in (1, 2, 3):  # someone else's drafts come first, so the author's come after
        start_child(other, other_headers, checkpoint["id"], ordinal=ordinal)
    mine = [start_child(client, headers, checkpoint["id"], ordinal=n) for n in (4, 5, 6)]

    listed = children(client, passage["id"])
    assert listed["hidden_count"] == 3
    assert listed["truncated"] is True
    assert [c["question_id"] for c in listed["data"]] == [mine[0]["id"], mine[1]["id"]]
    assert [c["ordinal"] for c in listed["data"]] == [4, 5]

    monkeypatch.setattr(passage_service, "MAX_CHILDREN", 3)
    assert children(client, passage["id"])["truncated"] is False


def test_children_are_ordered_by_their_numbers_even_when_a_number_is_not_a_number(
    client: TestClient, headers: dict[str, str]
) -> None:
    passage, checkpoint = passage_with_checkpoint(client, headers)
    odd = start_child(client, headers, checkpoint["id"], ordinal="two")
    ten = start_child(client, headers, checkpoint["id"], ordinal=10)
    two = start_child(client, headers, checkpoint["id"], ordinal=2)
    assert [c["question_id"] for c in children(client, passage["id"])["data"]] == [
        two["id"],
        ten["id"],
        odd["id"],
    ]


def test_a_pin_written_in_another_spelling_is_a_finding_not_a_silently_missing_child(
    client: TestClient, headers: dict[str, str]
) -> None:
    passage, checkpoint = passage_with_checkpoint(client, headers)
    shouting = start_child(client, headers, checkpoint["id"].upper())
    assert "CONTEXT_PASSAGE_INVALID" in [f["code"] for f in shouting["findings"]]
    assert children(client, passage["id"])["data"] == []
