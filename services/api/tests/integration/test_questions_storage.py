"""M3 PR 3b-1: questions are stored as master, version and revision (D-11, D-12, E-04; T27).

Service level: the routes arrive in the next pull request. The database rules (tenant isolation,
a frozen revision never changes, nothing is deleted) are tested against the real tables.
"""

import copy
from dataclasses import replace
from typing import Any
from uuid import UUID

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError

from qbank.core.auth import Principal
from qbank.core.codes import ALPHABET, CODE_LENGTH
from qbank.core.db import Database
from qbank.core.errors import Conflict, NotFound, PermissionDenied, ValidationFailed
from qbank.core.ids import new_id
from qbank.modules.audit.models import AuditEvent
from qbank.modules.questions import service
from qbank.modules.questions.models import QuestionMaster, QuestionRevision
from qbank.modules.questions.public import DEFAULT_RULES
from tests.integration.conftest import Member, make_member
from tests.integration.question_support import Catalogue, ready_for, seed_catalogue
from tests.unit.test_question_content import FIXTURES

DRAFT = FIXTURES["SCQ"]["draft"]
READY = FIXTURES["SCQ"]["ready"]


def principal_of(member: Member, role: str, grants: frozenset[str] = frozenset()) -> Principal:
    return Principal(
        user_id=member.user_id,
        display_name=role.title(),
        is_platform_admin=False,
        organization_id=member.org_id,
        role=role,
        grants=grants,
    )


@pytest.fixture
def team(owner_db: Database) -> dict[str, Principal]:
    owner = make_member(owner_db, "OWNER")
    return {
        "owner": principal_of(owner, "OWNER"),
        "admin": principal_of(make_member(owner_db, "ADMIN", org_id=owner.org_id), "ADMIN"),
        "author": principal_of(make_member(owner_db, "FACULTY", org_id=owner.org_id), "FACULTY"),
        "other": principal_of(make_member(owner_db, "FACULTY", org_id=owner.org_id), "FACULTY"),
        "editor": principal_of(
            make_member(owner_db, "FACULTY", org_id=owner.org_id, grants=["EDIT_OTHERS"]),
            "FACULTY",
            frozenset({"EDIT_OTHERS"}),
        ),
    }


@pytest.fixture
def catalogue(owner_db: Database, team: dict[str, Principal]) -> Catalogue:
    assert team["owner"].organization_id is not None
    return seed_catalogue(owner_db, team["owner"].organization_id)


def create(
    db: Database, who: Principal, content: dict[str, Any], key: str | None = None
) -> service.QuestionView:
    with db.transaction(who.tenant_context) as session:
        view = service.create_question(
            session, who, content, idempotency_key=key, request_id="req-1"
        )
        session.expunge_all()
        return view


def fetch(db: Database, who: Principal, question_id: UUID) -> service.QuestionView:
    with db.transaction(who.tenant_context) as session:
        view = service.get_question(session, who, question_id)
        session.expunge_all()
        return view


# --- creating ------------------------------------------------------------------------------------


def test_a_new_question_gets_a_code_a_first_version_and_a_working_revision(
    db: Database, team: dict[str, Principal], catalogue: Catalogue
) -> None:
    ready = ready_for(catalogue)
    view = create(db, team["author"], copy.deepcopy(ready))
    assert len(view.master.code) == CODE_LENGTH
    assert set(view.master.code) <= set(ALPHABET)
    assert view.master.created_by == team["author"].user_id
    assert view.master.archived_at is None
    assert view.version.number == 1
    assert view.revision.number == 1
    assert view.revision.frozen_at is None
    assert view.revision.content == ready
    assert view.findings == []


def test_a_draft_with_gaps_saves_and_says_what_is_missing(
    db: Database, team: dict[str, Principal]
) -> None:
    view = create(db, team["author"], copy.deepcopy(DRAFT))
    assert [f.code for f in view.findings] == [
        "METADATA_MISSING",
        "OPTIONS_MISSING",
        "ANSWER_MISSING",
    ]


def test_even_an_empty_draft_can_be_started(db: Database, team: dict[str, Principal]) -> None:
    view = create(db, team["author"], {})
    assert view.revision.content == {}
    assert view.findings  # it says what is wrong; it is still saved


