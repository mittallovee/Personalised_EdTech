"""M4 PR 4a-2 (test T33, database part): the trigger repeats the state machine, so even the table
owner cannot skip a step, and a review decision is never changed.

The allowed pairs come from the same hand-written table as the unit test
(``tests/unit/test_question_workflow.py``), so code and database are held to one list.
"""

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from qbank.core.config import AppEnv, Settings
from qbank.core.db import Database
from qbank.core.ids import new_id
from qbank.core.tenancy import TenantContext
from qbank.main import create_app
from qbank.modules.questions.domain.workflow import State
from tests.integration.conftest import MigratedDatabase, make_member, sign_in
from tests.integration.question_support import Catalogue, ready_for, seed_catalogue
from tests.unit.test_question_workflow import EXPECTED

PATH = "/api/v1/questions"
S = State

# The pairs of the table that move one version along (a correction makes a new version instead).
ALLOWED = {
    (state, result) for (state, _), (result, _, new_version) in EXPECTED.items() if not new_version
}
UNDER_REVIEW = {S.IN_REVIEW, S.QC_PASSED, S.APPROVED, S.PUBLISHED}
# The shortest way from DRAFT to each state, used to put a version where a test needs it.
WAY_TO: dict[State, list[State]] = {
    S.DRAFT: [],
    S.IN_REVIEW: [S.IN_REVIEW],
    S.CHANGES_REQUESTED: [S.IN_REVIEW, S.CHANGES_REQUESTED],
    S.QC_PASSED: [S.IN_REVIEW, S.QC_PASSED],
    S.APPROVED: [S.IN_REVIEW, S.QC_PASSED, S.APPROVED],
    S.PUBLISHED: [S.IN_REVIEW, S.QC_PASSED, S.APPROVED, S.PUBLISHED],
}


@pytest.fixture
def settings(migrated_database: MigratedDatabase) -> Settings:
    return Settings(
        app_env=AppEnv.TEST, database_url=migrated_database.app_url, session_cookie_secure=False
    )


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings)) as test_client:
        yield test_client


@dataclass
class Rows:
    """One question's version, two frozen revisions and the working one, and where it stands."""

    org_id: UUID
    master_id: UUID
    version_id: UUID
    frozen: list[UUID]
    working: UUID
    flow: int = 1


@pytest.fixture
def rows(client: TestClient, owner_db: Database) -> Rows:
    owner = make_member(owner_db, "OWNER")
    author = make_member(owner_db, "FACULTY", org_id=owner.org_id)
    catalogue: Catalogue = seed_catalogue(owner_db, owner.org_id)
    headers = sign_in(client, author.email)
    question = client.post(PATH, json={"content": ready_for(catalogue)}, headers=headers).json()
    for _ in range(2):  # two frozen revisions, so "another revision" exists
        etag = {"If-Match": f'"rev-{question["revision"]}"'}
        response = client.post(f"{PATH}/{question['id']}/checkpoints", headers={**headers, **etag})
        assert response.status_code == 201, response.text
        question = response.json()
    with owner_db.transaction(TenantContext(organization_id=owner.org_id)) as session:
        found = session.execute(
            text(
                "SELECT v.id AS version_id, r.id AS revision_id, r.frozen_at IS NOT NULL AS frozen"
                " FROM question_versions v JOIN question_revisions r ON r.version_id = v.id"
                " WHERE v.master_id = :master ORDER BY r.number"
            ),
            {"master": question["id"]},
        ).all()
    return Rows(
        org_id=owner.org_id,
        master_id=UUID(question["id"]),
        version_id=found[0].version_id,
        frozen=[r.revision_id for r in found if r.frozen],
        working=next(r.revision_id for r in found if not r.frozen),
    )


def run(owner_db: Database, rows: Rows, sql: str, **values: Any) -> None:
    with owner_db.transaction(TenantContext(organization_id=rows.org_id)) as session:
        session.execute(text(sql), values)


def state_of(owner_db: Database, rows: Rows) -> str:
    with owner_db.transaction(TenantContext(organization_id=rows.org_id)) as session:
        return str(
            session.execute(
                text("SELECT state FROM question_versions WHERE id = :v"), {"v": rows.version_id}
            ).scalar_one()
        )


