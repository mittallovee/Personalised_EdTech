"""M3 PR 2c-3: applying a previewed syllabus import (C-03, T25)."""

import threading
from collections.abc import Iterator
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from qbank.core.config import AppEnv, Settings
from qbank.core.db import Database
from qbank.core.errors import Conflict
from qbank.core.tenancy import TenantContext
from qbank.main import create_app
from qbank.modules.audit.models import AuditEvent
from qbank.modules.taxonomy import concepts, import_apply, import_plan
from qbank.modules.taxonomy.models import TaxonomyNode
from tests.integration.conftest import Member, MigratedDatabase, make_member, sign_in

IMPORTS = "/api/v1/taxonomy/imports"
NODES = "/api/v1/taxonomy/nodes"
CONCEPTS = "/api/v1/taxonomy/concepts"
HEADER = "kind,path,sort,aliases,label_hi\n"
FILE = (
    HEADER
    + "CLASS,Class 11,1,,कक्षा 11\n"
    + "SUBJECT,Class 11 > Physics,1,,\n"
    + "CHAPTER,Class 11 > Physics > Kinematics,2,,\n"
    + "CONCEPT,Class 11 > Physics > Newton's second law,,Newton's 2nd law; F = ma,\n"
)


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


def preview(client: TestClient, headers: dict[str, str], data: str) -> dict[str, Any]:
    response = client.post(
        IMPORTS,
        content=data.encode(),
        params={"file_name": "syllabus.csv"},
        headers={**headers, "Content-Type": "application/octet-stream"},
    )
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


def apply(client: TestClient, headers: dict[str, str], import_id: str) -> Any:
    return client.post(f"{IMPORTS}/{import_id}/apply", headers=headers)


def nodes(client: TestClient, headers: dict[str, str]) -> dict[str, dict[str, Any]]:
    data = client.get(NODES, params={"limit": 100}, headers=headers).json()["data"]
    return {item["name"]: item for item in data}


def all_concepts(client: TestClient, headers: dict[str, str]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = client.get(CONCEPTS, headers=headers).json()["data"]
    return result


def events(owner_db: Database, org_id: UUID, action: str) -> int:
    with owner_db.transaction(TenantContext(organization_id=org_id)) as session:
        return (
            session.scalar(
                select(func.count())
                .select_from(AuditEvent)
                .where(AuditEvent.organization_id == org_id, AuditEvent.action == action)
            )
            or 0
        )


# --- Applying ----------------------------------------------------------------------------------


def test_applying_adds_everything_the_preview_listed(
    client: TestClient, owner_db: Database, team: dict[str, Member], admin_headers: dict[str, str]
) -> None:
    result = preview(client, admin_headers, FILE)
    response = apply(client, admin_headers, result["id"])

    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["state"], body["can_apply"], body["applied_at"] is not None) == (
        "APPLIED",
        False,
        True,
    )
    items = nodes(client, admin_headers)
    assert set(items) == {"Class 11", "Physics", "Kinematics"}
    assert items["Class 11"]["labels"] == {"hi": "कक्षा 11"} and items["Class 11"]["sort_order"] == 1
    assert items["Kinematics"]["sort_order"] == 2
    assert items["Kinematics"]["parent_id"] == items["Physics"]["id"]
    [law] = all_concepts(client, admin_headers)
    assert law["name"] == "Newton's second law" and law["subject_id"] == items["Physics"]["id"]
    assert law["aliases"] == ["F = ma", "Newton's 2nd law"]

    org = team["owner"].org_id
    assert events(owner_db, org, "TAXONOMY_NODE_CREATED") == 3
    assert events(owner_db, org, "CONCEPT_CREATED") == 1
    assert events(owner_db, org, "CATALOGUE_IMPORT_APPLIED") == 1


