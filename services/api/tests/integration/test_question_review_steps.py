"""M4 PR 4a-3: return, pass QC and approve, and the publication checklist (E-01, E-04, E-06, E-07;
tests T34 and T36).

Every step carries the workflow ETag (``flow-N``). Pass QC and approve are allowed only when the
frozen review revision has no ``error`` and no ``incomplete`` finding, checked against the
coaching's catalogue and answer limits as they are *now*.
"""

import copy
from collections.abc import Iterator
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from qbank.core.config import AppEnv, Settings
from qbank.core.db import Database
from qbank.core.tenancy import TenantContext
from qbank.main import create_app
from qbank.modules.audit.models import AuditEvent
from qbank.modules.questions.models import ReviewDecision
from tests.integration.conftest import (
    PLATFORM,
    Member,
    MigratedDatabase,
    make_member,
    sign_in,
)
from tests.integration.question_support import Catalogue, ready_for, seed_catalogue
from tests.unit.test_question_content import FIXTURES

PATH = "/api/v1/questions"
LIMITS = "/api/v1/settings/answer-rules"
NOTE = "The answer key disagrees with the worked solution."


@pytest.fixture
def settings(migrated_database: MigratedDatabase) -> Settings:
    return Settings(
        app_env=AppEnv.TEST, database_url=migrated_database.app_url, session_cookie_secure=False
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
        "qc": make_member(owner_db, "FACULTY", org_id=org, grants=["QC"]),
        "approver": make_member(owner_db, "FACULTY", org_id=org, grants=["APPROVE"]),
        "publisher": make_member(owner_db, "FACULTY", org_id=org, grants=["PUBLISH"]),
    }


@pytest.fixture
def catalogue(owner_db: Database, team: dict[str, Member]) -> Catalogue:
    return seed_catalogue(owner_db, team["owner"].org_id)


def flow(question: dict[str, Any]) -> dict[str, str]:
    return {"If-Match": question["flow_etag"]}


def act(
    client: TestClient,
    headers: dict[str, str],
    question: dict[str, Any],
    step: str,
    body: dict[str, Any] | None = None,
) -> Any:
    return client.post(
        f"{PATH}/{question['id']}/{step}", json=body, headers={**headers, **flow(question)}
    )


def start_and_submit(
    client: TestClient, team: dict[str, Member], content: dict[str, Any]
) -> dict[str, Any]:
    headers = sign_in(client, team["author"].email)
    question = client.post(PATH, json={"content": content}, headers=headers).json()
    response = client.post(
        f"{PATH}/{question['id']}/submit",
        headers={**headers, "If-Match": f'"rev-{question["revision"]}"'},
    )
    assert response.status_code == 200, response.text
    return dict(response.json())


@pytest.fixture
def in_review(client: TestClient, team: dict[str, Member], catalogue: Catalogue) -> dict[str, Any]:
    return start_and_submit(client, team, ready_for(catalogue))


def as_(client: TestClient, team: dict[str, Member], who: str) -> dict[str, str]:
    return sign_in(client, team[who].email)


def passed(client: TestClient, team: dict[str, Member], question: dict[str, Any]) -> dict[str, Any]:
    response = act(client, as_(client, team, "qc"), question, "pass-qc")
    assert response.status_code == 200, response.text
    return dict(response.json())


def approved(client: TestClient, team: dict[str, Member], at_qc: dict[str, Any]) -> dict[str, Any]:
    """Approve a question that has passed QC (so it carries the QC_PASSED workflow ETag)."""
    response = act(client, as_(client, team, "approver"), at_qc, "approve")
    assert response.status_code == 200, response.text
    return dict(response.json())


def decisions(owner_db: Database, team: dict[str, Member]) -> list[ReviewDecision]:
    org = team["owner"].org_id
    with owner_db.transaction(TenantContext(organization_id=org)) as session:
        rows = session.scalars(
            select(ReviewDecision)
            .where(ReviewDecision.organization_id == org)
            .order_by(ReviewDecision.flow_revision)
        ).all()
        session.expunge_all()
    return list(rows)


# ---- return -----------------------------------------------------------------------------------