def move(
    owner_db: Database,
    rows: Rows,
    state: State,
    *,
    review: UUID | str | None = "default",
    flow_by: int = 1,
) -> None:
    """Change the version's state the way the service does: raise the workflow revision and set
    or clear the revision under review. ``review`` and ``flow_by`` can be bent to test a refusal."""
    if review == "default":
        review = rows.frozen[0] if state in UNDER_REVIEW else None
    run(
        owner_db,
        rows,
        "UPDATE question_versions SET state = :state, flow_revision = :flow,"
        " review_revision_id = :review WHERE id = :v",
        state=state.value,
        flow=rows.flow + flow_by,
        review=review,
        v=rows.version_id,
    )
    rows.flow += flow_by


def put_in(owner_db: Database, rows: Rows, state: State) -> None:
    for step in WAY_TO[state]:
        move(owner_db, rows, step)
    assert state_of(owner_db, rows) == state.value


# ---- every state pair -------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("source", "target"),
    [(a, b) for a in State for b in State if a is not b],
    ids=lambda s: s.value,
)
def test_the_database_allows_exactly_the_pairs_of_the_table(
    owner_db: Database, rows: Rows, source: State, target: State
) -> None:
    put_in(owner_db, rows, source)
    if (source, target) in ALLOWED:
        move(owner_db, rows, target)
        assert state_of(owner_db, rows) == target.value
        return
    with pytest.raises(DBAPIError, match=r"never changes|cannot go from"):
        move(owner_db, rows, target)
    assert state_of(owner_db, rows) == source.value


# ---- the other guards -------------------------------------------------------------------------


def test_every_change_of_state_raises_the_workflow_revision_by_one(
    owner_db: Database, rows: Rows
) -> None:
    with pytest.raises(DBAPIError, match="raises the workflow revision by one"):
        move(owner_db, rows, S.IN_REVIEW, flow_by=2)
    with pytest.raises(DBAPIError, match="raises the workflow revision by one"):
        move(owner_db, rows, S.IN_REVIEW, flow_by=0)
    assert state_of(owner_db, rows) == "DRAFT"


def test_review_needs_a_frozen_revision_of_the_same_version(owner_db: Database, rows: Rows) -> None:
    with pytest.raises(DBAPIError, match="frozen revision"):
        move(owner_db, rows, S.IN_REVIEW, review=rows.working)  # the working copy is not frozen
    with pytest.raises(DBAPIError, match=r"frozen revision|violates foreign key"):
        move(owner_db, rows, S.IN_REVIEW, review=new_id())  # no such revision
    assert state_of(owner_db, rows) == "DRAFT"


def test_work_in_progress_has_nothing_under_review_and_review_has_something(
    owner_db: Database, rows: Rows
) -> None:
    with pytest.raises(DBAPIError, match="changes only with the state"):
        run(
            owner_db,
            rows,
            "UPDATE question_versions SET review_revision_id = :r WHERE id = :v",
            r=rows.frozen[0],
            v=rows.version_id,
        )
    put_in(owner_db, rows, S.IN_REVIEW)
    with pytest.raises(DBAPIError, match="changes only with the state"):
        run(
            owner_db,
            rows,
            "UPDATE question_versions SET review_revision_id = NULL WHERE id = :v",
            v=rows.version_id,
        )


@pytest.mark.parametrize("state", [S.IN_REVIEW, S.QC_PASSED, S.APPROVED])
def test_the_revision_under_review_never_changes_while_it_is_under_review(
    owner_db: Database, rows: Rows, state: State
) -> None:
    put_in(owner_db, rows, state)
    with pytest.raises(DBAPIError, match="changes only with the state"):
        run(
            owner_db,
            rows,
            "UPDATE question_versions SET review_revision_id = :r WHERE id = :v",
            r=rows.frozen[1],
            v=rows.version_id,
        )
    for target in (S.QC_PASSED, S.APPROVED, S.PUBLISHED):
        if (state, target) in ALLOWED:
            with pytest.raises(DBAPIError, match="cannot change after it was submitted"):
                move(owner_db, rows, target, review=rows.frozen[1])


