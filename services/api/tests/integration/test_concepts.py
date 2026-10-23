"""M3 PR 2b: concepts with other-language names and aliases (C-02, C-03, C-04; T24, T26, T30)."""

import base64
import threading
from collections.abc import Iterator
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from qbank.core.auth import Principal
from qbank.core.config import AppEnv, Settings
from qbank.core.db import Database
from qbank.core.errors import PermissionDenied
from qbank.core.ids import new_id
from qbank.core.tenancy import TenantContext
from qbank.main import create_app
from qbank.modules.audit.models import AuditEvent
from qbank.modules.taxonomy import concepts as service
from qbank.modules.taxonomy.cursors import MAX_CURSOR_LENGTH
from qbank.modules.taxonomy.models import Concept, ConceptAlias, ConceptLabel, TaxonomyNode
from qbank.modules.taxonomy.schemas import CreateConcept, UpdateConcept
from tests.integration.conftest import (
    Member,
    MigratedDatabase,
    make_member,
    platform_admin,
    sign_in,
)

CONCEPTS = "/api/v1/taxonomy/concepts"
NODES = "/api/v1/taxonomy/nodes"
LAW = "Newton's second law"


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
    return {
        "owner": owner,
        "admin": make_member(owner_db, "ADMIN", org_id=owner.org_id),
        "faculty": make_member(owner_db, "FACULTY", org_id=owner.org_id, grants=["EDIT_OTHERS"]),
    }


@pytest.fixture
def admin_headers(client: TestClient, team: dict[str, Member]) -> dict[str, str]:
    return sign_in(client, team["admin"].email)


