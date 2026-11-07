"""M3 PR 3g-1: uploading and serving pictures (D-07; threat T29).

The picture checks themselves (formats, metadata, size limits) are in tests/unit/test_images.py;
these tests are about the route: who may use it, what is stored, and that coachings stay apart.
"""

import hashlib
import io
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from qbank.core.config import AppEnv, Settings
from qbank.core.db import Database
from qbank.core.tenancy import TenantContext
from qbank.main import create_app
from qbank.modules.assets.images import MAX_BYTES
from tests.integration.conftest import (
    Member,
    MigratedDatabase,
    make_member,
    platform_admin,
    sign_in,
)


def picture(fmt: str = "PNG", size: tuple[int, int] = (30, 20)) -> bytes:
    out = io.BytesIO()
    Image.new("RGB", size, (10, 120, 200)).save(out, fmt)
    return out.getvalue()


@pytest.fixture
def storage_dir(tmp_path: Path) -> Path:
    return tmp_path / "storage"


def make_client(migrated: MigratedDatabase, storage_dir: Path, **limits: int) -> Settings:
    return Settings(
        app_env=AppEnv.TEST,
        database_url=migrated.app_url,
        session_cookie_secure=False,
        storage_dir=storage_dir,
        **limits,
    )


@pytest.fixture
def client(migrated_database: MigratedDatabase, storage_dir: Path) -> Iterator[TestClient]:
    settings = make_client(migrated_database, storage_dir)
    with TestClient(create_app(settings)) as test_client:
        yield test_client


@pytest.fixture
def owner(owner_db: Database) -> Member:
    return make_member(owner_db, "OWNER")


@pytest.fixture
def headers(client: TestClient, owner: Member) -> dict[str, str]:
    return sign_in(client, owner.email)


def upload(
    client: TestClient,
    headers: dict[str, str],
    data: bytes,
    content_type: str = "application/octet-stream",
) -> Any:
    return client.post(
        "/api/v1/assets/images", content=data, headers={**headers, "Content-Type": content_type}
    )


def error_code(response: Any) -> str:
    return str(response.json()["error"]["code"])


def stored_files(storage_dir: Path) -> list[Path]:
    return [path for path in storage_dir.rglob("*") if path.is_file()]


def stored_row(owner_db: Database, org_id: UUID, asset_id: str) -> dict[str, Any]:
    with owner_db.transaction(TenantContext(organization_id=org_id)) as session:
        row = (
            session.execute(text("SELECT * FROM assets WHERE id = :id"), {"id": asset_id})
            .mappings()
            .one()
        )
        return dict(row)


# --- Uploading and reading back -----------------------------------------------------------------


def test_an_uploaded_picture_is_stored_and_read_back_as_a_clean_copy(
    client: TestClient,
    headers: dict[str, str],
    owner: Member,
    owner_db: Database,
    storage_dir: Path,
) -> None:
    response = upload(client, headers, picture("PNG", (30, 20)))

    assert response.status_code == 201, response.text
    body = response.json()
    assert (body["kind"], body["content_type"], body["width"], body["height"]) == (
        "IMAGE",
        "image/png",
        30,
        20,
    )
    assert response.headers["Location"] == f"/api/v1/assets/{body['id']}/content"

    served = client.get(f"/api/v1/assets/{body['id']}/content")
    assert served.status_code == 200
    assert served.headers["content-type"] == "image/png"
    assert served.headers["x-content-type-options"] == "nosniff"
    assert "private" in served.headers["cache-control"]
    assert "sandbox" in served.headers["content-security-policy"]
    assert Image.open(io.BytesIO(served.content)).size == (30, 20)
    assert len(served.content) == body["byte_size"]

    row = stored_row(owner_db, owner.org_id, body["id"])
    assert row["sha256"] == hashlib.sha256(served.content).hexdigest()
    assert row["created_by"] == owner.user_id
    # The key is ours, never anything the uploader sent, and the file is where the key says.
    assert row["storage_key"] == f"org/{owner.org_id}/image/{body['id']}"
    assert (storage_dir / row["storage_key"]).read_bytes() == served.content


