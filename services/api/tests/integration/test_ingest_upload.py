"""M6 PR 6b: uploading documents (T56, T57; threat model U8, U10, U11).

The API only receives bytes, decides the kind from the first few, keeps the original and queues one
render job. It never opens a document. Faculty see their own uploads, admins everyone's, another
coaching nothing.
"""

import hashlib
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from qbank.core.config import AppEnv, Settings
from qbank.core.db import Database
from qbank.core.tenancy import TenantContext
from qbank.main import create_app
from tests.integration.conftest import Member, MigratedDatabase, make_member, sign_in
from tests.unit.test_ingest_filetype import HEADS

FILES = "/api/v1/ingest/files"


def document(kind: str, tail: bytes = b"") -> bytes:
    return HEADS[kind] + b"body of " + kind.encode() + tail


@pytest.fixture
def storage_dir(tmp_path: Path) -> Path:
    return tmp_path / "storage"


def settings_for(migrated: MigratedDatabase, storage_dir: Path, **limits: int) -> Settings:
    return Settings(
        app_env=AppEnv.TEST,
        database_url=migrated.app_url,
        session_cookie_secure=False,
        storage_dir=storage_dir,
        **limits,
    )


@pytest.fixture
def client(migrated_database: MigratedDatabase, storage_dir: Path) -> Iterator[TestClient]:
    with TestClient(create_app(settings_for(migrated_database, storage_dir))) as test_client:
        yield test_client


@pytest.fixture
def team(owner_db: Database) -> dict[str, Member]:
    owner = make_member(owner_db, "OWNER")
    return {
        "owner": owner,
        "faculty": make_member(owner_db, "FACULTY", org_id=owner.org_id),
        "colleague": make_member(owner_db, "FACULTY", org_id=owner.org_id),
        "stranger": make_member(owner_db, "FACULTY"),
    }


def headers_of(client: TestClient, member: Member) -> dict[str, str]:
    return sign_in(client, member.email)


def upload(
    client: TestClient,
    headers: dict[str, str],
    data: bytes,
    name: str = "paper.pdf",
    content_type: str = "application/octet-stream",
) -> Any:
    return client.post(
        FILES,
        params={"file_name": name},
        content=data,
        headers={**headers, "Content-Type": content_type},
    )


def jobs_for(owner_db: Database, file_id: str) -> list[Any]:
    with owner_db.transaction(TenantContext(is_platform=True)) as session:
        return list(
            session.execute(
                text(
                    "SELECT type, state, organization_id FROM jobs WHERE payload->>'file_id' = :f"
                ),
                {"f": file_id},
            )
        )


@pytest.mark.parametrize("kind", ["PDF", "DOCX", "JPEG", "PNG", "WEBP", "HEIC"])
def test_each_kind_is_kept_as_sent_and_one_render_job_is_queued(
    client: TestClient, team: dict[str, Member], owner_db: Database, storage_dir: Path, kind: str
) -> None:
    headers = headers_of(client, team["faculty"])
    data = document(kind)
    response = upload(client, headers, data, name=f"a {kind}.bin")
    assert response.status_code == 201, response.text
    body = response.json()
    assert (body["kind"], body["state"], body["byte_size"]) == (kind, "UPLOADED", len(data))
    assert body["duplicate_of"] is None
    # The original is on disk exactly as sent, under a key made by us.
    stored = next((storage_dir / "org").rglob(body["id"]))
    assert stored.read_bytes() == data
    assert f"org/{team['faculty'].org_id}/ingest/{body['id']}" in stored.as_posix()
    # One job, in the right coaching, of the type only the sandbox takes.
    jobs = jobs_for(owner_db, body["id"])
    assert [(j.type, j.state, j.organization_id) for j in jobs] == [
        ("ingest.render", "QUEUED", team["faculty"].org_id)
    ]


def test_the_kind_comes_from_the_bytes_never_from_the_name_or_the_declared_type(
    client: TestClient, team: dict[str, Member]
) -> None:
    headers = headers_of(client, team["faculty"])
    wrongly_named = upload(
        client, headers, document("PNG"), name="exam.pdf", content_type="text/html"
    )
    assert wrongly_named.status_code == 201
    assert wrongly_named.json()["kind"] == "PNG"
    program = upload(
        client, headers, b"MZ\x90\x00 a program", name="paper.pdf", content_type="application/pdf"
    )
    assert program.status_code == 422
    assert program.json()["error"]["code"] == "INGEST_FILE_INVALID"
    assert upload(client, headers, b"", name="empty.pdf").status_code == 422


