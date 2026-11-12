"""M3 PR 3h-1: passages, the shared text that questions sit under (D-14; test T28 in part).

A passage is saved in place under ``If-Match`` and frozen by checkpoints; a checkpoint is what a
child question pins. These tests cover the routes, who may open a draft, the pictures a passage
uses, and what the database refuses.
"""

import copy
import io
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from qbank.core.config import AppEnv, Settings
from qbank.core.db import Database
from qbank.core.tenancy import TenantContext
from qbank.main import create_app
from qbank.modules.audit.models import AuditEvent
from tests.integration.conftest import (
    Member,
    MigratedDatabase,
    make_member,
    platform_admin,
    sign_in,
)

PATH = "/api/v1/passages"
READY: dict[str, Any] = {
    "schema_version": 1,
    "title": "Free fall",
    "body": [{"kind": "paragraph", "text": "A stone is dropped from a tower."}],
}


@pytest.fixture
def client(migrated_database: MigratedDatabase, tmp_path: Path) -> Iterator[TestClient]:
    settings = Settings(
        app_env=AppEnv.TEST,
        database_url=migrated_database.app_url,
        session_cookie_secure=False,
        storage_dir=tmp_path / "storage",
    )
    with TestClient(create_app(settings)) as test_client:
        yield test_client


@pytest.fixture
def team(owner_db: Database) -> dict[str, Member]:
    owner = make_member(owner_db, "OWNER")
    return {
        "owner": owner,
        "author": make_member(owner_db, "FACULTY", org_id=owner.org_id),
        "other": make_member(owner_db, "FACULTY", org_id=owner.org_id),
        "editor": make_member(owner_db, "FACULTY", org_id=owner.org_id, grants=["EDIT_OTHERS"]),
    }


@pytest.fixture
def headers(client: TestClient, team: dict[str, Member]) -> dict[str, str]:
    return sign_in(client, team["author"].email)


def tag(passage: dict[str, Any]) -> dict[str, str]:
    return {"If-Match": f'"rev-{passage["revision"]}"'}


def start(
    client: TestClient, headers: dict[str, str], content: dict[str, Any] | None = None
) -> dict[str, Any]:
    body = {} if content is None else {"content": content}
    response = client.post(PATH, json=body, headers=headers)
    assert response.status_code == 201, response.text
    return dict(response.json())


def save(
    client: TestClient, headers: dict[str, str], passage: dict[str, Any], content: dict[str, Any]
) -> dict[str, Any]:
    response = client.put(
        f"{PATH}/{passage['id']}/working-revision",
        json={"content": content},
        headers={**headers, **tag(passage)},
    )
    assert response.status_code == 200, response.text
    return dict(response.json())


def checkpoint(
    client: TestClient, headers: dict[str, str], passage: dict[str, Any]
) -> dict[str, Any]:
    response = client.post(
        f"{PATH}/{passage['id']}/checkpoints", headers={**headers, **tag(passage)}
    )
    assert response.status_code == 201, response.text
    return dict(response.json())


def codes(passage: dict[str, Any]) -> list[str]:
    return [f["code"] for f in passage["findings"]]


# --- Starting and reading -----------------------------------------------------------------------


def test_a_new_passage_is_empty_and_says_what_is_still_to_do(
    client: TestClient, headers: dict[str, str], team: dict[str, Member]
) -> None:
    passage = start(client, headers)
    assert passage["created_by"] == str(team["author"].user_id)
    assert passage["latest_checkpoint"] is None
    assert passage["content"]["body"] == []
    assert codes(passage) == ["PASSAGE_TITLE_MISSING", "PASSAGE_BODY_EMPTY"]
    read = client.get(f"{PATH}/{passage['id']}")
    assert read.status_code == 200
    assert read.headers["ETag"] == f'"rev-{passage["revision"]}"'
    assert read.json()["findings"] == passage["findings"]


def test_a_passage_can_be_started_with_content_and_a_retry_returns_the_same_one(
    client: TestClient, headers: dict[str, str]
) -> None:
    key = {**headers, "Idempotency-Key": "passage-start-1"}
    first = client.post(PATH, json={"content": READY}, headers=key)
    again = client.post(PATH, json={"content": READY}, headers=key)
    assert (first.status_code, again.status_code) == (201, 201)
    assert again.json()["id"] == first.json()["id"]
    assert codes(first.json()) == []
    different = client.post(PATH, json={"content": {**READY, "title": "Other"}}, headers=key)
    assert different.status_code == 409