def test_what_the_picture_is_comes_from_its_bytes_not_from_what_the_sender_says(
    client: TestClient, headers: dict[str, str]
) -> None:
    jpeg_called_html = upload(client, headers, picture("JPEG"), content_type="text/html")
    assert jpeg_called_html.status_code == 201
    assert jpeg_called_html.json()["content_type"] == "image/jpeg"

    svg_called_png = upload(
        client,
        headers,
        b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
        content_type="image/png",
    )
    assert svg_called_png.status_code == 422
    assert error_code(svg_called_png) == "IMAGE_INVALID"


def test_bytes_hidden_after_the_picture_are_not_stored(
    client: TestClient, headers: dict[str, str]
) -> None:
    polyglot = picture("PNG") + b"<script>alert(1)</script>"
    asset = upload(client, headers, polyglot).json()
    served = client.get(f"/api/v1/assets/{asset['id']}/content").content
    assert b"<script>" not in served


def test_a_picture_over_the_size_limit_is_refused(
    client: TestClient, headers: dict[str, str], storage_dir: Path
) -> None:
    response = upload(client, headers, b"\x89PNG" + b"0" * MAX_BYTES)
    assert response.status_code == 413
    assert error_code(response) == "IMAGE_TOO_LARGE"
    assert stored_files(storage_dir) == []


def test_nothing_is_kept_for_a_picture_that_was_refused(
    client: TestClient, headers: dict[str, str], storage_dir: Path
) -> None:
    assert upload(client, headers, b"not a picture").status_code == 422
    assert stored_files(storage_dir) == []


def test_a_missing_or_unknown_picture_is_404(client: TestClient, headers: dict[str, str]) -> None:
    unknown = "6f1c2a9e-0000-4000-8000-000000000009"
    assert client.get(f"/api/v1/assets/{unknown}").status_code == 404
    assert client.get(f"/api/v1/assets/{unknown}/content").status_code == 404
    assert client.get("/api/v1/assets/not-a-uuid/content").status_code == 400


# --- Who may use it -----------------------------------------------------------------------------


# The owner is the fixture's signed-in user (a coaching has exactly one).
@pytest.mark.parametrize("role", ["ADMIN", "FACULTY"])
def test_every_member_of_a_coaching_may_upload_and_read(
    client: TestClient, owner_db: Database, owner: Member, role: str
) -> None:
    member = make_member(owner_db, role, org_id=owner.org_id)
    member_headers = sign_in(client, member.email)
    response = upload(client, member_headers, picture())
    assert response.status_code == 201
    assert client.get(f"/api/v1/assets/{response.json()['id']}/content").status_code == 200


def test_someone_who_is_not_signed_in_may_not_upload_or_read(
    client: TestClient, headers: dict[str, str], migrated_database: MigratedDatabase
) -> None:
    asset = upload(client, headers, picture()).json()
    anonymous = TestClient(client.app)
    assert anonymous.post("/api/v1/assets/images", content=picture()).status_code == 401
    assert anonymous.get(f"/api/v1/assets/{asset['id']}/content").status_code == 401
    assert anonymous.get(f"/api/v1/assets/{asset['id']}").status_code == 401


def test_a_platform_admin_who_is_not_acting_in_a_coaching_may_not_upload(
    client: TestClient, owner_db: Database
) -> None:
    platform = TestClient(client.app)
    platform_headers = sign_in(platform, platform_admin(owner_db))
    assert upload(platform, platform_headers, picture()).status_code == 403


# --- Coachings stay apart (T29, ADR-0005) -------------------------------------------------------


def test_another_coachings_picture_is_not_found(
    client: TestClient, headers: dict[str, str], owner_db: Database
) -> None:
    asset = upload(client, headers, picture()).json()
    other = make_member(owner_db, "OWNER")  # a different coaching
    other_client = TestClient(client.app)
    sign_in(other_client, other.email)

    assert other_client.get(f"/api/v1/assets/{asset['id']}").status_code == 404
    content = other_client.get(f"/api/v1/assets/{asset['id']}/content")
    assert content.status_code == 404
    assert error_code(content) == "NOT_FOUND"
    # The picture is still there for its own coaching.
    assert client.get(f"/api/v1/assets/{asset['id']}/content").status_code == 200