def test_a_published_version_never_changes_even_for_the_table_owner(
    owner_db: Database, rows: Rows
) -> None:
    put_in(owner_db, rows, S.PUBLISHED)
    for sql in (
        "UPDATE question_versions SET state_changed_at = now() WHERE id = :v",
        "UPDATE question_versions SET state = 'DRAFT', review_revision_id = NULL,"
        " flow_revision = flow_revision + 1 WHERE id = :v",
    ):
        with pytest.raises(DBAPIError, match="published version never changes"):
            run(owner_db, rows, sql, v=rows.version_id)


def test_a_new_version_starts_as_a_draft(owner_db: Database, rows: Rows) -> None:
    insert = (
        "INSERT INTO question_versions (id, organization_id, master_id, number, state)"
        " VALUES (:id, :org, :master, 2, :state)"
    )
    for state in ("IN_REVIEW", "APPROVED", "PUBLISHED"):
        with pytest.raises(DBAPIError, match="starts as a draft"):
            run(
                owner_db,
                rows,
                insert,
                id=new_id(),
                org=rows.org_id,
                master=rows.master_id,
                state=state,
            )
    # Only one version may be open, so a correction can start only once the first is published.
    put_in(owner_db, rows, S.PUBLISHED)
    run(owner_db, rows, insert, id=new_id(), org=rows.org_id, master=rows.master_id, state="DRAFT")


def test_only_one_version_of_a_question_is_open_at_a_time(owner_db: Database, rows: Rows) -> None:
    insert = (
        "INSERT INTO question_versions (id, organization_id, master_id, number)"
        " VALUES (:id, :org, :master, 2)"
    )
    with pytest.raises(DBAPIError, match="question_versions_one_open"):
        run(owner_db, rows, insert, id=new_id(), org=rows.org_id, master=rows.master_id)
    put_in(owner_db, rows, S.PUBLISHED)
    run(owner_db, rows, insert, id=new_id(), org=rows.org_id, master=rows.master_id)
    with pytest.raises(DBAPIError, match="question_versions_one_open"):
        run(
            owner_db,
            rows,
            insert.replace(", 2)", ", 3)"),
            id=new_id(),
            org=rows.org_id,
            master=rows.master_id,
        )


# ---- the revisions of a published version never change (migration 0027) ------------------------


def test_the_revisions_of_a_published_version_never_change_even_for_the_table_owner(
    owner_db: Database, rows: Rows
) -> None:
    put_in(owner_db, rows, S.PUBLISHED)
    statements = (
        # The working copy, which the frozen-revision guard does not cover.
        ("UPDATE question_revisions SET content = '{}'::jsonb WHERE id = :r", rows.working),
        ("DELETE FROM question_revisions WHERE id = :r", rows.working),
        ("DELETE FROM question_revisions WHERE id = :r", rows.frozen[1]),
        ("UPDATE question_revisions SET number = 99 WHERE id = :r", rows.frozen[0]),
    )
    for sql, revision_id in statements:
        with pytest.raises(DBAPIError, match="never change"):
            run(owner_db, rows, sql, r=revision_id)
    with pytest.raises(DBAPIError, match="revisions of a published version never change"):
        run(
            owner_db,
            rows,
            "INSERT INTO question_revisions (id, organization_id, version_id, number, content,"
            " author_id) SELECT :id, organization_id, version_id, 99, '{}'::jsonb, author_id"
            " FROM question_revisions WHERE id = :r",
            id=new_id(),
            r=rows.working,
        )


def test_a_revision_may_still_change_while_its_version_is_not_published(
    owner_db: Database, rows: Rows
) -> None:
    put_in(owner_db, rows, S.APPROVED)
    run(
        owner_db,
        rows,
        "UPDATE question_revisions SET content = '{}'::jsonb WHERE id = :r",
        r=rows.working,
    )


# ---- the published version a master points at ----------------------------------------------------


def point(owner_db: Database, rows: Rows, version: UUID | None) -> None:
    run(
        owner_db,
        rows,
        "UPDATE question_masters SET published_version_id = :v WHERE id = :m",
        v=version,
        m=rows.master_id,
    )


def test_a_master_points_only_at_one_of_its_own_published_versions(
    owner_db: Database, rows: Rows
) -> None:
    with pytest.raises(DBAPIError, match="only at one of its published versions"):
        point(owner_db, rows, rows.version_id)  # not published yet
    put_in(owner_db, rows, S.PUBLISHED)
    point(owner_db, rows, rows.version_id)
    with pytest.raises(DBAPIError, match="never unpublished"):
        point(owner_db, rows, None)
    with pytest.raises(DBAPIError, match="only at one of its published versions"):
        point(owner_db, rows, new_id())  # no such version