def test_qc_returns_a_question_with_reasons_and_a_note(
    client: TestClient,
    team: dict[str, Member],
    in_review: dict[str, Any],
    owner_db: Database,
) -> None:
    response = act(
        client,
        as_(client, team, "qc"),
        in_review,
        "return",
        {"reasons": ["ANSWER_WRONG", "SOLUTION_WRONG", "ANSWER_WRONG"], "note": f"  {NOTE}  "},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["state"] == "CHANGES_REQUESTED"
    assert body["flow_etag"] == '"flow-3"'
    assert body["review_revision_id"] is None
    assert body["content"] == in_review["content"]  # the text the reviewer had in front of them
    # The reviewer who returned it no longer reads it: it is the author's work in progress again.
    row = [d for d in decisions(owner_db, team) if d.step == "RETURN"]
    assert len(row) == 1
    assert (row[0].from_state, row[0].to_state, row[0].flow_revision) == (
        "IN_REVIEW",
        "CHANGES_REQUESTED",
        3,
    )
    assert row[0].reasons == ["ANSWER_WRONG", "SOLUTION_WRONG"]  # in order, each once
    assert row[0].note == NOTE
    assert str(row[0].revision_id) == in_review["review_revision_id"]
    assert row[0].actor_id == team["qc"].user_id


def test_the_author_sees_the_returned_question_and_can_edit_and_resubmit_it(
    client: TestClient, team: dict[str, Member], in_review: dict[str, Any]
) -> None:
    assert (
        act(
            client,
            as_(client, team, "qc"),
            in_review,
            "return",
            {"reasons": ["OTHER"], "note": NOTE},
        ).status_code
        == 200
    )
    author = as_(client, team, "author")
    mine = client.get(f"{PATH}/{in_review['id']}", headers=author).json()
    assert mine["state"] == "CHANGES_REQUESTED"
    assert mine["allowed_steps"] == ["SUBMIT"]
    changed = copy.deepcopy(mine["content"])
    changed["stem"] = [{"kind": "paragraph", "text": "Fixed after the return"}]
    saved = client.put(
        f"{PATH}/{in_review['id']}/working-revision",
        json={"content": changed},
        headers={**author, "If-Match": f'"rev-{mine["revision"]}"'},
    )
    assert saved.status_code == 200, saved.text
    again = client.post(
        f"{PATH}/{in_review['id']}/submit",
        headers={**author, "If-Match": f'"rev-{saved.json()["revision"]}"'},
    )
    assert again.status_code == 200, again.text
    assert again.json()["state"] == "IN_REVIEW"
    assert again.json()["review_revision_id"] != in_review["review_revision_id"]
    # Other faculty could not see it while it was returned, and can again now it is resubmitted.
    other = as_(client, team, "other")
    assert client.get(f"{PATH}/{in_review['id']}", headers=other).status_code == 200


def test_a_returned_question_is_private_to_its_author(
    client: TestClient, team: dict[str, Member], in_review: dict[str, Any]
) -> None:
    act(client, as_(client, team, "qc"), in_review, "return", {"reasons": ["OTHER"], "note": NOTE})
    for who in ("other", "qc"):
        read = client.get(f"{PATH}/{in_review['id']}", headers=as_(client, team, who))
        assert read.status_code == 404, who


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"reasons": [], "note": NOTE},
        {"reasons": ["OTHER"]},
        {"reasons": ["OTHER"], "note": ""},
        {"reasons": ["OTHER"], "note": "too short"},  # nine characters
        {"reasons": ["OTHER"], "note": "   padded   "},  # spaces do not count
    ],
)
def test_a_return_needs_a_reason_and_a_note_of_ten_characters(
    client: TestClient, team: dict[str, Member], in_review: dict[str, Any], body: dict[str, Any]
) -> None:
    response = act(client, as_(client, team, "qc"), in_review, "return", body)
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "RETURN_REASON_REQUIRED"
    current = client.get(f"{PATH}/{in_review['id']}", headers=as_(client, team, "qc")).json()
    assert current["state"] == "IN_REVIEW"


def test_a_reason_must_be_one_of_the_list_and_the_note_has_a_limit(
    client: TestClient, team: dict[str, Member], in_review: dict[str, Any]
) -> None:
    """A body of the wrong shape is a malformed request (400), not a broken business rule."""
    qc = as_(client, team, "qc")
    unknown = act(client, qc, in_review, "return", {"reasons": ["BORING"], "note": NOTE})
    assert unknown.status_code == 400
    assert unknown.json()["error"]["code"] == "MALFORMED_REQUEST"
    long = act(client, qc, in_review, "return", {"reasons": ["OTHER"], "note": "x" * 2001})
    assert long.status_code == 400
    assert client.get(f"{PATH}/{in_review['id']}", headers=qc).json()["state"] == "IN_REVIEW"