def test_row_level_security_hides_another_coachings_pictures_from_the_database_role(
    client: TestClient, headers: dict[str, str], owner: Member, owner_db: Database, db: Database
) -> None:
    upload(client, headers, picture())
    other = make_member(owner_db, "OWNER")
    with db.transaction(TenantContext(organization_id=other.org_id)) as session:
        assert session.execute(text("SELECT count(*) FROM assets")).scalar_one() == 0
    with (
        pytest.raises(DBAPIError),
        db.transaction(TenantContext(organization_id=other.org_id)) as session,
    ):
        session.execute(
            text(
                "INSERT INTO assets (id, organization_id, kind, content_type, byte_size, sha256,"
                " width, height, storage_key, created_by) VALUES (gen_random_uuid(), :org,"
                " 'IMAGE', 'image/png', 1, :sha, 1, 1, 'k', :user)"
            ),
            {"org": owner.org_id, "sha": "0" * 64, "user": other.user_id},
        )


def test_the_database_role_cannot_change_or_delete_a_stored_picture(
    client: TestClient, headers: dict[str, str], owner: Member, db: Database
) -> None:
    asset = upload(client, headers, picture()).json()
    context = TenantContext(organization_id=owner.org_id)
    for statement in (
        "UPDATE assets SET width = 1 WHERE id = :id",
        "DELETE FROM assets WHERE id = :id",
    ):
        with pytest.raises(DBAPIError), db.transaction(context) as session:
            session.execute(text(statement), {"id": asset["id"]})


# --- Limits -------------------------------------------------------------------------------------


def test_too_many_uploads_in_a_short_time_are_refused_with_a_wait(
    migrated_database: MigratedDatabase, storage_dir: Path, owner_db: Database
) -> None:
    settings = make_client(migrated_database, storage_dir, asset_uploads_per_user=2)
    member = make_member(owner_db, "OWNER")
    with TestClient(create_app(settings)) as limited:
        limited_headers = sign_in(limited, member.email)
        assert upload(limited, limited_headers, picture()).status_code == 201
        assert upload(limited, limited_headers, picture()).status_code == 201
        refused = upload(limited, limited_headers, picture())
        assert refused.status_code == 429
        assert error_code(refused) == "RATE_LIMITED"
        assert int(refused.headers["Retry-After"]) >= 1


def test_when_the_server_is_busy_decoding_a_picture_is_turned_away_not_queued(
    client: TestClient, headers: dict[str, str]
) -> None:
    gate = client.app.state.image_decode_gate  # type: ignore[attr-defined]
    held = [gate.try_enter() for _ in range(2)]
    entered = [place.__enter__() for place in held]
    try:
        assert all(entered)
        refused = upload(client, headers, picture())
        assert refused.status_code == 429
        assert error_code(refused) == "RATE_LIMITED"
    finally:
        for place in held:
            place.__exit__(None, None, None)
    assert upload(client, headers, picture()).status_code == 201


# --- Cached copies must not outlive the right to see them ---------------------------------------


def test_a_picture_is_checked_again_each_time_it_is_asked_for(
    client: TestClient, headers: dict[str, str], owner_db: Database
) -> None:
    asset = upload(client, headers, picture()).json()
    first = client.get(f"/api/v1/assets/{asset['id']}/content")
    # The browser may keep it, but must ask before using it, so a different person on the same
    # browser (another coaching) reaches the permission checks instead of the cached copy.
    assert "no-cache" in first.headers["cache-control"]
    assert "max-age=31536000" not in first.headers["cache-control"]
    etag = first.headers["etag"]

    again = client.get(f"/api/v1/assets/{asset['id']}/content", headers={"If-None-Match": etag})
    assert again.status_code == 304
    assert again.content == b""
    assert again.headers["etag"] == etag

    # The same question from someone of another coaching, even holding the right ETag, is a 404.
    other = make_member(owner_db, "OWNER")
    other_client = TestClient(client.app)
    sign_in(other_client, other.email)
    stolen = other_client.get(
        f"/api/v1/assets/{asset['id']}/content", headers={"If-None-Match": etag}
    )
    assert stolen.status_code == 404

    # And after signing out, the same question is a 401, never a 304.
    signed_out = TestClient(client.app)
    assert (
        signed_out.get(
            f"/api/v1/assets/{asset['id']}/content", headers={"If-None-Match": etag}
        ).status_code
        == 401
    )
