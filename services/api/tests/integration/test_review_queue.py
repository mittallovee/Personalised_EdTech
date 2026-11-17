"""M4 PR 4c: the shared review queue and its counts (E-05; test T37 part 1).

The queue shows what waits for QC, approval and publication, oldest first, to people who hold at
least one review grant. Work in progress (drafts, returned questions) is never shown to anyone but
its author, and the "returned" tab is the caller's own.
"""

from collections.abc import Iterator
from typing import Any
from uuid import UUID, uuid4

import itertools
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from qbank.core.config import AppEnv, Settings
from qbank.core.db import Database
from qbank.core.tenancy import TenantContext
from qbank.main import create_app
from tests.integration.conftest import (
    Member,
    MigratedDatabase,
    make_member,
    platform_admin,
    sign_in,
)
from tests.integration.question_support import Catalogue, ready_for, seed_catalogue

QUESTIONS = "/api/v1/questions"
QUEUE = "/api/v1/review/queue"
COUNTS = "/api/v1/review/queue/counts"
NOTE = "The answer key disagrees with the worked solution."
RETURN = {"reasons": ["ANSWER_WRONG"], "note": NOTE}


@pytest.fixture
def settings(migrated_database: MigratedDatabase) -> Settings:
    # These tests sign in as many people many times; the sign-in limits are not what they test.
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
        "qc": make_member(owner_db, "FACULTY", org_id=org, grants=["QC"]),
        "approver": make_member(owner_db, "FACULTY", org_id=org, grants=["APPROVE"]),
        "publisher": make_member(owner_db, "FACULTY", org_id=org, grants=["PUBLISH"]),
        "editor": make_member(owner_db, "FACULTY", org_id=org, grants=["EDIT_OTHERS"]),
    }


@pytest.fixture
def catalogue(owner_db: Database, team: dict[str, Member]) -> Catalogue:
    return seed_catalogue(owner_db, team["owner"].org_id)


def as_(client: TestClient, team: dict[str, Member], who: str) -> dict[str, str]:
    return sign_in(client, team[who].email)


def ok(response: Any) -> dict[str, Any]:
    assert response.status_code in (200, 201), response.text
    return dict(response.json())


def start(
    client: TestClient,
    team: dict[str, Member],
    content: dict[str, Any],
    who: str = "author",
) -> dict[str, Any]:
    response = client.post(QUESTIONS, json={"content": content}, headers=as_(client, team, who))
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
) -> Any:
    headers = {**as_(client, team, who), "If-Match": question["flow_etag"]}
    return client.post(f"{QUESTIONS}/{question['id']}/{step}", json=body, headers=headers)


CHAIN = [("pass-qc", "qc"), ("approve", "approver"), ("publish", "publisher")]


def advance(
    client: TestClient, team: dict[str, Member], question: dict[str, Any], through: str
) -> dict[str, Any]:
    """A submitted question taken on through the step named ``through``."""
    for step, who in CHAIN:
        question = ok(act(client, team, who, question, step))
        if step == through:
            break
    return question


_NUMBERS = itertools.count(1)


def waiting(
    client: TestClient,
    team: dict[str, Member],
    catalogue: Catalogue,
    through: str | None = None,
    *,
    who: str = "author",
    **changes: Any,
) -> dict[str, Any]:
    """A new question, submitted by ``who`` and then taken through ``through`` (or left in review).
    ``changes`` replaces top-level fields of the content, such as ``language``."""
    # A stem of its own: identical questions would correctly wait at Pass QC as duplicates (D-16).
    own = [{"kind": "paragraph", "text": f"What is 2 + {next(_NUMBERS)}?"}]
    content = {**ready_for(catalogue), "stem": own, **changes}
    question = submit(client, team, start(client, team, content, who), who)
    return advance(client, team, question, through) if through else question


def queue(client: TestClient, team: dict[str, Member], who: str, **params: Any) -> dict[str, Any]:
    response = client.get(QUEUE, params=params, headers=as_(client, team, who))
    assert response.status_code == 200, response.text
    return dict(response.json())


def codes(page: dict[str, Any]) -> list[str]:
    return [row["code"] for row in page["data"]]


def counts(client: TestClient, team: dict[str, Member], who: str) -> dict[str, int]:
    response = client.get(COUNTS, headers=as_(client, team, who))
    assert response.status_code == 200, response.text
    return dict(response.json())


def backdate(owner_db: Database, org_id: UUID, question_id: str, days: int) -> None:
    """Pretend the question has waited ``days`` days in its present state."""
    with owner_db.transaction(TenantContext(organization_id=org_id)) as session:
        session.execute(
            text(
                "UPDATE question_versions SET state_changed_at = now() - make_interval(days => :d)"
                " WHERE organization_id = :org AND master_id = :master"
            ),
            {"d": days, "org": org_id, "master": question_id},
        )


