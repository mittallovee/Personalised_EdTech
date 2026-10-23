"""M3 PR 2b: exams and sources (C-11, C-13, C-04; tests T26 and T30 for these tables).

Exams and sources behave alike, so most tests run once for each.
"""

import threading
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from qbank.core.auth import Principal
from qbank.core.config import AppEnv, Settings
from qbank.core.db import Database
from qbank.core.errors import PermissionDenied
from qbank.core.tenancy import TenantContext
from qbank.main import create_app
from qbank.modules.audit.models import AuditEvent
from qbank.modules.taxonomy import catalogue_service as service
from qbank.modules.taxonomy.models import Exam, Source
from tests.integration.conftest import (
    Member,
    MigratedDatabase,
    make_member,
    platform_admin,
    sign_in,
)


@dataclass(frozen=True)
class Kind:
    """Which of the two lists a test is about."""

    path: str
    catalogue: service.Catalogue
    audit_prefix: str
    body: Callable[[str], dict[str, Any]]  # a create body with this name
    other_name: str  # a second, different name


EXAMS = Kind("/api/v1/exams", service.EXAMS, "EXAM", lambda name: {"name": name}, "NEET")
SOURCES = Kind(
    "/api/v1/sources",
    service.SOURCES,
    "SOURCE",
    lambda name: {"kind": "BOOK", "name": name},
    "DC Pandey, Understanding Physics",
)
BOTH = pytest.mark.parametrize("kind", [EXAMS, SOURCES], ids=["exams", "sources"])
FIRST = "JEE Main"


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


def add(client: TestClient, headers: dict[str, str], kind: Kind, name: str) -> dict[str, Any]:
    response = client.post(kind.path, json=kind.body(name), headers=headers)
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


# --- Adding and reading -------------------------------------------------------------------------


@BOTH
def test_an_admin_adds_items_and_everyone_in_the_coaching_reads_them(
    client: TestClient, team: dict[str, Member], admin_headers: dict[str, str], kind: Kind
) -> None:
    item = add(client, admin_headers, kind, FIRST)
    faculty = TestClient(client.app)
    sign_in(faculty, team["faculty"].email)

    listed = faculty.get(kind.path).json()["data"]
    one = faculty.get(f"{kind.path}/{item['id']}")

    assert [entry["name"] for entry in listed] == [FIRST]
    assert one.json()["id"] == item["id"]
    assert one.headers["ETag"] == '"rev-1"'
    assert (item["state"], item["revision"]) == ("ACTIVE", 1)


