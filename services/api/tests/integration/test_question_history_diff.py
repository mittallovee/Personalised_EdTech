"""M4 PR 4d: a question's history and the diff of two of its texts (E-08, E-09; tests T37 for
history and diff, and T40 part 2).

The history lists every step in order, with who and when; what a person sees is decided per version
with the same rule as every other read (drafts and returned questions are private, a correction is
private until submitted), and the diff checks each of its two texts on its own, by revision id.
"""

import copy
from collections.abc import Iterator
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from qbank.core.config import AppEnv, Settings
from qbank.core.db import Database
from qbank.main import create_app
from tests.integration.conftest import Member, MigratedDatabase, make_member, sign_in
from tests.integration.question_support import Catalogue, ready_for, seed_catalogue

PATH = "/api/v1/questions"
NOTE = "The answer key disagrees with the worked solution."
MISSING = "00000000-0000-4000-8000-000000000999"


@pytest.fixture
def settings(migrated_database: MigratedDatabase) -> Settings:
    return Settings(
        app_env=AppEnv.TEST,
        database_url=migrated_database.app_url,
        session_cookie_secure=False,
        login_attempts_per_ip=10_000,
        login_attempts_per_email=10_000,
    )


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings)) as test_client:
        yield test_client


@pytest.fixture
def team(owner_db: Database) -> dict[str, Member]:
    owner = make_member(owner_db, "OWNER")
    org = owner.org_id
    return {
        "owner": owner,
        "admin": make_member(owner_db, "ADMIN", org_id=org),
        "author": make_member(owner_db, "FACULTY", org_id=org),
        "other": make_member(owner_db, "FACULTY", org_id=org),
        "editor": make_member(owner_db, "FACULTY", org_id=org, grants=["EDIT_OTHERS"]),
        "qc": make_member(owner_db, "FACULTY", org_id=org, grants=["QC"]),
        "approver": make_member(owner_db, "FACULTY", org_id=org, grants=["APPROVE"]),
        "publisher": make_member(owner_db, "FACULTY", org_id=org, grants=["PUBLISH"]),
        "stranger": make_member(owner_db, "FACULTY"),  # another coaching
    }


@pytest.fixture
def catalogue(owner_db: Database, team: dict[str, Member]) -> Catalogue:
    return seed_catalogue(owner_db, team["owner"].org_id)


def as_(client: TestClient, team: dict[str, Member], who: str) -> dict[str, str]:
    return sign_in(client, team[who].email)


def ok(response: Any) -> dict[str, Any]:
    assert response.status_code in (200, 201), response.text
    return dict(response.json())


def read(client: TestClient, team: dict[str, Member], who: str, question_id: str) -> dict[str, Any]:
    return ok(client.get(f"{PATH}/{question_id}", headers=as_(client, team, who)))


def start(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue, who: str = "author"
) -> dict[str, Any]:
    body = {"content": ready_for(catalogue)}
    return ok(client.post(PATH, json=body, headers=as_(client, team, who)))


def edit(
    client: TestClient, team: dict[str, Member], question: dict[str, Any], text: str
) -> dict[str, Any]:
    """Replace the first paragraph of the stem, as the author."""
    content = copy.deepcopy(read(client, team, "author", question["id"])["content"])
    at = next(i for i, block in enumerate(content["stem"]) if block["kind"] == "paragraph")
    content["stem"][at]["text"] = text
    current = read(client, team, "author", question["id"])
    headers = {**as_(client, team, "author"), "If-Match": f'"rev-{current["revision"]}"'}
    return ok(
        client.put(
            f"{PATH}/{question['id']}/working-revision", json={"content": content}, headers=headers
        )
    )


def checkpoint(client: TestClient, team: dict[str, Member], question: dict[str, Any]) -> None:
    current = read(client, team, "author", question["id"])
    headers = {**as_(client, team, "author"), "If-Match": f'"rev-{current["revision"]}"'}
    ok(client.post(f"{PATH}/{question['id']}/checkpoints", headers=headers))


