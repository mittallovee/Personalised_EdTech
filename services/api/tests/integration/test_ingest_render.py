"""M6 PR 6c/6d, tests T58 and T60: the sandboxed worker turns originals into pages, safely.

Each test uploads a made-up document through the API and runs the sandbox worker (with its own
restricted database role) on the queued job. A bad file ends ``FAILED`` with a code; a restart, a
retry or a cancel never loses pages and never makes one twice.
"""

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from qbank.core.config import AppEnv, Settings
from qbank.core.db import Database
from qbank.core.jobs import JobRegistry, Worker
from qbank.core.storage import LocalDiskStorage, StorageError
from qbank.core.tenancy import TenantContext
from qbank.main import create_app
from qbank.modules.ingestion.public import SANDBOX_JOB_TYPES
from qbank.modules.ingestion.render import jobs as render_jobs
from qbank.modules.ingestion.render import limits
from tests import ingest_samples as samples
from tests.integration.conftest import Member, MigratedDatabase, make_member, sign_in

FILES = "/api/v1/ingest/files"


@pytest.fixture(autouse=True)
def empty_queue(owner_db: Database) -> None:
    with owner_db.transaction(TenantContext(is_platform=True)) as session:
        session.execute(
            text("UPDATE jobs SET state = 'FAILED' WHERE state IN ('QUEUED', 'RUNNING')")
        )


@pytest.fixture
def storage_dir(tmp_path: Path) -> Path:
    return tmp_path / "storage"


@pytest.fixture
def client(migrated_database: MigratedDatabase, storage_dir: Path) -> Iterator[TestClient]:
    settings = Settings(
        app_env=AppEnv.TEST,
        database_url=migrated_database.app_url,
        session_cookie_secure=False,
        storage_dir=storage_dir,
    )
    with TestClient(create_app(settings)) as test_client:
        yield test_client


@pytest.fixture
def ingest_db(migrated_database: MigratedDatabase) -> Iterator[Database]:
    database = Database(migrated_database.ingest_url)
    yield database
    database.dispose()


@pytest.fixture
def team(owner_db: Database) -> dict[str, Member]:
    owner = make_member(owner_db, "OWNER")
    return {
        "owner": owner,
        "faculty": make_member(owner_db, "FACULTY", org_id=owner.org_id),
        "colleague": make_member(owner_db, "FACULTY", org_id=owner.org_id),
    }


def run_sandbox(ingest_db: Database, storage_dir: Path, storage: Any = None) -> int:
    registry = JobRegistry()
    render_jobs.register_jobs(registry, storage or LocalDiskStorage(storage_dir))
    return Worker(ingest_db, registry, only_types=SANDBOX_JOB_TYPES).run_until_idle()


def send(client: TestClient, member: Member, data: bytes, name: str = "paper") -> dict[str, Any]:
    made = client.post(
        FILES,
        params={"file_name": name},
        content=data,
        headers=sign_in(client, member.email),
    )
    assert made.status_code == 201, made.text
    body: dict[str, Any] = made.json()
    return body


def file_of(client: TestClient, member: Member, file_id: str) -> dict[str, Any]:
    body: dict[str, Any] = client.get(
        f"{FILES}/{file_id}", headers=sign_in(client, member.email)
    ).json()
    return body


def pages_of(client: TestClient, member: Member, file_id: str) -> list[dict[str, Any]]:
    got = client.get(f"{FILES}/{file_id}/pages", headers=sign_in(client, member.email))
    assert got.status_code == 200, got.text
    data: list[dict[str, Any]] = got.json()["data"]
    return data


