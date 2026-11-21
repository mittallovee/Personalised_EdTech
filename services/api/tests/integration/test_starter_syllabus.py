"""C-14 (ADR-0022): loading a built-in starter syllabus through the import preview."""

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from qbank.core.config import AppEnv, Settings
from qbank.core.db import Database
from qbank.core.tenancy import TenantContext
from qbank.main import create_app
from qbank.modules.audit.models import AuditEvent
from qbank.modules.taxonomy import starter_syllabus
from qbank.modules.taxonomy.models import Concept, TaxonomyNode
from tests.integration.conftest import Member, MigratedDatabase, make_member, sign_in

STARTERS = "/api/v1/taxonomy/starter-syllabuses"
IMPORTS = "/api/v1/taxonomy/imports"
PHYSICS_ROWS = starter_syllabus.row_count(starter_syllabus.find("jee-physics"))
CHEMISTRY_ROWS = starter_syllabus.row_count(starter_syllabus.find("jee-chemistry"))


def app_settings(migrated_database: MigratedDatabase, **limits: int) -> Settings:
    return Settings(
        app_env=AppEnv.TEST,
        database_url=migrated_database.app_url,
        session_cookie_secure=False,
        **limits,
    )


@pytest.fixture
def client(migrated_database: MigratedDatabase) -> Iterator[TestClient]:
    with TestClient(create_app(app_settings(migrated_database))) as test_client:
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


def preview(client: TestClient, headers: dict[str, str], key: str, **extra: str) -> Any:
    return client.post(f"{STARTERS}/{key}/imports", headers={**headers, **extra})


def apply(client: TestClient, headers: dict[str, str], import_id: str) -> Any:
    return client.post(f"{IMPORTS}/{import_id}/apply", headers=headers)


def syllabus_size(db: Database, org_id: Any) -> tuple[int, int]:
    """How many syllabus items and concepts the coaching has."""
    with db.transaction(TenantContext(organization_id=org_id)) as session:
        nodes = session.scalar(select(func.count()).select_from(TaxonomyNode))
        concepts = session.scalar(select(func.count()).select_from(Concept))
        return nodes or 0, concepts or 0