def step(
    client: TestClient,
    team: dict[str, Member],
    who: str,
    question: dict[str, Any],
    name: str,
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Take a workflow step as ``who`` with the question's current workflow ETag (a submit takes
    the working text's ETag instead)."""
    current = read(client, team, "author", question["id"])
    tag = f'"rev-{current["revision"]}"' if name == "submit" else current["flow_etag"]
    headers = {**as_(client, team, who), "If-Match": tag}
    return ok(client.post(f"{PATH}/{question['id']}/{name}", json=body, headers=headers))


def to_published(
    client: TestClient, team: dict[str, Member], question: dict[str, Any]
) -> dict[str, Any]:
    step(client, team, "author", question, "submit")
    step(client, team, "qc", question, "pass-qc")
    step(client, team, "approver", question, "approve")
    return step(client, team, "publisher", question, "publish")


def history(client: TestClient, team: dict[str, Member], who: str, question_id: str) -> Any:
    return client.get(f"{PATH}/{question_id}/history", headers=as_(client, team, who))


def entries(
    client: TestClient, team: dict[str, Member], who: str, question_id: str
) -> list[dict[str, Any]]:
    return list(ok(history(client, team, who, question_id))["data"])


def kinds(client: TestClient, team: dict[str, Member], who: str, question_id: str) -> list[str]:
    return [entry["kind"] for entry in entries(client, team, who, question_id)]


def revisions(
    client: TestClient, team: dict[str, Member], who: str, question_id: str
) -> list[dict[str, Any]]:
    return list(
        ok(client.get(f"{PATH}/{question_id}/revisions", headers=as_(client, team, who)))["data"]
    )


def diff(
    client: TestClient, team: dict[str, Member], who: str, question_id: str, before: str, after: str
) -> Any:
    return client.get(
        f"{PATH}/{question_id}/diff",
        params={"from": before, "to": after},
        headers=as_(client, team, who),
    )


# ---- the timeline -----------------------------------------------------------------------------


def test_history_lists_every_step_in_order_with_who_and_what(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    question = start(client, team, catalogue)
    checkpoint(client, team, question)
    step(client, team, "author", question, "submit")
    step(
        client,
        team,
        "qc",
        question,
        "return",
        {"reasons": ["ANSWER_WRONG", "SOLUTION_WRONG"], "note": NOTE},
    )
    edit(client, team, question, "A corrected statement.")
    step(client, team, "author", question, "submit")
    step(client, team, "qc", question, "pass-qc")
    step(client, team, "approver", question, "approve")
    step(client, team, "publisher", question, "publish")
    step(client, team, "author", question, "start-correction")
    headers = as_(client, team, "author")
    ok(client.post(f"{PATH}/{question['id']}/archive", headers=headers))
    ok(client.post(f"{PATH}/{question['id']}/restore", headers=headers))

    found = entries(client, team, "author", question["id"])

    who = {name: str(team[name].user_id) for name in team}
    assert [(e["kind"], e["version_number"], e["actor_id"]) for e in found] == [
        ("CREATED", 1, who["author"]),
        ("CHECKPOINT", 1, who["author"]),
        ("SUBMIT", 1, who["author"]),
        ("RETURN", 1, who["qc"]),
        ("SUBMIT", 1, who["author"]),
        ("PASS_QC", 1, who["qc"]),
        ("APPROVE", 1, who["approver"]),
        ("PUBLISH", 1, who["publisher"]),
        ("START_CORRECTION", 2, who["author"]),
        ("ARCHIVED", None, who["author"]),
        ("RESTORED", None, who["author"]),
    ]
    times = [e["at"] for e in found]
    assert times == sorted(times)
    returned = found[3]
    assert returned["reasons"] == ["ANSWER_WRONG", "SOLUTION_WRONG"]
    assert returned["note"] == NOTE
    assert found[2]["reasons"] == [] and found[2]["note"] is None


def test_a_checkpoint_taken_between_steps_sits_between_them(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    question = start(client, team, catalogue)
    step(client, team, "author", question, "submit")
    step(client, team, "qc", question, "return", {"reasons": ["FORMATTING"], "note": NOTE})
    edit(client, team, question, "Reworded after the return.")
    checkpoint(client, team, question)
    ok(client.post(f"{PATH}/{question['id']}/archive", headers=as_(client, team, "author")))
    ok(client.post(f"{PATH}/{question['id']}/restore", headers=as_(client, team, "author")))
    step(client, team, "author", question, "submit")

    assert kinds(client, team, "author", question["id"]) == [
        "CREATED",
        "SUBMIT",
        "RETURN",
        "CHECKPOINT",
        "ARCHIVED",
        "RESTORED",
        "SUBMIT",
    ]


def test_a_checkpoint_stays_attributed_to_who_took_it_after_someone_else_edits(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    question = start(client, team, catalogue)
    checkpoint(client, team, question)
    current = read(client, team, "author", question["id"])
    headers = {**as_(client, team, "editor"), "If-Match": f'"rev-{current["revision"]}"'}
    ok(
        client.put(
            f"{PATH}/{question['id']}/working-revision",
            json={"content": current["content"]},
            headers=headers,
        )
    )  # saving makes the editor the author of the working copy, as it always has

    [created, taken] = entries(client, team, "author", question["id"])
    assert taken["kind"] == "CHECKPOINT"
    assert taken["actor_id"] == str(team["author"].user_id)
    assert created["actor_id"] == str(team["author"].user_id)


def test_a_step_names_the_text_it_was_taken_on_and_a_checkpoint_the_text_it_froze(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    question = start(client, team, catalogue)
    checkpoint(client, team, question)
    step(client, team, "author", question, "submit")
    step(client, team, "qc", question, "return", {"reasons": ["FORMATTING"], "note": NOTE})
    edit(client, team, question, "Changed after the return.")
    step(client, team, "author", question, "submit")

    found = entries(client, team, "author", question["id"])
    frozen = {
        r["id"] for r in revisions(client, team, "author", question["id"]) if not r["working"]
    }

    by_kind = [(e["kind"], e["revision_id"]) for e in found]
    checkpoint_id = by_kind[1][1]
    first_submit, the_return, second_submit = by_kind[2][1], by_kind[3][1], by_kind[4][1]
    assert by_kind[1][0] == "CHECKPOINT" and by_kind[0][1] is None
    assert {checkpoint_id, first_submit, second_submit} <= frozen
    assert len({checkpoint_id, first_submit, second_submit}) == 3
    assert the_return == first_submit  # the reviewers acted on the text that was submitted


def test_revisions_carry_the_id_the_diff_route_takes(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    question = start(client, team, catalogue)
    checkpoint(client, team, question)
    listed = revisions(client, team, "author", question["id"])
    assert len(listed) == 2
    assert len({r["id"] for r in listed}) == 2
    one = ok(
        client.get(f"{PATH}/{question['id']}/revisions/1", headers=as_(client, team, "author"))
    )
    assert one["id"] in {r["id"] for r in listed}


# ---- who may see it ---------------------------------------------------------------------------


def test_a_drafts_history_is_private_and_opens_when_it_is_submitted(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    question = start(client, team, catalogue)
    qid = question["id"]
    assert history(client, team, "other", qid).status_code == 404
    assert history(client, team, "qc", qid).status_code == 404
    for who in ("author", "editor", "admin"):
        assert kinds(client, team, who, qid) == ["CREATED"]

    step(client, team, "author", question, "submit")
    assert kinds(client, team, "other", qid) == ["CREATED", "SUBMIT"]

    step(client, team, "qc", question, "return", {"reasons": ["FORMATTING"], "note": NOTE})
    assert history(client, team, "other", qid).status_code == 404  # private again while returned
    assert history(client, team, "qc", qid).status_code == 404
    assert kinds(client, team, "author", qid)[-1] == "RETURN"
    assert kinds(client, team, "editor", qid)[-1] == "RETURN"


def test_the_steps_of_a_private_correction_are_not_listed_to_readers_of_the_published_text(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    question = start(client, team, catalogue)
    to_published(client, team, question)
    step(client, team, "author", question, "start-correction")
    qid = question["id"]

    seen_by_a_member = entries(client, team, "other", qid)
    assert [e["kind"] for e in seen_by_a_member] == [
        "CREATED",
        "SUBMIT",
        "PASS_QC",
        "APPROVE",
        "PUBLISH",
    ]
    assert {e["version_number"] for e in seen_by_a_member} == {1}

    seen_by_an_editor = entries(client, team, "editor", qid)
    assert seen_by_an_editor[-1]["kind"] == "START_CORRECTION"
    assert seen_by_an_editor[-1]["version_number"] == 2


def test_nothing_is_listed_to_another_coaching_or_to_someone_not_signed_in(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    question = start(client, team, catalogue)
    to_published(client, team, question)
    qid = question["id"]
    assert history(client, team, "stranger", qid).status_code == 404
    assert (
        client.get(f"{PATH}/{MISSING}/history", headers=as_(client, team, "author")).status_code
        == 404
    )
    client.cookies.clear()
    assert client.get(f"{PATH}/{qid}/history").status_code == 401


# ---- the diff ---------------------------------------------------------------------------------


def two_checkpoints(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> tuple[dict[str, Any], str, str]:
    """A question frozen twice, the second time with a reworded first paragraph."""
    question = start(client, team, catalogue)
    checkpoint(client, team, question)
    edit(client, team, question, "A body of mass 2 kg is pushed with a force of 10 N.")
    checkpoint(client, team, question)
    frozen = sorted(
        (r for r in revisions(client, team, "author", question["id"]) if not r["working"]),
        key=lambda r: r["number"],
    )
    return question, frozen[0]["id"], frozen[1]["id"]


def test_the_diff_of_two_checkpoints_shows_the_reworded_paragraph_word_by_word(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    question, before, after = two_checkpoints(client, team, catalogue)

    result = ok(diff(client, team, "author", question["id"], before, after))

    assert result["identical"] is False
    assert result["from_revision"]["id"] == before and result["to_revision"]["id"] == after
    assert result["from_revision"]["frozen_at"] is not None
    [change] = result["changes"]
    assert change["op"] == "replace"
    assert change["path"][0] == "stem" and change["path"][-1] == "text"
    assert change["after"] == "A body of mass 2 kg is pushed with a force of 10 N."
    segments = change["segments"]
    assert "".join(s["text"] for s in segments if s["kind"] != "insert") == change["before"]
    assert "".join(s["text"] for s in segments if s["kind"] != "delete") == change["after"]
    assert {s["kind"] for s in segments} >= {"insert"}


def test_the_diff_the_other_way_round_swaps_before_and_after(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    question, before, after = two_checkpoints(client, team, catalogue)
    forward = ok(diff(client, team, "author", question["id"], before, after))["changes"][0]
    backward = ok(diff(client, team, "author", question["id"], after, before))["changes"][0]
    assert (backward["before"], backward["after"]) == (forward["after"], forward["before"])


def test_a_text_compared_with_itself_has_no_changes(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    question, before, _ = two_checkpoints(client, team, catalogue)
    result = ok(diff(client, team, "author", question["id"], before, before))
    assert result["identical"] is True and result["changes"] == []


def test_a_correction_can_be_compared_with_the_published_text_by_those_who_may_read_both(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    question = start(client, team, catalogue)
    to_published(client, team, question)
    step(client, team, "author", question, "start-correction")
    edit(client, team, question, "The corrected statement of the problem.")
    qid = question["id"]
    published = next(
        e["revision_id"] for e in entries(client, team, "other", qid) if e["kind"] == "PUBLISH"
    )
    correction = next(
        r["id"]
        for r in revisions(client, team, "author", qid)
        if r["working"] and r["version_number"] == 2
    )

    result = ok(diff(client, team, "editor", qid, published, correction))
    assert [c["op"] for c in result["changes"]] == ["replace"]
    assert (
        result["to_revision"]["version_number"] == 2 and result["to_revision"]["frozen_at"] is None
    )
    ok(diff(client, team, "author", qid, published, correction))

    # A member who may read only the published text can read that, and nothing of the correction.
    assert ok(diff(client, team, "other", qid, published, published))["identical"] is True
    assert diff(client, team, "other", qid, published, correction).status_code == 404
    assert diff(client, team, "other", qid, correction, published).status_code == 404


def test_someone_elses_working_text_is_not_found_even_in_a_submitted_question(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    question = start(client, team, catalogue)
    step(client, team, "author", question, "submit")
    qid = question["id"]
    frozen = next(
        e["revision_id"] for e in entries(client, team, "other", qid) if e["kind"] == "SUBMIT"
    )
    working = next(r["id"] for r in revisions(client, team, "author", qid) if r["working"])

    assert ok(diff(client, team, "other", qid, frozen, frozen))["identical"] is True
    assert diff(client, team, "other", qid, frozen, working).status_code == 404
    assert diff(client, team, "editor", qid, frozen, working).status_code == 200


def test_a_draft_cannot_be_compared_by_someone_who_may_not_open_it(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    question, before, after = two_checkpoints(client, team, catalogue)
    assert diff(client, team, "other", question["id"], before, after).status_code == 404
    assert diff(client, team, "editor", question["id"], before, after).status_code == 200


def test_a_revision_of_another_question_is_not_found(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    first, before, _ = two_checkpoints(client, team, catalogue)
    second = start(client, team, catalogue)
    foreign = next(r["id"] for r in revisions(client, team, "author", second["id"]))
    assert diff(client, team, "author", first["id"], before, foreign).status_code == 404
    assert diff(client, team, "author", first["id"], foreign, before).status_code == 404
    assert diff(client, team, "author", first["id"], before, MISSING).status_code == 404


def test_another_coaching_cannot_compare_texts_even_with_their_ids(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    question, before, after = two_checkpoints(client, team, catalogue)
    assert diff(client, team, "stranger", question["id"], before, after).status_code == 404


def test_the_diff_refuses_a_missing_or_malformed_id_and_a_visitor(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    question, before, after = two_checkpoints(client, team, catalogue)
    qid = question["id"]
    headers = as_(client, team, "author")
    assert (
        client.get(f"{PATH}/{qid}/diff", params={"from": before}, headers=headers).status_code
        == 400
    )
    assert diff(client, team, "author", qid, "not-an-id", after).status_code == 400
    assert diff(client, team, "author", "not-an-id", before, after).status_code == 400
    client.cookies.clear()
    assert client.get(f"{PATH}/{qid}/diff", params={"from": before, "to": after}).status_code == 401


def test_every_revision_id_in_the_history_can_be_compared(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    question = start(client, team, catalogue)
    qid = question["id"]
    checkpoint(client, team, question)
    to_published(client, team, question)
    ids = [UUID(e["revision_id"]) for e in entries(client, team, "other", qid) if e["revision_id"]]
    assert ids
    for revision_id in ids:
        assert diff(client, team, "other", qid, str(ids[0]), str(revision_id)).status_code == 200
