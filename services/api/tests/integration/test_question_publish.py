"""M4 PR 4a-4: publish, the label snapshot and start-correction (E-01, E-04, E-07; test T35 and the
publish part of T36).

A published version never changes. A correction is version n+1 under the same master and code: it
starts as a draft copy, stays private to people who may edit, and the published version remains
what every member reads until the new one is published too.
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
from qbank.modules.questions.models import PublishedVersion, ReviewDecision
from tests.integration.conftest import (
    PLATFORM,
    Member,
    MigratedDatabase,
    make_member,
    sign_in,
)
from tests.integration.question_support import Catalogue, ready_for, seed_catalogue

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
        "editor": make_member(owner_db, "FACULTY", org_id=org, grants=["EDIT_OTHERS"]),
        "qc": make_member(owner_db, "FACULTY", org_id=org, grants=["QC"]),
        "approver": make_member(owner_db, "FACULTY", org_id=org, grants=["APPROVE"]),
        "publisher": make_member(owner_db, "FACULTY", org_id=org, grants=["PUBLISH"]),
    }


@pytest.fixture
def catalogue(owner_db: Database, team: dict[str, Member]) -> Catalogue:
    return seed_catalogue(owner_db, team["owner"].org_id)


def as_(client: TestClient, team: dict[str, Member], who: str) -> dict[str, str]:
    return sign_in(client, team[who].email)


def act(
    client: TestClient,
    team: dict[str, Member],
    who: str,
    question: dict[str, Any],
    step: str,
    flow_etag: str | None = None,
) -> Any:
    """Take a step as ``who``, with the question's own workflow ETag unless one is given."""
    headers = as_(client, team, who)
    headers["If-Match"] = flow_etag or question["flow_etag"]
    return client.post(f"{PATH}/{question['id']}/{step}", headers=headers)


def ok(response: Any) -> dict[str, Any]:
    assert response.status_code in (200, 201), response.text
    return dict(response.json())


def submit(client: TestClient, team: dict[str, Member], question: dict[str, Any]) -> dict[str, Any]:
    headers = {**as_(client, team, "author"), "If-Match": f'"rev-{question["revision"]}"'}
    return ok(client.post(f"{PATH}/{question['id']}/submit", headers=headers))


def start(client: TestClient, team: dict[str, Member], content: dict[str, Any]) -> dict[str, Any]:
    response = client.post(PATH, json={"content": content}, headers=as_(client, team, "author"))
    return ok(response)


def run_to(
    client: TestClient, team: dict[str, Member], question: dict[str, Any], last: str
) -> dict[str, Any]:
    """Take the question on from where it is (a draft or returned one) up to ``last``."""
    chain = [("submit", None), ("pass-qc", "qc"), ("approve", "approver"), ("publish", "publisher")]
    for step, who in chain:
        question = (
            submit(client, team, question)
            if who is None
            else ok(act(client, team, who, question, step))
        )
        if step == last:
            break
    return question


@pytest.fixture
def approved(client: TestClient, team: dict[str, Member], catalogue: Catalogue) -> dict[str, Any]:
    return run_to(client, team, start(client, team, ready_for(catalogue)), "approve")


@pytest.fixture
def published(
    client: TestClient, team: dict[str, Member], approved: dict[str, Any]
) -> dict[str, Any]:
    return ok(act(client, team, "publisher", approved, "publish"))


def rows(owner_db: Database, team: dict[str, Member], sql: str, **values: Any) -> list[Any]:
    with owner_db.transaction(TenantContext(organization_id=team["owner"].org_id)) as session:
        # The owner connection is not filtered by row-level security: ``:org`` filters by hand.
        return list(session.execute(text(sql), {"org": team["owner"].org_id, **values}).all())


# ---- publish ----------------------------------------------------------------------------------