def test_a_note_is_kept_as_plain_text(
    client: TestClient, team: dict[str, Member], in_review: dict[str, Any], owner_db: Database
) -> None:
    hostile = "<script>alert(1)</script> check the answer key"
    act(
        client,
        as_(client, team, "qc"),
        in_review,
        "return",
        {"reasons": ["OTHER"], "note": hostile},
    )
    stored = next(d for d in decisions(owner_db, team) if d.step == "RETURN")
    assert stored.note == hostile  # stored as written; the web shows it as text, never as markup


def test_who_may_return_at_each_stage(
    client: TestClient, team: dict[str, Member], in_review: dict[str, Any]
) -> None:
    body = {"reasons": ["OTHER"], "note": NOTE}
    # In review: the QC grant (an admin always holds it); the author and plain faculty do not.
    for who in ("author", "other", "approver", "publisher"):
        denied = act(client, as_(client, team, who), in_review, "return", body)
        assert denied.status_code == 403, who
    # Passed QC: the approve grant returns it, the QC grant no longer does.
    at_qc = passed(client, team, in_review)
    assert act(client, as_(client, team, "qc"), at_qc, "return", body).status_code == 403
    assert act(client, as_(client, team, "publisher"), at_qc, "return", body).status_code == 403
    # Approved: the publish grant returns it.
    at_approved = approved(client, team, at_qc)
    assert (
        act(client, as_(client, team, "approver"), at_approved, "return", body).status_code == 403
    )
    sent_back = act(client, as_(client, team, "publisher"), at_approved, "return", body)
    assert sent_back.status_code == 200, sent_back.text
    assert sent_back.json()["state"] == "CHANGES_REQUESTED"


def test_an_admin_may_return_at_any_stage(
    client: TestClient, team: dict[str, Member], in_review: dict[str, Any]
) -> None:
    admin = as_(client, team, "admin")
    sent_back = act(client, admin, in_review, "return", {"reasons": ["FORMATTING"], "note": NOTE})
    assert sent_back.status_code == 200, sent_back.text


# ---- pass QC and approve ----------------------------------------------------------------------


def test_qc_passes_and_the_approver_approves_the_same_frozen_revision(
    client: TestClient,
    team: dict[str, Member],
    in_review: dict[str, Any],
    owner_db: Database,
) -> None:
    at_qc = passed(client, team, in_review)
    assert at_qc["state"] == "QC_PASSED"
    assert at_qc["flow_etag"] == '"flow-3"'
    assert at_qc["review_revision_id"] == in_review["review_revision_id"]
    done = approved(client, team, at_qc)
    assert done["state"] == "APPROVED"
    assert done["flow_etag"] == '"flow-4"'
    assert done["review_revision_id"] == in_review["review_revision_id"]
    assert done["content"] == in_review["content"]
    rows = decisions(owner_db, team)
    assert [(d.step, d.from_state, d.to_state) for d in rows] == [
        ("SUBMIT", "DRAFT", "IN_REVIEW"),
        ("PASS_QC", "IN_REVIEW", "QC_PASSED"),
        ("APPROVE", "QC_PASSED", "APPROVED"),
    ]
    assert {str(d.revision_id) for d in rows} == {in_review["review_revision_id"]}
    assert rows[1].actor_id == team["qc"].user_id
    assert rows[2].actor_id == team["approver"].user_id
    # The checklist that was checked is kept as evidence: nothing blocked, nothing to warn about.
    assert rows[1].checklist == {"passed": True, "warnings": []}
    assert rows[2].checklist == {"passed": True, "warnings": []}