def test_the_starters_are_listed_with_their_size(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    response = client.get(STARTERS, headers=admin_headers)
    assert response.status_code == 200
    listed = response.json()
    assert [item["key"] for item in listed] == ["jee-physics", "jee-chemistry", "jee-mathematics"]
    assert listed[0]["title"] == "JEE Physics (Class 11 and 12)"
    assert listed[0]["rows"] == PHYSICS_ROWS
    assert all(item["description"] for item in listed)


def test_a_starter_is_previewed_and_nothing_in_the_syllabus_changes(
    client: TestClient, db: Database, team: dict[str, Member], admin_headers: dict[str, str]
) -> None:
    response = preview(client, admin_headers, "jee-physics")
    assert response.status_code == 201, response.text
    body = response.json()
    assert response.headers["Location"] == f"{IMPORTS}/{body['id']}"
    assert body["file_name"] == "Built-in: JEE Physics (Class 11 and 12)"
    assert body["state"] == "PREVIEWED" and body["can_apply"] is True
    assert body["counts"] == {"new": PHYSICS_ROWS, "changed": 0, "unchanged": 0, "error": 0}
    assert syllabus_size(db, team["admin"].org_id) == (0, 0)
    # It is an ordinary preview: its rows are read like those of an uploaded file.
    rows = client.get(f"{IMPORTS}/{body['id']}/rows", params={"limit": 2}, headers=admin_headers)
    assert [row["path"] for row in rows.json()["data"]] == ["Class 11", "Class 11 > Physics"]


def test_applying_a_starter_adds_it_once_and_loading_it_again_changes_nothing(
    client: TestClient, db: Database, team: dict[str, Member], admin_headers: dict[str, str]
) -> None:
    first = preview(client, admin_headers, "jee-physics").json()
    applied = apply(client, admin_headers, first["id"])
    assert applied.status_code == 200, applied.text
    assert applied.json()["state"] == "APPLIED"
    nodes, concepts = syllabus_size(db, team["admin"].org_id)
    assert nodes + concepts == PHYSICS_ROWS and concepts > 0

    again = preview(client, admin_headers, "jee-physics").json()
    assert again["counts"] == {"new": 0, "changed": 0, "unchanged": PHYSICS_ROWS, "error": 0}
    assert again["can_apply"] is False

    with db.transaction(TenantContext(organization_id=team["admin"].org_id)) as session:
        events = session.scalars(
            select(AuditEvent).where(AuditEvent.action == "CATALOGUE_IMPORT_APPLIED")
        ).all()
    assert [event.actor_user_id for event in events] == [team["admin"].user_id]


def test_a_second_subject_shares_the_classes_of_the_first(
    client: TestClient, db: Database, team: dict[str, Member], admin_headers: dict[str, str]
) -> None:
    physics = preview(client, admin_headers, "jee-physics").json()
    assert apply(client, admin_headers, physics["id"]).status_code == 200
    chemistry = preview(client, admin_headers, "jee-chemistry").json()
    # "Class 11" and "Class 12" are already there; everything else of chemistry is new.
    assert chemistry["counts"] == {
        "new": CHEMISTRY_ROWS - 2,
        "changed": 0,
        "unchanged": 2,
        "error": 0,
    }
    assert apply(client, admin_headers, chemistry["id"]).status_code == 200
    nodes, concepts = syllabus_size(db, team["admin"].org_id)
    assert nodes + concepts == PHYSICS_ROWS + CHEMISTRY_ROWS - 2


def test_only_admins_and_owners_may_see_or_load_a_starter(
    client: TestClient, team: dict[str, Member]
) -> None:
    faculty = sign_in(client, team["faculty"].email)
    assert client.get(STARTERS, headers=faculty).status_code == 403
    assert preview(client, faculty, "jee-physics").status_code == 403
    owner = sign_in(client, team["owner"].email)
    assert client.get(STARTERS, headers=owner).status_code == 200
    assert preview(client, owner, "jee-physics").status_code == 201
    nobody = TestClient(client.app)
    assert nobody.get(STARTERS).status_code == 401
    assert nobody.post(f"{STARTERS}/jee-physics/imports").status_code in (401, 403)


def test_a_starter_preview_belongs_to_the_coaching_that_asked_for_it(
    client: TestClient, db: Database, owner_db: Database, admin_headers: dict[str, str]
) -> None:
    ours = preview(client, admin_headers, "jee-physics").json()
    other = make_member(owner_db, "ADMIN")
    stranger = TestClient(client.app)
    other_headers = sign_in(stranger, other.email)
    assert stranger.get(f"{IMPORTS}/{ours['id']}", headers=other_headers).status_code == 404
    assert apply(stranger, other_headers, ours["id"]).status_code == 404
    assert syllabus_size(db, other.org_id) == (0, 0)


def test_an_unknown_starter_is_not_found(client: TestClient, admin_headers: dict[str, str]) -> None:
    missing = preview(client, admin_headers, "neet-biology")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "NOT_FOUND"
    # A key is lower-case letters, digits and dashes; anything else never reaches the files.
    assert preview(client, admin_headers, "..%2Fsecrets").status_code == 404
    malformed = preview(client, admin_headers, "JEE Physics")
    assert malformed.status_code == 400
    assert malformed.json()["error"]["code"] == "MALFORMED_REQUEST"


def test_a_retry_with_the_same_key_returns_the_same_preview(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    key = {"Idempotency-Key": "starter-retry-1"}
    first = preview(client, admin_headers, "jee-physics", **key).json()
    second = preview(client, admin_headers, "jee-physics", **key).json()
    assert first["id"] == second["id"]
    reused = preview(client, admin_headers, "jee-chemistry", **key)
    assert reused.status_code == 409
    assert reused.json()["error"]["code"] == "IDEMPOTENCY_KEY_REUSED"


def test_starter_previews_count_towards_the_upload_limit_but_refusals_do_not(
    migrated_database: MigratedDatabase, team: dict[str, Member]
) -> None:
    settings = app_settings(migrated_database, import_uploads_per_user=2)
    with TestClient(create_app(settings)) as client:
        admin = sign_in(client, team["admin"].email)
        assert preview(client, admin, "neet-biology").status_code == 404  # uses up nothing
        assert [preview(client, admin, "jee-physics").status_code for _ in range(2)] == [201, 201]
        refused = preview(client, admin, "jee-physics")
        assert refused.status_code == 429
        assert refused.json()["error"]["code"] == "RATE_LIMITED"
        assert int(refused.headers["Retry-After"]) >= 1
        upload = client.post(
            IMPORTS,
            content=b"kind,path\nCLASS,Class 11\n",
            params={"file_name": "syllabus.csv"},
            headers={**admin, "Content-Type": "application/octet-stream"},
        )
        assert upload.status_code == 429  # one limit for uploads and starters together