def test_publish_makes_the_approved_revision_the_published_one(
    client: TestClient,
    team: dict[str, Member],
    approved: dict[str, Any],
    published: dict[str, Any],
    owner_db: Database,
) -> None:
    assert published["state"] == "PUBLISHED"
    assert published["flow_etag"] == '"flow-5"'
    assert published["review_revision_id"] == approved["review_revision_id"]
    assert published["content"] == approved["content"]
    assert published["allowed_steps"] == []  # the publisher may not edit; no step is left for them
    mine = client.get(f"{PATH}/{published['id']}", headers=as_(client, team, "author")).json()
    assert mine["allowed_steps"] == ["START_CORRECTION"]
    master = rows(
        owner_db,
        team,
        "SELECT m.published_version_id, v.id AS version_id, v.number"
        " FROM question_masters m JOIN question_versions v ON v.master_id = m.id WHERE m.id = :m",
        m=published["id"],
    )
    assert [(r.published_version_id == r.version_id, r.number) for r in master] == [(True, 1)]
    with owner_db.transaction(TenantContext(organization_id=team["owner"].org_id)) as session:
        org = team["owner"].org_id
        decision = session.scalars(
            select(ReviewDecision).where(
                ReviewDecision.organization_id == org, ReviewDecision.step == "PUBLISH"
            )
        ).one()
        record = session.scalars(
            select(PublishedVersion).where(PublishedVersion.organization_id == org)
        ).one()
        assert (decision.from_state, decision.to_state, decision.flow_revision) == (
            "APPROVED",
            "PUBLISHED",
            5,
        )
        assert decision.checklist == {"passed": True, "warnings": []}
        assert decision.actor_id == team["publisher"].user_id
        assert record.published_by == team["publisher"].user_id
        assert str(record.revision_id) == published["review_revision_id"]
        assert len(record.content_hash) == 64
    with owner_db.transaction(PLATFORM) as session:
        events = session.scalars(
            select(AuditEvent).where(
                AuditEvent.entity_id == UUID(published["id"]),
                AuditEvent.action == "QUESTION_PUBLISHED",
            )
        ).all()
    assert len(events) == 1
    assert events[0].after is not None
    assert events[0].after["state"] == "PUBLISHED"


def test_every_member_reads_the_published_version_and_nobody_edits_it(
    client: TestClient, team: dict[str, Member], published: dict[str, Any]
) -> None:
    for who in ("other", "qc", "approver"):
        headers = as_(client, team, who)
        read = client.get(f"{PATH}/{published['id']}", headers=headers)
        assert read.status_code == 200, who
        assert read.json()["state"] == "PUBLISHED"
        assert read.json()["content"] == published["content"]
        assert client.get(f"{PATH}/by-code/{published['code']}", headers=headers).status_code == 200
    author = as_(client, team, "author")
    changed = copy.deepcopy(published["content"])
    changed["stem"] = [{"kind": "paragraph", "text": "Changed after publishing"}]
    saved = client.put(
        f"{PATH}/{published['id']}/working-revision",
        json={"content": changed},
        headers={**author, "If-Match": f'"rev-{published["revision"]}"'},
    )
    assert saved.status_code == 409
    assert saved.json()["error"]["code"] == "QUESTION_NOT_EDITABLE"
    assert saved.json()["error"]["details"] == {"state": "PUBLISHED"}
    withdrawn = act(client, team, "author", published, "withdraw")
    assert withdrawn.status_code == 409
    assert withdrawn.json()["error"]["code"] == "WORKFLOW_STEP_INVALID"
    assert withdrawn.json()["error"]["details"] == {
        "state": "PUBLISHED",
        "allowed": ["START_CORRECTION"],
    }


def test_only_the_publish_grant_or_an_admin_publishes(
    client: TestClient, team: dict[str, Member], approved: dict[str, Any]
) -> None:
    for who in ("author", "other", "qc", "approver"):
        assert act(client, team, who, approved, "publish").status_code == 403, who
    assert client.get(f"{PATH}/{approved['id']}", headers=as_(client, team, "publisher")).json()[
        "allowed_steps"
    ] == ["RETURN", "PUBLISH"]
    assert act(client, team, "admin", approved, "publish").status_code == 200


