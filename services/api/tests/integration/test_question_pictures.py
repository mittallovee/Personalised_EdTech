"""M3 PR 3g-2: the pictures a question uses (D-07; test T29).

An image block names a picture by id. The id must be one of this coaching's pictures (a finding
says so if not), and a saved revision records which pictures it uses so that none of them can be
deleted while history still shows it.
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
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from qbank.core.config import AppEnv, Settings
from qbank.core.db import Database
from qbank.core.tenancy import TenantContext
from qbank.main import create_app
from tests.integration.conftest import Member, MigratedDatabase, make_member, sign_in
from tests.unit.test_question_content import FIXTURES

DRAFT = FIXTURES["SCQ"]["draft"]
PATH = "/api/v1/questions"
GONE = "IMAGE_NOT_AVAILABLE"


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
def owner(owner_db: Database) -> Member:
    return make_member(owner_db, "OWNER")


@pytest.fixture
def headers(client: TestClient, owner: Member) -> dict[str, str]:
    return sign_in(client, owner.email)


def upload(client: TestClient, headers: dict[str, str]) -> UUID:
    out = io.BytesIO()
    Image.new("RGB", (8, 8), (1, 2, 3)).save(out, "PNG")
    response = client.post("/api/v1/assets/images", content=out.getvalue(), headers=headers)
    assert response.status_code == 201, response.text
    return UUID(response.json()["id"])


def with_pictures(*assets: UUID | str) -> dict[str, Any]:
    content = copy.deepcopy(DRAFT)
    content["stem"] = [
        *content["stem"],
        *({"kind": "image", "asset_id": str(a), "alt_text": "A picture"} for a in assets),
    ]
    return content


def start(client: TestClient, headers: dict[str, str], content: dict[str, Any]) -> dict[str, Any]:
    response = client.post(PATH, json={"content": content}, headers=headers)
    assert response.status_code == 201, response.text
    return dict(response.json())


def save(
    client: TestClient, headers: dict[str, str], question: dict[str, Any], content: dict[str, Any]
) -> dict[str, Any]:
    response = client.put(
        f"{PATH}/{question['id']}/working-revision",
        json={"content": content},
        headers={**headers, "If-Match": f'"rev-{question["revision"]}"'},
    )
    assert response.status_code == 200, response.text
    return dict(response.json())


def codes(question: dict[str, Any]) -> list[tuple[str, str]]:
    return [(f["path"], f["code"]) for f in question["findings"] if f["code"] == GONE]


def recorded(owner_db: Database, org_id: UUID, question_id: str) -> list[tuple[int, UUID]]:
    """(revision number, picture) pairs recorded for a question, oldest revision first."""
    with owner_db.transaction(TenantContext(organization_id=org_id)) as session:
        rows = session.execute(
            text(
                "SELECT r.number, ra.asset_id FROM revision_assets ra"
                " JOIN question_revisions r ON r.id = ra.revision_id"
                " JOIN question_versions v ON v.id = r.version_id"
                " WHERE v.master_id = :q ORDER BY r.number, ra.asset_id"
            ),
            {"q": question_id},
        ).all()
    return [(int(number), asset) for number, asset in rows]


# --- Findings -----------------------------------------------------------------------------------


def test_a_picture_of_this_coaching_is_fine(client: TestClient, headers: dict[str, str]) -> None:
    picture = upload(client, headers)
    question = start(client, headers, with_pictures(picture))
    assert codes(question) == []
    assert client.get(f"{PATH}/{question['id']}").json()["findings"] == question["findings"]


def test_a_picture_that_does_not_exist_is_a_finding_not_a_refusal(
    client: TestClient, headers: dict[str, str]
) -> None:
    unknown = UUID("6f1c2a9e-0000-4000-8000-000000000009")
    question = start(client, headers, with_pictures(unknown))
    stem_index = len(DRAFT["stem"])
    assert codes(question) == [(f"stem[{stem_index}].asset_id", GONE)]


def test_another_coachings_picture_is_a_finding_and_is_not_used(
    client: TestClient, headers: dict[str, str], owner_db: Database, owner: Member
) -> None:
    other = make_member(owner_db, "OWNER")
    other_client = TestClient(client.app)
    foreign = upload(other_client, sign_in(other_client, other.email))

    question = start(client, headers, with_pictures(foreign))
    assert [code for _, code in codes(question)] == [GONE]
    assert recorded(owner_db, owner.org_id, question["id"]) == []


def test_the_finding_names_each_missing_picture_and_leaves_the_good_ones(
    client: TestClient, headers: dict[str, str]
) -> None:
    good = upload(client, headers)
    missing = UUID("6f1c2a9e-0000-4000-8000-000000000008")
    question = start(client, headers, with_pictures(good, missing, good))
    first = len(DRAFT["stem"])
    assert codes(question) == [(f"stem[{first + 1}].asset_id", GONE)]


# --- What a revision records --------------------------------------------------------------------


def test_a_save_records_the_pictures_it_uses_and_follows_the_content(
    client: TestClient, headers: dict[str, str], owner_db: Database, owner: Member
) -> None:
    a, b = upload(client, headers), upload(client, headers)
    question = start(client, headers, with_pictures(a))
    assert recorded(owner_db, owner.org_id, question["id"]) == [(1, a)]

    question = save(client, headers, question, with_pictures(a, b, a))
    assert recorded(owner_db, owner.org_id, question["id"]) == sorted([(1, a), (1, b)])

    question = save(client, headers, question, with_pictures(b))
    assert recorded(owner_db, owner.org_id, question["id"]) == [(1, b)]

    save(client, headers, question, copy.deepcopy(DRAFT))
    assert recorded(owner_db, owner.org_id, question["id"]) == []


def test_a_checkpoint_keeps_the_frozen_revisions_pictures_and_copies_them_forward(
    client: TestClient, headers: dict[str, str], owner_db: Database, owner: Member
) -> None:
    a, b = upload(client, headers), upload(client, headers)
    question = start(client, headers, with_pictures(a, b))
    frozen = client.post(
        f"{PATH}/{question['id']}/checkpoints",
        headers={**headers, "If-Match": f'"rev-{question["revision"]}"'},
    )
    assert frozen.status_code in (200, 201), frozen.text
    working = client.get(f"{PATH}/{question['id']}").json()
    assert recorded(owner_db, owner.org_id, question["id"]) == sorted(
        [(1, a), (1, b), (2, a), (2, b)]
    )

    # Editing the working revision never touches the frozen one.
    save(client, headers, working, with_pictures(a))
    assert recorded(owner_db, owner.org_id, question["id"]) == sorted([(1, a), (1, b), (2, a)])


# --- The database holds the line ----------------------------------------------------------------


def test_the_pictures_of_a_frozen_revision_cannot_be_added_or_removed(
    client: TestClient, headers: dict[str, str], owner_db: Database, owner: Member
) -> None:
    a, b = upload(client, headers), upload(client, headers)
    question = start(client, headers, with_pictures(a))
    client.post(
        f"{PATH}/{question['id']}/checkpoints",
        headers={**headers, "If-Match": f'"rev-{question["revision"]}"'},
    )
    context = TenantContext(organization_id=owner.org_id)
    with pytest.raises(DBAPIError), owner_db.transaction(context) as session:
        session.execute(
            text(
                "DELETE FROM revision_assets WHERE asset_id = :a AND revision_id IN"
                " (SELECT id FROM question_revisions WHERE number = 1)"
            ),
            {"a": a},
        )
    with pytest.raises(DBAPIError), owner_db.transaction(context) as session:
        session.execute(
            text(
                "INSERT INTO revision_assets (organization_id, revision_id, asset_id)"
                " SELECT organization_id, id, :b FROM question_revisions WHERE number = 1"
            ),
            {"b": b},
        )


def test_a_picture_that_a_revision_uses_cannot_be_deleted_even_by_the_table_owner(
    client: TestClient, headers: dict[str, str], owner_db: Database, owner: Member
) -> None:
    used, spare = upload(client, headers), upload(client, headers)
    start(client, headers, with_pictures(used))
    context = TenantContext(organization_id=owner.org_id)
    with pytest.raises(DBAPIError), owner_db.transaction(context) as session:
        session.execute(text("DELETE FROM assets WHERE id = :id"), {"id": used})
    # A picture nothing uses can be removed by the owner role (the later clean-up job).
    with owner_db.transaction(context) as session:
        session.execute(text("DELETE FROM assets WHERE id = :id"), {"id": spare})


def test_one_coaching_cannot_see_or_record_pictures_of_another(
    client: TestClient, headers: dict[str, str], owner_db: Database, owner: Member, db: Database
) -> None:
    picture = upload(client, headers)
    question = start(client, headers, with_pictures(picture))
    assert recorded(owner_db, owner.org_id, question["id"]) == [(1, picture)]
    other = make_member(owner_db, "OWNER")
    with owner_db.transaction(TenantContext(organization_id=owner.org_id)) as session:
        revision_id = session.execute(
            text("SELECT id FROM question_revisions WHERE organization_id = :o"),
            {"o": owner.org_id},
        ).scalar_one()
    other_context = TenantContext(organization_id=other.org_id)
    with db.transaction(other_context) as session:
        assert session.execute(text("SELECT count(*) FROM revision_assets")).scalar_one() == 0
    insert = text(
        "INSERT INTO revision_assets (organization_id, revision_id, asset_id)"
        " VALUES (:org, :revision, :asset)"
    )
    # Claiming the first coaching's rows is refused by the row policy; claiming the revision for
    # the other coaching is refused by the composite key (the revision is not theirs).
    for org in (owner.org_id, other.org_id):
        with pytest.raises(DBAPIError), db.transaction(other_context) as session:
            session.execute(insert, {"org": org, "revision": revision_id, "asset": picture})