def test_content_that_is_too_large_is_refused_and_gaps_are_not(
    client: TestClient, headers: dict[str, str]
) -> None:
    huge = {**READY, "body": [{"kind": "paragraph", "text": "x" * (300 * 1024)}]}
    refused = client.post(PATH, json={"content": huge}, headers=headers)
    assert refused.status_code == 422
    assert refused.json()["error"]["code"] == "CONTENT_TOO_LARGE"
    mistaken = start(client, headers, {"schema_version": 1, "title": 5, "body": "text"})
    assert "TEXT_NOT_STRING" in codes(mistaken)


# --- Saving and checkpoints ---------------------------------------------------------------------


def test_autosave_replaces_the_working_content_under_if_match(
    client: TestClient, headers: dict[str, str]
) -> None:
    passage = start(client, headers)
    saved = save(client, headers, passage, READY)
    assert saved["revision"] == passage["revision"] + 1
    assert saved["content"] == READY
    assert codes(saved) == []

    stale = client.put(
        f"{PATH}/{passage['id']}/working-revision",
        json={"content": {**READY, "title": "Late"}},
        headers={**headers, **tag(passage)},
    )
    assert stale.status_code == 412
    assert stale.json()["error"]["code"] == "REVISION_STALE"
    missing = client.put(
        f"{PATH}/{passage['id']}/working-revision", json={"content": READY}, headers=headers
    )
    assert missing.status_code == 428
    assert client.get(f"{PATH}/{passage['id']}").json()["content"] == READY


def test_a_checkpoint_freezes_the_revision_and_starts_a_working_copy(
    client: TestClient, headers: dict[str, str], team: dict[str, Member], owner_db: Database
) -> None:
    passage = save(client, headers, start(client, headers), READY)
    after = checkpoint(client, headers, passage)

    frozen = after["latest_checkpoint"]
    assert frozen["number"] == 1
    assert after["working_revision_id"] != frozen["id"]
    assert after["revision"] == passage["revision"] + 1  # the ETag keeps counting
    assert after["content"] == READY  # the working copy starts as a copy

    # Further editing never touches the checkpoint.
    save(client, headers, after, {**READY, "title": "Changed"})
    read = client.get(f"/api/v1/passage-revisions/{frozen['id']}").json()
    assert read["content"] == READY
    assert read["working"] is False
    assert len(read["content_hash"]) == 64
    assert read["passage_id"] == passage["id"]

    with owner_db.transaction(TenantContext(organization_id=team["owner"].org_id)) as session:
        events = session.scalars(
            select(AuditEvent.action).where(AuditEvent.entity_id == UUID(passage["id"]))
        ).all()
    assert "PASSAGE_CREATED" in events
    assert events.count("PASSAGE_CHECKPOINTED") == 1


def test_a_checkpoint_says_where_the_frozen_revision_is(
    client: TestClient, headers: dict[str, str]
) -> None:
    passage = start(client, headers)
    response = client.post(
        f"{PATH}/{passage['id']}/checkpoints", headers={**headers, **tag(passage)}
    )
    frozen = response.json()["latest_checkpoint"]
    assert response.headers["Location"] == f"/api/v1/passage-revisions/{frozen['id']}"
    assert client.get(response.headers["Location"]).status_code == 200


def test_the_old_etag_cannot_checkpoint_again(client: TestClient, headers: dict[str, str]) -> None:
    passage = start(client, headers)
    checkpoint(client, headers, passage)
    again = client.post(f"{PATH}/{passage['id']}/checkpoints", headers={**headers, **tag(passage)})
    assert again.status_code == 412


def test_the_revisions_are_listed_working_first(
    client: TestClient, headers: dict[str, str]
) -> None:
    passage = start(client, headers)
    second = checkpoint(client, headers, passage)
    checkpoint(client, headers, second)
    listed = client.get(f"{PATH}/{passage['id']}/revisions").json()["data"]
    assert [(r["number"], r["working"]) for r in listed] == [(3, True), (2, False), (1, False)]


def test_a_draft_working_revision_is_not_served_as_a_checkpoint(
    client: TestClient, headers: dict[str, str]
) -> None:
    passage = start(client, headers)
    response = client.get(f"/api/v1/passage-revisions/{passage['working_revision_id']}")
    assert response.status_code == 404


# --- Who may open what --------------------------------------------------------------------------


