"""M3 PR 2c-2: previewing a syllabus import file (C-03, T25). Nothing in the syllabus changes."""

import io
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from qbank.core.config import AppEnv, Settings
from qbank.core.db import Database
from qbank.core.tenancy import NO_CONTEXT, TenantContext
from qbank.main import create_app
from qbank.modules.taxonomy import import_service
from qbank.modules.taxonomy.import_file import MAX_FILE_BYTES
from tests.integration.conftest import Member, MigratedDatabase, make_member, sign_in

IMPORTS = "/api/v1/taxonomy/imports"
NODES = "/api/v1/taxonomy/nodes"
CONCEPTS = "/api/v1/taxonomy/concepts"
HEADER = "kind,path,sort,aliases,label_hi\n"
FILE = (
    HEADER
    + "CLASS,Class 11,1,,कक्षा 11\n"
    + "SUBJECT,Class 11 > Physics,1,,\n"
    + "CHAPTER,Class 11 > Physics > Kinematics,1,,\n"
    + "CONCEPT,Class 11 > Physics > Newton's second law,,Newton's 2nd law,\n"
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


def upload(
    client: TestClient,
    headers: dict[str, str],
    data: bytes | str,
    name: str = "syllabus.csv",
    **extra: str,
) -> Any:
    content = data.encode() if isinstance(data, str) else data
    return client.post(
        IMPORTS,
        content=content,
        params={"file_name": name},
        headers={**headers, "Content-Type": "application/octet-stream", **extra},
    )


def preview(client: TestClient, headers: dict[str, str], data: bytes | str) -> dict[str, Any]:
    response = upload(client, headers, data)
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


def rows_of(client: TestClient, headers: dict[str, str], import_id: str, **params: Any) -> Any:
    return client.get(f"{IMPORTS}/{import_id}/rows", params=params, headers=headers)


# --- Previewing ----------------------------------------------------------------------------------


def test_a_file_is_previewed_and_nothing_in_the_syllabus_changes(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    result = preview(client, admin_headers, FILE)

    assert result["counts"] == {"new": 4, "changed": 0, "unchanged": 0, "error": 0}
    assert (result["state"], result["can_apply"], result["file_name"]) == (
        "PREVIEWED",
        True,
        "syllabus.csv",
    )
    assert client.get(NODES, headers=admin_headers).json()["data"] == []
    assert client.get(CONCEPTS, headers=admin_headers).json()["data"] == []
    again = client.get(f"{IMPORTS}/{result['id']}", headers=admin_headers)
    assert again.status_code == 200 and again.json() == result


def test_the_rows_are_listed_in_file_order_with_a_reason_for_each_error(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    data = FILE + "CHAPTER,Class 12 > Physics > Optics,,,\nBOOK,Class 11,,,\n"
    result = preview(client, admin_headers, data)
    assert result["counts"] == {"new": 4, "changed": 0, "unchanged": 0, "error": 2}
    assert result["can_apply"] is False

    page = rows_of(client, admin_headers, result["id"]).json()["data"]
    assert [(r["number"], r["status"]) for r in page] == [
        (2, "NEW"),
        (3, "NEW"),
        (4, "NEW"),
        (5, "NEW"),
        (6, "ERROR"),
        (7, "ERROR"),
    ]
    assert page[0]["labels"] == {"hi": "कक्षा 11"} and page[0]["sort_order"] == 1
    assert page[3]["aliases"] == ["Newton's 2nd law"]
    assert "not in the syllabus and not in the file" in page[4]["message"]
    assert "not one of" in page[5]["message"]

    errors = rows_of(client, admin_headers, result["id"], status="ERROR").json()["data"]
    assert [r["number"] for r in errors] == [6, 7]


def test_the_rows_are_paged_with_a_cursor(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    lines = "".join(f"CLASS,Class {n},,,\n" for n in range(1, 8))
    result = preview(client, admin_headers, HEADER + lines)
    first = rows_of(client, admin_headers, result["id"], limit=3).json()
    assert [r["number"] for r in first["data"]] == [2, 3, 4] and first["page"]["has_more"]
    second = rows_of(
        client, admin_headers, result["id"], limit=3, cursor=first["page"]["next_cursor"]
    ).json()
    assert [r["number"] for r in second["data"]] == [5, 6, 7] and second["page"]["has_more"]
    last = rows_of(
        client, admin_headers, result["id"], limit=3, cursor=second["page"]["next_cursor"]
    ).json()
    assert [r["number"] for r in last["data"]] == [8] and not last["page"]["has_more"]
    for bad in ("not-a-cursor", "AAAA", "Ag", "AgAAAAAAAAA"):
        assert rows_of(client, admin_headers, result["id"], cursor=bad).status_code == 400


def test_a_file_that_matches_the_syllabus_shows_what_would_change(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    cls = client.post(
        NODES, json={"kind": "CLASS", "name": "class  11", "sort_order": 1}, headers=admin_headers
    ).json()
    subject = client.post(
        NODES,
        json={"kind": "SUBJECT", "parent_id": cls["id"], "name": "Physics"},
        headers=admin_headers,
    ).json()
    client.post(
        CONCEPTS,
        json={"subject_id": subject["id"], "name": "Newton's second law"},
        headers=admin_headers,
    )

    result = preview(client, admin_headers, FILE)
    # The class gets its Hindi name, the subject its sort order, the chapter is added, and the
    # concept gains an alias.
    assert result["counts"] == {"new": 1, "changed": 3, "unchanged": 0, "error": 0}
    again_statuses = [
        r["status"] for r in rows_of(client, admin_headers, result["id"]).json()["data"]
    ]
    assert again_statuses == ["CHANGED", "CHANGED", "NEW", "CHANGED"]


def test_a_spreadsheet_is_read_like_a_csv(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    workbook = Workbook()
    sheet = workbook.active
    assert sheet is not None
    sheet.append(["Kind", "Path", "Sort"])
    sheet.append(["CLASS", "Class 11", 1])
    sheet.append(["SUBJECT", "Class 11 > Physics", 2.0])
    buffer = io.BytesIO()
    workbook.save(buffer)
    result = preview(client, admin_headers, buffer.getvalue())
    assert result["counts"]["new"] == 2


def test_a_retry_with_the_same_key_returns_the_same_preview(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    key = {"Idempotency-Key": "import-retry-1"}
    first = upload(client, admin_headers, FILE, **key)
    second = upload(client, admin_headers, FILE, **key)
    assert first.status_code == second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    other = upload(client, admin_headers, FILE + "CLASS,Class 12,,,\n", **key)
    assert other.status_code == 409 and other.json()["error"]["code"] == "IDEMPOTENCY_KEY_REUSED"


# --- Files that cannot be read --------------------------------------------------------------------


@pytest.mark.parametrize(
    "data",
    [b"", b"\x89PNG\r\n\x1a\n\x00", b"kind,wat\nCLASS,x\n", b"path\nClass 11\n", b"PK\x03\x04junk"],
)
def test_a_file_that_cannot_be_read_is_refused(
    client: TestClient, admin_headers: dict[str, str], data: bytes
) -> None:
    response = upload(client, admin_headers, data)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "IMPORT_INVALID"


def test_an_oversize_file_is_refused_without_being_read_to_the_end(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    response = upload(client, admin_headers, b"kind\n" + b"CLASS\n" * MAX_FILE_BYTES)
    assert response.status_code == 422 and "larger than" in response.json()["error"]["message"]
    # Even a body whose length is not declared (sent in chunks) is cut off.
    chunks = (b"kind\n" + b"x" * 1_000_000 for _ in range(7))
    streamed = client.post(
        IMPORTS,
        content=chunks,
        params={"file_name": "big.csv"},
        headers={**admin_headers, "Content-Type": "application/octet-stream"},
    )
    assert streamed.status_code == 422 and "larger than" in streamed.json()["error"]["message"]


@pytest.mark.parametrize("name", ["", "a" * 201, "bad\x00name.csv", "two\nlines.csv"])
def test_the_file_name_is_checked(
    client: TestClient, admin_headers: dict[str, str], name: str
) -> None:
    assert upload(client, admin_headers, FILE, name=name).status_code in (400, 422)


# --- Who may import ------------------------------------------------------------------------------


def test_only_admins_and_owners_may_import(
    client: TestClient, team: dict[str, Member], admin_headers: dict[str, str]
) -> None:
    result = preview(client, admin_headers, FILE)
    faculty = sign_in(client, team["faculty"].email)
    assert upload(client, faculty, FILE).status_code == 403
    assert client.get(f"{IMPORTS}/{result['id']}", headers=faculty).status_code == 403
    assert rows_of(client, faculty, result["id"]).status_code == 403
    assert client.get("/api/v1/taxonomy/import-template", headers=faculty).status_code == 403
    owner = sign_in(client, team["owner"].email)
    assert upload(client, owner, FILE).status_code == 201
    nobody = TestClient(client.app)
    assert nobody.get(f"{IMPORTS}/{result['id']}").status_code == 401


def test_a_preview_is_invisible_to_another_coaching(
    client: TestClient, owner_db: Database, admin_headers: dict[str, str]
) -> None:
    result = preview(client, admin_headers, FILE)
    other = make_member(owner_db, "ADMIN")
    stranger = TestClient(client.app)
    other_headers = sign_in(stranger, other.email)
    assert stranger.get(f"{IMPORTS}/{result['id']}", headers=other_headers).status_code == 404
    assert rows_of(stranger, other_headers, result["id"]).status_code == 404
    # Their own syllabus is what a file is compared with, not ours.
    theirs = preview(stranger, other_headers, FILE)
    assert theirs["counts"]["new"] == 4


def test_the_template_can_be_downloaded_and_is_itself_a_valid_file(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    response = client.get("/api/v1/taxonomy/import-template", headers=admin_headers)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment" in response.headers["content-disposition"]
    assert response.content.startswith(b"\xef\xbb\xbfkind,path,sort,aliases,label_hi,label_gu,")
    result = preview(client, admin_headers, response.content)
    assert result["counts"] == {"new": 5, "changed": 0, "unchanged": 0, "error": 0}


# --- The database keeps previews as they were -----------------------------------------------------


def test_the_app_role_cannot_delete_a_preview_or_rewrite_its_rows(
    client: TestClient,
    team: dict[str, Member],
    admin_headers: dict[str, str],
    db: Database,
) -> None:
    result = preview(client, admin_headers, FILE)
    app_db = db
    context = TenantContext(organization_id=team["owner"].org_id, user_id=team["owner"].user_id)
    for statement in (
        "DELETE FROM catalogue_imports",
        "UPDATE catalogue_imports SET rows = '[]'::jsonb",
        "UPDATE catalogue_imports SET counts = '{}'::jsonb",
        "UPDATE catalogue_imports SET file_name = 'other.csv'",
    ):
        with pytest.raises(DBAPIError, match="permission denied"):  # noqa: SIM117
            with app_db.transaction(context) as session:
                session.execute(text(statement))
    with app_db.transaction(context) as session:  # marking it applied is allowed
        session.execute(
            text(
                "UPDATE catalogue_imports SET state = 'APPLIED', applied_at = now() WHERE id = :id"
            ),
            {"id": UUID(result["id"])},
        )
    with pytest.raises(DBAPIError, match="catalogue_imports_check"):  # noqa: SIM117
        with app_db.transaction(context) as session:
            session.execute(text("UPDATE catalogue_imports SET applied_at = NULL"))


# --- The syllabus is read as it was at one moment ----------------------------------------


def test_a_repeatable_read_transaction_ignores_what_is_committed_after_it_starts(
    db: Database, owner_db: Database, team: dict[str, Member]
) -> None:
    context = TenantContext(organization_id=team["owner"].org_id, user_id=team["owner"].user_id)
    count = text("SELECT count(*) FROM taxonomy_nodes")
    with db.transaction(context, isolation_level="REPEATABLE READ") as session:
        assert session.scalar(count) == 0
        with owner_db.transaction(context) as other:  # another request commits meanwhile
            other.execute(
                text(
                    "INSERT INTO taxonomy_nodes (id, organization_id, kind, name, name_key)"
                    " VALUES (gen_random_uuid(), :org, 'CLASS', 'Class 11', 'class 11')"
                ),
                {"org": team["owner"].org_id},
            )
        assert session.scalar(count) == 0
    with db.transaction(context) as session:
        assert session.scalar(count) == 1


def test_a_preview_reads_the_syllabus_in_one_repeatable_read_transaction(
    client: TestClient, admin_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    levels: list[str | None] = []
    original = Database.transaction

    def spy(self: Database, context: TenantContext, *, isolation_level: str | None = None) -> Any:
        levels.append(isolation_level)
        return original(self, context, isolation_level=isolation_level)

    monkeypatch.setattr(Database, "transaction", spy)
    preview(client, admin_headers, FILE)
    assert "REPEATABLE READ" in levels


# --- Limits on uploading (K-10a, ADR-0018) -------------------------------------------------------


@contextmanager
def limited_client(migrated_database: MigratedDatabase, **limits: int) -> Iterator[TestClient]:
    settings = Settings(
        app_env=AppEnv.TEST,
        database_url=migrated_database.app_url,
        session_cookie_secure=False,
        **limits,
    )
    with TestClient(create_app(settings)) as test_client:
        yield test_client


def test_a_user_may_upload_only_a_few_files_in_a_short_time(
    migrated_database: MigratedDatabase, team: dict[str, Member]
) -> None:
    with limited_client(migrated_database, import_uploads_per_user=3) as client:
        admin = sign_in(client, team["admin"].email)
        assert [upload(client, admin, FILE).status_code for _ in range(3)] == [201, 201, 201]

        refused = upload(client, admin, FILE)
        assert refused.status_code == 429
        assert refused.json()["error"]["code"] == "RATE_LIMITED"
        assert 1 <= int(refused.headers["Retry-After"]) <= 600

        # Another person is not held back by it, and reading an earlier preview is not limited.
        other = TestClient(client.app)  # its own sign-in, apart from the admin's
        owner = sign_in(other, team["owner"].email)
        earlier = preview(other, owner, FILE)["id"]
        assert other.get(f"{IMPORTS}/{earlier}", headers=owner).status_code == 200
        assert client.get(f"{IMPORTS}/{earlier}", headers=admin).status_code == 200


def test_people_who_may_not_import_are_refused_before_the_limit_counts_them(
    migrated_database: MigratedDatabase, team: dict[str, Member]
) -> None:
    with limited_client(migrated_database, import_uploads_per_user=1) as client:
        faculty = sign_in(client, team["faculty"].email)
        assert [upload(client, faculty, FILE).status_code for _ in range(3)] == [403, 403, 403]


def test_only_a_few_files_are_read_at_the_same_time_and_the_rest_are_turned_away(
    migrated_database: MigratedDatabase,
    team: dict[str, Member],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    started, release = threading.Event(), threading.Event()
    real_read = import_service.read_table

    def slow_read(data: bytes) -> Any:
        started.set()
        assert release.wait(timeout=30)
        return real_read(data)

    monkeypatch.setattr(import_service, "read_table", slow_read)
    with limited_client(migrated_database, import_parses_at_once=1) as client:
        other = TestClient(client.app)  # its own sign-in, apart from the admin's
        admin = sign_in(client, team["admin"].email)
        owner = sign_in(other, team["owner"].email)
        first: list[Any] = []

        def first_upload() -> None:
            try:
                first.append(upload(client, admin, FILE))
            except BaseException as error:  # shown by the assertion below, not lost in the thread
                first.append(error)

        worker = threading.Thread(target=first_upload)
        worker.start()
        try:
            assert started.wait(timeout=30), first  # the first file is being read now

            busy = upload(other, owner, FILE)  # a different person, at the same moment
            assert busy.status_code == 429 and busy.json()["error"]["code"] == "RATE_LIMITED"
            assert busy.headers["Retry-After"] == "5"
            assert "busy" in busy.json()["error"]["message"]
        finally:
            release.set()
            worker.join(timeout=30)
        assert first[0].status_code == 201  # the first one was not harmed

        # The place is free again once the first has finished.
        assert upload(other, owner, FILE).status_code == 201


def test_a_place_is_freed_when_the_file_turns_out_to_be_unreadable(
    migrated_database: MigratedDatabase, team: dict[str, Member]
) -> None:
    with limited_client(migrated_database, import_parses_at_once=1) as client:
        admin = sign_in(client, team["admin"].email)
        for _ in range(
            3
        ):  # each failure must give its place back, or the next would be turned away
            assert upload(client, admin, b"PK\x03\x04junk").status_code == 422
        assert upload(client, admin, FILE).status_code == 201


# --- Previews that are never applied do not pile up (K-10b, ADR-0018) -----------------------------

OTHER_FILE = "kind,path\nCLASS,Class 12\n"


def states_of(db: Database, org_id: UUID, user_id: UUID) -> dict[str, int]:
    """How many previews of a coaching are in each state, and how many still hold their rows."""
    context = TenantContext(organization_id=org_id, user_id=user_id)
    with db.transaction(context) as session:
        found = session.execute(
            text(
                "SELECT state, count(*), count(*) FILTER (WHERE jsonb_array_length(rows) > 0)"
                " FROM catalogue_imports WHERE organization_id = :org GROUP BY state"
            ),
            {"org": org_id},  # asked for by name: an owner connection may see every coaching
        ).all()
    return {f"{state}": count for state, count, _ in found} | {
        f"{state}+rows": with_rows for state, _, with_rows in found
    }


def test_only_the_newest_twenty_unapplied_previews_keep_their_rows(
    migrated_database: MigratedDatabase, team: dict[str, Member], owner_db: Database
) -> None:
    with limited_client(migrated_database, import_uploads_per_user=100) as client:
        admin = sign_in(client, team["admin"].email)
        ids = [preview(client, admin, FILE)["id"] for _ in range(23)]

        counts = states_of(owner_db, team["owner"].org_id, team["owner"].user_id)
        assert counts["PREVIEWED"] == 20 and counts["PREVIEWED+rows"] == 20
        assert counts["EXPIRED"] == 3 and counts["EXPIRED+rows"] == 0

        # An expired preview is gone as far as the API is concerned: 410, with a message that says
        # what to do. (Its small record stays in the database: who, when, the counts.)
        for gone in (
            client.get(f"{IMPORTS}/{ids[0]}", headers=admin),
            rows_of(client, admin, ids[0]),
            client.post(f"{IMPORTS}/{ids[0]}/apply", headers=admin),
        ):
            assert gone.status_code == 410 and gone.json()["error"]["code"] == "IMPORT_EXPIRED"
            assert "Upload the file again" in gone.json()["error"]["message"]
        newest = client.get(f"{IMPORTS}/{ids[-1]}", headers=admin).json()
        assert newest["state"] == "PREVIEWED" and newest["can_apply"] is True
        assert client.post(f"{IMPORTS}/{ids[-1]}/apply", headers=admin).status_code == 200


def test_an_applied_preview_keeps_its_rows_however_many_come_after(
    migrated_database: MigratedDatabase, team: dict[str, Member], owner_db: Database
) -> None:
    with limited_client(migrated_database, import_uploads_per_user=100) as client:
        admin = sign_in(client, team["admin"].email)
        applied = preview(client, admin, FILE)["id"]
        assert client.post(f"{IMPORTS}/{applied}/apply", headers=admin).status_code == 200
        context = TenantContext(organization_id=team["owner"].org_id, user_id=team["owner"].user_id)
        with owner_db.transaction(context) as session:  # a year old: age must not matter to it
            session.execute(
                text("UPDATE catalogue_imports SET created_at = now() - interval '400 days'")
            )
        for _ in range(25):
            assert upload(client, admin, OTHER_FILE).status_code == 201

        again = client.get(f"{IMPORTS}/{applied}", headers=admin).json()
        assert again["state"] == "APPLIED"
        assert len(rows_of(client, admin, applied).json()["data"]) > 0
        counts = states_of(owner_db, team["owner"].org_id, team["owner"].user_id)
        assert counts["APPLIED+rows"] == 1 and counts["PREVIEWED"] == 20


def test_a_preview_older_than_thirty_days_is_expired_and_cannot_be_applied(
    client: TestClient, admin_headers: dict[str, str], team: dict[str, Member], owner_db: Database
) -> None:
    old = preview(client, admin_headers, FILE)["id"]
    recent = preview(client, admin_headers, OTHER_FILE)["id"]
    context = TenantContext(organization_id=team["owner"].org_id, user_id=team["owner"].user_id)
    with owner_db.transaction(context) as session:
        session.execute(
            text(
                "UPDATE catalogue_imports SET created_at = now() - interval '31 days' WHERE id = :i"
            ),
            {"i": UUID(old)},
        )
    # Not yet swept, but already gone as far as the API is concerned.
    for gone in (
        client.get(f"{IMPORTS}/{old}", headers=admin_headers),
        rows_of(client, admin_headers, old),
        client.post(f"{IMPORTS}/{old}/apply", headers=admin_headers),
    ):
        assert gone.status_code == 410 and gone.json()["error"]["code"] == "IMPORT_EXPIRED"
    # A refused apply writes nothing; the next upload drops its rows.
    assert states_of(owner_db, team["owner"].org_id, team["owner"].user_id)["PREVIEWED"] == 2
    assert upload(client, admin_headers, FILE).status_code == 201
    counts = states_of(owner_db, team["owner"].org_id, team["owner"].user_id)
    assert counts["EXPIRED"] == 1 and counts["EXPIRED+rows"] == 0
    assert client.post(f"{IMPORTS}/{recent}/apply", headers=admin_headers).status_code == 200


def test_another_coachings_previews_are_never_touched(
    migrated_database: MigratedDatabase,
    team: dict[str, Member],
    owner_db: Database,
    db: Database,
) -> None:
    neighbour = make_member(owner_db, "OWNER", coaching_name="Neighbour Coaching")
    with limited_client(migrated_database, import_uploads_per_user=100) as client:
        other = TestClient(client.app)
        theirs = sign_in(other, neighbour.email)
        for _ in range(3):
            preview(other, theirs, FILE)
        admin = sign_in(client, team["admin"].email)
        for _ in range(23):
            preview(client, admin, FILE)

        assert states_of(owner_db, neighbour.org_id, neighbour.user_id) == {
            "PREVIEWED": 3,
            "PREVIEWED+rows": 3,
        }
        # The function itself, called straight from the runtime role, only reaches the caller's own
        # coaching, and does nothing at all without one.
        mine = TenantContext(organization_id=neighbour.org_id, user_id=neighbour.user_id)
        with db.transaction(mine) as session:
            assert session.scalar(text("SELECT catalogue_imports_expire(0, 0)")) == 3
        assert states_of(owner_db, team["owner"].org_id, team["owner"].user_id)["PREVIEWED"] == 20
        with db.transaction(NO_CONTEXT) as session:
            assert session.scalar(text("SELECT catalogue_imports_expire(0, 0)")) == 0
        assert states_of(owner_db, team["owner"].org_id, team["owner"].user_id)["PREVIEWED"] == 20


def test_the_expiry_function_cannot_be_used_to_rewrite_or_delete_anything_else(
    migrated_database: MigratedDatabase, team: dict[str, Member], owner_db: Database, db: Database
) -> None:
    with limited_client(migrated_database, import_uploads_per_user=100) as client:
        admin = sign_in(client, team["admin"].email)
        applied = preview(client, admin, FILE)["id"]
        client.post(f"{IMPORTS}/{applied}/apply", headers=admin)
        context = TenantContext(organization_id=team["owner"].org_id, user_id=team["owner"].user_id)
        with db.transaction(context) as session:  # even asked to expire everything, now
            session.execute(text("SELECT catalogue_imports_expire(0, 0)"))
        counts = states_of(owner_db, team["owner"].org_id, team["owner"].user_id)
        assert counts == {"APPLIED": 1, "APPLIED+rows": 1}


def test_two_uploads_at_once_cannot_both_find_room_and_leave_more_than_twenty(
    migrated_database: MigratedDatabase,
    team: dict[str, Member],
    owner_db: Database,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_sweep = import_service.expire_old_previews

    def slow_sweep(*args: Any, **kwargs: Any) -> int:
        expired = real_sweep(*args, **kwargs)
        threading.Event().wait(0.6)  # widen the gap between "making room" and "inserting"
        return expired

    with limited_client(
        migrated_database, import_uploads_per_user=100, import_parses_at_once=2
    ) as client:
        other = TestClient(client.app)
        admin, owner = sign_in(client, team["admin"].email), sign_in(other, team["owner"].email)
        for _ in range(19):  # one short of full
            preview(client, admin, FILE)
        monkeypatch.setattr(import_service, "expire_old_previews", slow_sweep)
        codes: list[int] = []

        def go(browser: TestClient, headers: dict[str, str]) -> None:
            codes.append(upload(browser, headers, FILE).status_code)

        threads = [
            threading.Thread(target=go, args=(client, admin)),
            threading.Thread(target=go, args=(other, owner)),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=60)

        assert codes == [201, 201]
        counts = states_of(owner_db, team["owner"].org_id, team["owner"].user_id)
        assert counts["PREVIEWED"] == 20 and counts["PREVIEWED+rows"] == 20
        assert counts["EXPIRED"] == 1