def test_each_step_writes_an_audit_event(
    client: TestClient, team: dict[str, Member], in_review: dict[str, Any], owner_db: Database
) -> None:
    done = approved(client, team, passed(client, team, in_review))
    sent_back = act(
        client,
        as_(client, team, "admin"),
        done,
        "return",
        {"reasons": ["OTHER"], "note": NOTE},
    )
    assert sent_back.status_code == 200
    with owner_db.transaction(PLATFORM) as session:
        actions = [
            e.action
            for e in session.scalars(
                select(AuditEvent)
                .where(AuditEvent.entity_id == UUID(in_review["id"]))
                .order_by(AuditEvent.created_at)
            ).all()
            if e.action.startswith("QUESTION_") and e.action != "QUESTION_CREATED"
        ]
    assert actions == [
        "QUESTION_SUBMITTED",
        "QUESTION_QC_PASSED",
        "QUESTION_APPROVED",
        "QUESTION_RETURNED",
    ]


def test_the_wrong_person_may_not_pass_qc_or_approve(
    client: TestClient, team: dict[str, Member], in_review: dict[str, Any]
) -> None:
    for who in ("author", "other", "approver", "publisher"):
        assert act(client, as_(client, team, who), in_review, "pass-qc").status_code == 403, who
    at_qc = passed(client, team, in_review)
    for who in ("author", "other", "qc", "publisher"):
        assert act(client, as_(client, team, who), at_qc, "approve").status_code == 403, who
    assert act(client, as_(client, team, "admin"), at_qc, "approve").status_code == 200


def test_a_step_out_of_order_is_refused_with_what_is_allowed(
    client: TestClient, team: dict[str, Member], in_review: dict[str, Any]
) -> None:
    skip = act(client, as_(client, team, "approver"), in_review, "approve")
    assert skip.status_code == 409
    assert skip.json()["error"]["code"] == "WORKFLOW_STEP_INVALID"
    assert skip.json()["error"]["details"] == {
        "state": "IN_REVIEW",
        "allowed": ["RETURN", "PASS_QC", "WITHDRAW"],
    }
    at_qc = passed(client, team, in_review)
    twice = act(client, as_(client, team, "qc"), at_qc, "pass-qc")
    assert twice.status_code == 409
    assert twice.json()["error"]["details"]["state"] == "QC_PASSED"


def test_the_allowed_steps_follow_the_state_and_the_person(
    client: TestClient, team: dict[str, Member], in_review: dict[str, Any]
) -> None:
    def steps(question: dict[str, Any], who: str) -> list[str]:
        read = client.get(f"{PATH}/{question['id']}", headers=as_(client, team, who))
        return list(read.json()["allowed_steps"])

    assert steps(in_review, "qc") == ["RETURN", "PASS_QC"]
    assert steps(in_review, "author") == ["WITHDRAW"]
    assert steps(in_review, "other") == []
    at_qc = passed(client, team, in_review)
    assert steps(at_qc, "approver") == ["RETURN", "APPROVE"]
    assert steps(at_qc, "qc") == []
    assert steps(at_qc, "author") == ["WITHDRAW"]
    assert steps(at_qc, "admin") == ["RETURN", "APPROVE", "WITHDRAW"]


def test_the_author_may_review_their_own_question(
    client: TestClient, team: dict[str, Member], owner_db: Database, catalogue: Catalogue
) -> None:
    """E-03 ("reviewer must differ from the author") is P2, outside M4; this pins that."""
    author = make_member(owner_db, "FACULTY", org_id=team["owner"].org_id, grants=["QC"])
    headers = sign_in(client, author.email)
    question = client.post(PATH, json={"content": ready_for(catalogue)}, headers=headers).json()
    sent = client.post(
        f"{PATH}/{question['id']}/submit",
        headers={**headers, "If-Match": f'"rev-{question["revision"]}"'},
    ).json()
    assert act(client, headers, sent, "pass-qc").status_code == 200


# ---- the exact revision (T34) -----------------------------------------------------------------


def test_every_step_needs_the_workflow_etag(
    client: TestClient, team: dict[str, Member], in_review: dict[str, Any]
) -> None:
    qc = as_(client, team, "qc")
    for step, body in (
        ("pass-qc", None),
        ("return", {"reasons": ["OTHER"], "note": NOTE}),
    ):
        url = f"{PATH}/{in_review['id']}/{step}"
        assert client.post(url, json=body, headers=qc).status_code == 428, step
        wrong = client.post(url, json=body, headers={**qc, "If-Match": '"rev-2"'})
        assert wrong.status_code == 412, step
        assert wrong.json()["error"]["details"]["current_etag"] == '"flow-2"'