# ---- publication records are append-only ---------------------------------------------------------


def add_publication(owner_db: Database, rows: Rows) -> UUID:
    record_id = new_id()
    with owner_db.transaction(TenantContext(organization_id=rows.org_id)) as session:
        author = session.execute(
            text("SELECT created_by FROM question_masters WHERE id = :m"), {"m": rows.master_id}
        ).scalar_one()
        session.execute(
            text(
                "INSERT INTO published_versions (id, organization_id, version_id, revision_id,"
                " published_by, content_hash, labels)"
                " VALUES (:id, :org, :v, :r, :by, :hash, '{}'::jsonb)"
            ),
            {
                "id": record_id,
                "org": rows.org_id,
                "v": rows.version_id,
                "r": rows.frozen[0],
                "by": author,
                "hash": "0" * 64,
            },
        )
    return record_id


def test_a_publication_record_is_never_changed_or_deleted_even_by_the_owner(
    owner_db: Database, rows: Rows
) -> None:
    record_id = add_publication(owner_db, rows)
    for sql in (
        "UPDATE published_versions SET labels = '{\"x\": 1}'::jsonb WHERE id = :d",
        "DELETE FROM published_versions WHERE id = :d",
    ):
        with pytest.raises(DBAPIError, match="never changed or deleted"):
            run(owner_db, rows, sql, d=record_id)


def test_a_version_is_published_only_once(owner_db: Database, rows: Rows) -> None:
    add_publication(owner_db, rows)
    with pytest.raises(DBAPIError, match="published_versions_version_id_key"):
        add_publication(owner_db, rows)


def test_the_runtime_role_can_only_add_and_read_publication_records(
    db: Database, rows: Rows
) -> None:
    context = TenantContext(organization_id=rows.org_id)
    for sql in (
        "UPDATE published_versions SET labels = '{}'::jsonb",
        "DELETE FROM published_versions",
    ):
        with (
            pytest.raises(DBAPIError, match="permission denied"),
            db.transaction(context) as session,
        ):
            session.execute(text(sql))


# ---- review decisions are append-only ---------------------------------------------------------


def add_decision(owner_db: Database, rows: Rows) -> UUID:
    decision_id = new_id()
    with owner_db.transaction(TenantContext(organization_id=rows.org_id)) as session:
        author = session.execute(
            text("SELECT created_by FROM question_masters WHERE id = :m"), {"m": rows.master_id}
        ).scalar_one()
        session.execute(
            text(
                "INSERT INTO review_decisions (id, organization_id, version_id, revision_id, step,"
                " from_state, to_state, flow_revision, actor_id)"
                " VALUES (:id, :org, :v, :r, 'SUBMIT', 'DRAFT', 'IN_REVIEW', 2, :actor)"
            ),
            {
                "id": decision_id,
                "org": rows.org_id,
                "v": rows.version_id,
                "r": rows.frozen[0],
                "actor": author,
            },
        )
    return decision_id


def test_a_review_decision_is_never_changed_or_deleted_even_by_the_owner(
    owner_db: Database, rows: Rows
) -> None:
    decision_id = add_decision(owner_db, rows)
    with pytest.raises(DBAPIError, match="never changed or deleted"):
        run(owner_db, rows, "UPDATE review_decisions SET note = 'x' WHERE id = :d", d=decision_id)
    with pytest.raises(DBAPIError, match="never changed or deleted"):
        run(owner_db, rows, "DELETE FROM review_decisions WHERE id = :d", d=decision_id)


def test_the_runtime_role_can_only_add_and_read_decisions(db: Database, rows: Rows) -> None:
    context = TenantContext(organization_id=rows.org_id)
    with db.transaction(context) as session:
        assert session.execute(text("SELECT count(*) FROM review_decisions")).scalar_one() == 0
    for sql in (
        "UPDATE review_decisions SET note = 'x'",
        "DELETE FROM review_decisions",
    ):
        with (
            pytest.raises(DBAPIError, match="permission denied"),
            db.transaction(context) as session,
        ):
            session.execute(text(sql))