def add_node(
    client: TestClient, headers: dict[str, str], kind: str, name: str, parent: str | None = None
) -> dict[str, Any]:
    response = client.post(
        NODES, json={"kind": kind, "parent_id": parent, "name": name}, headers=headers
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
def physics(client: TestClient, admin_headers: dict[str, str]) -> dict[str, Any]:
    """Class 11 > Physics (the subject concepts go under) > Kinematics (a chapter)."""
    cls = add_node(client, admin_headers, "CLASS", "Class 11")
    subject = add_node(client, admin_headers, "SUBJECT", "Physics", cls["id"])
    chapter = add_node(client, admin_headers, "CHAPTER", "Kinematics", subject["id"])
    return {"subject": subject, "chapter": chapter, "class": cls}


def add(
    client: TestClient,
    headers: dict[str, str],
    subject: dict[str, Any],
    name: str,
    **extra: Any,
) -> dict[str, Any]:
    body = {"subject_id": subject["id"], "name": name, **extra}
    response = client.post(CONCEPTS, json=body, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def if_match(item: dict[str, Any]) -> dict[str, str]:
    return {"If-Match": f'"rev-{item["revision"]}"'}


def audit(owner_db: Database, org_id: UUID, action: str) -> list[AuditEvent]:
    """The coaching's events of one kind (filtered by hand: the table owner bypasses RLS)."""
    with owner_db.transaction(TenantContext(organization_id=org_id)) as session:
        return list(
            session.scalars(
                select(AuditEvent)
                .where(AuditEvent.organization_id == org_id, AuditEvent.action == action)
                .order_by(AuditEvent.created_at)
            )
        )


# --- The database keeps concepts valid ----------------------------------------------------------


def insert_concept(
    owner_db: Database,
    org_id: UUID,
    subject_id: UUID,
    name: str,
    subject_kind: str = "SUBJECT",
) -> UUID:
    concept_id = new_id()
    with owner_db.transaction(TenantContext(organization_id=org_id)) as session:
        session.execute(
            text(
                "INSERT INTO concepts (id, organization_id, subject_id, subject_kind, name,"
                " name_key) VALUES (:id, :org, :subject, :kind, :name, :key)"
            ),
            {
                "id": concept_id,
                "org": org_id,
                "subject": subject_id,
                "kind": subject_kind,
                "name": name,
                "key": name.casefold(),
            },
        )
    return concept_id


def test_database_refuses_a_concept_under_a_chapter(
    client: TestClient,
    owner_db: Database,
    team: dict[str, Member],
    admin_headers: dict[str, str],
    physics: dict[str, Any],
) -> None:
    org, chapter = team["owner"].org_id, UUID(physics["chapter"]["id"])

    with pytest.raises(IntegrityError):  # says "SUBJECT" about a chapter: no such node
        insert_concept(owner_db, org, chapter, LAW)
    with pytest.raises(IntegrityError):  # says what it really is, which is not a subject
        insert_concept(owner_db, org, chapter, LAW, subject_kind="CHAPTER")


def test_database_refuses_a_subject_of_another_coaching_or_none_at_all(
    client: TestClient,
    owner_db: Database,
    team: dict[str, Member],
    physics: dict[str, Any],
) -> None:
    org = team["owner"].org_id

    with pytest.raises(IntegrityError):
        insert_concept(owner_db, org, new_id(), LAW)
    other = make_member(owner_db, "ADMIN")
    other_client = TestClient(client.app)
    other_headers = sign_in(other_client, other.email)
    foreign_class = add_node(other_client, other_headers, "CLASS", "Class 11")
    foreign_subject = add_node(
        other_client, other_headers, "SUBJECT", "Physics", foreign_class["id"]
    )
    with pytest.raises(IntegrityError):
        insert_concept(owner_db, org, UUID(foreign_subject["id"]), LAW)


def test_database_refuses_an_alias_that_names_a_different_subject_than_its_concept(
    client: TestClient,
    owner_db: Database,
    team: dict[str, Member],
    admin_headers: dict[str, str],
    physics: dict[str, Any],
) -> None:
    org = team["owner"].org_id
    chemistry = add_node(client, admin_headers, "SUBJECT", "Chemistry", physics["class"]["id"])
    concept = insert_concept(owner_db, org, UUID(physics["subject"]["id"]), LAW)

    with (
        pytest.raises(IntegrityError),
        owner_db.transaction(TenantContext(organization_id=org)) as session,
    ):
        session.execute(
            text(
                "INSERT INTO concept_aliases (organization_id, concept_id, subject_id, alias,"
                " alias_key) VALUES (:org, :concept, :subject, 'x', 'x')"
            ),
            {"org": org, "concept": concept, "subject": UUID(chemistry["id"])},
        )


def test_the_runtime_role_can_retire_but_not_delete_a_concept(
    db: Database,
    owner_db: Database,
    team: dict[str, Member],
    physics: dict[str, Any],
) -> None:
    org = team["owner"].org_id
    insert_concept(owner_db, org, UUID(physics["subject"]["id"]), LAW)

    with (
        pytest.raises(DBAPIError, match="permission denied"),
        db.transaction(TenantContext(organization_id=org)) as session,
    ):
        session.execute(text("DELETE FROM concepts"))


def test_a_coaching_sees_and_writes_only_its_own_concepts(
    db: Database,
    owner_db: Database,
    client: TestClient,
    team: dict[str, Member],
    physics: dict[str, Any],
) -> None:
    mine = insert_concept(owner_db, team["owner"].org_id, UUID(physics["subject"]["id"]), LAW)
    other = make_member(owner_db, "ADMIN")
    other_client = TestClient(client.app)
    other_headers = sign_in(other_client, other.email)
    other_class = add_node(other_client, other_headers, "CLASS", "Class 11")
    other_subject = add_node(other_client, other_headers, "SUBJECT", "Physics", other_class["id"])
    theirs = add(other_client, other_headers, other_subject, LAW, aliases=["2nd law"])
    context = TenantContext(organization_id=team["owner"].org_id)

    with db.transaction(context) as session:
        ids = set(session.scalars(select(Concept.id)))
        alias_count = len(list(session.scalars(select(ConceptAlias))))
        label_count = len(list(session.scalars(select(ConceptLabel))))
    sneaky = Concept(
        organization_id=other.org_id,
        subject_id=UUID(other_subject["id"]),
        name="Sneaky",
        name_key="sneaky",
    )

    assert (ids, alias_count, label_count) == ({mine}, 0, 0)
    assert UUID(theirs["id"]) not in ids
    with pytest.raises(DBAPIError, match="row-level security"), db.transaction(context) as session:
        session.add(sneaky)


# --- Adding and reading -------------------------------------------------------------------------


def test_an_admin_adds_a_concept_with_names_and_aliases_and_everyone_reads_it(
    client: TestClient,
    team: dict[str, Member],
    admin_headers: dict[str, str],
    physics: dict[str, Any],
) -> None:
    concept = add(
        client,
        admin_headers,
        physics["subject"],
        LAW,
        labels={"hi": "न्यूटन का दूसरा नियम"},
        aliases=["Newton's 2nd law", "F = ma law"],
    )
    faculty = TestClient(client.app)
    sign_in(faculty, team["faculty"].email)

    one = faculty.get(f"{CONCEPTS}/{concept['id']}")

    assert one.json() == concept
    assert one.headers["ETag"] == '"rev-1"'
    assert concept["subject_id"] == physics["subject"]["id"]
    assert concept["labels"] == {"hi": "न्यूटन का दूसरा नियम"}
    assert concept["aliases"] == ["F = ma law", "Newton's 2nd law"]  # alphabetical
    assert (concept["state"], concept["revision"]) == ("ACTIVE", 1)


def test_aliases_that_are_the_same_name_written_twice_are_one_alias(
    client: TestClient, admin_headers: dict[str, str], physics: dict[str, Any]
) -> None:
    concept = add(
        client,
        admin_headers,
        physics["subject"],
        LAW,
        aliases=["Newton 2", "newton   2", "NEWTON 2"],
    )

    assert concept["aliases"] == ["Newton 2"]  # the first spelling is kept


def test_a_concept_must_go_under_an_active_subject_of_this_coaching(
    client: TestClient, admin_headers: dict[str, str], physics: dict[str, Any]
) -> None:
    under_chapter = client.post(
        CONCEPTS, json={"subject_id": physics["chapter"]["id"], "name": LAW}, headers=admin_headers
    )
    unknown = client.post(
        CONCEPTS, json={"subject_id": str(new_id()), "name": LAW}, headers=admin_headers
    )
    subject = physics["subject"]
    client.post(
        f"{NODES}/{subject['id']}/deprecate", headers={**admin_headers, **if_match(subject)}
    )
    under_retired = client.post(
        CONCEPTS, json={"subject_id": subject["id"], "name": LAW}, headers=admin_headers
    )

    assert (under_chapter.status_code, under_chapter.json()["error"]["code"]) == (
        422,
        "HIERARCHY_INVALID",
    )
    assert unknown.status_code == 404
    assert (under_retired.status_code, under_retired.json()["error"]["code"]) == (
        409,
        "PARENT_DEPRECATED",
    )


@pytest.mark.parametrize("aliases", [["x"] * 1 + [f"alias {n}" for n in range(10)], [" "]])
def test_aliases_are_limited_and_must_have_text(
    client: TestClient,
    admin_headers: dict[str, str],
    physics: dict[str, Any],
    aliases: list[str],
) -> None:
    response = client.post(
        CONCEPTS,
        json={"subject_id": physics["subject"]["id"], "name": LAW, "aliases": aliases},
        headers=admin_headers,
    )

    assert (response.status_code, response.json()["error"]["code"]) == (400, "MALFORMED_REQUEST")


def test_a_name_or_alias_that_grows_too_long_once_normalised_is_a_422_not_a_500(
    client: TestClient, admin_headers: dict[str, str], physics: dict[str, Any]
) -> None:
    ligatures = "ﬃ" * 200  # 200 characters, 600 once expanded to letters
    body = {"subject_id": physics["subject"]["id"]}

    long_name = client.post(CONCEPTS, json={**body, "name": ligatures}, headers=admin_headers)
    long_alias = client.post(
        CONCEPTS, json={**body, "name": LAW, "aliases": [ligatures]}, headers=admin_headers
    )
    long_search = client.get(CONCEPTS, params={"q": ligatures})

    assert [r.status_code for r in (long_name, long_alias)] == [422, 422]
    assert long_name.json()["error"]["code"] == "NAME_TOO_LONG"
    assert long_search.status_code == 422


# --- Names and aliases never collide within a subject --------------------------------------------


def test_two_concepts_of_a_subject_cannot_share_a_name_but_two_subjects_can(
    client: TestClient, admin_headers: dict[str, str], physics: dict[str, Any]
) -> None:
    chemistry = add_node(client, admin_headers, "SUBJECT", "Chemistry", physics["class"]["id"])
    add(client, admin_headers, physics["subject"], "Work")

    clash = client.post(
        CONCEPTS,
        json={"subject_id": physics["subject"]["id"], "name": "  WORK "},
        headers=admin_headers,
    )
    elsewhere = client.post(
        CONCEPTS, json={"subject_id": chemistry["id"], "name": "Work"}, headers=admin_headers
    )

    assert (clash.status_code, clash.json()["error"]["code"]) == (409, "DUPLICATE_NAME")
    assert elsewhere.status_code == 201


def test_an_alias_cannot_be_another_concepts_alias_or_name_or_its_own_name(
    client: TestClient, admin_headers: dict[str, str], physics: dict[str, Any]
) -> None:
    subject = physics["subject"]
    add(client, admin_headers, subject, "Work", aliases=["W"])
    body = {"subject_id": subject["id"]}

    same_alias = client.post(
        CONCEPTS, json={**body, "name": "Energy", "aliases": ["w"]}, headers=admin_headers
    )
    alias_is_a_name = client.post(
        CONCEPTS, json={**body, "name": "Energy", "aliases": ["WORK"]}, headers=admin_headers
    )
    name_is_an_alias = client.post(CONCEPTS, json={**body, "name": "w"}, headers=admin_headers)
    own_name = client.post(
        CONCEPTS, json={**body, "name": "Energy", "aliases": ["energy"]}, headers=admin_headers
    )

    for response in (same_alias, alias_is_a_name, name_is_an_alias, own_name):
        assert (response.status_code, response.json()["error"]["code"]) == (409, "DUPLICATE_NAME")
    assert len(client.get(CONCEPTS).json()["data"]) == 1  # the refused attempts left nothing


def test_the_same_alias_may_be_used_in_different_subjects(
    client: TestClient, admin_headers: dict[str, str], physics: dict[str, Any]
) -> None:
    chemistry = add_node(client, admin_headers, "SUBJECT", "Chemistry", physics["class"]["id"])
    add(client, admin_headers, physics["subject"], "Work", aliases=["W"])

    other = client.post(
        CONCEPTS,
        json={"subject_id": chemistry["id"], "name": "Tungsten", "aliases": ["W"]},
        headers=admin_headers,
    )

    assert other.status_code == 201


def test_two_admins_adding_the_same_name_at_once_leave_exactly_one(
    client: TestClient,
    team: dict[str, Member],
    admin_headers: dict[str, str],
    physics: dict[str, Any],
) -> None:
    owner = TestClient(client.app)
    owner_headers = sign_in(owner, team["owner"].email)
    results: list[int] = []

    def create(browser: TestClient, headers: dict[str, str], name: str, alias: str) -> None:
        response = browser.post(
            CONCEPTS,
            json={"subject_id": physics["subject"]["id"], "name": name, "aliases": [alias]},
            headers=headers,
        )
        results.append(response.status_code)

    # One names a concept "Work" while the other gives a different concept the alias "Work".
    threads = [
        threading.Thread(target=create, args=(client, admin_headers, "Work", "W1")),
        threading.Thread(target=create, args=(owner, owner_headers, "Energy", "work")),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(results) == [201, 409]


def test_concept_writes_wait_for_whoever_holds_the_subject(
    client: TestClient,
    owner_db: Database,
    team: dict[str, Member],
    admin_headers: dict[str, str],
    physics: dict[str, Any],
) -> None:
    """Every write to a subject's concepts starts by locking the subject, so their checks for a
    clashing name or alias cannot interleave. Here the subject is held while writes are sent."""
    subject = UUID(physics["subject"]["id"])
    concept = add(client, admin_headers, physics["subject"], LAW)
    results: dict[str, int] = {}

    def create() -> None:
        body = {"subject_id": str(subject), "name": "Work"}
        results["create"] = client.post(CONCEPTS, json=body, headers=admin_headers).status_code

    def rename() -> None:
        results["rename"] = client.patch(
            f"{CONCEPTS}/{concept['id']}",
            json={"name": "Second law"},
            headers={**admin_headers, **if_match(concept)},
        ).status_code

    workers = [threading.Thread(target=create), threading.Thread(target=rename)]
    with owner_db.transaction(TenantContext(organization_id=team["owner"].org_id)) as session:
        # A shared hold: it blocks the writers' exclusive lock on the subject, but not the weaker
        # lock the database takes on the subject for the foreign key of a new concept.
        held = select(TaxonomyNode.id).where(TaxonomyNode.id == subject).with_for_update(read=True)
        session.execute(held)
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join(timeout=1.0)
        assert results == {}  # both are waiting for the subject
    for worker in workers:
        worker.join(timeout=10.0)

    assert results == {"create": 201, "rename": 200}


# --- Retrying a create ---------------------------------------------------------------------------


def test_retrying_a_create_with_the_same_key_returns_the_same_concept(
    client: TestClient,
    owner_db: Database,
    team: dict[str, Member],
    admin_headers: dict[str, str],
    physics: dict[str, Any],
) -> None:
    headers = {**admin_headers, "Idempotency-Key": "retry-1"}
    body = {"subject_id": physics["subject"]["id"], "name": LAW, "aliases": ["2nd law"]}

    first = client.post(CONCEPTS, json=body, headers=headers)
    retry = client.post(CONCEPTS, json=body, headers=headers)
    other = client.post(CONCEPTS, json={**body, "name": "Other"}, headers=headers)

    assert (first.status_code, retry.status_code) == (201, 201)
    assert retry.json() == first.json()
    assert (other.status_code, other.json()["error"]["code"]) == (409, "IDEMPOTENCY_KEY_REUSED")
    assert len(client.get(CONCEPTS).json()["data"]) == 1
    assert len(audit(owner_db, team["owner"].org_id, "CONCEPT_CREATED")) == 1


# --- Searching and paging ------------------------------------------------------------------------


def test_the_list_filters_by_subject_state_and_text_in_any_case_or_spacing(
    client: TestClient, admin_headers: dict[str, str], physics: dict[str, Any]
) -> None:
    chemistry = add_node(client, admin_headers, "SUBJECT", "Chemistry", physics["class"]["id"])
    law = add(client, admin_headers, physics["subject"], LAW, aliases=["F = ma law"])
    add(client, admin_headers, physics["subject"], "Work and energy", aliases=["W 100%"])
    add(client, admin_headers, chemistry, "Mole concept")
    client.post(f"{CONCEPTS}/{law['id']}/deprecate", headers={**admin_headers, **if_match(law)})

    def names(**params: str) -> list[str]:
        return [c["name"] for c in client.get(CONCEPTS, params=params).json()["data"]]

    assert names(subject_id=physics["subject"]["id"]) == [LAW, "Work and energy"]
    assert names(subject_id=physics["subject"]["id"], state="ACTIVE") == ["Work and energy"]
    assert names(q="NEWTON'S   second") == [LAW]  # by name, any case and spacing
    assert names(q="f = MA") == [LAW]  # by alias
    assert names(q="100%") == ["Work and energy"]  # a % in the text means itself
    assert names(q="%") == ["Work and energy"]  # ...and does not match everything
    assert names(q="_") == []  # ...nor does an underscore
    assert names(q="mole") == ["Mole concept"]
    assert names(q="nothing like this") == []


def test_pages_are_in_name_order_and_survive_a_rename_of_the_last_item(
    client: TestClient, admin_headers: dict[str, str], physics: dict[str, Any]
) -> None:
    items = {
        name: add(client, admin_headers, physics["subject"], name)
        for name in ("Alpha", "Bravo", "Charlie", "Delta", "Echo")
    }
    first = client.get(CONCEPTS, params={"limit": 3}).json()
    charlie = items["Charlie"]

    client.patch(
        f"{CONCEPTS}/{charlie['id']}",
        json={"name": "Zulu"},
        headers={**admin_headers, **if_match(charlie)},
    )
    second = client.get(CONCEPTS, params={"cursor": first["page"]["next_cursor"]}).json()

    assert [c["name"] for c in first["data"]] == ["Alpha", "Bravo", "Charlie"]
    assert first["page"]["has_more"] is True
    assert [c["name"] for c in second["data"]] == ["Delta", "Echo", "Zulu"]
    assert client.get(CONCEPTS, params={"cursor": "not-a-cursor"}).status_code == 400


def test_every_cursor_is_accepted_after_long_non_latin_names(
    client: TestClient, admin_headers: dict[str, str], physics: dict[str, Any]
) -> None:
    names = [letter * 200 for letter in ("क", "ख", "ग")]
    for name in names:
        add(client, admin_headers, physics["subject"], name)

    seen: list[str] = []
    cursor: str | None = None
    while True:
        params: dict[str, Any] = {"limit": 1, **({"cursor": cursor} if cursor else {})}
        page = client.get(CONCEPTS, params=params)
        assert page.status_code == 200, page.text
        seen += [c["name"] for c in page.json()["data"]]
        cursor = page.json()["page"]["next_cursor"]
        if cursor is None:
            break
        assert len(cursor) <= MAX_CURSOR_LENGTH

    assert seen == names
    too_short = base64.urlsafe_b64encode(b"short").decode().rstrip("=")
    assert client.get(CONCEPTS, params={"cursor": too_short}).status_code == 400


# --- Changing ------------------------------------------------------------------------------------


def test_renaming_retranslating_and_changing_aliases_replaces_what_was_sent(
    client: TestClient, admin_headers: dict[str, str], physics: dict[str, Any]
) -> None:
    concept = add(
        client,
        admin_headers,
        physics["subject"],
        LAW,
        labels={"hi": "दूसरा नियम"},
        aliases=["2nd law", "F=ma"],
    )

    renamed = client.patch(
        f"{CONCEPTS}/{concept['id']}",
        json={"name": "Second law of motion", "labels": {"gu": "બીજો નિયમ"}, "aliases": ["F=ma"]},
        headers={**admin_headers, **if_match(concept)},
    ).json()
    only_name = client.patch(
        f"{CONCEPTS}/{concept['id']}",
        json={"name": "Newton II"},
        headers={**admin_headers, **if_match(renamed)},
    ).json()

    assert (renamed["name"], renamed["revision"]) == ("Second law of motion", 2)
    assert renamed["labels"] == {"gu": "બીજો નિયમ"}  # replaced, not merged
    assert renamed["aliases"] == ["F=ma"]
    assert (only_name["labels"], only_name["aliases"]) == (renamed["labels"], renamed["aliases"])


def test_an_alias_and_the_name_can_swap_in_one_change(
    client: TestClient, admin_headers: dict[str, str], physics: dict[str, Any]
) -> None:
    concept = add(client, admin_headers, physics["subject"], "Newton II", aliases=["Second law"])

    swapped = client.patch(
        f"{CONCEPTS}/{concept['id']}",
        json={"name": "Second law", "aliases": ["Newton II"]},
        headers={**admin_headers, **if_match(concept)},
    )

    assert swapped.status_code == 200
    assert (swapped.json()["name"], swapped.json()["aliases"]) == ("Second law", ["Newton II"])


def test_a_rename_or_alias_change_that_clashes_is_refused_and_changes_nothing(
    client: TestClient, admin_headers: dict[str, str], physics: dict[str, Any]
) -> None:
    add(client, admin_headers, physics["subject"], "Work", aliases=["W"])
    other = add(client, admin_headers, physics["subject"], "Energy")

    clashes = [
        {"name": "work"},  # another concept's name
        {"name": "w"},  # another concept's alias
        {"aliases": ["WORK"]},  # an alias that is another concept's name
        {"aliases": ["w"]},  # an alias that is another concept's alias
        {"aliases": ["energy"]},  # an alias that is its own name
    ]

    for change in clashes:
        response = client.patch(
            f"{CONCEPTS}/{other['id']}", json=change, headers={**admin_headers, **if_match(other)}
        )
        assert (response.status_code, response.json()["error"]["code"]) == (409, "DUPLICATE_NAME")
    again = client.get(f"{CONCEPTS}/{other['id']}").json()
    assert (again["name"], again["aliases"], again["revision"]) == ("Energy", [], 1)


def test_a_change_needs_if_match_and_a_stale_one_is_refused(
    client: TestClient, admin_headers: dict[str, str], physics: dict[str, Any]
) -> None:
    concept = add(client, admin_headers, physics["subject"], LAW)
    first = client.patch(
        f"{CONCEPTS}/{concept['id']}",
        json={"name": "Second law"},
        headers={**admin_headers, **if_match(concept)},
    )

    missing = client.patch(f"{CONCEPTS}/{concept['id']}", json={"name": "A"}, headers=admin_headers)
    stale = client.patch(
        f"{CONCEPTS}/{concept['id']}",
        json={"name": "B"},
        headers={**admin_headers, **if_match(concept)},
    )

    assert first.status_code == 200
    assert (missing.status_code, missing.json()["error"]["code"]) == (428, "IF_MATCH_REQUIRED")
    assert (stale.status_code, stale.json()["error"]["code"]) == (412, "REVISION_STALE")
    assert stale.json()["error"]["details"]["current_etag"] == '"rev-2"'


def test_a_change_that_changes_nothing_keeps_the_revision_and_writes_no_audit_event(
    client: TestClient,
    owner_db: Database,
    team: dict[str, Member],
    admin_headers: dict[str, str],
    physics: dict[str, Any],
) -> None:
    concept = add(
        client, admin_headers, physics["subject"], LAW, labels={"hi": "x"}, aliases=["2nd law"]
    )

    response = client.patch(
        f"{CONCEPTS}/{concept['id']}",
        json={
            "name": LAW,
            "labels": {"hi": "x"},
            "aliases": ["2nd law"],
        },
        headers={**admin_headers, **if_match(concept)},
    )

    assert response.json()["revision"] == 1
    assert audit(owner_db, team["owner"].org_id, "CONCEPT_UPDATED") == []


def test_respelling_an_alias_is_a_real_change(
    client: TestClient, admin_headers: dict[str, str], physics: dict[str, Any]
) -> None:
    concept = add(client, admin_headers, physics["subject"], LAW, aliases=["2nd law"])

    response = client.patch(
        f"{CONCEPTS}/{concept['id']}",
        json={"aliases": ["2nd Law"]},  # the same alias for matching, but people see the spelling
        headers={**admin_headers, **if_match(concept)},
    )

    assert (response.json()["aliases"], response.json()["revision"]) == (["2nd Law"], 2)


def test_a_null_name_means_keep_the_name(
    client: TestClient, admin_headers: dict[str, str], physics: dict[str, Any]
) -> None:
    concept = add(client, admin_headers, physics["subject"], LAW)

    response = client.patch(
        f"{CONCEPTS}/{concept['id']}",
        json={"name": None},
        headers={**admin_headers, **if_match(concept)},
    )

    assert (response.status_code, response.json()["name"], response.json()["revision"]) == (
        200,
        LAW,
        1,
    )


# --- Retiring and restoring (C-04) ----------------------------------------------------------------


def test_retiring_hides_a_concept_from_pickers_and_restoring_brings_it_back(
    client: TestClient, admin_headers: dict[str, str], physics: dict[str, Any]
) -> None:
    concept = add(client, admin_headers, physics["subject"], LAW)

    retired = client.post(
        f"{CONCEPTS}/{concept['id']}/deprecate", headers={**admin_headers, **if_match(concept)}
    ).json()
    in_picker = client.get(CONCEPTS, params={"state": "ACTIVE"}).json()["data"]
    in_full_list = client.get(CONCEPTS).json()["data"]
    twice = client.post(
        f"{CONCEPTS}/{concept['id']}/deprecate", headers={**admin_headers, **if_match(retired)}
    ).json()
    restored = client.post(
        f"{CONCEPTS}/{concept['id']}/restore", headers={**admin_headers, **if_match(twice)}
    ).json()

    assert retired["state"] == "DEPRECATED"
    assert in_picker == []
    assert [c["name"] for c in in_full_list] == [LAW]
    assert twice["revision"] == retired["revision"]  # retiring twice changes nothing
    assert (restored["state"], restored["revision"]) == ("ACTIVE", 3)


def test_retiring_and_restoring_need_the_current_revision(
    client: TestClient, admin_headers: dict[str, str], physics: dict[str, Any]
) -> None:
    concept = add(client, admin_headers, physics["subject"], LAW)
    client.patch(
        f"{CONCEPTS}/{concept['id']}",
        json={"name": "Renamed"},
        headers={**admin_headers, **if_match(concept)},
    )  # now at revision 2

    for action in ("deprecate", "restore"):
        url = f"{CONCEPTS}/{concept['id']}/{action}"
        missing = client.post(url, headers=admin_headers)
        stale = client.post(url, headers={**admin_headers, **if_match(concept)})
        assert (missing.status_code, missing.json()["error"]["code"]) == (428, "IF_MATCH_REQUIRED")
        assert (stale.status_code, stale.json()["error"]["code"]) == (412, "REVISION_STALE")
    assert client.get(f"{CONCEPTS}/{concept['id']}").json()["state"] == "ACTIVE"


def test_a_concept_cannot_be_restored_while_its_subject_is_retired(
    client: TestClient, admin_headers: dict[str, str], physics: dict[str, Any]
) -> None:
    concept = add(client, admin_headers, physics["subject"], LAW)
    retired = client.post(
        f"{CONCEPTS}/{concept['id']}/deprecate", headers={**admin_headers, **if_match(concept)}
    ).json()
    subject = physics["subject"]
    client.post(
        f"{NODES}/{subject['id']}/deprecate", headers={**admin_headers, **if_match(subject)}
    )

    blocked = client.post(
        f"{CONCEPTS}/{concept['id']}/restore", headers={**admin_headers, **if_match(retired)}
    )

    assert (blocked.status_code, blocked.json()["error"]["code"]) == (409, "PARENT_DEPRECATED")
    assert client.get(f"{CONCEPTS}/{concept['id']}").json()["state"] == "DEPRECATED"


def test_every_change_is_in_the_audit_log_with_before_and_after(
    client: TestClient,
    owner_db: Database,
    team: dict[str, Member],
    admin_headers: dict[str, str],
    physics: dict[str, Any],
) -> None:
    concept = add(client, admin_headers, physics["subject"], LAW, aliases=["2nd law"])
    renamed = client.patch(
        f"{CONCEPTS}/{concept['id']}",
        json={"name": "Second law", "aliases": ["F=ma"]},
        headers={**admin_headers, **if_match(concept)},
    ).json()
    retired = client.post(
        f"{CONCEPTS}/{concept['id']}/deprecate", headers={**admin_headers, **if_match(renamed)}
    ).json()
    client.post(
        f"{CONCEPTS}/{concept['id']}/restore", headers={**admin_headers, **if_match(retired)}
    )

    org = team["owner"].org_id
    (created,) = audit(owner_db, org, "CONCEPT_CREATED")
    (updated,) = audit(owner_db, org, "CONCEPT_UPDATED")
    (deprecated,) = audit(owner_db, org, "CONCEPT_DEPRECATED")
    (restored,) = audit(owner_db, org, "CONCEPT_RESTORED")

    assert created.before is None and created.after["aliases"] == ["2nd law"]  # type: ignore[index]
    assert (updated.before["name"], updated.after["name"]) == (LAW, "Second law")  # type: ignore[index]
    assert (updated.before["aliases"], updated.after["aliases"]) == (["2nd law"], ["F=ma"])  # type: ignore[index]
    assert (deprecated.before["state"], deprecated.after["state"]) == ("ACTIVE", "DEPRECATED")  # type: ignore[index]
    assert (restored.before["state"], restored.after["state"]) == ("DEPRECATED", "ACTIVE")  # type: ignore[index]
    events = (created, updated, deprecated, restored)
    assert {event.entity_id for event in events} == {UUID(concept["id"])}
    assert {event.entity_type for event in events} == {"concept"}
    assert {event.actor_user_id for event in events} == {team["admin"].user_id}


# --- Who may do what (T26) ------------------------------------------------------------------------


def test_faculty_read_but_cannot_change_concepts(
    client: TestClient,
    team: dict[str, Member],
    admin_headers: dict[str, str],
    physics: dict[str, Any],
) -> None:
    concept = add(client, admin_headers, physics["subject"], LAW)
    faculty = TestClient(client.app)
    headers = sign_in(faculty, team["faculty"].email)  # even with EDIT_OTHERS
    stale = {**headers, **if_match(concept)}

    responses = [
        faculty.post(
            CONCEPTS, json={"subject_id": physics["subject"]["id"], "name": "New"}, headers=headers
        ),
        faculty.patch(f"{CONCEPTS}/{concept['id']}", json={"name": "X"}, headers=stale),
        faculty.post(f"{CONCEPTS}/{concept['id']}/deprecate", headers=stale),
        faculty.post(f"{CONCEPTS}/{concept['id']}/restore", headers=stale),
    ]

    assert [response.status_code for response in responses] == [403, 403, 403, 403]
    assert faculty.get(CONCEPTS).status_code == 200
    assert faculty.get(f"{CONCEPTS}/{concept['id']}").status_code == 200


def test_the_service_functions_refuse_a_principal_who_may_not_change_concepts(
    db: Database, team: dict[str, Member], physics: dict[str, Any]
) -> None:
    """Other code (the import, jobs) calls the service directly, so it must check for itself."""
    faculty = Principal(
        user_id=team["faculty"].user_id,
        display_name="Faculty",
        is_platform_admin=False,
        organization_id=team["owner"].org_id,
        role="FACULTY",
    )
    with db.transaction(faculty.tenant_context) as session:
        with pytest.raises(PermissionDenied):
            service.create_concept(
                session,
                faculty,
                CreateConcept(subject_id=UUID(physics["subject"]["id"]), name=LAW),
                idempotency_key=None,
                request_id=None,
            )
        with pytest.raises(PermissionDenied):
            service.update_concept(
                session,
                faculty,
                UUID(int=1),
                UpdateConcept(name="X"),
                if_match='"rev-1"',
                request_id=None,
            )
        with pytest.raises(PermissionDenied):
            service.set_state(
                session, faculty, UUID(int=1), "DEPRECATED", if_match='"rev-1"', request_id=None
            )


def test_another_coachings_admin_cannot_see_or_change_a_concept(
    client: TestClient,
    owner_db: Database,
    admin_headers: dict[str, str],
    physics: dict[str, Any],
) -> None:
    concept = add(client, admin_headers, physics["subject"], LAW)
    stranger = TestClient(client.app)
    headers = sign_in(stranger, make_member(owner_db, "ADMIN").email)
    stale = {**headers, **if_match(concept)}

    assert stranger.get(f"{CONCEPTS}/{concept['id']}").status_code == 404
    patch = stranger.patch(f"{CONCEPTS}/{concept['id']}", json={"name": "X"}, headers=stale)
    assert patch.status_code == 404
    retire = stranger.post(f"{CONCEPTS}/{concept['id']}/deprecate", headers=stale)
    assert retire.status_code == 404
    assert stranger.get(CONCEPTS).json()["data"] == []
    other_subject = stranger.post(
        CONCEPTS, json={"subject_id": physics["subject"]["id"], "name": "X"}, headers=headers
    )
    assert other_subject.status_code == 404  # another coaching's subject does not exist for them


def test_a_platform_admin_needs_to_act_in_a_coaching_first(
    client: TestClient,
    owner_db: Database,
    team: dict[str, Member],
    admin_headers: dict[str, str],
    physics: dict[str, Any],
) -> None:
    add(client, admin_headers, physics["subject"], LAW)
    staff = TestClient(client.app)
    headers = sign_in(staff, platform_admin(owner_db))
    body = {"subject_id": physics["subject"]["id"], "name": "Energy"}

    before = staff.get(CONCEPTS)
    refused = staff.post(CONCEPTS, json=body, headers=headers)
    staff.post(
        "/api/v1/platform/acting-organization",
        json={"organization_id": str(team["owner"].org_id)},
        headers=headers,
    )
    after = staff.get(CONCEPTS)
    created = staff.post(CONCEPTS, json=body, headers=headers)

    assert (before.status_code, refused.status_code) == (403, 403)
    assert [c["name"] for c in after.json()["data"]] == [LAW]
    assert created.status_code == 201
    event = audit(owner_db, team["owner"].org_id, "CONCEPT_CREATED")[-1]
    assert event.actor_is_platform is True
