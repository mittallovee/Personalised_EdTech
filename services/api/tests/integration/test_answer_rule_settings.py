"""M3 PR 3i-1: the answer limits a coaching can change (D-03).

The numbers that say what an answer may be are settings: a built-in value, the coaching's own, and
optionally an exam's. A changed limit changes the findings on the next look and rewrites nothing.
"""

from collections.abc import Iterator
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from qbank.core.config import AppEnv, Settings
from qbank.core.db import Database
from qbank.core.tenancy import TenantContext
from qbank.main import create_app
from qbank.modules.audit.models import AuditEvent
from tests.integration.conftest import (
    Member,
    MigratedDatabase,
    make_member,
    platform_admin,
    sign_in,
)
from tests.integration.question_support import Catalogue, ready_for, seed_catalogue, seed_exam

PATH = "/api/v1/settings/answer-rules"
QUESTIONS = "/api/v1/questions"
OUT_OF_RANGE = "ANSWER_OUT_OF_RANGE"


@pytest.fixture
def client(migrated_database: MigratedDatabase) -> Iterator[TestClient]:
    settings = Settings(
        app_env=AppEnv.TEST, database_url=migrated_database.app_url, session_cookie_secure=False
    )
    with TestClient(create_app(settings)) as test_client:
        yield test_client


@pytest.fixture
def team(owner_db: Database) -> dict[str, Member]:
    owner = make_member(owner_db, "OWNER")
    return {
        "owner": owner,
        "admin": make_member(owner_db, "ADMIN", org_id=owner.org_id),
        "faculty": make_member(owner_db, "FACULTY", org_id=owner.org_id, grants=["EDIT_OTHERS"]),
    }


@pytest.fixture
def admin_headers(client: TestClient, team: dict[str, Member]) -> dict[str, str]:
    return sign_in(client, team["admin"].email)


@pytest.fixture
def catalogue(owner_db: Database, team: dict[str, Member]) -> Catalogue:
    return seed_catalogue(owner_db, team["owner"].org_id)


def tag(revision: int) -> dict[str, str]:
    return {"If-Match": f'"rev-{revision}"'}


def put(
    client: TestClient,
    headers: dict[str, str],
    revision: int,
    defaults: dict[str, Any],
    exams: dict[str, Any] | None = None,
) -> Any:
    return client.put(
        PATH,
        json={"defaults": defaults, "exams": exams or {}},
        headers={**headers, **tag(revision)},
    )


def integer_question(catalogue: Catalogue, value: int, exam: UUID | None = None) -> dict[str, Any]:
    content = ready_for(catalogue, "INTEGER")
    content["answer"] = {"value": value}
    if exam is not None:
        content["metadata"]["exam_id"] = str(exam)
    return content


def start(client: TestClient, headers: dict[str, str], content: dict[str, Any]) -> dict[str, Any]:
    response = client.post(QUESTIONS, json={"content": content}, headers=headers)
    assert response.status_code == 201, response.text
    return dict(response.json())


def codes(question: dict[str, Any]) -> list[str]:
    return [f["code"] for f in question["findings"]]


# --- Reading and saving -------------------------------------------------------------------------