def test_two_reviewers_racing_on_one_step_only_one_wins(
    client: TestClient, team: dict[str, Member], in_review: dict[str, Any]
) -> None:
    first = act(client, as_(client, team, "qc"), in_review, "pass-qc")
    second = act(
        client,
        as_(client, team, "admin"),
        in_review,
        "return",
        {"reasons": ["OTHER"], "note": NOTE},
    )
    assert first.status_code == 200
    assert second.status_code == 412
    assert second.json()["error"]["code"] == "REVISION_STALE"
    assert second.json()["error"]["details"]["current_etag"] == '"flow-3"'


def test_a_withdraw_and_resubmit_cancels_the_earlier_review(
    client: TestClient, team: dict[str, Member], in_review: dict[str, Any]
) -> None:
    at_qc = passed(client, team, in_review)
    author = as_(client, team, "author")
    back = act(client, author, at_qc, "withdraw").json()
    resent = client.post(
        f"{PATH}/{in_review['id']}/submit",
        headers={**author, "If-Match": f'"rev-{back["revision"]}"'},
    ).json()
    assert resent["state"] == "IN_REVIEW"  # QC does not carry over to the new revision
    assert resent["review_revision_id"] != at_qc["review_revision_id"]
    # The approver who read "QC passed" a moment ago is turned away: the ETag moved on.
    stale = act(client, as_(client, team, "approver"), at_qc, "approve")
    assert stale.status_code == 412
    assert stale.json()["error"]["details"]["current_etag"] == resent["flow_etag"]
    assert (
        act(client, as_(client, team, "approver"), resent, "approve").json()["error"]["code"]
        == "WORKFLOW_STEP_INVALID"
    )


def test_another_coachings_question_is_not_found(
    client: TestClient, team: dict[str, Member], in_review: dict[str, Any], owner_db: Database
) -> None:
    outsider = make_member(owner_db, "OWNER", grants=["QC", "APPROVE", "PUBLISH"])
    headers = sign_in(client, outsider.email)
    for step, body in (
        ("pass-qc", None),
        ("approve", None),
        ("return", {"reasons": ["OTHER"], "note": NOTE}),
    ):
        assert act(client, headers, in_review, step, body).status_code == 404, step


def test_a_removed_grant_stops_working_on_the_next_request(
    client: TestClient, team: dict[str, Member], in_review: dict[str, Any], owner_db: Database
) -> None:
    qc = as_(client, team, "qc")
    assert client.get(f"{PATH}/{in_review['id']}", headers=qc).json()["allowed_steps"] == [
        "RETURN",
        "PASS_QC",
    ]
    with owner_db.transaction(TenantContext(organization_id=team["owner"].org_id)) as session:
        session.execute(
            text("DELETE FROM membership_grants WHERE membership_id = :m"),
            {"m": team["qc"].membership_id},
        )
    assert act(client, qc, in_review, "pass-qc").status_code == 403


def test_an_archived_question_takes_no_step(
    client: TestClient, team: dict[str, Member], in_review: dict[str, Any]
) -> None:
    assert (
        client.post(
            f"{PATH}/{in_review['id']}/archive", headers=as_(client, team, "admin")
        ).status_code
        == 200
    )
    blocked = act(client, as_(client, team, "qc"), in_review, "pass-qc")
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "QUESTION_ARCHIVED"


# ---- the publication checklist (T36) ----------------------------------------------------------


def set_integer_max(client: TestClient, team: dict[str, Member], value: int, revision: int) -> None:
    """Change the coaching's integer answer limit as an admin (settings revision ``revision``)."""
    response = client.put(
        LIMITS,
        json={"defaults": {"integer_max": value}, "exams": {}},
        headers={**as_(client, team, "admin"), "If-Match": f'"rev-{revision}"'},
    )
    assert response.status_code == 200, response.text


def a_question_still_to_do(client: TestClient, team: dict[str, Member]) -> dict[str, Any]:
    return start_and_submit(client, team, copy.deepcopy(FIXTURES["SCQ"]["draft"]))