def test_a_pdf_is_read_into_pages_with_pictures_and_text(
    client: TestClient,
    team: dict[str, Member],
    ingest_db: Database,
    storage_dir: Path,
) -> None:
    faculty = team["faculty"]
    sent = send(client, faculty, samples.pdf(samples.PAGE_TEXT))
    assert run_sandbox(ingest_db, storage_dir) == 1
    done = file_of(client, faculty, sent["id"])
    assert (done["state"], done["page_count"], done["error_code"]) == ("READY", 3, None)
    pages = pages_of(client, faculty, sent["id"])
    assert [p["page_no"] for p in pages] == [1, 2, 3]
    assert all(p["has_picture"] and p["state"] == "READY" for p in pages)
    assert "What is 2 + 3?" in pages[0]["text"]
    headers = sign_in(client, faculty.email)
    picture = client.get(f"{FILES}/{sent['id']}/pages/1/image", headers=headers)
    assert picture.status_code == 200 and picture.headers["content-type"] == "image/jpeg"
    assert (
        picture.content[:3] == b"\xff\xd8\xff"
        and "sandbox" in picture.headers["content-security-policy"]
    )
    thumb = client.get(f"{FILES}/{sent['id']}/pages/1/image?size=thumb", headers=headers)
    assert 0 < len(thumb.content) < len(picture.content)
    assert client.get(f"{FILES}/{sent['id']}/pages/9/image", headers=headers).status_code == 404


@pytest.mark.parametrize("fmt", ["PNG", "JPEG", "WEBP", "HEIF"])
def test_every_picture_kind_becomes_one_page(
    client: TestClient, team: dict[str, Member], ingest_db: Database, storage_dir: Path, fmt: str
) -> None:
    sent = send(client, team["faculty"], samples.picture(fmt, (200, 100)))
    run_sandbox(ingest_db, storage_dir)
    done = file_of(client, team["faculty"], sent["id"])
    assert (done["state"], done["page_count"]) == ("READY", 1)
    (page,) = pages_of(client, team["faculty"], sent["id"])
    assert (page["width"], page["height"], page["has_picture"]) == (200, 100, True)


def test_a_word_file_gives_text_pages_and_keeps_its_pictures(
    client: TestClient, team: dict[str, Member], ingest_db: Database, storage_dir: Path
) -> None:
    data = samples.docx(
        samples.paragraph("Q1")
        + samples.drawing("rId1")
        + "<w:p><m:oMath><m:r><m:t>v=u+at</m:t></m:r></m:oMath></w:p>",
        parts={"word/media/image1.png": samples.picture("PNG")},
        rels=samples.image_rels("media/image1.png"),
    )
    sent = send(client, team["faculty"], data)
    run_sandbox(ingest_db, storage_dir)
    assert file_of(client, team["faculty"], sent["id"])["state"] == "READY"
    (page,) = pages_of(client, team["faculty"], sent["id"])
    assert page["has_picture"] is False and page["figures"] == 1
    assert page["warnings"] == ["EQUATION_AS_TEXT"] and "v=u+at" in page["text"]
    # No picture to show for a text page.
    got = client.get(
        f"{FILES}/{sent['id']}/pages/1/image", headers=sign_in(client, team["faculty"].email)
    )
    assert got.status_code == 404


@pytest.mark.parametrize(
    ("data", "code"),
    [
        (b"%PDF-1.7 garbage that is no pdf", "UNREADABLE_DOCUMENT"),
        (b"PK\x03\x04 not really a zip", "UNREADABLE_DOCUMENT"),
        (
            samples.docx(parts={"x": b""}).replace(b"word/document.xml", b"word/documentXX.xml"),
            None,
        ),
        (b"\x89PNG\r\n\x1a\n" + b"\x00" * 50, "UNREADABLE_PICTURE"),
    ],
)
def test_a_bad_file_fails_with_a_code_and_the_worker_goes_on(
    client: TestClient,
    team: dict[str, Member],
    ingest_db: Database,
    storage_dir: Path,
    data: bytes,
    code: str | None,
) -> None:
    sent = send(client, team["faculty"], data)
    good = send(client, team["faculty"], samples.pdf())
    assert run_sandbox(ingest_db, storage_dir) == 2  # both jobs ran: a bad file did not stop it
    failed = file_of(client, team["faculty"], sent["id"])
    assert failed["state"] == "FAILED" and failed["error_code"] is not None
    if code is not None:
        assert failed["error_code"] == code
    assert file_of(client, team["faculty"], good["id"])["state"] == "READY"