def test_before_any_change_the_built_in_values_are_shown(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    response = client.get(PATH)
    assert response.status_code == 200
    assert response.headers["ETag"] == '"rev-0"'
    body = response.json()
    assert body["revision"] == 0
    assert (body["defaults"], body["exams"]) == ({}, [])
    assert body["built_in"]["integer_max"] == 999
    assert body["built_in"]["numeric_max"] == "999.00"
    assert body["built_in"]["matching_max_items"] == 10
    assert body["bounds"]["integer_max"] == {"kind": "int", "low": -999999, "high": 999999}
    assert body["bounds"]["numeric_max"]["kind"] == "decimal"
    assert "revision_bytes" not in body["built_in"]  # the safety limits are not settings


def test_saving_changes_the_limits_and_the_next_save_needs_the_new_etag(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    first = put(client, admin_headers, 0, {"integer_max": 9999, "numeric_max": "100.50"})
    assert first.status_code == 200, first.text
    assert first.headers["ETag"] == '"rev-1"'
    assert first.json()["defaults"] == {"integer_max": 9999, "numeric_max": "100.50"}
    assert client.get(PATH).json()["defaults"] == first.json()["defaults"]

    stale = put(client, admin_headers, 0, {"integer_max": 1})
    assert stale.status_code == 412
    assert stale.json()["error"]["code"] == "REVISION_STALE"
    missing = client.put(PATH, json={"defaults": {}}, headers=admin_headers)
    assert missing.status_code == 428
    second = put(client, admin_headers, 1, {})
    assert second.status_code == 200
    assert (second.json()["revision"], second.json()["defaults"]) == (2, {})


def test_every_problem_is_listed_and_nothing_is_saved_when_there_are_any(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    response = put(
        client,
        admin_headers,
        0,
        {"integer_min": 50, "integer_max": 5, "digit_max": 12, "typo_max": 1, "numeric_max": 9.5},
    )
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "ANSWER_RULES_INVALID"
    found = {(p["path"], p["code"]) for p in error["details"]["problems"]}
    assert found == {
        ("defaults.digit_max", "SETTING_OUT_OF_RANGE"),
        ("defaults.typo_max", "SETTING_UNKNOWN"),
        ("defaults.numeric_max", "SETTING_NOT_A_NUMBER"),
        ("defaults", "RANGE_EMPTY"),
    }
    assert client.get(PATH).json()["revision"] == 0


def test_an_unknown_body_field_is_refused(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    response = client.put(
        PATH, json={"defaults": {}, "extra": 1}, headers={**admin_headers, **tag(0)}
    )
    assert response.status_code in (400, 422)


def test_a_change_is_written_to_the_audit_log_with_before_and_after(
    client: TestClient, admin_headers: dict[str, str], team: dict[str, Member], owner_db: Database
) -> None:
    put(client, admin_headers, 0, {"integer_max": 2000})
    put(client, admin_headers, 1, {"integer_max": 3000})
    with owner_db.transaction(TenantContext(organization_id=team["owner"].org_id)) as session:
        events = session.scalars(
            select(AuditEvent)
            .where(
                AuditEvent.action == "ANSWER_RULES_CHANGED",
                AuditEvent.organization_id == team["owner"].org_id,  # the table owner sees all
            )
            .order_by(AuditEvent.created_at)
        ).all()
    assert [(e.before["defaults"], e.after["defaults"]) for e in events] == [
        ({}, {"integer_max": 2000}),
        ({"integer_max": 2000}, {"integer_max": 3000}),
    ]
    assert all(e.actor_user_id == team["admin"].user_id for e in events)


# --- Who may --------------------------------------------------------------------------------


def test_only_the_owner_and_admins_may_read_or_change_the_limits(
    client: TestClient, team: dict[str, Member], owner_db: Database
) -> None:
    faculty = TestClient(client.app)
    faculty_headers = sign_in(faculty, team["faculty"].email)
    assert faculty.get(PATH).status_code == 403
    assert put(faculty, faculty_headers, 0, {}).status_code == 403

    owner = TestClient(client.app)
    owner_headers = sign_in(owner, team["owner"].email)
    assert owner.get(PATH).status_code == 200
    assert put(owner, owner_headers, 0, {"integer_max": 5}).status_code == 200

    assert TestClient(client.app).get(PATH).status_code == 401
    platform = TestClient(client.app)
    sign_in(platform, platform_admin(owner_db))
    assert platform.get(PATH).status_code == 403  # not acting in a coaching


def test_one_coachings_limits_do_not_reach_another(
    client: TestClient, admin_headers: dict[str, str], owner_db: Database, db: Database
) -> None:
    put(client, admin_headers, 0, {"integer_max": 5})
    outsider = TestClient(client.app)
    sign_in(outsider, make_member(owner_db, "OWNER").email)
    assert outsider.get(PATH).json()["revision"] == 0
    other = TenantContext(organization_id=make_member(owner_db, "OWNER").org_id)
    with db.transaction(other) as session:
        assert session.execute(text("SELECT count(*) FROM answer_rule_settings")).scalar_one() == 0


def test_the_database_role_can_change_but_never_delete_the_settings(
    client: TestClient, admin_headers: dict[str, str], team: dict[str, Member], db: Database
) -> None:
    put(client, admin_headers, 0, {"integer_max": 5})
    with (
        pytest.raises(DBAPIError),
        db.transaction(TenantContext(organization_id=team["owner"].org_id)) as session,
    ):
        session.execute(text("DELETE FROM answer_rule_settings"))


# --- Exams ------------------------------------------------------------------------------------


def test_an_exam_must_be_one_of_this_coachings(
    client: TestClient,
    admin_headers: dict[str, str],
    team: dict[str, Member],
    owner_db: Database,
) -> None:
    mine = seed_exam(owner_db, team["owner"].org_id, "JEE Advanced")
    foreign = seed_exam(owner_db, make_member(owner_db, "OWNER").org_id, "NEET")
    ok = put(client, admin_headers, 0, {}, {str(mine): {"integer_max": 100}})
    assert ok.status_code == 200
    assert ok.json()["exams"] == [{"exam_id": str(mine), "values": {"integer_max": 100}}]

    bad = put(client, admin_headers, 1, {}, {str(foreign): {"integer_max": 100}})
    assert bad.status_code == 422
    assert [(p["path"], p["code"]) for p in bad.json()["error"]["details"]["problems"]] == [
        (f"exams.{foreign}", "EXAM_NOT_FOUND")
    ]
    gone = put(client, admin_headers, 1, {}, {"6f1c2a9e-0000-4000-8000-000000000009": {}})
    assert gone.status_code == 422


def test_an_exam_with_no_values_is_not_kept(
    client: TestClient, admin_headers: dict[str, str], team: dict[str, Member], owner_db: Database
) -> None:
    exam = seed_exam(owner_db, team["owner"].org_id)
    saved = put(client, admin_headers, 0, {}, {str(exam): {}})
    assert saved.status_code == 200
    assert saved.json()["exams"] == []


# --- What the limits do to findings -------------------------------------------------------------


def test_a_changed_limit_changes_the_findings_on_the_next_look_and_rewrites_nothing(
    client: TestClient, admin_headers: dict[str, str], catalogue: Catalogue
) -> None:
    question = start(client, admin_headers, integer_question(catalogue, 5000))
    assert OUT_OF_RANGE in codes(question)
    stored = client.get(f"{QUESTIONS}/{question['id']}").json()["content"]

    assert put(client, admin_headers, 0, {"integer_max": 9999}).status_code == 200
    after = client.get(f"{QUESTIONS}/{question['id']}").json()
    assert OUT_OF_RANGE not in codes(after)
    assert after["content"] == stored  # the content is exactly what was saved

    assert put(client, admin_headers, 1, {"integer_max": 100}).status_code == 200
    assert OUT_OF_RANGE in codes(client.get(f"{QUESTIONS}/{question['id']}").json())


def test_an_exams_limits_apply_only_to_questions_labelled_with_that_exam(
    client: TestClient,
    admin_headers: dict[str, str],
    catalogue: Catalogue,
    team: dict[str, Member],
    owner_db: Database,
) -> None:
    advanced = seed_exam(owner_db, team["owner"].org_id, "JEE Advanced")
    main = seed_exam(owner_db, team["owner"].org_id, "JEE Main")
    for_advanced = start(client, admin_headers, integer_question(catalogue, 5000, advanced))
    for_main = start(client, admin_headers, integer_question(catalogue, 5000, main))
    unlabelled = start(client, admin_headers, integer_question(catalogue, 5000))
    assert all(OUT_OF_RANGE in codes(q) for q in (for_advanced, for_main, unlabelled))

    put(client, admin_headers, 0, {}, {str(advanced): {"integer_max": 9999}})
    seen = {
        name: OUT_OF_RANGE in codes(client.get(f"{QUESTIONS}/{q['id']}").json())
        for name, q in (("advanced", for_advanced), ("main", for_main), ("none", unlabelled))
    }
    assert seen == {"advanced": False, "main": True, "none": True}


def test_the_coachings_values_apply_under_an_exams_and_the_list_page_uses_them_too(
    client: TestClient,
    admin_headers: dict[str, str],
    catalogue: Catalogue,
    team: dict[str, Member],
    owner_db: Database,
) -> None:
    exam = seed_exam(owner_db, team["owner"].org_id)
    question = start(client, admin_headers, integer_question(catalogue, -5, exam))
    assert OUT_OF_RANGE in codes(question)  # the built-in minimum is 0
    put(client, admin_headers, 0, {"integer_min": -10}, {str(exam): {"integer_max": 50}})
    assert OUT_OF_RANGE not in codes(client.get(f"{QUESTIONS}/{question['id']}").json())
    summary = client.get(QUESTIONS).json()["data"][0]
    assert summary["finding_counts"]["error"] == 0


def test_the_item_counts_of_a_matching_question_follow_the_limits(
    client: TestClient, admin_headers: dict[str, str], catalogue: Catalogue
) -> None:
    # The fixture has 2 items on the left and 4 on the right.
    question = start(client, admin_headers, ready_for(catalogue, "MATCHING"))
    assert not {"LEFT_COUNT", "RIGHT_COUNT"} & set(codes(question))

    assert put(client, admin_headers, 0, {"matching_max_items": 3}).status_code == 200
    narrow = client.get(f"{QUESTIONS}/{question['id']}").json()
    assert "RIGHT_COUNT" in codes(narrow)
    assert "LEFT_COUNT" not in codes(narrow)

    assert put(client, admin_headers, 1, {"matching_min_items": 3}).status_code == 200
    wider = client.get(f"{QUESTIONS}/{question['id']}").json()
    assert "LEFT_COUNT" in codes(wider)
    assert "RIGHT_COUNT" not in codes(wider)