def test_publish_follows_approve_and_nothing_else(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    question = start(client, team, ready_for(catalogue))
    # Someone else's draft is not found at all, so its existence is not given away.
    assert act(client, team, "publisher", question, "publish").status_code == 404
    in_review = submit(client, team, question)
    skipped = act(client, team, "publisher", in_review, "publish")
    assert skipped.status_code == 409
    assert skipped.json()["error"]["details"]["state"] == "IN_REVIEW"
    at_qc = ok(act(client, team, "qc", in_review, "pass-qc"))
    assert act(client, team, "publisher", at_qc, "publish").status_code == 409


def test_publish_needs_the_current_workflow_etag(
    client: TestClient, team: dict[str, Member], approved: dict[str, Any]
) -> None:
    headers = as_(client, team, "publisher")
    url = f"{PATH}/{approved['id']}/publish"
    assert client.post(url, headers=headers).status_code == 428
    old = act(client, team, "publisher", approved, "publish", flow_etag='"flow-3"')
    assert old.status_code == 412
    assert old.json()["error"]["details"]["current_etag"] == approved["flow_etag"]
    assert act(client, team, "publisher", approved, "publish").status_code == 200
    again = act(client, team, "admin", approved, "publish")  # a second person, on the old ETag
    assert again.status_code == 412


def test_the_checklist_is_checked_again_at_publish(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    def set_limit(value: int, revision: int) -> None:
        response = client.put(
            LIMITS,
            json={"defaults": {"integer_max": value}, "exams": {}},
            headers={**as_(client, team, "admin"), "If-Match": f'"rev-{revision}"'},
        )
        assert response.status_code == 200, response.text

    set_limit(9999, 0)
    content = ready_for(catalogue, "INTEGER")
    content["answer"] = {"value": 5000}
    at_approved = run_to(client, team, start(client, team, content), "approve")
    set_limit(100, 1)  # after QC and approval, the limit is lowered
    blocked = act(client, team, "publisher", at_approved, "publish")
    assert blocked.status_code == 422
    assert blocked.json()["error"]["code"] == "PUBLICATION_CHECKLIST_FAILED"
    assert [f["code"] for f in blocked.json()["error"]["details"]["findings"]] == [
        "ANSWER_OUT_OF_RANGE"
    ]
    read = client.get(f"{PATH}/{at_approved['id']}", headers=as_(client, team, "publisher")).json()
    assert read["state"] == "APPROVED"
    assert "RETURN" in read["allowed_steps"]


def test_a_publisher_may_return_an_approved_question_instead(
    client: TestClient, team: dict[str, Member], approved: dict[str, Any]
) -> None:
    headers = {**as_(client, team, "publisher"), "If-Match": approved["flow_etag"]}
    sent_back = client.post(
        f"{PATH}/{approved['id']}/return",
        json={"reasons": ["OTHER"], "note": NOTE},
        headers=headers,
    )
    assert sent_back.status_code == 200, sent_back.text
    assert sent_back.json()["state"] == "CHANGES_REQUESTED"


# ---- the label snapshot -----------------------------------------------------------------------


def test_the_label_names_are_kept_as_they_were_on_the_day_of_publication(
    team: dict[str, Member],
    catalogue: Catalogue,
    published: dict[str, Any],
    owner_db: Database,
    client: TestClient,
) -> None:
    def labels() -> dict[str, Any]:
        found = rows(
            owner_db, team, "SELECT labels FROM published_versions WHERE organization_id = :org"
        )
        assert len(found) == 1
        return dict(found[0].labels)

    before = labels()
    assert before["class_id"] == {"id": str(catalogue.class_id), "name": "Class 11"}
    assert before["chapter_id"] == {"id": str(catalogue.chapter_id), "name": "Kinematics"}
    assert before["primary_concept_id"] == {"id": str(catalogue.concept_id), "name": "Velocity"}
    rows_changed = rows(
        owner_db,
        team,
        "UPDATE taxonomy_nodes SET name = 'Motion', name_key = 'motion' WHERE id = :id"
        " RETURNING id",
        id=catalogue.chapter_id,
    )
    assert len(rows_changed) == 1
    assert labels() == before  # renaming the chapter later does not change the record
    # The question itself keeps pointing at the same id.
    read = client.get(f"{PATH}/{published['id']}", headers=sign_in(client, team["author"].email))
    assert read.json()["content"]["metadata"]["chapter_id"] == str(catalogue.chapter_id)


# ---- start correction -------------------------------------------------------------------------


def test_a_correction_is_a_new_draft_version_with_the_same_code(
    client: TestClient, team: dict[str, Member], published: dict[str, Any], owner_db: Database
) -> None:
    response = act(client, team, "author", published, "start-correction")
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["id"] == published["id"]
    assert body["code"] == published["code"]
    assert body["version_number"] == 2
    assert body["state"] == "DRAFT"
    assert body["flow_etag"] == '"flow-1"'
    assert body["allowed_steps"] == ["SUBMIT"]
    assert body["review_revision_id"] is None
    assert body["content"] == published["content"]
    assert body["revision"] == 1
    decision = rows(
        owner_db,
        team,
        "SELECT from_state, to_state, flow_revision, revision_id FROM review_decisions"
        " WHERE step = 'START_CORRECTION' AND organization_id = :org",
    )
    assert [(r.from_state, r.to_state, r.flow_revision) for r in decision] == [
        ("PUBLISHED", "DRAFT", 1)
    ]
    assert str(decision[0].revision_id) == published["review_revision_id"]
    versions = rows(
        owner_db,
        team,
        "SELECT number, state FROM question_versions WHERE master_id = :m ORDER BY number",
        m=published["id"],
    )
    assert [(r.number, r.state) for r in versions] == [(1, "PUBLISHED"), (2, "DRAFT")]


def test_while_a_correction_is_open_everyone_else_still_reads_the_published_version(
    client: TestClient, team: dict[str, Member], published: dict[str, Any]
) -> None:
    correction = ok(act(client, team, "author", published, "start-correction"))
    author = as_(client, team, "author")
    changed = copy.deepcopy(correction["content"])
    changed["stem"] = [{"kind": "paragraph", "text": "The corrected question text"}]
    saved = client.put(
        f"{PATH}/{published['id']}/working-revision",
        json={"content": changed},
        headers={**author, "If-Match": f'"rev-{correction["revision"]}"'},
    )
    assert saved.status_code == 200, saved.text
    # The author, and anyone who may edit it, work on version 2.
    for who in ("author", "editor", "admin"):
        read = client.get(f"{PATH}/{published['id']}", headers=as_(client, team, who)).json()
        assert (read["version_number"], read["state"]) == (2, "DRAFT"), who
    # Everyone else still reads version 1, exactly as published.
    for who in ("other", "qc", "approver", "publisher"):
        read = client.get(f"{PATH}/{published['id']}", headers=as_(client, team, who)).json()
        assert (read["version_number"], read["state"]) == (1, "PUBLISHED"), who
        assert read["content"] == published["content"]
        assert read["allowed_steps"] == []


def test_only_one_correction_is_open_at_a_time(
    client: TestClient, team: dict[str, Member], published: dict[str, Any], owner_db: Database
) -> None:
    ok(act(client, team, "author", published, "start-correction"))
    second = act(client, team, "admin", published, "start-correction")
    assert second.status_code == 409
    error = second.json()["error"]
    assert error["code"] == "CORRECTION_ALREADY_OPEN"
    version = rows(
        owner_db,
        team,
        "SELECT id FROM question_versions WHERE master_id = :m AND number = 2",
        m=published["id"],
    )
    assert error["details"] == {"version_id": str(version[0].id)}


def test_a_correction_needs_the_right_to_edit_and_the_published_etag(
    client: TestClient, team: dict[str, Member], published: dict[str, Any], owner_db: Database
) -> None:
    for who in ("other", "qc", "publisher"):
        assert act(client, team, who, published, "start-correction").status_code == 403, who
    headers = as_(client, team, "author")
    url = f"{PATH}/{published['id']}/start-correction"
    assert client.post(url, headers=headers).status_code == 428
    stale = act(client, team, "author", published, "start-correction", flow_etag='"flow-2"')
    assert stale.status_code == 412
    assert stale.json()["error"]["details"]["current_etag"] == published["flow_etag"]
    assert act(client, team, "editor", published, "start-correction").status_code == 201
    outsider = make_member(owner_db, "OWNER", grants=["QC", "APPROVE", "PUBLISH"])
    foreign = client.post(
        url,
        headers={**sign_in(client, outsider.email), "If-Match": published["flow_etag"]},
    )
    assert foreign.status_code == 404


def test_only_a_published_question_can_start_a_correction(
    client: TestClient, team: dict[str, Member], approved: dict[str, Any], catalogue: Catalogue
) -> None:
    refused = act(client, team, "admin", approved, "start-correction")
    assert refused.status_code == 409
    assert refused.json()["error"]["code"] == "WORKFLOW_STEP_INVALID"
    draft = start(client, team, ready_for(catalogue))
    never = act(client, team, "author", draft, "start-correction")
    assert never.status_code == 409
    assert never.json()["error"]["details"]["state"] == "DRAFT"


def test_an_archived_question_cannot_start_a_correction(
    client: TestClient, team: dict[str, Member], published: dict[str, Any]
) -> None:
    archived = client.post(f"{PATH}/{published['id']}/archive", headers=as_(client, team, "admin"))
    assert archived.status_code == 200
    blocked = act(client, team, "author", published, "start-correction")
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "QUESTION_ARCHIVED"


def test_a_corrected_version_goes_through_review_and_replaces_the_published_one(
    client: TestClient, team: dict[str, Member], published: dict[str, Any], owner_db: Database
) -> None:
    correction = ok(act(client, team, "author", published, "start-correction"))
    corrected = copy.deepcopy(correction["content"])
    corrected["stem"] = [{"kind": "paragraph", "text": "The corrected question text"}]
    saved = ok(
        client.put(
            f"{PATH}/{published['id']}/working-revision",
            json={"content": corrected},
            headers={
                **as_(client, team, "author"),
                "If-Match": f'"rev-{correction["revision"]}"',
            },
        )
    )
    second = run_to(client, team, saved, "publish")
    assert (second["version_number"], second["state"]) == (2, "PUBLISHED")
    assert second["code"] == published["code"]
    # Now everyone reads version 2; version 1 is still there, exactly as it was.
    other = client.get(f"{PATH}/{published['id']}", headers=as_(client, team, "other")).json()
    assert (other["version_number"], other["content"]) == (2, corrected)
    versions = rows(
        owner_db,
        team,
        "SELECT v.number, v.state, m.published_version_id = v.id AS current, r.content"
        " FROM question_versions v JOIN question_masters m ON m.id = v.master_id"
        " JOIN question_revisions r ON r.id = v.review_revision_id"
        " WHERE v.master_id = :m ORDER BY v.number",
        m=published["id"],
    )
    assert [(r.number, r.state, r.current) for r in versions] == [
        (1, "PUBLISHED", False),
        (2, "PUBLISHED", True),
    ]
    assert versions[0].content == published["content"]
    assert versions[1].content == corrected
    assert (
        len(rows(owner_db, team, "SELECT 1 FROM published_versions WHERE organization_id = :org"))
        == 2
    )
    # And a third correction can start from version 2.
    third = act(client, team, "author", second, "start-correction")
    assert third.status_code == 201
    assert third.json()["version_number"] == 3