def test_the_code_is_reserved_in_the_global_code_table(
    db: Database, owner_db: Database, team: dict[str, Principal]
) -> None:
    view = create(db, team["author"], copy.deepcopy(READY))
    with owner_db.transaction(team["author"].tenant_context) as session:
        row = session.execute(
            text("SELECT entity_type, organization_id FROM public_codes WHERE code = :c"),
            {"c": view.master.code},
        ).one()
    assert (row.entity_type, row.organization_id) == ("question", team["author"].organization_id)


def test_creating_is_audited_without_the_content(
    db: Database, owner_db: Database, team: dict[str, Principal]
) -> None:
    view = create(db, team["author"], copy.deepcopy(READY))
    with owner_db.transaction(team["author"].tenant_context) as session:
        events = list(
            session.scalars(select(AuditEvent).where(AuditEvent.entity_id == view.master.id))
        )
    assert [e.action for e in events] == ["QUESTION_CREATED"]
    assert events[0].actor_user_id == team["author"].user_id
    assert events[0].request_id == "req-1"
    assert events[0].after == {"code": view.master.code, "question_type": "SCQ"}


def test_content_over_the_size_limit_is_refused_not_saved(
    db: Database, team: dict[str, Principal]
) -> None:
    huge = {"stem": [{"kind": "paragraph", "text": "x" * (DEFAULT_RULES.revision_bytes + 1)}]}
    with pytest.raises(ValidationFailed) as raised:
        create(db, team["author"], huge)
    assert raised.value.code == "CONTENT_TOO_LARGE"


def test_content_that_is_not_plain_data_is_refused(
    db: Database, team: dict[str, Principal]
) -> None:
    with pytest.raises(ValidationFailed) as raised:
        create(db, team["author"], {"stem": float("nan")})
    assert raised.value.code == "CONTENT_NOT_JSON"


def test_a_retry_with_the_same_key_returns_the_same_question(
    db: Database, owner_db: Database, team: dict[str, Principal]
) -> None:
    first = create(db, team["author"], copy.deepcopy(READY), key="k-1")
    again = create(db, team["author"], copy.deepcopy(READY), key="k-1")
    assert again.master.id == first.master.id
    assert again.master.code == first.master.code
    with owner_db.transaction(team["author"].tenant_context) as session:
        count = session.scalar(
            select(func.count())
            .select_from(QuestionMaster)
            .where(QuestionMaster.created_by == team["author"].user_id)
        )
    assert count == 1


def test_the_same_key_with_other_content_is_refused(
    db: Database, team: dict[str, Principal]
) -> None:
    create(db, team["author"], copy.deepcopy(READY), key="k-2")
    with pytest.raises(Conflict) as raised:
        create(db, team["author"], copy.deepcopy(DRAFT), key="k-2")
    assert raised.value.code == "IDEMPOTENCY_KEY_REUSED"


def test_someone_without_a_coaching_role_cannot_create(
    db: Database, team: dict[str, Principal]
) -> None:
    outsider = Principal(
        user_id=new_id(),
        display_name="Nobody",
        is_platform_admin=False,
        organization_id=team["owner"].organization_id,
        role=None,
    )
    with pytest.raises(PermissionDenied):
        create(db, outsider, copy.deepcopy(READY))


# --- reading: drafts are private to their author -------------------------------------------------


@pytest.mark.parametrize("who", ["author", "admin", "owner", "editor"])
def test_who_may_open_someone_elses_draft(
    db: Database, team: dict[str, Principal], who: str
) -> None:
    view = create(db, team["author"], copy.deepcopy(READY))
    assert fetch(db, team[who], view.master.id).master.code == view.master.code


def test_another_faculty_member_gets_not_found_not_forbidden(
    db: Database, team: dict[str, Principal]
) -> None:
    view = create(db, team["author"], copy.deepcopy(READY))
    with pytest.raises(NotFound):
        fetch(db, team["other"], view.master.id)
    with pytest.raises(NotFound), db.transaction(team["other"].tenant_context) as session:
        service.get_question_by_code(session, team["other"], view.master.code)