def test_a_question_with_things_still_to_do_cannot_pass_qc(
    client: TestClient, team: dict[str, Member]
) -> None:
    question = a_question_still_to_do(client, team)
    assert any(f["level"] == "incomplete" for f in question["findings"])
    blocked = act(client, as_(client, team, "qc"), question, "pass-qc")
    assert blocked.status_code == 422
    error = blocked.json()["error"]
    assert error["code"] == "PUBLICATION_CHECKLIST_FAILED"
    listed = error["details"]["findings"]
    assert listed and {f["level"] for f in listed} <= {"error", "incomplete"}
    assert all({"path", "code", "level", "message"} <= f.keys() for f in listed)
    # Nothing moved, so the same ETag still works for a return.
    sent_back = act(
        client, as_(client, team, "qc"), question, "return", {"reasons": ["OTHER"], "note": NOTE}
    )
    assert sent_back.status_code == 200


def test_each_missing_item_names_the_finding_that_blocks(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    for field in ("difficulty", "bloom_level", "topic_id", "primary_concept_id"):
        content = ready_for(catalogue)
        del content["metadata"][field]
        question = start_and_submit(client, team, content)
        blocked = act(client, as_(client, team, "qc"), question, "pass-qc")
        assert blocked.status_code == 422, field
        paths = [f["path"] for f in blocked.json()["error"]["details"]["findings"]]
        assert f"metadata.{field}" in paths, (field, paths)


def test_an_answer_limit_lowered_after_submit_blocks_pass_qc(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    set_integer_max(client, team, 9999, revision=0)
    content = ready_for(catalogue, "INTEGER")
    content["answer"] = {"value": 5000}
    question = start_and_submit(client, team, content)
    assert question["findings"] == []
    set_integer_max(client, team, 100, revision=1)
    blocked = act(client, as_(client, team, "qc"), question, "pass-qc")
    assert blocked.status_code == 422
    assert [f["code"] for f in blocked.json()["error"]["details"]["findings"]] == [
        "ANSWER_OUT_OF_RANGE"
    ]


def test_the_checklist_is_checked_again_at_approve(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    set_integer_max(client, team, 9999, revision=0)
    content = ready_for(catalogue, "INTEGER")
    content["answer"] = {"value": 5000}
    at_qc = passed(client, team, start_and_submit(client, team, content))
    set_integer_max(client, team, 100, revision=1)
    blocked = act(client, as_(client, team, "approver"), at_qc, "approve")
    assert blocked.status_code == 422
    assert blocked.json()["error"]["code"] == "PUBLICATION_CHECKLIST_FAILED"
    # The question stays where it was, and the approver may still send it back.
    read = client.get(f"{PATH}/{at_qc['id']}", headers=as_(client, team, "approver")).json()
    assert read["state"] == "QC_PASSED"
    assert "RETURN" in read["allowed_steps"]


def test_a_warning_does_not_block_and_is_kept_with_the_decision(
    client: TestClient,
    team: dict[str, Member],
    in_review: dict[str, Any],
    catalogue: Catalogue,
    owner_db: Database,
) -> None:
    with owner_db.transaction(TenantContext(organization_id=team["owner"].org_id)) as session:
        session.execute(
            text("UPDATE taxonomy_nodes SET state = 'DEPRECATED' WHERE id = :id"),
            {"id": catalogue.chapter_id},
        )
    at_qc = passed(client, team, in_review)  # a retired chapter is only a warning
    assert [(f["code"], f["level"]) for f in at_qc["findings"]] == [
        ("DEPRECATED_REFERENCE", "warning")
    ]
    qc_decision = next(d for d in decisions(owner_db, team) if d.step == "PASS_QC")
    assert qc_decision.checklist == {"passed": True, "warnings": ["DEPRECATED_REFERENCE"]}


def test_the_checklist_reads_the_frozen_revision_not_the_working_copy(
    client: TestClient, team: dict[str, Member], in_review: dict[str, Any], owner_db: Database
) -> None:
    """Nothing can reach the frozen text: even a change made behind the API to the working copy
    (which the server refuses to save in review) cannot change what QC checks."""
    with owner_db.transaction(TenantContext(organization_id=team["owner"].org_id)) as session:
        session.execute(
            text(
                "UPDATE question_revisions SET content = '{}'::jsonb"
                " WHERE version_id IN (SELECT id FROM question_versions WHERE master_id = :m)"
                " AND frozen_at IS NULL"
            ),
            {"m": in_review["id"]},
        )
    assert passed(client, team, in_review)["state"] == "QC_PASSED"