def test_a_file_whose_children_come_before_their_parents_applies(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    lines = FILE.splitlines()
    reversed_file = lines[0] + "\n" + "\n".join(reversed(lines[1:])) + "\n"
    result = preview(client, admin_headers, reversed_file)
    assert apply(client, admin_headers, result["id"]).status_code == 200
    assert set(nodes(client, admin_headers)) == {"Class 11", "Physics", "Kinematics"}
    assert len(all_concepts(client, admin_headers)) == 1


def test_applying_twice_changes_nothing_the_second_time(
    client: TestClient, owner_db: Database, team: dict[str, Member], admin_headers: dict[str, str]
) -> None:
    result = preview(client, admin_headers, FILE)
    first = apply(client, admin_headers, result["id"])
    second = apply(client, admin_headers, result["id"])
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert events(owner_db, team["owner"].org_id, "CATALOGUE_IMPORT_APPLIED") == 1
    assert len(nodes(client, admin_headers)) == 3


def test_the_same_file_again_has_nothing_left_to_do(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    apply(client, admin_headers, preview(client, admin_headers, FILE)["id"])
    again = preview(client, admin_headers, FILE)
    assert again["counts"] == {"new": 0, "changed": 0, "unchanged": 4, "error": 0}
    assert again["can_apply"] is False
    response = apply(client, admin_headers, again["id"])
    assert response.status_code == 422 and response.json()["error"]["code"] == "IMPORT_INVALID"
    assert "nothing to import" in response.json()["error"]["message"]


def test_applying_fills_in_what_is_there_and_removes_nothing(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    cls = client.post(
        NODES,
        json={"kind": "CLASS", "name": "Class 11", "labels": {"gu": "ધોરણ 11"}, "sort_order": 9},
        headers=admin_headers,
    ).json()
    subject = client.post(
        NODES,
        json={"kind": "SUBJECT", "parent_id": cls["id"], "name": "Physics"},
        headers=admin_headers,
    ).json()
    law = client.post(
        CONCEPTS,
        json={
            "subject_id": subject["id"],
            "name": "Newton's second law",
            "aliases": ["Second Law of Motion"],
            "labels": {"gu": "ન્યૂટન"},
        },
        headers=admin_headers,
    ).json()

    result = preview(client, admin_headers, FILE)
    assert result["counts"] == {"new": 1, "changed": 3, "unchanged": 0, "error": 0}
    assert apply(client, admin_headers, result["id"]).status_code == 200

    items = nodes(client, admin_headers)
    assert items["Class 11"]["labels"] == {"gu": "ધોરણ 11", "hi": "कक्षा 11"}
    assert items["Class 11"]["sort_order"] == 1  # the file gave a sort order, so it is set
    assert items["Class 11"]["revision"] == cls["revision"] + 1
    [changed] = all_concepts(client, admin_headers)
    assert changed["id"] == law["id"]
    assert changed["aliases"] == ["F = ma", "Newton's 2nd law", "Second Law of Motion"]
    assert changed["labels"] == {"gu": "ન્યૂટન"}
    assert changed["revision"] == law["revision"] + 1


# --- Applying is refused -----------------------------------------------------------------------


def test_a_preview_with_error_rows_cannot_be_applied(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    result = preview(client, admin_headers, FILE + "CHAPTER,Class 12 > Physics > Optics,,,\n")
    assert result["can_apply"] is False
    response = apply(client, admin_headers, result["id"])
    assert (
        response.status_code == 422 and "cannot be imported" in response.json()["error"]["message"]
    )
    assert nodes(client, admin_headers) == {}


def test_a_preview_is_stale_once_the_syllabus_has_changed(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    result = preview(client, admin_headers, FILE)
    client.post(NODES, json={"kind": "CLASS", "name": "Class 12"}, headers=admin_headers)

    response = apply(client, admin_headers, result["id"])
    assert response.status_code == 409 and response.json()["error"]["code"] == "IMPORT_STALE"
    assert set(nodes(client, admin_headers)) == {"Class 12"}  # nothing from the file was added
    assert (
        client.get(f"{IMPORTS}/{result['id']}", headers=admin_headers).json()["state"]
        == "PREVIEWED"
    )
    # Uploading the file again gives a fresh preview that applies.
    assert (
        apply(client, admin_headers, preview(client, admin_headers, FILE)["id"]).status_code == 200
    )


def test_too_many_changes_at_once_are_refused(
    client: TestClient, admin_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(import_plan, "MAX_APPLY_ROWS", 3)
    monkeypatch.setattr(import_apply, "MAX_APPLY_ROWS", 3)
    result = preview(client, admin_headers, FILE)
    assert result["can_apply"] is False
    response = apply(client, admin_headers, result["id"])
    assert (
        response.status_code == 422 and "at most 3 at once" in response.json()["error"]["message"]
    )


def test_a_failure_part_way_leaves_the_syllabus_as_it_was(
    client: TestClient, admin_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    result = preview(client, admin_headers, FILE)

    def clash(*args: Any, **kwargs: Any) -> Any:
        raise Conflict("taken meanwhile", code="DUPLICATE_NAME")

    monkeypatch.setattr(concepts, "create_concept", clash)  # the last row fails
    response = apply(client, admin_headers, result["id"])
    assert response.status_code == 409 and response.json()["error"]["code"] == "IMPORT_STALE"
    assert nodes(client, admin_headers) == {}  # the three items added before it are undone too
    assert (
        client.get(f"{IMPORTS}/{result['id']}", headers=admin_headers).json()["state"]
        == "PREVIEWED"
    )


def test_two_people_applying_at_once_apply_it_once(
    client: TestClient, team: dict[str, Member], admin_headers: dict[str, str]
) -> None:
    result = preview(client, admin_headers, FILE)
    owner = TestClient(client.app)
    owner_headers = sign_in(owner, team["owner"].email)
    codes: list[int] = []

    def go(browser: TestClient, headers: dict[str, str]) -> None:
        codes.append(apply(browser, headers, result["id"]).status_code)

    threads = [
        threading.Thread(target=go, args=(client, admin_headers)),
        threading.Thread(target=go, args=(owner, owner_headers)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert codes == [200, 200]
    assert len(nodes(client, admin_headers)) == 3 and len(all_concepts(client, admin_headers)) == 1


# --- Who may apply -----------------------------------------------------------------------------


def test_only_admins_and_owners_may_apply_and_only_in_their_own_coaching(
    client: TestClient, owner_db: Database, team: dict[str, Member], admin_headers: dict[str, str]
) -> None:
    result = preview(client, admin_headers, FILE)
    faculty = sign_in(TestClient(client.app), team["faculty"].email)
    assert apply(client, faculty, result["id"]).status_code == 403
    stranger = TestClient(client.app)
    stranger_headers = sign_in(stranger, make_member(owner_db, "ADMIN").email)
    assert apply(stranger, stranger_headers, result["id"]).status_code == 404
    assert nodes(client, admin_headers) == {}


def test_the_database_holds_the_applied_state_together(
    client: TestClient, owner_db: Database, team: dict[str, Member], admin_headers: dict[str, str]
) -> None:
    apply(client, admin_headers, preview(client, admin_headers, FILE)["id"])
    with owner_db.transaction(TenantContext(organization_id=team["owner"].org_id)) as session:
        count = session.scalar(
            select(func.count())
            .select_from(TaxonomyNode)
            .where(TaxonomyNode.organization_id == team["owner"].org_id)
        )
    assert count == 3