def test_someone_elses_draft_is_not_found_unless_they_may_open_all_drafts(
    client: TestClient, headers: dict[str, str], team: dict[str, Member]
) -> None:
    passage = start(client, headers, READY)
    other = TestClient(client.app)
    other_headers = sign_in(other, team["other"].email)
    assert other.get(f"{PATH}/{passage['id']}").status_code == 404
    assert other.get(f"{PATH}/{passage['id']}/revisions").status_code == 404
    assert (
        other.put(
            f"{PATH}/{passage['id']}/working-revision",
            json={"content": READY},
            headers={**other_headers, **tag(passage)},
        ).status_code
        == 404
    )
    assert other.get(PATH).json()["data"] == []

    editor = TestClient(client.app)
    sign_in(editor, team["editor"].email)
    assert editor.get(f"{PATH}/{passage['id']}").status_code == 200
    assert [p["id"] for p in editor.get(PATH).json()["data"]] == [passage["id"]]
    assert editor.get(PATH, params={"mine": "true"}).json()["data"] == []


def test_a_checkpoint_can_be_read_by_any_member_because_questions_under_it_show_it(
    client: TestClient, headers: dict[str, str], team: dict[str, Member]
) -> None:
    passage = save(client, headers, start(client, headers), READY)
    frozen = checkpoint(client, headers, passage)["latest_checkpoint"]
    other = TestClient(client.app)
    sign_in(other, team["other"].email)
    assert other.get(f"/api/v1/passage-revisions/{frozen['id']}").status_code == 200


def test_the_list_shows_title_and_newest_checkpoint_in_pages(
    client: TestClient, headers: dict[str, str]
) -> None:
    first = save(client, headers, start(client, headers), READY)
    checkpoint(client, headers, first)
    start(client, headers, {**READY, "title": "Second"})
    page = client.get(PATH, params={"limit": 1}).json()
    assert [(p["title"], p["latest_checkpoint_number"]) for p in page["data"]] == [("Second", None)]
    assert page["page"]["has_more"] is True
    rest = client.get(PATH, params={"limit": 1, "cursor": page["page"]["next_cursor"]}).json()
    assert [(p["title"], p["latest_checkpoint_number"]) for p in rest["data"]] == [("Free fall", 1)]
    assert rest["page"]["has_more"] is False


def test_another_coaching_cannot_see_a_passage_or_its_checkpoint(
    client: TestClient, headers: dict[str, str], owner_db: Database
) -> None:
    passage = save(client, headers, start(client, headers), READY)
    frozen = checkpoint(client, headers, passage)["latest_checkpoint"]
    outsider = TestClient(client.app)
    sign_in(outsider, make_member(owner_db, "OWNER").email)
    assert outsider.get(f"{PATH}/{passage['id']}").status_code == 404
    assert outsider.get(f"/api/v1/passage-revisions/{frozen['id']}").status_code == 404
    assert outsider.get(PATH).json()["data"] == []


def test_someone_who_is_not_signed_in_or_acts_in_no_coaching_may_do_nothing(
    client: TestClient, headers: dict[str, str], owner_db: Database
) -> None:
    passage = start(client, headers)
    assert TestClient(client.app).get(f"{PATH}/{passage['id']}").status_code == 401
    platform = TestClient(client.app)
    platform_headers = sign_in(platform, platform_admin(owner_db))
    assert platform.post(PATH, json={}, headers=platform_headers).status_code == 403


# --- Pictures -----------------------------------------------------------------------------------


def upload(client: TestClient, headers: dict[str, str]) -> UUID:
    out = io.BytesIO()
    Image.new("RGB", (8, 8), (1, 2, 3)).save(out, "PNG")
    response = client.post("/api/v1/assets/images", content=out.getvalue(), headers=headers)
    assert response.status_code == 201, response.text
    return UUID(response.json()["id"])


def with_pictures(*assets: UUID | str) -> dict[str, Any]:
    content = copy.deepcopy(READY)
    content["body"] = [
        *content["body"],
        *({"kind": "image", "asset_id": str(a), "alt_text": "A diagram"} for a in assets),
    ]
    return content


def recorded(owner_db: Database, org_id: UUID, passage_id: str) -> list[tuple[int, UUID]]:
    with owner_db.transaction(TenantContext(organization_id=org_id)) as session:
        rows = session.execute(
            text(
                "SELECT r.number, pa.asset_id FROM passage_revision_assets pa"
                " JOIN passage_revisions r ON r.id = pa.revision_id"
                " WHERE r.passage_id = :p ORDER BY r.number, pa.asset_id"
            ),
            {"p": passage_id},
        ).all()
    return [(int(number), asset) for number, asset in rows]


def test_a_passage_may_hold_pictures_of_its_own_coaching_only(
    client: TestClient, headers: dict[str, str], team: dict[str, Member], owner_db: Database
) -> None:
    own = upload(client, headers)
    stranger = make_member(owner_db, "OWNER")
    stranger_client = TestClient(client.app)
    foreign = upload(stranger_client, sign_in(stranger_client, stranger.email))
    org = team["owner"].org_id

    passage = start(client, headers, with_pictures(own))
    assert "IMAGE_NOT_AVAILABLE" not in codes(passage)
    assert recorded(owner_db, org, passage["id"]) == [(1, own)]

    passage = save(client, headers, passage, with_pictures(foreign))
    assert [
        (f["path"], f["code"]) for f in passage["findings"] if f["code"].startswith("IMAGE")
    ] == [("body[1].asset_id", "IMAGE_NOT_AVAILABLE")]
    assert recorded(owner_db, org, passage["id"]) == []


