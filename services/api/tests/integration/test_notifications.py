"""M4 PR 4b: in-app notifications (I-01; test T41).

A return and a publication each tell the author, in the same transaction as the step. A person
reads and marks only their own, even next to a colleague in the same coaching, and a step that
fails or is rolled back tells nobody.
"""

from collections.abc import Iterator
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from qbank.core.config import AppEnv, Settings
from qbank.core.db import Database
from qbank.core.tenancy import TenantContext
from qbank.main import create_app
from qbank.modules.notifications.public import notify
from tests.integration.conftest import (
    Member,
    MigratedDatabase,
    make_member,
    platform_admin,
    sign_in,
)
from tests.integration.question_support import Catalogue, ready_for, seed_catalogue

QUESTIONS = "/api/v1/questions"
NOTIFICATIONS = "/api/v1/notifications"
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


def as_(client: TestClient, team: dict[str, Member], who: str) -> dict[str, str]:
    return sign_in(client, team[who].email)


def ok(response: Any) -> dict[str, Any]:
    assert response.status_code in (200, 201), response.text
    return dict(response.json())


def start(client: TestClient, team: dict[str, Member], content: dict[str, Any]) -> dict[str, Any]:
    response = client.post(
        QUESTIONS, json={"content": content}, headers=as_(client, team, "author")
    )
    return ok(response)


def submit(
    client: TestClient, team: dict[str, Member], question: dict[str, Any], who: str = "author"
) -> dict[str, Any]:
    headers = {**as_(client, team, who), "If-Match": f'"rev-{question["revision"]}"'}
    return ok(client.post(f"{QUESTIONS}/{question['id']}/submit", headers=headers))


def act(
    client: TestClient,
    team: dict[str, Member],
    who: str,
    question: dict[str, Any],
    step: str,
    body: dict[str, Any] | None = None,
    flow_etag: str | None = None,
) -> Any:
    headers = {**as_(client, team, who), "If-Match": flow_etag or question["flow_etag"]}
    return client.post(f"{QUESTIONS}/{question['id']}/{step}", json=body, headers=headers)


def publish_chain(
    client: TestClient, team: dict[str, Member], question: dict[str, Any], last: str = "publish"
) -> dict[str, Any]:
    """A submitted question taken on through QC, approval and (by default) publication."""
    chain = [("pass-qc", "qc"), ("approve", "approver"), ("publish", "publisher")]
    for step, who in chain:
        question = ok(act(client, team, who, question, step))
        if step == last:
            break
    return question


def mine(client: TestClient, team: dict[str, Member], who: str, **params: Any) -> dict[str, Any]:
    response = client.get(NOTIFICATIONS, params=params, headers=as_(client, team, who))
    assert response.status_code == 200, response.text
    return dict(response.json())


def unread(client: TestClient, team: dict[str, Member], who: str) -> int:
    response = client.get(f"{NOTIFICATIONS}/unread-count", headers=as_(client, team, who))
    assert response.status_code == 200, response.text
    return int(response.json()["count"])


def stored(owner_db: Database, org_id: UUID, user_id: UUID | None = None) -> list[Any]:
    """The rows in the table, newest first. The owner connection is not filtered by row-level
    security, so the coaching is filtered by hand."""
    with owner_db.transaction(TenantContext(organization_id=org_id)) as session:
        return list(
            session.execute(
                text(
                    "SELECT id, user_id, kind, data, read_at FROM notifications"
                    " WHERE organization_id = :org AND (CAST(:user AS uuid) IS NULL"
                    " OR user_id = :user) ORDER BY created_at DESC, id DESC"
                ),
                {"org": org_id, "user": user_id},
            )
        )


def give(owner_db: Database, member: Member, count: int, kind: str = "TEST_KIND") -> None:
    """Notifications for ``member``, written the way the app writes them."""
    for number in range(count):
        with owner_db.transaction(TenantContext(organization_id=member.org_id)) as session:
            notify(
                session,
                organization_id=member.org_id,
                user_id=member.user_id,
                kind=kind,
                data={"number": number},
            )


# ---- the two kinds M4 sends -------------------------------------------------------------------