def test_a_partly_unreadable_pdf_keeps_its_good_pages_and_says_so(
    client: TestClient, team: dict[str, Member], ingest_db: Database, storage_dir: Path
) -> None:
    sizes = [(300, 200), (50_000, 50_000), (300, 200)]  # the middle page is absurdly large
    sent = send(client, team["faculty"], samples.pdf(("a", "b", "c"), page_size=sizes))
    run_sandbox(ingest_db, storage_dir)
    done = file_of(client, team["faculty"], sent["id"])
    assert (done["state"], done["error_code"], done["page_count"]) == (
        "READY",
        "SOME_PAGES_FAILED",
        3,
    )
    pages = pages_of(client, team["faculty"], sent["id"])
    assert [(p["state"], p["error_code"]) for p in pages] == [
        ("READY", None),
        ("FAILED", "PAGE_TOO_LARGE"),
        ("READY", None),
    ]


def test_a_pdf_whose_every_page_fails_is_a_failed_file(
    client: TestClient, team: dict[str, Member], ingest_db: Database, storage_dir: Path
) -> None:
    sent = send(client, team["faculty"], samples.pdf(("a",), page_size=(50_000, 50_000)))
    run_sandbox(ingest_db, storage_dir)
    failed = file_of(client, team["faculty"], sent["id"])
    assert (failed["state"], failed["error_code"]) == ("FAILED", "NO_READABLE_PAGE")