def test_an_exam_may_have_a_short_code_and_a_source_has_a_kind(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    exam = client.post(
        EXAMS.path, json={"name": "JEE Main", "short_code": " JEEM "}, headers=admin_headers
    ).json()
    source = client.post(
        SOURCES.path,
        json={"kind": "TEST_SERIES", "name": "All India Test Series"},
        headers=admin_headers,
    ).json()
    bad_kind = client.post(
        SOURCES.path, json={"kind": "MAGAZINE", "name": "X"}, headers=admin_headers
    )

    assert exam["short_code"] == "JEEM"  # surrounding spaces are trimmed
    assert source["kind"] == "TEST_SERIES"
    assert bad_kind.status_code == 400


def test_sources_can_be_listed_by_kind(client: TestClient, admin_headers: dict[str, str]) -> None:
    for kind, name in (("BOOK", "HC Verma"), ("MODULE", "Module 1"), ("BOOK", "DC Pandey")):
        client.post(SOURCES.path, json={"kind": kind, "name": name}, headers=admin_headers)

    books = client.get(SOURCES.path, params={"kind": "BOOK"}).json()["data"]

    assert [source["name"] for source in books] == ["DC Pandey", "HC Verma"]


@BOTH
def test_pages_are_in_name_order_and_a_damaged_cursor_is_a_400(
    client: TestClient, admin_headers: dict[str, str], kind: Kind
) -> None:
    for name in ("Charlie", "alpha", "Bravo", "delta"):
        add(client, admin_headers, kind, name)

    first = client.get(kind.path, params={"limit": 3}).json()
    second = client.get(kind.path, params={"limit": 3, "cursor": first["page"]["next_cursor"]})

    assert [entry["name"] for entry in first["data"]] == ["alpha", "Bravo", "Charlie"]
    assert first["page"]["has_more"] is True
    assert [entry["name"] for entry in second.json()["data"]] == ["delta"]
    assert second.json()["page"] == {"next_cursor": None, "has_more": False}
    assert client.get(kind.path, params={"cursor": "not-a-cursor"}).status_code == 400


# --- Names are unique -----------------------------------------------------------------------------


@BOTH
def test_a_name_cannot_be_used_twice_however_it_is_spelled(
    client: TestClient, admin_headers: dict[str, str], kind: Kind
) -> None:
    add(client, admin_headers, kind, FIRST)

    clash = client.post(kind.path, json=kind.body("  jee   MAIN "), headers=admin_headers)

    assert (clash.status_code, clash.json()["error"]["code"]) == (409, "DUPLICATE_NAME")


def test_the_same_source_name_may_be_used_for_different_kinds(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    book = client.post(
        SOURCES.path, json={"kind": "BOOK", "name": "Mechanics"}, headers=admin_headers
    )
    module = client.post(
        SOURCES.path, json={"kind": "MODULE", "name": "Mechanics"}, headers=admin_headers
    )

    assert (book.status_code, module.status_code) == (201, 201)


@BOTH
def test_two_admins_adding_the_same_name_at_once_leave_exactly_one(
    client: TestClient, team: dict[str, Member], admin_headers: dict[str, str], kind: Kind
) -> None:
    owner = TestClient(client.app)
    owner_headers = sign_in(owner, team["owner"].email)
    results: list[int] = []

    def create(browser: TestClient, headers: dict[str, str]) -> None:
        results.append(browser.post(kind.path, json=kind.body(FIRST), headers=headers).status_code)

    threads = [
        threading.Thread(target=create, args=(client, admin_headers)),
        threading.Thread(target=create, args=(owner, owner_headers)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(results) == [201, 409]


@BOTH
def test_a_rename_that_clashes_is_refused_and_changes_nothing(
    client: TestClient, admin_headers: dict[str, str], kind: Kind
) -> None:
    add(client, admin_headers, kind, FIRST)
    other = add(client, admin_headers, kind, kind.other_name)

    clash = client.patch(
        f"{kind.path}/{other['id']}",
        json={"name": "jee main"},
        headers={**admin_headers, **if_match(other)},
    )

    assert (clash.status_code, clash.json()["error"]["code"]) == (409, "DUPLICATE_NAME")
    again = client.get(f"{kind.path}/{other['id']}").json()
    assert (again["name"], again["revision"]) == (kind.other_name, 1)


# --- Retrying a create --------------------------------------------------------------------------


@BOTH
def test_retrying_a_create_with_the_same_key_returns_the_same_item(
    client: TestClient,
    owner_db: Database,
    team: dict[str, Member],
    admin_headers: dict[str, str],
    kind: Kind,
) -> None:
    headers = {**admin_headers, "Idempotency-Key": "retry-1"}

    first = client.post(kind.path, json=kind.body(FIRST), headers=headers)
    retry = client.post(kind.path, json=kind.body(FIRST), headers=headers)

    assert (first.status_code, retry.status_code) == (201, 201)
    assert retry.json()["id"] == first.json()["id"]
    assert len(client.get(kind.path).json()["data"]) == 1
    created = audit(owner_db, team["owner"].org_id, f"{kind.audit_prefix}_CREATED")
    assert len(created) == 1


@BOTH
def test_the_same_key_with_a_different_body_is_refused(
    client: TestClient, admin_headers: dict[str, str], kind: Kind
) -> None:
    headers = {**admin_headers, "Idempotency-Key": "retry-2"}
    client.post(kind.path, json=kind.body(FIRST), headers=headers)

    other = client.post(kind.path, json=kind.body(kind.other_name), headers=headers)

    assert (other.status_code, other.json()["error"]["code"]) == (409, "IDEMPOTENCY_KEY_REUSED")


# --- Changing ------------------------------------------------------------------------------------


def test_an_exam_is_renamed_and_its_short_code_added_changed_and_removed(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    exam = add(client, admin_headers, EXAMS, "JEE Main")

    renamed = client.patch(
        f"{EXAMS.path}/{exam['id']}",
        json={"name": "JEE (Main)", "short_code": "JM"},
        headers={**admin_headers, **if_match(exam)},
    ).json()
    only_code = client.patch(
        f"{EXAMS.path}/{exam['id']}",
        json={"short_code": "JEEM"},
        headers={**admin_headers, **if_match(renamed)},
    ).json()
    cleared = client.patch(
        f"{EXAMS.path}/{exam['id']}",
        json={"short_code": None},
        headers={**admin_headers, **if_match(only_code)},
    ).json()

    assert (renamed["name"], renamed["short_code"], renamed["revision"]) == ("JEE (Main)", "JM", 2)
    assert (only_code["name"], only_code["short_code"]) == ("JEE (Main)", "JEEM")  # name kept
    assert (cleared["name"], cleared["short_code"], cleared["revision"]) == ("JEE (Main)", None, 4)


def test_a_source_is_renamed_but_keeps_its_kind(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    source = add(client, admin_headers, SOURCES, "HC Verma")

    renamed = client.patch(
        f"{SOURCES.path}/{source['id']}",
        json={"name": "H C Verma", "kind": "MODULE"},  # the kind is ignored: it never changes
        headers={**admin_headers, **if_match(source)},
    ).json()

    assert (renamed["name"], renamed["kind"]) == ("H C Verma", "BOOK")


@BOTH
def test_a_change_needs_if_match_and_a_stale_one_is_refused(
    client: TestClient, admin_headers: dict[str, str], kind: Kind
) -> None:
    item = add(client, admin_headers, kind, FIRST)
    first = client.patch(
        f"{kind.path}/{item['id']}",
        json={"name": "JEE Main 2"},
        headers={**admin_headers, **if_match(item)},
    )

    missing = client.patch(f"{kind.path}/{item['id']}", json={"name": "A"}, headers=admin_headers)
    stale = client.patch(
        f"{kind.path}/{item['id']}", json={"name": "B"}, headers={**admin_headers, **if_match(item)}
    )

    assert first.status_code == 200
    assert (missing.status_code, missing.json()["error"]["code"]) == (428, "IF_MATCH_REQUIRED")
    assert (stale.status_code, stale.json()["error"]["code"]) == (412, "REVISION_STALE")
    assert stale.json()["error"]["details"]["current_etag"] == '"rev-2"'


@BOTH
def test_a_change_that_changes_nothing_keeps_the_revision_and_writes_no_audit_event(
    client: TestClient,
    owner_db: Database,
    team: dict[str, Member],
    admin_headers: dict[str, str],
    kind: Kind,
) -> None:
    item = add(client, admin_headers, kind, FIRST)

    response = client.patch(
        f"{kind.path}/{item['id']}",
        json={"name": FIRST},
        headers={**admin_headers, **if_match(item)},
    )

    assert response.json()["revision"] == 1
    assert audit(owner_db, team["owner"].org_id, f"{kind.audit_prefix}_UPDATED") == []


@BOTH
def test_a_null_name_means_keep_the_name(
    client: TestClient, admin_headers: dict[str, str], kind: Kind
) -> None:
    item = add(client, admin_headers, kind, FIRST)

    response = client.patch(
        f"{kind.path}/{item['id']}",
        json={"name": None},
        headers={**admin_headers, **if_match(item)},
    )

    assert (response.status_code, response.json()["name"], response.json()["revision"]) == (
        200,
        FIRST,
        1,
    )


@BOTH
def test_retiring_and_restoring_need_the_current_revision(
    client: TestClient, admin_headers: dict[str, str], kind: Kind
) -> None:
    item = add(client, admin_headers, kind, FIRST)
    client.patch(
        f"{kind.path}/{item['id']}",
        json={"name": "Renamed"},
        headers={**admin_headers, **if_match(item)},
    )  # now at revision 2

    for action in ("deprecate", "restore"):
        url = f"{kind.path}/{item['id']}/{action}"
        missing = client.post(url, headers=admin_headers)
        stale = client.post(url, headers={**admin_headers, **if_match(item)})
        assert (missing.status_code, missing.json()["error"]["code"]) == (428, "IF_MATCH_REQUIRED")
        assert (stale.status_code, stale.json()["error"]["code"]) == (412, "REVISION_STALE")
    assert client.get(f"{kind.path}/{item['id']}").json()["state"] == "ACTIVE"


# --- Retiring and restoring (C-04) ----------------------------------------------------------------


@BOTH
def test_retiring_hides_an_item_from_pickers_and_restoring_brings_it_back(
    client: TestClient, admin_headers: dict[str, str], kind: Kind
) -> None:
    item = add(client, admin_headers, kind, FIRST)

    retired = client.post(
        f"{kind.path}/{item['id']}/deprecate", headers={**admin_headers, **if_match(item)}
    ).json()
    in_picker = client.get(kind.path, params={"state": "ACTIVE"}).json()["data"]
    in_full_list = client.get(kind.path).json()["data"]
    restored = client.post(
        f"{kind.path}/{item['id']}/restore", headers={**admin_headers, **if_match(retired)}
    ).json()

    assert retired["state"] == "DEPRECATED"
    assert in_picker == []
    assert [entry["name"] for entry in in_full_list] == [FIRST]  # still there, still readable
    assert (restored["state"], restored["revision"]) == ("ACTIVE", 3)


@BOTH
def test_retiring_twice_changes_nothing_the_second_time(
    client: TestClient,
    owner_db: Database,
    team: dict[str, Member],
    admin_headers: dict[str, str],
    kind: Kind,
) -> None:
    item = add(client, admin_headers, kind, FIRST)
    first = client.post(
        f"{kind.path}/{item['id']}/deprecate", headers={**admin_headers, **if_match(item)}
    )

    second = client.post(
        f"{kind.path}/{item['id']}/deprecate", headers={**admin_headers, "If-Match": '"rev-2"'}
    )

    assert (first.json()["revision"], second.json()["revision"]) == (2, 2)
    retired = audit(owner_db, team["owner"].org_id, f"{kind.audit_prefix}_DEPRECATED")
    assert len(retired) == 1


@BOTH
def test_every_change_is_in_the_audit_log_with_before_and_after(
    client: TestClient,
    owner_db: Database,
    team: dict[str, Member],
    admin_headers: dict[str, str],
    kind: Kind,
) -> None:
    item = add(client, admin_headers, kind, FIRST)
    renamed = client.patch(
        f"{kind.path}/{item['id']}",
        json={"name": "Renamed"},
        headers={**admin_headers, **if_match(item)},
    ).json()
    retired = client.post(
        f"{kind.path}/{item['id']}/deprecate", headers={**admin_headers, **if_match(renamed)}
    ).json()
    client.post(f"{kind.path}/{item['id']}/restore", headers={**admin_headers, **if_match(retired)})

    org, prefix = team["owner"].org_id, kind.audit_prefix
    (created,) = audit(owner_db, org, f"{prefix}_CREATED")
    (updated,) = audit(owner_db, org, f"{prefix}_UPDATED")
    (deprecated,) = audit(owner_db, org, f"{prefix}_DEPRECATED")
    (restored,) = audit(owner_db, org, f"{prefix}_RESTORED")

    assert created.before is None and created.after["name"] == FIRST  # type: ignore[index]
    assert (updated.before["name"], updated.after["name"]) == (FIRST, "Renamed")  # type: ignore[index]
    assert (deprecated.before["state"], deprecated.after["state"]) == ("ACTIVE", "DEPRECATED")  # type: ignore[index]
    assert (restored.before["state"], restored.after["state"]) == ("DEPRECATED", "ACTIVE")  # type: ignore[index]
    events = (created, updated, deprecated, restored)
    assert {event.entity_id for event in events} == {UUID(item["id"])}
    assert {event.entity_type for event in events} == {kind.catalogue.entity_type}
    assert {event.actor_user_id for event in events} == {team["admin"].user_id}


# --- Who may do what (T26) ------------------------------------------------------------------------


@BOTH
def test_faculty_read_but_cannot_change_the_lists(
    client: TestClient, team: dict[str, Member], admin_headers: dict[str, str], kind: Kind
) -> None:
    item = add(client, admin_headers, kind, FIRST)
    faculty = TestClient(client.app)
    headers = sign_in(faculty, team["faculty"].email)  # even with EDIT_OTHERS
    stale = {**headers, **if_match(item)}

    responses = [
        faculty.post(kind.path, json=kind.body("New"), headers=headers),
        faculty.patch(f"{kind.path}/{item['id']}", json={"name": "X"}, headers=stale),
        faculty.post(f"{kind.path}/{item['id']}/deprecate", headers=stale),
        faculty.post(f"{kind.path}/{item['id']}/restore", headers=stale),
    ]

    assert [response.status_code for response in responses] == [403, 403, 403, 403]
    assert faculty.get(kind.path).status_code == 200
    assert faculty.get(f"{kind.path}/{item['id']}").status_code == 200


@BOTH
def test_the_service_functions_refuse_a_principal_who_may_not_change_the_lists(
    db: Database, owner_db: Database, team: dict[str, Member], kind: Kind
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
            service.create_item(
                session,
                faculty,
                kind.catalogue,
                kind.body("New"),
                idempotency_key=None,
                request_id=None,
            )
        with pytest.raises(PermissionDenied):
            service.update_item(
                session,
                faculty,
                kind.catalogue,
                UUID(int=1),
                {"name": "X"},
                if_match='"rev-1"',
                request_id=None,
            )
        with pytest.raises(PermissionDenied):
            service.set_state(
                session,
                faculty,
                kind.catalogue,
                UUID(int=1),
                "DEPRECATED",
                if_match='"rev-1"',
                request_id=None,
            )


@BOTH
def test_another_coachings_admin_cannot_see_or_change_an_item(
    client: TestClient, owner_db: Database, admin_headers: dict[str, str], kind: Kind
) -> None:
    item = add(client, admin_headers, kind, FIRST)
    stranger = TestClient(client.app)
    headers = sign_in(stranger, make_member(owner_db, "ADMIN").email)
    stale = {**headers, **if_match(item)}

    assert stranger.get(f"{kind.path}/{item['id']}").status_code == 404
    patch = stranger.patch(f"{kind.path}/{item['id']}", json={"name": "X"}, headers=stale)
    assert patch.status_code == 404
    retire = stranger.post(f"{kind.path}/{item['id']}/deprecate", headers=stale)
    assert retire.status_code == 404
    assert stranger.get(kind.path).json()["data"] == []


@BOTH
def test_a_platform_admin_needs_to_act_in_a_coaching_first(
    client: TestClient,
    owner_db: Database,
    team: dict[str, Member],
    admin_headers: dict[str, str],
    kind: Kind,
) -> None:
    add(client, admin_headers, kind, FIRST)
    staff = TestClient(client.app)
    headers = sign_in(staff, platform_admin(owner_db))

    before = staff.get(kind.path)
    refused = staff.post(kind.path, json=kind.body("New"), headers=headers)
    staff.post(
        "/api/v1/platform/acting-organization",
        json={"organization_id": str(team["owner"].org_id)},
        headers=headers,
    )
    after = staff.get(kind.path)
    created = staff.post(kind.path, json=kind.body("New"), headers=headers)

    assert (before.status_code, refused.status_code) == (403, 403)
    assert [entry["name"] for entry in after.json()["data"]] == [FIRST]
    assert created.status_code == 201
    event = audit(owner_db, team["owner"].org_id, f"{kind.audit_prefix}_CREATED")[-1]
    assert event.actor_is_platform is True


# --- One coaching never sees another's lists (T30) ---------------------------------------------


def insert_rows(owner_db: Database, org_id: UUID) -> tuple[UUID, UUID]:
    exam_id, source_id = UUID(int=org_id.int + 1), UUID(int=org_id.int + 2)
    with owner_db.transaction(TenantContext(organization_id=org_id)) as session:
        session.execute(
            text(
                "INSERT INTO exams (id, organization_id, name, name_key)"
                " VALUES (:id, :org, 'JEE Main', 'jee main')"
            ),
            {"id": exam_id, "org": org_id},
        )
        session.execute(
            text(
                "INSERT INTO sources (id, organization_id, kind, name, name_key)"
                " VALUES (:id, :org, 'BOOK', 'HC Verma', 'hc verma')"
            ),
            {"id": source_id, "org": org_id},
        )
    return exam_id, source_id


def test_a_coaching_sees_only_its_own_exams_and_sources(
    db: Database, owner_db: Database, team: dict[str, Member]
) -> None:
    mine = insert_rows(owner_db, team["owner"].org_id)
    insert_rows(owner_db, make_member(owner_db, "OWNER").org_id)

    with db.transaction(TenantContext(organization_id=team["owner"].org_id)) as session:
        exam_ids = set(session.scalars(select(Exam.id)))
        source_ids = set(session.scalars(select(Source.id)))

    assert (exam_ids, source_ids) == ({mine[0]}, {mine[1]})


def test_a_coaching_cannot_write_an_exam_or_source_for_another(
    db: Database, owner_db: Database, team: dict[str, Member]
) -> None:
    other = make_member(owner_db, "OWNER")
    context = TenantContext(organization_id=team["owner"].org_id)
    sneaky_exam = Exam(organization_id=other.org_id, name="Sneaky", name_key="sneaky")
    sneaky_source = Source(organization_id=other.org_id, kind="BOOK", name="S", name_key="s")

    with pytest.raises(DBAPIError, match="row-level security"), db.transaction(context) as session:
        session.add(sneaky_exam)
    with pytest.raises(DBAPIError, match="row-level security"), db.transaction(context) as session:
        session.add(sneaky_source)


def test_the_runtime_role_can_retire_but_not_delete_exams_and_sources(
    db: Database, owner_db: Database, team: dict[str, Member]
) -> None:
    org = team["owner"].org_id
    insert_rows(owner_db, org)

    for table in ("exams", "sources"):
        with (
            pytest.raises(DBAPIError, match="permission denied"),
            db.transaction(TenantContext(organization_id=org)) as session,
        ):
            session.execute(text(f"DELETE FROM {table}"))  # noqa: S608 (fixed table names)