def test_a_return_tells_the_author_with_the_reasons_and_the_note(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    in_review = submit(client, team, start(client, team, ready_for(catalogue)))
    assert unread(client, team, "author") == 0
    reply = act(
        client,
        team,
        "qc",
        in_review,
        "return",
        {"reasons": ["ANSWER_WRONG", "SOLUTION_WRONG"], "note": NOTE},
    )
    assert reply.status_code == 200, reply.text
    page = mine(client, team, "author")
    assert len(page["data"]) == 1
    item = page["data"][0]
    assert item["kind"] == "REVIEW_RETURNED"
    assert item["read_at"] is None
    assert item["data"] == {
        "question_id": in_review["id"],
        "code": in_review["code"],
        "version_number": 1,
        "reasons": ["ANSWER_WRONG", "SOLUTION_WRONG"],
        "note": NOTE,
    }
    assert unread(client, team, "author") == 1


def test_a_publication_tells_the_author(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    in_review = submit(client, team, start(client, team, ready_for(catalogue)))
    published = publish_chain(client, team, in_review)
    # Pass QC and approve tell nobody; only the return and the publication do.
    page = mine(client, team, "author")
    assert [item["kind"] for item in page["data"]] == ["QUESTION_PUBLISHED"]
    assert page["data"][0]["data"] == {
        "question_id": published["id"],
        "code": published["code"],
        "version_number": 1,
    }


def test_nothing_is_sent_by_the_steps_that_are_not_a_return_or_a_publication(
    client: TestClient,
    team: dict[str, Member],
    catalogue: Catalogue,
    owner_db: Database,
) -> None:
    in_review = submit(client, team, start(client, team, ready_for(catalogue)))
    publish_chain(client, team, in_review, last="approve")
    assert stored(owner_db, team["owner"].org_id) == []


def test_the_notice_goes_to_the_author_not_to_the_reviewer_or_a_colleague(
    client: TestClient,
    team: dict[str, Member],
    catalogue: Catalogue,
    owner_db: Database,
) -> None:
    in_review = submit(client, team, start(client, team, ready_for(catalogue)))
    ok(act(client, team, "qc", in_review, "return", {"reasons": ["OTHER"], "note": NOTE}))
    rows = stored(owner_db, team["owner"].org_id)
    assert [row.user_id for row in rows] == [team["author"].user_id]
    for who in ("qc", "other", "owner", "admin", "publisher"):
        assert mine(client, team, who)["data"] == []
        assert unread(client, team, who) == 0


def test_a_correction_tells_the_person_who_submitted_it_not_the_first_author(
    client: TestClient,
    team: dict[str, Member],
    catalogue: Catalogue,
    owner_db: Database,
) -> None:
    """The author of version 2 is whoever started and submitted it (here an admin)."""
    published = publish_chain(
        client, team, submit(client, team, start(client, team, ready_for(catalogue)))
    )
    correction = ok(act(client, team, "admin", published, "start-correction"))
    in_review = submit(client, team, correction, who="admin")
    publish_chain(client, team, in_review)
    rows = stored(owner_db, team["owner"].org_id)
    # Newest first: the correction's notice is for the admin, version 1's is still the author's.
    assert [(row.user_id, row.data["version_number"]) for row in rows] == [
        (team["admin"].user_id, 2),
        (team["author"].user_id, 1),
    ]


def test_the_notice_is_written_with_the_step_and_a_failed_step_sends_none(
    client: TestClient,
    team: dict[str, Member],
    catalogue: Catalogue,
    owner_db: Database,
) -> None:
    in_review = submit(client, team, start(client, team, ready_for(catalogue)))
    # A stale tag (412), no tag (428), no right to take the step (403) and a note that is too short
    # (422) each leave the question where it was and send nothing.
    stale = act(
        client, team, "qc", in_review, "return", {"reasons": ["OTHER"], "note": NOTE}, '"flow-9"'
    )
    assert stale.status_code == 412
    headers = as_(client, team, "qc")
    missing = client.post(
        f"{QUESTIONS}/{in_review['id']}/return",
        json={"reasons": ["OTHER"], "note": NOTE},
        headers=headers,
    )
    assert missing.status_code == 428
    forbidden = act(
        client, team, "other", in_review, "return", {"reasons": ["OTHER"], "note": NOTE}
    )
    assert forbidden.status_code == 403
    short = act(client, team, "qc", in_review, "return", {"reasons": ["OTHER"], "note": "no"})
    assert short.status_code == 422
    assert stored(owner_db, team["owner"].org_id) == []


def test_a_notice_rolls_back_with_its_transaction(
    owner_db: Database, team: dict[str, Member]
) -> None:
    member = team["author"]
    context = TenantContext(organization_id=member.org_id)
    with pytest.raises(RuntimeError), owner_db.transaction(context) as session:
        notify(
            session,
            organization_id=member.org_id,
            user_id=member.user_id,
            kind="REVIEW_RETURNED",
            data={},
        )
        raise RuntimeError("the step failed after the notice was added")
    assert stored(owner_db, member.org_id) == []


# ---- reading and marking: only your own -------------------------------------------------------


def test_the_list_is_newest_first_and_pages(
    client: TestClient, team: dict[str, Member], owner_db: Database
) -> None:
    give(owner_db, team["author"], 5)
    first = mine(client, team, "author", limit=2)
    assert [item["data"]["number"] for item in first["data"]] == [4, 3]
    assert first["page"]["has_more"] is True
    second = mine(client, team, "author", limit=2, cursor=first["page"]["next_cursor"])
    assert [item["data"]["number"] for item in second["data"]] == [2, 1]
    last = mine(client, team, "author", limit=2, cursor=second["page"]["next_cursor"])
    assert [item["data"]["number"] for item in last["data"]] == [0]
    assert last["page"] == {"next_cursor": None, "has_more": False}


def test_a_damaged_cursor_is_a_400(client: TestClient, team: dict[str, Member]) -> None:
    response = client.get(
        NOTIFICATIONS, params={"cursor": "not-a-cursor"}, headers=as_(client, team, "author")
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "MALFORMED_REQUEST"


def test_reading_one_marks_it_and_marking_again_keeps_the_first_time(
    client: TestClient, team: dict[str, Member], owner_db: Database
) -> None:
    give(owner_db, team["author"], 2)
    assert unread(client, team, "author") == 2
    target = mine(client, team, "author")["data"][0]
    headers = as_(client, team, "author")
    first = client.post(f"{NOTIFICATIONS}/{target['id']}/read", headers=headers)
    assert first.status_code == 200, first.text
    assert first.json()["read_at"] is not None
    again = client.post(f"{NOTIFICATIONS}/{target['id']}/read", headers=headers)
    assert again.status_code == 200
    assert again.json()["read_at"] == first.json()["read_at"]
    assert unread(client, team, "author") == 1
    only_unread = mine(client, team, "author", unread="true")
    assert [item["id"] for item in only_unread["data"]] == [
        item["id"] for item in mine(client, team, "author")["data"] if item["read_at"] is None
    ]
    assert len(only_unread["data"]) == 1


def test_read_all_marks_only_the_callers_own(
    client: TestClient, team: dict[str, Member], owner_db: Database
) -> None:
    give(owner_db, team["author"], 3)
    give(owner_db, team["other"], 2)
    headers = as_(client, team, "author")
    first = client.post(f"{NOTIFICATIONS}/read-all", headers=headers)
    assert first.status_code == 200, first.text
    assert first.json() == {"updated": 3}
    assert unread(client, team, "author") == 0
    assert unread(client, team, "other") == 2
    again = client.post(f"{NOTIFICATIONS}/read-all", headers=as_(client, team, "author"))
    assert again.json() == {"updated": 0}


def test_someone_elses_notification_cannot_be_read_or_marked(
    client: TestClient, team: dict[str, Member], owner_db: Database
) -> None:
    give(owner_db, team["author"], 1)
    theirs = mine(client, team, "author")["data"][0]
    response = client.post(
        f"{NOTIFICATIONS}/{theirs['id']}/read", headers=as_(client, team, "other")
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
    assert stored(owner_db, team["owner"].org_id)[0].read_at is None
    missing = client.post(
        f"{NOTIFICATIONS}/00000000-0000-4000-8000-000000000000/read",
        headers=as_(client, team, "other"),
    )
    assert missing.status_code == 404


def test_another_coaching_sees_nothing(
    client: TestClient, team: dict[str, Member], owner_db: Database
) -> None:
    give(owner_db, team["author"], 2)
    stranger = {"stranger": make_member(owner_db, "OWNER")}
    assert mine(client, stranger, "stranger")["data"] == []
    assert unread(client, stranger, "stranger") == 0
    theirs = mine(client, team, "author")["data"][0]
    response = client.post(
        f"{NOTIFICATIONS}/{theirs['id']}/read", headers=as_(client, stranger, "stranger")
    )
    assert response.status_code == 404


def test_it_needs_a_sign_in_and_a_coaching(
    client: TestClient, team: dict[str, Member], owner_db: Database
) -> None:
    assert client.get(NOTIFICATIONS).status_code == 401
    assert client.get(f"{NOTIFICATIONS}/unread-count").status_code == 401
    # A platform admin who is not acting in a coaching has none.
    email = platform_admin(owner_db)
    headers = sign_in(client, email)
    assert client.get(NOTIFICATIONS, headers=headers).status_code == 403
    assert client.post(f"{NOTIFICATIONS}/read-all", headers=headers).status_code == 403


# ---- the database itself ----------------------------------------------------------------------


def test_the_database_shows_a_person_only_their_own_rows(
    db: Database, owner_db: Database, team: dict[str, Member]
) -> None:
    give(owner_db, team["author"], 1)
    give(owner_db, team["other"], 1)
    org = team["owner"].org_id
    for who, expected in (("author", 1), ("other", 1), ("qc", 0)):
        context = TenantContext(organization_id=org, user_id=team[who].user_id)
        with db.transaction(context) as session:
            seen = session.execute(
                text("SELECT user_id FROM notifications WHERE organization_id = :org"),
                {"org": org},
            ).all()
        assert len(seen) == expected, who
        assert all(row.user_id == team[who].user_id for row in seen)
    # Without a person in the context, nothing at all.
    with db.transaction(TenantContext(organization_id=org)) as session:
        assert session.execute(text("SELECT count(*) FROM notifications")).scalar() == 0


def test_the_app_can_add_a_notice_for_a_colleague_but_only_in_its_own_coaching(
    db: Database, owner_db: Database, team: dict[str, Member]
) -> None:
    author = team["author"]
    stranger = make_member(owner_db, "OWNER")
    context = TenantContext(organization_id=author.org_id, user_id=team["qc"].user_id)
    with db.transaction(context) as session:
        notify(
            session,
            organization_id=author.org_id,
            user_id=author.user_id,
            kind="REVIEW_RETURNED",
            data={},
        )
    assert len(stored(owner_db, author.org_id, author.user_id)) == 1
    # A row for another coaching is refused by the policy.
    with pytest.raises(DBAPIError), db.transaction(context) as session:
        notify(
            session,
            organization_id=stranger.org_id,
            user_id=stranger.user_id,
            kind="REVIEW_RETURNED",
            data={},
        )
    assert stored(owner_db, stranger.org_id) == []


def test_the_app_may_change_only_the_read_time_and_never_delete(
    db: Database, owner_db: Database, team: dict[str, Member]
) -> None:
    member = team["author"]
    give(owner_db, member, 1)
    context = TenantContext(organization_id=member.org_id, user_id=member.user_id)
    for statement in (
        "UPDATE notifications SET kind = 'OTHER_KIND'",
        "UPDATE notifications SET data = '{}'::jsonb",
        "UPDATE notifications SET user_id = organization_id",
        "DELETE FROM notifications",
    ):
        with pytest.raises(DBAPIError), db.transaction(context) as session:
            session.execute(text(statement))
    with db.transaction(context) as session:
        session.execute(text("UPDATE notifications SET read_at = now()"))
    assert stored(owner_db, member.org_id)[0].read_at is not None


def test_the_kind_and_data_are_checked(owner_db: Database, team: dict[str, Member]) -> None:
    member = team["author"]
    context = TenantContext(organization_id=member.org_id)
    for kind, data in (("lower", "{}"), ("", "{}"), ("A" * 61, "{}"), ("OK_KIND", "[]")):
        with pytest.raises(DBAPIError), owner_db.transaction(context) as session:
            session.execute(
                text(
                    "INSERT INTO notifications (id, organization_id, user_id, kind, data)"
                    " VALUES (gen_random_uuid(), :org, :user, :kind, CAST(:data AS jsonb))"
                ),
                {"org": member.org_id, "user": member.user_id, "kind": kind, "data": data},
            )