def test_a_slow_render_fails_with_a_code_and_a_retry_finishes_it_without_doubling_pages(
    client: TestClient,
    team: dict[str, Member],
    ingest_db: Database,
    storage_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    faculty = team["faculty"]
    sent = send(client, faculty, samples.pdf(samples.PAGE_TEXT))
    monkeypatch.setattr(render_jobs, "RENDER_SECONDS", -1)  # time is already up
    run_sandbox(ingest_db, storage_dir)
    assert file_of(client, faculty, sent["id"])["error_code"] == "TOO_SLOW"
    monkeypatch.setattr(render_jobs, "RENDER_SECONDS", limits.RENDER_SECONDS)
    retried = client.post(f"{FILES}/{sent['id']}/retry", headers=sign_in(client, faculty.email))
    assert retried.status_code == 200 and retried.json()["state"] == "UPLOADED"
    run_sandbox(ingest_db, storage_dir)
    assert file_of(client, faculty, sent["id"])["state"] == "READY"
    assert [p["page_no"] for p in pages_of(client, faculty, sent["id"])] == [1, 2, 3]


class FailingOnce(LocalDiskStorage):
    """A storage that fails once while keeping the second page, like a disk that hiccups."""

    def __init__(self, root: Path) -> None:
        super().__init__(root)
        self.failed = False

    def put(self, key: str, data: bytes) -> None:
        if key.endswith("/2") and not self.failed:
            self.failed = True
            raise StorageError("the disk hiccuped")
        super().put(key, data)


def test_a_storage_fault_is_retried_not_blamed_on_the_file_and_nothing_is_made_twice(
    client: TestClient,
    team: dict[str, Member],
    ingest_db: Database,
    storage_dir: Path,
    owner_db: Database,
) -> None:
    faculty = team["faculty"]
    sent = send(client, faculty, samples.pdf(samples.PAGE_TEXT))
    storage = FailingOnce(storage_dir)
    run_sandbox(
        ingest_db, storage_dir, storage
    )  # first attempt fails on page 2, the retry is later
    assert storage.failed
    with owner_db.transaction(TenantContext(is_platform=True)) as session:
        session.execute(text("UPDATE jobs SET run_after = now() WHERE state = 'QUEUED'"))
    run_sandbox(ingest_db, storage_dir, storage)
    assert file_of(client, faculty, sent["id"])["state"] == "READY"
    assert [p["page_no"] for p in pages_of(client, faculty, sent["id"])] == [1, 2, 3]
    with owner_db.transaction(TenantContext(is_platform=True)) as session:
        count = session.scalar(
            text("SELECT count(*) FROM ingest_pages WHERE file_id = :f"), {"f": sent["id"]}
        )
    assert count == 3


def test_running_the_same_job_again_changes_nothing(
    client: TestClient,
    team: dict[str, Member],
    ingest_db: Database,
    storage_dir: Path,
    owner_db: Database,
) -> None:
    faculty = team["faculty"]
    sent = send(client, faculty, samples.pdf())
    run_sandbox(ingest_db, storage_dir)
    before = pages_of(client, faculty, sent["id"])
    with owner_db.transaction(TenantContext(is_platform=True)) as session:
        session.execute(
            text(
                "INSERT INTO jobs (id, organization_id, type, payload, state)"
                " VALUES (gen_random_uuid(), :o, 'ingest.render', CAST(:p AS jsonb), 'QUEUED')"
            ),
            {"o": faculty.org_id, "p": f'{{"file_id": "{sent["id"]}"}}'},
        )
    assert run_sandbox(ingest_db, storage_dir) == 1
    assert pages_of(client, faculty, sent["id"]) == before


def test_cancel_stops_a_waiting_document_and_keeps_nothing_half_made(
    client: TestClient, team: dict[str, Member], ingest_db: Database, storage_dir: Path
) -> None:
    faculty = team["faculty"]
    sent = send(client, faculty, samples.pdf(samples.PAGE_TEXT))
    headers = sign_in(client, faculty.email)
    cancelled = client.post(f"{FILES}/{sent['id']}/cancel", headers=headers)
    assert cancelled.status_code == 200 and cancelled.json()["state"] == "CANCELLED"
    run_sandbox(ingest_db, storage_dir)
    assert file_of(client, faculty, sent["id"])["state"] == "CANCELLED"
    assert pages_of(client, faculty, sent["id"]) == []
    headers = sign_in(client, faculty.email)  # signing in again renews the CSRF token
    again = client.post(f"{FILES}/{sent['id']}/cancel", headers=headers)
    assert again.status_code == 409 and again.json()["error"]["code"] == "INGEST_ALREADY_FINISHED"
    # A cancelled document can be read again.
    assert client.post(f"{FILES}/{sent['id']}/retry", headers=headers).status_code == 200
    run_sandbox(ingest_db, storage_dir)
    assert file_of(client, faculty, sent["id"])["state"] == "READY"


def test_only_a_failed_or_cancelled_document_can_be_retried(
    client: TestClient, team: dict[str, Member], ingest_db: Database, storage_dir: Path
) -> None:
    sent = send(client, team["faculty"], samples.pdf())
    headers = sign_in(client, team["faculty"].email)
    for _ in range(2):  # waiting, then finished: neither can be retried
        refused = client.post(f"{FILES}/{sent['id']}/retry", headers=headers)
        assert (
            refused.status_code == 409 and refused.json()["error"]["code"] == "INGEST_NOT_RETRYABLE"
        )
        run_sandbox(ingest_db, storage_dir)


def test_a_colleague_cannot_cancel_or_retry_your_upload_but_an_admin_can(
    client: TestClient, team: dict[str, Member]
) -> None:
    sent = send(client, team["faculty"], samples.pdf())
    colleague = sign_in(client, team["colleague"].email)
    assert client.post(f"{FILES}/{sent['id']}/cancel", headers=colleague).status_code == 404
    assert client.post(f"{FILES}/{sent['id']}/retry", headers=colleague).status_code == 404
    owner = sign_in(client, team["owner"].email)
    assert client.post(f"{FILES}/{sent['id']}/cancel", headers=owner).status_code == 200


def test_pages_are_visible_only_to_whoever_sees_the_file(
    client: TestClient, team: dict[str, Member], ingest_db: Database, storage_dir: Path
) -> None:
    sent = send(client, team["faculty"], samples.pdf())
    run_sandbox(ingest_db, storage_dir)
    colleague = sign_in(client, team["colleague"].email)
    assert client.get(f"{FILES}/{sent['id']}/pages", headers=colleague).status_code == 404
    assert client.get(f"{FILES}/{sent['id']}/pages/1/image", headers=colleague).status_code == 404
    owner = sign_in(client, team["owner"].email)
    assert client.get(f"{FILES}/{sent['id']}/pages/1/image", headers=owner).status_code == 200


def test_a_worker_with_no_filter_cannot_be_made_to_render_in_the_api_process(
    client: TestClient, team: dict[str, Member], storage_dir: Path
) -> None:
    """Uploading alone never reads the file: the page tables stay empty until the sandbox runs."""
    sent = send(client, team["faculty"], samples.pdf())
    assert pages_of(client, team["faculty"], sent["id"]) == []
    assert file_of(client, team["faculty"], sent["id"])["state"] == "UPLOADED"