def test_pictures_are_recorded_per_revision_and_a_checkpoint_keeps_them(
    client: TestClient, headers: dict[str, str], team: dict[str, Member], owner_db: Database
) -> None:
    a, b = upload(client, headers), upload(client, headers)
    org = team["owner"].org_id
    passage = start(client, headers, with_pictures(a, b))
    after = checkpoint(client, headers, passage)
    assert recorded(owner_db, org, passage["id"]) == sorted([(1, a), (1, b), (2, a), (2, b)])

    save(client, headers, after, with_pictures(a))
    assert recorded(owner_db, org, passage["id"]) == sorted([(1, a), (1, b), (2, a)])


def test_a_picture_a_passage_uses_cannot_be_deleted_and_a_frozen_revisions_list_is_fixed(
    client: TestClient, headers: dict[str, str], team: dict[str, Member], owner_db: Database
) -> None:
    used, spare = upload(client, headers), upload(client, headers)
    passage = start(client, headers, with_pictures(used))
    checkpoint(client, headers, passage)
    context = TenantContext(organization_id=team["owner"].org_id)
    with pytest.raises(DBAPIError), owner_db.transaction(context) as session:
        session.execute(text("DELETE FROM assets WHERE id = :id"), {"id": used})
    with pytest.raises(DBAPIError), owner_db.transaction(context) as session:
        session.execute(
            text(
                "DELETE FROM passage_revision_assets WHERE revision_id IN"
                " (SELECT id FROM passage_revisions WHERE number = 1 AND passage_id = :p)"
            ),
            {"p": passage["id"]},
        )
    with pytest.raises(DBAPIError), owner_db.transaction(context) as session:
        session.execute(
            text(
                "INSERT INTO passage_revision_assets (organization_id, revision_id, asset_id)"
                " SELECT organization_id, id, :a FROM passage_revisions"
                " WHERE number = 1 AND passage_id = :p"
            ),
            {"a": spare, "p": passage["id"]},
        )


# --- The database holds the line ----------------------------------------------------------------


def test_a_frozen_revision_never_changes_even_for_the_table_owner(
    client: TestClient, headers: dict[str, str], team: dict[str, Member], owner_db: Database
) -> None:
    passage = save(client, headers, start(client, headers), READY)
    checkpoint(client, headers, passage)
    with (
        pytest.raises(DBAPIError),
        owner_db.transaction(TenantContext(organization_id=team["owner"].org_id)) as session,
    ):
        session.execute(
            text(
                "UPDATE passage_revisions SET content = '{}' WHERE number = 1 AND passage_id = :p"
            ),
            {"p": passage["id"]},
        )


def test_the_database_role_cannot_delete_passages_and_other_coachings_rows_are_invisible(
    client: TestClient,
    headers: dict[str, str],
    team: dict[str, Member],
    owner_db: Database,
    db: Database,
) -> None:
    passage = start(client, headers)
    context = TenantContext(organization_id=team["owner"].org_id)
    for table, column in (("passages", "id"), ("passage_revisions", "passage_id")):
        with pytest.raises(DBAPIError), db.transaction(context) as session:
            session.execute(text(f"DELETE FROM {table} WHERE {column} = :p"), {"p": passage["id"]})  # noqa: S608
    other = TenantContext(organization_id=make_member(owner_db, "OWNER").org_id)
    with db.transaction(other) as session:
        for table in ("passages", "passage_revisions", "passage_revision_assets"):
            assert session.execute(text(f"SELECT count(*) FROM {table}")).scalar_one() == 0  # noqa: S608


def test_there_is_one_working_revision_per_passage(
    client: TestClient, headers: dict[str, str], team: dict[str, Member], owner_db: Database
) -> None:
    passage = start(client, headers)
    with (
        pytest.raises(DBAPIError),
        owner_db.transaction(TenantContext(organization_id=team["owner"].org_id)) as session,
    ):
        session.execute(
            text(
                "INSERT INTO passage_revisions (id, organization_id, passage_id, number, content,"
                " author_id) SELECT gen_random_uuid(), organization_id, passage_id, 99, '{}',"
                " author_id FROM passage_revisions WHERE passage_id = :p"
            ),
            {"p": passage["id"]},
        )