def test_a_typed_code_is_forgiven_and_an_unknown_one_is_not_found(
    db: Database, team: dict[str, Principal]
) -> None:
    view = create(db, team["author"], copy.deepcopy(READY))
    typed = f" {view.master.code[:4].lower()}-{view.master.code[4:].lower()} "
    author = team["author"]
    with db.transaction(author.tenant_context) as session:
        found = service.get_question_by_code(session, author, typed)
        assert found.master.id == view.master.id
        with pytest.raises(NotFound):
            service.get_question_by_code(session, author, "00000000")
        with pytest.raises(ValidationFailed):
            service.get_question_by_code(session, author, "short")


def test_findings_are_computed_on_every_read_not_stored(
    db: Database, team: dict[str, Principal]
) -> None:
    view = create(db, team["author"], copy.deepcopy(DRAFT))
    assert fetch(db, team["author"], view.master.id).findings == view.findings


# --- the database itself -------------------------------------------------------------------------


def test_another_coaching_cannot_see_a_question(
    db: Database, owner_db: Database, team: dict[str, Principal]
) -> None:
    view = create(db, team["author"], copy.deepcopy(READY))
    stranger = principal_of(make_member(owner_db, "ADMIN", coaching_name="Other"), "ADMIN")
    with pytest.raises(NotFound):
        fetch(db, stranger, view.master.id)
    with db.transaction(stranger.tenant_context) as session:
        assert session.scalars(select(QuestionMaster)).all() == []
        assert session.scalars(select(QuestionRevision)).all() == []


def test_a_frozen_revision_can_never_change(
    db: Database, owner_db: Database, team: dict[str, Principal]
) -> None:
    view = create(db, team["author"], copy.deepcopy(READY))
    with owner_db.transaction(team["author"].tenant_context) as session:
        session.execute(
            text(
                "UPDATE question_revisions SET frozen_at = now(), content_hash = repeat('a', 64)"
                " WHERE id = :id"
            ),
            {"id": view.revision.id},
        )
    for sql in (
        "UPDATE question_revisions SET content = '{}'::jsonb WHERE id = :id",
        "UPDATE question_revisions SET frozen_at = NULL, content_hash = NULL WHERE id = :id",
    ):
        with pytest.raises(DBAPIError), db.transaction(team["author"].tenant_context) as session:
            session.execute(text(sql), {"id": view.revision.id})


def test_a_version_has_only_one_working_revision(db: Database, team: dict[str, Principal]) -> None:
    view = create(db, team["author"], copy.deepcopy(READY))
    with pytest.raises(DBAPIError), db.transaction(team["author"].tenant_context) as session:
        session.execute(
            text(
                "INSERT INTO question_revisions (id, organization_id, version_id, number,"
                " content, author_id) VALUES (:id, :org, :version, 2, '{}'::jsonb, :author)"
            ),
            {
                "id": new_id(),
                "org": team["author"].organization_id,
                "version": view.version.id,
                "author": team["author"].user_id,
            },
        )


@pytest.mark.parametrize("table", ["question_masters", "question_versions", "question_revisions"])
def test_nothing_is_ever_deleted(db: Database, team: dict[str, Principal], table: str) -> None:
    create(db, team["author"], copy.deepcopy(READY))
    with pytest.raises(DBAPIError), db.transaction(team["author"].tenant_context) as session:
        session.execute(
            text(f"DELETE FROM {table} WHERE organization_id = :org"),  # noqa: S608
            {"org": team["author"].organization_id},
        )


def test_creating_uses_the_same_rules_as_reading(
    db: Database, team: dict[str, Principal], catalogue: Catalogue
) -> None:
    content = ready_for(catalogue, "INTEGER")
    content["answer"] = {"value": 1000}
    wide = replace(DEFAULT_RULES, integer_max=2000)
    author = team["author"]
    for key in ("wide-1", "wide-1"):  # the second is a retry of the first
        with db.transaction(author.tenant_context) as session:
            view = service.create_question(
                session, author, content, idempotency_key=key, request_id=None, rules=wide
            )
            assert view.findings == []
    with db.transaction(author.tenant_context) as session:
        read = service.get_question(session, author, view.master.id, wide)
        assert read.findings == []
        default = service.get_question(session, author, view.master.id)
        assert [f.code for f in default.findings] == ["ANSWER_OUT_OF_RANGE"]
