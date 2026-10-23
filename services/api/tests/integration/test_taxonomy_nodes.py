"""M3 PR 2a: the syllabus tree (C-01, C-04, C-10; tests T24, T26 and T30 for syllabus items)."""

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
from qbank.modules.taxonomy import service
from qbank.modules.taxonomy.models import TaxonomyLabel, TaxonomyNode
from qbank.modules.taxonomy.schemas import CreateNode, UpdateNode
from tests.integration.conftest import (
    PLATFORM,
    Member,
    MigratedDatabase,
    make_member,
    platform_admin,
    sign_in,
)

NODES = "/api/v1/taxonomy/nodes"


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


def add(
    client: TestClient,
    headers: dict[str, str],
    kind: str,
    name: str,
    parent: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    response = client.post(
        NODES, json={"kind": kind, "parent_id": parent, "name": name, **extra}, headers=headers
    )
    assert response.status_code == 201, response.text
    return response.json()


def tree(client: TestClient, headers: dict[str, str]) -> dict[str, dict[str, Any]]:
    """Class 11 > Physics > Kinematics > Motion in a line > Velocity."""
    cls = add(client, headers, "CLASS", "Class 11")
    subject = add(client, headers, "SUBJECT", "Physics", cls["id"])
    chapter = add(client, headers, "CHAPTER", "Kinematics", subject["id"])
    topic = add(client, headers, "TOPIC", "Motion in a line", chapter["id"])
    subtopic = add(client, headers, "SUBTOPIC", "Velocity", topic["id"])
    return {
        "class": cls,
        "subject": subject,
        "chapter": chapter,
        "topic": topic,
        "subtopic": subtopic,
    }


def if_match(node: dict[str, Any]) -> dict[str, str]:
    return {"If-Match": f'"rev-{node["revision"]}"'}


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


# --- The database itself keeps the tree valid (T24) -------------------------------------------


def insert_node(
    owner_db: Database,
    org_id: UUID,
    kind: str,
    name: str,
    parent: tuple[UUID, str | None] | None = None,
) -> UUID:
    node_id = new_id()
    with owner_db.transaction(TenantContext(organization_id=org_id)) as session:
        session.execute(
            text(
                "INSERT INTO taxonomy_nodes (id, organization_id, kind, parent_id, parent_kind,"
                " name, name_key) VALUES (:id, :org, :kind, :parent, :parent_kind, :name, :key)"
            ),
            {
                "id": node_id,
                "org": org_id,
                "kind": kind,
                "parent": parent[0] if parent else None,
                "parent_kind": parent[1] if parent else None,
                "name": name,
                "key": name.casefold(),
            },
        )
    return node_id


def test_database_refuses_a_topic_under_a_class(
    owner_db: Database, team: dict[str, Member]
) -> None:
    org = team["owner"].org_id
    cls = insert_node(owner_db, org, "CLASS", "Class 11")

    with pytest.raises(IntegrityError):
        insert_node(owner_db, org, "TOPIC", "Motion", (cls, "CLASS"))


def test_database_refuses_a_parent_kind_that_is_not_the_parents_real_kind(
    owner_db: Database, team: dict[str, Member]
) -> None:
    org = team["owner"].org_id
    cls = insert_node(owner_db, org, "CLASS", "Class 11")

    with pytest.raises(IntegrityError):  # says "SUBJECT" about a class, to pass the pair check
        insert_node(owner_db, org, "CHAPTER", "Kinematics", (cls, "SUBJECT"))


def test_database_refuses_a_class_with_a_parent_and_a_subject_without_one(
    owner_db: Database, team: dict[str, Member]
) -> None:
    org = team["owner"].org_id
    cls = insert_node(owner_db, org, "CLASS", "Class 11")

    with pytest.raises(IntegrityError):
        insert_node(owner_db, org, "CLASS", "Class 12", (cls, "CLASS"))
    with pytest.raises(IntegrityError):
        insert_node(owner_db, org, "SUBJECT", "Physics")


def test_database_refuses_a_parent_with_no_parent_kind(
    owner_db: Database, team: dict[str, Member]
) -> None:
    """A NULL parent kind would skip the composite key, so any made-up parent id would pass."""
    org = team["owner"].org_id

    with pytest.raises(IntegrityError):
        insert_node(owner_db, org, "TOPIC", "Motion", (new_id(), None))


def test_database_refuses_a_parent_in_another_coaching(
    owner_db: Database, team: dict[str, Member]
) -> None:
    other = make_member(owner_db, "OWNER")
    foreign_class = insert_node(owner_db, other.org_id, "CLASS", "Class 11")

    with pytest.raises(IntegrityError):
        insert_node(owner_db, team["owner"].org_id, "SUBJECT", "Physics", (foreign_class, "CLASS"))


def test_database_refuses_two_siblings_with_the_same_name_but_not_the_same_name_elsewhere(
    owner_db: Database, team: dict[str, Member]
) -> None:
    org = team["owner"].org_id
    insert_node(owner_db, org, "CLASS", "class 11")
    with pytest.raises(IntegrityError):
        insert_node(owner_db, org, "CLASS", "class 11")

    other = make_member(owner_db, "OWNER")
    insert_node(owner_db, other.org_id, "CLASS", "class 11")  # another coaching: fine


def test_the_runtime_role_can_retire_but_not_delete_a_node(
    db: Database, owner_db: Database, team: dict[str, Member]
) -> None:
    node = insert_node(owner_db, team["owner"].org_id, "CLASS", "Class 11")

    context = TenantContext(organization_id=team["owner"].org_id)
    with pytest.raises(DBAPIError, match="permission denied"), db.transaction(context) as session:
        session.execute(text("DELETE FROM taxonomy_nodes WHERE id = :id"), {"id": node})


# --- One coaching never sees another's syllabus (T30) -----------------------------------------


def test_a_coaching_sees_only_its_own_syllabus(
    db: Database, owner_db: Database, team: dict[str, Member]
) -> None:
    mine = insert_node(owner_db, team["owner"].org_id, "CLASS", "Class 11")
    other = make_member(owner_db, "OWNER")
    theirs = insert_node(owner_db, other.org_id, "CLASS", "Class 11")
    with owner_db.transaction(TenantContext(organization_id=other.org_id)) as session:
        session.add(
            TaxonomyLabel(organization_id=other.org_id, node_id=theirs, language="hi", label="x")
        )

    with db.transaction(TenantContext(organization_id=team["owner"].org_id)) as session:
        node_ids = set(session.scalars(select(TaxonomyNode.id)))
        label_count = len(list(session.scalars(select(TaxonomyLabel))))

    assert node_ids == {mine}
    assert label_count == 0


def test_a_coaching_cannot_write_a_node_or_label_for_another(
    db: Database, owner_db: Database, team: dict[str, Member]
) -> None:
    other = make_member(owner_db, "OWNER")
    theirs = insert_node(owner_db, other.org_id, "CLASS", "Class 11")
    context = TenantContext(organization_id=team["owner"].org_id)

    sneaky_node = TaxonomyNode(
        organization_id=other.org_id, kind="CLASS", name="Sneaky", name_key="sneaky"
    )
    sneaky_label = TaxonomyLabel(
        organization_id=other.org_id, node_id=theirs, language="hi", label="x"
    )
    with pytest.raises(DBAPIError, match="row-level security"), db.transaction(context) as session:
        session.add(sneaky_node)
    with pytest.raises(DBAPIError, match="row-level security"), db.transaction(context) as session:
        session.add(sneaky_label)


def test_a_platform_admin_with_no_coaching_selected_sees_no_syllabus_items(
    db: Database, owner_db: Database, team: dict[str, Member]
) -> None:
    insert_node(owner_db, team["owner"].org_id, "CLASS", "Class 11")

    with db.transaction(TenantContext(is_platform=True)) as session:
        assert list(session.scalars(select(TaxonomyNode))) == []
    assert PLATFORM.is_platform  # the arrangement above is the platform context


# --- Fixed lists --------------------------------------------------------------------------------


def test_fixed_lists_need_a_sign_in(client: TestClient) -> None:
    for path in (
        "/api/v1/languages",
        "/api/v1/catalogues/bloom",
        "/api/v1/catalogues/difficulty-guide",
    ):
        assert client.get(path).status_code == 401


def test_anyone_signed_in_reads_the_fixed_lists(
    client: TestClient, team: dict[str, Member]
) -> None:
    sign_in(client, team["faculty"].email)

    languages = client.get("/api/v1/languages").json()
    bloom = client.get("/api/v1/catalogues/bloom").json()
    guide = client.get("/api/v1/catalogues/difficulty-guide").json()

    assert [language["tag"] for language in languages] == ["en", "hi", "gu", "bn", "mr", "te", "ta"]
    assert languages[1] == {"tag": "hi", "english_name": "Hindi", "native_name": "हिन्दी"}
    assert [level["key"] for level in bloom][:3] == ["REMEMBER", "UNDERSTAND", "APPLY"]
    assert [item["level"] for item in guide] == list(range(1, 11))


FIXED_LISTS = (
    "/api/v1/languages",
    "/api/v1/catalogues/bloom",
    "/api/v1/catalogues/difficulty-guide",
)


def test_a_platform_admin_reads_the_fixed_lists_only_while_acting_in_a_coaching(
    client: TestClient, owner_db: Database, team: dict[str, Member]
) -> None:
    headers = sign_in(client, platform_admin(owner_db))

    before = [client.get(path).status_code for path in FIXED_LISTS]
    client.post(
        "/api/v1/platform/acting-organization",
        json={"organization_id": str(team["owner"].org_id)},
        headers=headers,
    )
    after = [client.get(path).status_code for path in FIXED_LISTS]

    assert before == [403, 403, 403]
    assert after == [200, 200, 200]


# --- Building the tree through the API ---------------------------------------------------------


def test_an_admin_builds_the_whole_tree_and_everyone_reads_it(
    client: TestClient, team: dict[str, Member], admin_headers: dict[str, str]
) -> None:
    nodes = tree(client, admin_headers)
    faculty = TestClient(client.app)
    sign_in(faculty, team["faculty"].email)

    chapters = faculty.get(NODES, params={"kind": "CHAPTER"}).json()["data"]
    under_physics = faculty.get(NODES, params={"parent_id": nodes["subject"]["id"]}).json()["data"]
    one = faculty.get(f"{NODES}/{nodes['topic']['id']}")

    assert [chapter["name"] for chapter in chapters] == ["Kinematics"]
    assert [child["name"] for child in under_physics] == ["Kinematics"]
    assert one.json()["parent_id"] == nodes["chapter"]["id"]
    assert one.headers["ETag"] == '"rev-1"'


def test_names_in_other_languages_are_kept_and_returned(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    node = add(
        client, admin_headers, "CLASS", "Class 11", labels={"hi": "कक्षा 11", "ta": "வகுப்பு 11"}
    )

    assert node["labels"] == {"hi": "कक्षा 11", "ta": "வகுப்பு 11"}
    assert client.get(f"{NODES}/{node['id']}").json()["labels"] == node["labels"]


@pytest.mark.parametrize("labels", [{"en": "Class 11"}, {"xx": "Class 11"}, {"hi": " "}])
def test_a_label_must_be_a_real_non_english_language_with_text(
    client: TestClient, admin_headers: dict[str, str], labels: dict[str, str]
) -> None:
    response = client.post(
        NODES, json={"kind": "CLASS", "name": "Class 11", "labels": labels}, headers=admin_headers
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "MALFORMED_REQUEST"


def test_wrong_parents_are_refused_in_plain_words(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    nodes = tree(client, admin_headers)

    topic_under_class = client.post(
        NODES,
        json={"kind": "TOPIC", "parent_id": nodes["class"]["id"], "name": "X"},
        headers=admin_headers,
    )
    class_with_parent = client.post(
        NODES,
        json={"kind": "CLASS", "parent_id": nodes["class"]["id"], "name": "Class 12"},
        headers=admin_headers,
    )
    subject_without_parent = client.post(
        NODES, json={"kind": "SUBJECT", "name": "Chemistry"}, headers=admin_headers
    )
    unknown_parent = client.post(
        NODES,
        json={"kind": "SUBJECT", "parent_id": str(new_id()), "name": "Chemistry"},
        headers=admin_headers,
    )

    assert [
        r.status_code for r in (topic_under_class, class_with_parent, subject_without_parent)
    ] == [
        422,
        422,
        422,
    ]
    assert topic_under_class.json()["error"]["code"] == "HIERARCHY_INVALID"
    assert "belongs under a chapter, not a class" in topic_under_class.json()["error"]["message"]
    assert class_with_parent.json()["error"]["code"] == "HIERARCHY_INVALID"
    assert subject_without_parent.json()["error"]["code"] == "HIERARCHY_INVALID"
    assert unknown_parent.status_code == 404


def test_siblings_cannot_share_a_name_but_cousins_can(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    nodes = tree(client, admin_headers)
    other_class = add(client, admin_headers, "CLASS", "Class 12")
    other_subject = add(client, admin_headers, "SUBJECT", "Physics", other_class["id"])

    clash = client.post(
        NODES,
        json={"kind": "SUBJECT", "parent_id": nodes["class"]["id"], "name": "  PHYSICS "},
        headers=admin_headers,
    )

    assert clash.status_code == 409
    assert clash.json()["error"]["code"] == "DUPLICATE_NAME"
    assert other_subject["name"] == "Physics"  # the same name under another class is fine


def test_a_syllabus_name_that_grows_too_long_once_normalised_is_a_422_not_a_500(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    ligatures = "\ufb03" * 200  # 200 characters, 600 once expanded to letters

    response = client.post(NODES, json={"kind": "CLASS", "name": ligatures}, headers=admin_headers)

    assert (response.status_code, response.json()["error"]["code"]) == (422, "NAME_TOO_LONG")


def test_two_admins_adding_the_same_name_at_once_leave_exactly_one(
    client: TestClient, team: dict[str, Member], admin_headers: dict[str, str]
) -> None:
    owner = TestClient(client.app)
    owner_headers = sign_in(owner, team["owner"].email)
    results: list[int] = []

    def create(browser: TestClient, headers: dict[str, str]) -> None:
        response = browser.post(NODES, json={"kind": "CLASS", "name": "Class 11"}, headers=headers)
        results.append(response.status_code)

    threads = [
        threading.Thread(target=create, args=(client, admin_headers)),
        threading.Thread(target=create, args=(owner, owner_headers)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(results) == [201, 409]


# --- Who may do what (T26) ---------------------------------------------------------------------


def test_retrying_a_create_with_the_same_key_returns_the_same_item(
    client: TestClient, owner_db: Database, team: dict[str, Member], admin_headers: dict[str, str]
) -> None:
    headers = {**admin_headers, "Idempotency-Key": "retry-1"}
    body = {"kind": "CLASS", "name": "Class 11", "labels": {"hi": "कक्षा 11"}}

    first = client.post(NODES, json=body, headers=headers)
    retry = client.post(NODES, json=body, headers=headers)  # the first answer was "lost"

    assert (first.status_code, retry.status_code) == (201, 201)
    assert retry.json()["id"] == first.json()["id"]
    assert len(client.get(NODES).json()["data"]) == 1
    assert len(audit(owner_db, team["owner"].org_id, "TAXONOMY_NODE_CREATED")) == 1


def test_the_same_key_with_a_different_body_is_refused(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    headers = {**admin_headers, "Idempotency-Key": "retry-2"}
    client.post(NODES, json={"kind": "CLASS", "name": "Class 11"}, headers=headers)

    other = client.post(NODES, json={"kind": "CLASS", "name": "Class 12"}, headers=headers)

    assert (other.status_code, other.json()["error"]["code"]) == (409, "IDEMPOTENCY_KEY_REUSED")
    assert [node["name"] for node in client.get(NODES).json()["data"]] == ["Class 11"]


def test_a_failed_create_does_not_use_up_its_key(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    headers = {**admin_headers, "Idempotency-Key": "retry-3"}
    client.post(NODES, json={"kind": "CLASS", "name": "Class 11"}, headers=admin_headers)
    clash = client.post(NODES, json={"kind": "CLASS", "name": "class 11"}, headers=headers)

    fixed = client.post(NODES, json={"kind": "CLASS", "name": "Class 12"}, headers=headers)

    assert clash.status_code == 409
    # The refused attempt was rolled back with its claim, so the key is free for a corrected body.
    assert (fixed.status_code, fixed.json()["name"]) == (201, "Class 12")


def test_faculty_read_but_cannot_change_the_syllabus(
    client: TestClient, team: dict[str, Member], admin_headers: dict[str, str]
) -> None:
    node = add(client, admin_headers, "CLASS", "Class 11")
    faculty = TestClient(client.app)
    headers = sign_in(faculty, team["faculty"].email)  # even with EDIT_OTHERS

    responses = [
        faculty.post(NODES, json={"kind": "CLASS", "name": "Class 12"}, headers=headers),
        faculty.patch(
            f"{NODES}/{node['id']}", json={"name": "X"}, headers={**headers, **if_match(node)}
        ),
        faculty.post(f"{NODES}/{node['id']}/deprecate", headers={**headers, **if_match(node)}),
        faculty.post(f"{NODES}/{node['id']}/restore", headers={**headers, **if_match(node)}),
    ]

    assert [response.status_code for response in responses] == [403, 403, 403, 403]
    assert faculty.get(NODES).status_code == 200


def test_the_service_functions_refuse_a_principal_who_may_not_change_the_syllabus(
    db: Database, owner_db: Database, team: dict[str, Member]
) -> None:
    """Other code (the import, jobs) calls the service directly, so it must check for itself."""
    org = team["owner"].org_id
    node_id = insert_node(owner_db, org, "CLASS", "Class 11")
    faculty = Principal(
        user_id=team["faculty"].user_id,
        display_name="Faculty",
        is_platform_admin=False,
        organization_id=org,
        role="FACULTY",
        grants=frozenset({"EDIT_OTHERS"}),
    )

    with db.transaction(faculty.tenant_context) as session:
        with pytest.raises(PermissionDenied):
            service.create_node(
                session,
                faculty,
                CreateNode(kind="CLASS", name="Class 12"),
                idempotency_key=None,
                request_id=None,
            )
        with pytest.raises(PermissionDenied):
            service.update_node(
                session, faculty, node_id, UpdateNode(name="X"), if_match='"rev-1"', request_id=None
            )
        with pytest.raises(PermissionDenied):
            service.set_state(
                session, faculty, node_id, "DEPRECATED", if_match='"rev-1"', request_id=None
            )


def test_the_owner_may_change_the_syllabus_too(client: TestClient, team: dict[str, Member]) -> None:
    headers = sign_in(client, team["owner"].email)

    assert add(client, headers, "CLASS", "Class 11")["name"] == "Class 11"


def test_another_coachings_admin_cannot_see_or_change_an_item(
    client: TestClient, owner_db: Database, admin_headers: dict[str, str]
) -> None:
    node = add(client, admin_headers, "CLASS", "Class 11")
    stranger = TestClient(client.app)
    headers = sign_in(stranger, make_member(owner_db, "ADMIN").email)

    assert stranger.get(f"{NODES}/{node['id']}").status_code == 404
    assert (
        stranger.patch(
            f"{NODES}/{node['id']}", json={"name": "X"}, headers={**headers, **if_match(node)}
        ).status_code
        == 404
    )
    assert (
        stranger.post(
            f"{NODES}/{node['id']}/deprecate", headers={**headers, **if_match(node)}
        ).status_code
        == 404
    )
    assert stranger.get(NODES).json()["data"] == []


def test_a_platform_admin_needs_to_act_in_a_coaching_first(
    client: TestClient, owner_db: Database, team: dict[str, Member], admin_headers: dict[str, str]
) -> None:
    add(client, admin_headers, "CLASS", "Class 11")
    staff = TestClient(client.app)
    headers = sign_in(staff, platform_admin(owner_db))

    before = staff.get(NODES)
    refused = staff.post(NODES, json={"kind": "CLASS", "name": "Class 12"}, headers=headers)
    staff.post(
        "/api/v1/platform/acting-organization",
        json={"organization_id": str(team["owner"].org_id)},
        headers=headers,
    )
    after = staff.get(NODES)
    created = staff.post(NODES, json={"kind": "CLASS", "name": "Class 12"}, headers=headers)

    assert before.status_code == 403
    assert refused.status_code == 403
    assert [node["name"] for node in after.json()["data"]] == ["Class 11"]
    assert created.status_code == 201
    event = audit(owner_db, team["owner"].org_id, "TAXONOMY_NODE_CREATED")[-1]
    assert event.actor_is_platform is True


# --- Changing an item ---------------------------------------------------------------------------


def test_renaming_reordering_and_translating_with_the_current_revision(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    node = add(client, admin_headers, "CLASS", "Class 11", labels={"hi": "कक्षा 11"})

    response = client.patch(
        f"{NODES}/{node['id']}",
        json={"name": "Class XI", "sort_order": 3, "labels": {"gu": "ધોરણ 11"}},
        headers={**admin_headers, **if_match(node)},
    )

    body = response.json()
    assert response.status_code == 200
    assert (body["name"], body["sort_order"], body["revision"]) == ("Class XI", 3, 2)
    assert body["labels"] == {"gu": "ધોરણ 11"}  # the labels sent replace the old ones
    assert response.headers["ETag"] == '"rev-2"'


def test_a_change_needs_if_match_and_a_stale_one_is_refused(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    node = add(client, admin_headers, "CLASS", "Class 11")
    first = client.patch(
        f"{NODES}/{node['id']}",
        json={"name": "Class XI"},
        headers={**admin_headers, **if_match(node)},
    )

    missing = client.patch(f"{NODES}/{node['id']}", json={"name": "A"}, headers=admin_headers)
    stale = client.patch(
        f"{NODES}/{node['id']}", json={"name": "B"}, headers={**admin_headers, **if_match(node)}
    )

    assert first.status_code == 200
    assert (missing.status_code, missing.json()["error"]["code"]) == (428, "IF_MATCH_REQUIRED")
    assert (stale.status_code, stale.json()["error"]["code"]) == (412, "REVISION_STALE")
    assert stale.json()["error"]["details"]["current_etag"] == '"rev-2"'
    assert client.get(f"{NODES}/{node['id']}").json()["name"] == "Class XI"


def test_a_change_that_changes_nothing_keeps_the_revision_and_writes_no_audit_event(
    client: TestClient, owner_db: Database, team: dict[str, Member], admin_headers: dict[str, str]
) -> None:
    node = add(client, admin_headers, "CLASS", "Class 11", labels={"hi": "कक्षा 11"})

    response = client.patch(
        f"{NODES}/{node['id']}",
        json={"name": "Class 11", "labels": {"hi": "कक्षा 11"}},
        headers={**admin_headers, **if_match(node)},
    )

    assert response.json()["revision"] == 1
    assert audit(owner_db, team["owner"].org_id, "TAXONOMY_NODE_UPDATED") == []


def test_a_rename_that_clashes_is_refused_and_changes_nothing(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    add(client, admin_headers, "CLASS", "Class 11")
    twelve = add(client, admin_headers, "CLASS", "Class 12")

    clash = client.patch(
        f"{NODES}/{twelve['id']}",
        json={"name": "class 11"},
        headers={**admin_headers, **if_match(twelve)},
    )

    assert (clash.status_code, clash.json()["error"]["code"]) == (409, "DUPLICATE_NAME")
    again = client.get(f"{NODES}/{twelve['id']}").json()
    assert (again["name"], again["revision"]) == ("Class 12", 1)


# --- Retiring and restoring (C-04) --------------------------------------------------------------


def test_retiring_hides_an_item_from_pickers_but_not_from_the_full_list_or_its_children(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    nodes = tree(client, admin_headers)

    retired = client.post(
        f"{NODES}/{nodes['chapter']['id']}/deprecate",
        headers={**admin_headers, **if_match(nodes["chapter"])},
    )

    assert retired.json()["state"] == "DEPRECATED"
    active = client.get(NODES, params={"kind": "CHAPTER", "state": "ACTIVE"}).json()["data"]
    everything = client.get(NODES, params={"kind": "CHAPTER"}).json()["data"]
    assert active == []
    assert [chapter["name"] for chapter in everything] == ["Kinematics"]
    topic = client.get(f"{NODES}/{nodes['topic']['id']}").json()
    assert (topic["state"], topic["revision"]) == ("ACTIVE", 1)  # the children are left alone


def test_nothing_new_goes_under_a_retired_item_and_a_child_waits_for_its_parent_to_return(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    nodes = tree(client, admin_headers)
    child = nodes["topic"]
    client.post(f"{NODES}/{child['id']}/deprecate", headers={**admin_headers, **if_match(child)})
    parent = client.get(f"{NODES}/{nodes['chapter']['id']}")
    parent_node = parent.json()
    client.post(
        f"{NODES}/{parent_node['id']}/deprecate", headers={**admin_headers, **if_match(parent_node)}
    )

    new_under_retired = client.post(
        NODES,
        json={"kind": "TOPIC", "parent_id": parent_node["id"], "name": "Another"},
        headers=admin_headers,
    )
    restore_child_first = client.post(
        f"{NODES}/{child['id']}/restore",
        headers={**admin_headers, "If-Match": '"rev-2"'},
    )
    restore_parent = client.post(
        f"{NODES}/{parent_node['id']}/restore", headers={**admin_headers, "If-Match": '"rev-2"'}
    )
    restore_child = client.post(
        f"{NODES}/{child['id']}/restore", headers={**admin_headers, "If-Match": '"rev-2"'}
    )

    assert (new_under_retired.status_code, new_under_retired.json()["error"]["code"]) == (
        409,
        "PARENT_DEPRECATED",
    )
    assert (restore_child_first.status_code, restore_child_first.json()["error"]["code"]) == (
        409,
        "PARENT_DEPRECATED",
    )
    assert restore_parent.json()["state"] == "ACTIVE"
    assert restore_child.json()["state"] == "ACTIVE"


def test_retiring_or_restoring_twice_changes_nothing_the_second_time(
    client: TestClient, owner_db: Database, team: dict[str, Member], admin_headers: dict[str, str]
) -> None:
    node = add(client, admin_headers, "CLASS", "Class 11")
    first = client.post(
        f"{NODES}/{node['id']}/deprecate", headers={**admin_headers, **if_match(node)}
    )

    second = client.post(
        f"{NODES}/{node['id']}/deprecate", headers={**admin_headers, "If-Match": '"rev-2"'}
    )

    assert (first.json()["revision"], second.json()["revision"]) == (2, 2)
    assert len(audit(owner_db, team["owner"].org_id, "TAXONOMY_NODE_DEPRECATED")) == 1


# --- Paging and audit ---------------------------------------------------------------------------


def test_pages_follow_the_admins_order_and_a_damaged_cursor_is_a_400(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    for name, order in (("C", 2), ("A", 2), ("B", 1), ("D", 3)):
        add(client, admin_headers, "CLASS", name, sort_order=order)

    first = client.get(NODES, params={"limit": 3}).json()
    second = client.get(NODES, params={"limit": 3, "cursor": first["page"]["next_cursor"]}).json()

    assert [n["name"] for n in first["data"]] == ["B", "A", "C"]
    assert first["page"]["has_more"] is True
    assert [n["name"] for n in second["data"]] == ["D"]
    assert second["page"] == {"next_cursor": None, "has_more": False}
    assert client.get(NODES, params={"cursor": "not-a-cursor"}).status_code == 400


def test_every_change_is_in_the_audit_log_with_before_and_after(
    client: TestClient, owner_db: Database, team: dict[str, Member], admin_headers: dict[str, str]
) -> None:
    node = add(client, admin_headers, "CLASS", "Class 11")
    renamed = client.patch(
        f"{NODES}/{node['id']}",
        json={"name": "Class XI"},
        headers={**admin_headers, **if_match(node)},
    ).json()
    retired = client.post(
        f"{NODES}/{node['id']}/deprecate", headers={**admin_headers, **if_match(renamed)}
    ).json()
    client.post(f"{NODES}/{node['id']}/restore", headers={**admin_headers, **if_match(retired)})

    org = team["owner"].org_id
    (created,) = audit(owner_db, org, "TAXONOMY_NODE_CREATED")
    (updated,) = audit(owner_db, org, "TAXONOMY_NODE_UPDATED")
    (deprecated,) = audit(owner_db, org, "TAXONOMY_NODE_DEPRECATED")
    (restored,) = audit(owner_db, org, "TAXONOMY_NODE_RESTORED")

    assert created.before is None and created.after["name"] == "Class 11"  # type: ignore[index]
    assert (updated.before["name"], updated.after["name"]) == ("Class 11", "Class XI")  # type: ignore[index]
    assert (deprecated.before["state"], deprecated.after["state"]) == ("ACTIVE", "DEPRECATED")  # type: ignore[index]
    assert (restored.before["state"], restored.after["state"]) == ("DEPRECATED", "ACTIVE")  # type: ignore[index]
    assert {event.entity_id for event in (created, updated, deprecated, restored)} == {
        UUID(node["id"])
    }
    assert {event.actor_user_id for event in (created, updated)} == {team["admin"].user_id}