def test_nothing_is_stored_or_queued_for_a_refused_file(
    client: TestClient, team: dict[str, Member], owner_db: Database, storage_dir: Path
) -> None:
    headers = headers_of(client, team["faculty"])
    assert upload(client, headers, b"<svg onload=alert(1)>").status_code == 422
    assert not [p for p in storage_dir.rglob("*") if p.is_file()]
    with owner_db.transaction(TenantContext(is_platform=True)) as session:
        assert (
            session.scalar(
                text("SELECT count(*) FROM ingest_files WHERE organization_id = :o"),
                {"o": team["faculty"].org_id},
            )
            == 0
        )


def test_a_picture_larger_than_10_mb_and_a_document_larger_than_the_limit_are_refused(
    client: TestClient, team: dict[str, Member], monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = headers_of(client, team["faculty"])
    big_picture = document("PNG", b"x" * (10 * 1024 * 1024))
    too_big = upload(client, headers, big_picture, name="photo.png")
    assert too_big.status_code == 413
    assert too_big.json()["error"]["code"] == "INGEST_FILE_TOO_LARGE"
    monkeypatch.setattr("qbank.modules.ingestion.api.MAX_DOCUMENT_BYTES", 1000)
    long_pdf = upload(client, headers, document("PDF", b"y" * 2000))
    assert long_pdf.status_code == 413  # stopped while reading, before the kind was even looked at


def test_a_person_may_upload_only_so_many_files_in_a_short_time(
    migrated_database: MigratedDatabase, storage_dir: Path, team: dict[str, Member]
) -> None:
    settings = settings_for(migrated_database, storage_dir, ingest_uploads_per_user=2)
    with TestClient(create_app(settings)) as limited:
        headers = headers_of(limited, team["faculty"])
        assert upload(limited, headers, document("PDF", b"1")).status_code == 201
        assert upload(limited, headers, document("PDF", b"2")).status_code == 201
        third = upload(limited, headers, document("PDF", b"3"))
        assert third.status_code == 429
        assert int(third.headers["retry-after"]) >= 1
        # Someone else is not held back by it.
        other = headers_of(limited, team["colleague"])
        assert upload(limited, other, document("PDF", b"4")).status_code == 201


def test_a_coaching_may_have_only_so_many_documents_waiting(
    migrated_database: MigratedDatabase, storage_dir: Path, team: dict[str, Member]
) -> None:
    settings = settings_for(migrated_database, storage_dir, ingest_files_in_flight=2)
    with TestClient(create_app(settings)) as limited:
        headers = headers_of(limited, team["faculty"])
        for n in range(2):
            assert upload(limited, headers, document("PDF", bytes([n]))).status_code == 201
        refused = upload(limited, headers, document("PDF", b"more"))
        assert refused.status_code == 409
        assert refused.json()["error"]["code"] == "INGEST_TOO_MANY_IN_FLIGHT"
        # Another coaching has its own room.
        stranger = headers_of(limited, team["stranger"])
        assert upload(limited, stranger, document("PDF", b"mine")).status_code == 201


def test_the_same_bytes_twice_are_both_kept_and_the_second_names_the_first(
    client: TestClient, team: dict[str, Member]
) -> None:
    headers = headers_of(client, team["faculty"])
    first = upload(client, headers, document("PDF", b"same")).json()
    second = upload(client, headers, document("PDF", b"same")).json()
    assert second["id"] != first["id"] and second["duplicate_of"] == first["id"]
    # A coaching never learns of another's file this way.
    stranger = headers_of(client, team["stranger"])
    other = upload(client, stranger, document("PDF", b"same")).json()
    assert other["duplicate_of"] is None


def test_faculty_see_their_own_uploads_admins_see_all_and_nobody_sees_another_coachings(
    client: TestClient, team: dict[str, Member]
) -> None:
    mine = upload(client, headers_of(client, team["faculty"]), document("PDF", b"a")).json()
    theirs = upload(client, headers_of(client, team["colleague"]), document("PDF", b"b")).json()
    faculty = headers_of(client, team["faculty"])
    seen = {f["id"] for f in client.get(FILES, headers=faculty).json()["data"]}
    assert seen == {mine["id"]}
    assert client.get(f"{FILES}/{theirs['id']}", headers=faculty).status_code == 404
    assert client.get(f"{FILES}/{theirs['id']}/original", headers=faculty).status_code == 404
    owner = headers_of(client, team["owner"])
    everyone = {f["id"] for f in client.get(FILES, headers=owner).json()["data"]}
    assert everyone == {mine["id"], theirs["id"]}
    stranger = headers_of(client, team["stranger"])
    assert client.get(FILES, headers=stranger).json()["data"] == []
    assert client.get(f"{FILES}/{mine['id']}", headers=stranger).status_code == 404


def test_the_list_is_newest_first_in_pages_and_can_be_filtered_by_state(
    client: TestClient, team: dict[str, Member]
) -> None:
    headers = headers_of(client, team["faculty"])
    ids = [upload(client, headers, document("PDF", bytes([n]))).json()["id"] for n in range(3)]
    first = client.get(FILES, params={"limit": 2}, headers=headers).json()
    assert [f["id"] for f in first["data"]] == [ids[2], ids[1]]
    assert first["page"]["has_more"] is True
    rest = client.get(
        FILES, params={"limit": 2, "cursor": first["page"]["next_cursor"]}, headers=headers
    ).json()
    assert [f["id"] for f in rest["data"]] == [ids[0]] and rest["page"]["has_more"] is False
    assert client.get(FILES, params={"state": "DONE"}, headers=headers).json()["data"] == []
    assert client.get(FILES, params={"state": "NOPE"}, headers=headers).status_code == 400


def test_the_original_comes_back_only_as_a_download_with_a_type_we_fixed(
    client: TestClient, team: dict[str, Member]
) -> None:
    headers = headers_of(client, team["faculty"])
    data = document("PNG")
    made = upload(client, headers, data, name='my "photo".html', content_type="text/html").json()
    got = client.get(f"{FILES}/{made['id']}/original", headers=headers)
    assert got.status_code == 200 and got.content == data
    assert got.headers["content-type"] == "image/png"  # from the kind, not the upload or the name
    assert got.headers["content-disposition"].startswith("attachment; filename*=UTF-8''")
    assert got.headers["x-content-type-options"] == "nosniff"
    assert "sandbox" in got.headers["content-security-policy"]
    assert got.headers["etag"] == f'"{hashlib.sha256(data).hexdigest()}"'


def test_the_name_is_cleaned_and_never_part_of_the_stored_key(
    client: TestClient, team: dict[str, Member], storage_dir: Path
) -> None:
    headers = headers_of(client, team["faculty"])
    made = upload(client, headers, document("PDF"), name="../../etc/passwd\x00.pdf").json()
    assert made["file_name"] == "passwd.pdf"
    assert not (storage_dir.parent / "etc").exists()
    assert all("passwd" not in p.as_posix() for p in storage_dir.rglob("*"))


def test_signing_in_is_required(client: TestClient) -> None:
    assert client.post(
        FILES, params={"file_name": "a.pdf"}, content=document("PDF")
    ).status_code in (
        401,
        403,
    )
    assert client.get(FILES).status_code == 401


def test_the_sandbox_role_may_change_only_the_state_columns_of_its_own_coachings_files(
    client: TestClient,
    team: dict[str, Member],
    migrated_database: MigratedDatabase,
) -> None:
    made = upload(client, headers_of(client, team["faculty"]), document("PDF")).json()
    sandbox = Database(migrated_database.ingest_url)
    org = team["faculty"].org_id
    try:
        with sandbox.transaction(TenantContext(organization_id=org)) as session:
            assert (
                session.execute(
                    text("UPDATE ingest_files SET state = 'RENDERING' WHERE id = :i"),
                    {"i": made["id"]},
                ).rowcount
                == 1
            )
        for column in ("file_name", "sha256", "storage_key", "uploaded_by", "kind"):
            with (
                pytest.raises(ProgrammingError, match="permission denied"),
                sandbox.transaction(TenantContext(organization_id=org)) as session,
            ):
                session.execute(text(f"UPDATE ingest_files SET {column} = {column}"))  # noqa: S608
        with (
            pytest.raises(ProgrammingError, match="permission denied"),
            sandbox.transaction(TenantContext(organization_id=org)) as session,
        ):
            session.execute(text("DELETE FROM ingest_files"))
        # Working for another coaching it sees nothing of this one: row-level security binds it too.
        other = team["stranger"].org_id
        with sandbox.transaction(TenantContext(organization_id=other)) as session:
            assert session.scalar(text("SELECT count(*) FROM ingest_files")) == 0
            assert session.execute(text("UPDATE ingest_files SET state = 'DONE'")).rowcount == 0
    finally:
        sandbox.dispose()


def test_an_id_that_is_not_ours_is_not_found(client: TestClient, team: dict[str, Member]) -> None:
    headers = headers_of(client, team["faculty"])
    unknown = UUID(int=7)
    assert client.get(f"{FILES}/{unknown}", headers=headers).status_code == 404
    assert client.get(f"{FILES}/{unknown}/original", headers=headers).status_code == 404