# ---- what the queue shows ---------------------------------------------------------------------


def test_the_queue_lists_what_waits_with_who_sent_it_and_since_when(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    in_review = waiting(client, team, catalogue)
    passed = waiting(client, team, catalogue, "pass-qc")
    approved = waiting(client, team, catalogue, "approve")
    published = waiting(client, team, catalogue, "publish")

    page = queue(client, team, "qc")

    assert set(codes(page)) == {in_review["code"], passed["code"], approved["code"]}
    assert published["code"] not in codes(page)
    assert page["page"] == {"next_cursor": None, "has_more": False}
    row = next(r for r in page["data"] if r["question_id"] == in_review["id"])
    assert row == {
        "question_id": in_review["id"],
        "code": in_review["code"],
        "question_type": in_review["content"]["question_type"],
        "language": in_review["content"]["language"],
        "subject_id": str(catalogue.subject_id),
        "chapter_id": str(catalogue.chapter_id),
        "state": "IN_REVIEW",
        "version_number": 1,
        "submitted_by": str(team["author"].user_id),
        "waiting_since": row["waiting_since"],
    }
    assert {r["state"] for r in page["data"]} == {"IN_REVIEW", "QC_PASSED", "APPROVED"}


def test_the_queue_is_oldest_first(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    first = waiting(client, team, catalogue)
    second = waiting(client, team, catalogue)
    third = waiting(client, team, catalogue)

    assert codes(queue(client, team, "qc")) == [first["code"], second["code"], third["code"]]
    # Moving the first on puts it behind the others: the queue is ordered by how long each has
    # waited in its present state.
    ok(act(client, team, "qc", first, "pass-qc"))
    waits = [row["waiting_since"] for row in queue(client, team, "qc")["data"]]
    assert waits == sorted(waits)
    assert codes(queue(client, team, "qc"))[-1] == first["code"]


def test_work_in_progress_is_never_in_the_queue(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue, owner_db: Database
) -> None:
    draft = start(client, team, ready_for(catalogue))
    archived = waiting(client, team, catalogue)
    ok(client.post(f"{QUESTIONS}/{archived['id']}/archive", headers=as_(client, team, "author")))
    returned = waiting(client, team, catalogue)
    ok(act(client, team, "qc", returned, "return", RETURN))
    shown = waiting(client, team, catalogue)

    for who in ("qc", "admin", "owner"):
        page = queue(client, team, who)
        assert codes(page) == [shown["code"]], who
        assert draft["code"] not in codes(page)


def test_a_correction_waits_as_version_two_and_the_old_version_does_not(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    question = waiting(client, team, catalogue, "publish")
    assert codes(queue(client, team, "qc")) == []

    correction = ok(act(client, team, "author", question, "start-correction"))
    assert correction["version_number"] == 2
    assert codes(queue(client, team, "qc")) == []  # a draft correction is private work

    submit(client, team, correction)
    page = queue(client, team, "qc")
    assert [(r["code"], r["version_number"], r["state"]) for r in page["data"]] == [
        (question["code"], 2, "IN_REVIEW")
    ]


# ---- the returned tab -------------------------------------------------------------------------


def test_returned_shows_only_what_the_caller_sent_in(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    # Two people who may review each send in a question of their own; the author sends a third.
    mine = waiting(client, team, catalogue, who="qc")
    theirs = waiting(client, team, catalogue, who="approver")
    authors = waiting(client, team, catalogue)
    for question in (mine, theirs, authors):
        ok(act(client, team, "admin", question, "return", RETURN))

    assert codes(queue(client, team, "qc", state="CHANGES_REQUESTED")) == [mine["code"]]
    assert codes(queue(client, team, "approver", state="CHANGES_REQUESTED")) == [theirs["code"]]
    # Not even an admin sees other people's returned work here: it is the author's again.
    assert queue(client, team, "admin", state="CHANGES_REQUESTED")["data"] == []
    # The default view is what waits for review, never what was returned.
    assert queue(client, team, "qc")["data"] == []


def test_returned_goes_back_to_review_once_resubmitted(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    question = waiting(client, team, catalogue, who="qc")
    returned = ok(act(client, team, "admin", question, "return", RETURN))
    assert counts(client, team, "qc")["returned_to_me"] == 1

    revision = ok(client.get(f"{QUESTIONS}/{returned['id']}", headers=as_(client, team, "qc")))
    submit(client, team, revision, "qc")

    assert counts(client, team, "qc") == {
        "waiting_for_qc": 1,
        "waiting_for_approval": 0,
        "waiting_to_publish": 0,
        "returned_to_me": 0,
    }


# ---- counts -----------------------------------------------------------------------------------


def test_counts_say_how_many_wait_at_each_step(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    assert counts(client, team, "qc") == {
        "waiting_for_qc": 0,
        "waiting_for_approval": 0,
        "waiting_to_publish": 0,
        "returned_to_me": 0,
    }
    waiting(client, team, catalogue)
    waiting(client, team, catalogue)
    waiting(client, team, catalogue, "pass-qc")
    waiting(client, team, catalogue, "approve")
    waiting(client, team, catalogue, "publish")  # published: no longer waiting
    sent_back = waiting(client, team, catalogue, who="approver")
    ok(act(client, team, "qc", sent_back, "return", RETURN))

    expected = {"waiting_for_qc": 2, "waiting_for_approval": 1, "waiting_to_publish": 1}
    assert counts(client, team, "qc") == {**expected, "returned_to_me": 0}
    assert counts(client, team, "approver") == {**expected, "returned_to_me": 1}
    # Each count is the length of the list it stands for.
    for who, state, key in (
        ("qc", "IN_REVIEW", "waiting_for_qc"),
        ("qc", "QC_PASSED", "waiting_for_approval"),
        ("qc", "APPROVED", "waiting_to_publish"),
        ("approver", "CHANGES_REQUESTED", "returned_to_me"),
    ):
        assert len(queue(client, team, who, state=state)["data"]) == counts(client, team, who)[key]


# ---- filters (E-05) ---------------------------------------------------------------------------


def test_filter_by_state(client: TestClient, team: dict[str, Member], catalogue: Catalogue) -> None:
    review = waiting(client, team, catalogue)
    passed = waiting(client, team, catalogue, "pass-qc")
    approved = waiting(client, team, catalogue, "approve")

    assert codes(queue(client, team, "qc", state="IN_REVIEW")) == [review["code"]]
    assert codes(queue(client, team, "qc", state="QC_PASSED")) == [passed["code"]]
    assert codes(queue(client, team, "qc", state="APPROVED")) == [approved["code"]]
    # Only the four queue states are queue states (a malformed request is a 400).
    for state in ("DRAFT", "PUBLISHED", "NOPE"):
        response = client.get(QUEUE, params={"state": state}, headers=as_(client, team, "qc"))
        assert response.status_code == 400, state


def test_filter_by_subject_chapter_language_and_author(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    english = waiting(client, team, catalogue)
    hindi = waiting(client, team, catalogue, language="hi", who="other")

    assert codes(queue(client, team, "qc", subject_id=str(catalogue.subject_id))) == [
        english["code"],
        hindi["code"],
    ]
    assert codes(queue(client, team, "qc", chapter_id=str(catalogue.chapter_id))) == [
        english["code"],
        hindi["code"],
    ]
    assert queue(client, team, "qc", subject_id=str(uuid4()))["data"] == []
    assert queue(client, team, "qc", chapter_id=str(uuid4()))["data"] == []
    assert codes(queue(client, team, "qc", language="hi")) == [hindi["code"]]
    assert codes(queue(client, team, "qc", language="HI")) == [hindi["code"]]
    assert queue(client, team, "qc", language="fr")["data"] == []
    assert codes(queue(client, team, "qc", author_id=str(team["other"].user_id))) == [hindi["code"]]
    assert codes(queue(client, team, "qc", author_id=str(team["author"].user_id))) == [
        english["code"]
    ]
    assert queue(client, team, "qc", author_id=str(uuid4()))["data"] == []
    # Filters combine.
    both = {"language": "hi", "author_id": str(team["author"].user_id)}
    assert queue(client, team, "qc", **both)["data"] == []


def test_the_author_is_whoever_sent_that_version_in(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    """A correction started by someone else belongs to them, not to whoever wrote version 1."""
    question = waiting(client, team, catalogue, "publish")
    correction = ok(act(client, team, "admin", question, "start-correction"))
    submit(client, team, correction, "admin")

    page = queue(client, team, "qc")
    assert [r["submitted_by"] for r in page["data"]] == [str(team["admin"].user_id)]
    assert codes(queue(client, team, "qc", author_id=str(team["admin"].user_id))) == [
        question["code"]
    ]
    assert queue(client, team, "qc", author_id=str(team["author"].user_id))["data"] == []


def test_filter_by_how_long_it_has_waited(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue, owner_db: Database
) -> None:
    old = waiting(client, team, catalogue)
    fresh = waiting(client, team, catalogue)
    backdate(owner_db, team["owner"].org_id, old["id"], 5)

    assert codes(queue(client, team, "qc", older_than_days=3)) == [old["code"]]
    assert queue(client, team, "qc", older_than_days=10)["data"] == []
    assert codes(queue(client, team, "qc", older_than_days=1)) == [old["code"]]
    assert codes(queue(client, team, "qc")) == [old["code"], fresh["code"]]
    for bad in (0, -1, 100000):
        response = client.get(
            QUEUE, params={"older_than_days": bad}, headers=as_(client, team, "qc")
        )
        assert response.status_code == 400, bad


def test_hostile_filter_text_is_refused_or_inert(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    waiting(client, team, catalogue)
    headers = as_(client, team, "qc")
    for params in (
        {"subject_id": "1; DROP TABLE question_versions"},
        {"author_id": "not-a-uuid"},
        {"language": "en'; DELETE FROM notifications; --"},
        {"language": "x" * 200},
    ):
        assert client.get(QUEUE, params=params, headers=headers).status_code == 400, params
    assert len(queue(client, team, "qc")["data"]) == 1


# ---- paging -----------------------------------------------------------------------------------


def test_the_queue_pages_in_order_without_gaps_or_repeats(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    sent = [waiting(client, team, catalogue)["code"] for _ in range(5)]

    seen: list[str] = []
    cursor: str | None = None
    pages = 0
    while True:
        params: dict[str, Any] = {"limit": 2, **({"cursor": cursor} if cursor else {})}
        page = queue(client, team, "qc", **params)
        seen += codes(page)
        pages += 1
        assert len(page["data"]) <= 2
        if not page["page"]["has_more"]:
            assert page["page"]["next_cursor"] is None
            break
        cursor = page["page"]["next_cursor"]
        assert cursor
    assert seen == sent
    assert pages == 3


def test_a_damaged_cursor_or_limit_is_refused(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue
) -> None:
    waiting(client, team, catalogue)
    headers = as_(client, team, "qc")
    assert client.get(QUEUE, params={"cursor": "garbage"}, headers=headers).status_code == 400
    assert client.get(QUEUE, params={"limit": 0}, headers=headers).status_code == 400
    assert client.get(QUEUE, params={"limit": 101}, headers=headers).status_code == 400


# ---- who may see it ---------------------------------------------------------------------------


@pytest.mark.parametrize("who", ["author", "other", "editor"])
def test_faculty_without_a_review_grant_may_not_see_the_queue(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue, who: str
) -> None:
    waiting(client, team, catalogue)
    headers = as_(client, team, who)
    for path in (QUEUE, COUNTS):
        response = client.get(path, headers=headers)
        assert response.status_code == 403, (who, path)
        assert response.json()["error"]["code"] == "PERMISSION_DENIED"


@pytest.mark.parametrize("who", ["qc", "approver", "publisher", "admin", "owner"])
def test_any_review_grant_or_an_admin_may_see_all_of_it(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue, who: str
) -> None:
    sent = waiting(client, team, catalogue)
    assert codes(queue(client, team, who)) == [sent["code"]]
    assert counts(client, team, who)["waiting_for_qc"] == 1


def test_it_needs_a_sign_in_and_a_coaching(
    client: TestClient, team: dict[str, Member], owner_db: Database
) -> None:
    assert client.get(QUEUE).status_code == 401
    assert client.get(COUNTS).status_code == 401
    headers = sign_in(client, platform_admin(owner_db))  # not acting in any coaching
    assert client.get(QUEUE, headers=headers).status_code == 403
    assert client.get(COUNTS, headers=headers).status_code == 403


def test_another_coaching_sees_none_of_it(
    client: TestClient, team: dict[str, Member], catalogue: Catalogue, owner_db: Database
) -> None:
    waiting(client, team, catalogue)
    waiting(client, team, catalogue, "pass-qc")
    stranger = make_member(owner_db, "OWNER")
    headers = sign_in(client, stranger.email)

    assert client.get(QUEUE, headers=headers).json()["data"] == []
    assert client.get(COUNTS, headers=headers).json() == {
        "waiting_for_qc": 0,
        "waiting_for_approval": 0,
        "waiting_to_publish": 0,
        "returned_to_me": 0,
    }
    # A filter cannot reach across either: another coaching's subject id finds nothing.
    other = {"subject_id": str(catalogue.subject_id)}
    assert client.get(QUEUE, params=other, headers=headers).json()["data"] == []
    # And the first coaching still sees its own two.
    assert len(queue(client, team, "qc")["data"]) == 2
