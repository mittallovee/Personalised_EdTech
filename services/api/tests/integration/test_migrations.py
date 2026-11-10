"""M1 exit test T8: migrations go up, down and up again cleanly on an empty database."""

import json
import secrets
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text

from qbank.core.ids import new_id
from qbank.main import create_app
from tests.conftest import make_settings
from tests.integration.conftest import (
    MigratedDatabase,
    alembic_config,
    create_database,
    drop_database,
)


@pytest.fixture
def empty_database() -> Iterator[tuple[str, str]]:
    name = f"qbank_test_{secrets.token_hex(6)}"
    owner_url, app_url, _worker_url = create_database(name)
    try:
        yield owner_url, app_url
    finally:
        drop_database(name)


def table_names(url: str) -> set[str]:
    engine = create_engine(url)
    try:
        return set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def test_upgrade_downgrade_upgrade(empty_database: tuple[str, str]) -> None:
    owner_url, _ = empty_database
    config = alembic_config(owner_url)

    command.upgrade(config, "head")
    assert {
        "organizations",
        "users",
        "memberships",
        "audit_events",
        "password_credentials",
        "platform_roles",
        "sessions",
        "jobs",
        "public_codes",
        "membership_grants",
        "account_emails",
        "account_links",
        "idempotency_keys",
    } <= table_names(owner_url)

    command.downgrade(config, "base")
    assert table_names(owner_url) <= {"alembic_version"}

    command.upgrade(config, "head")
    assert "memberships" in table_names(owner_url)


def test_ready_when_schema_is_current(migrated_database: MigratedDatabase) -> None:
    with TestClient(create_app(make_settings(migrated_database.app_url))) as client:
        response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok", "migrations": "ok"}


def test_not_ready_when_migrations_are_pending(empty_database: tuple[str, str]) -> None:
    owner_url, app_url = empty_database
    command.upgrade(alembic_config(owner_url), "head")
    command.downgrade(alembic_config(owner_url), "base")
    # alembic_version still exists (empty) but the runtime role lost access to it on downgrade.

    with TestClient(create_app(make_settings(app_url))) as client:
        response = client.get("/health/ready")

    assert response.status_code == 503


def test_existing_password_logins_get_their_email_reserved(
    empty_database: tuple[str, str],
) -> None:
    """Migration 0005 fills account_emails from the logins that already exist (B-07)."""
    owner_url, _ = empty_database
    config = alembic_config(owner_url)
    command.upgrade(config, "0004")
    user_id = new_id()
    engine = create_engine(owner_url)
    try:
        with engine.begin() as conn:
            conn.execute(text("SELECT set_config('app.is_platform', 'true', true)"))
            conn.execute(
                text("INSERT INTO users (id, display_name) VALUES (:id, 'Existing')"),
                {"id": user_id},
            )
            conn.execute(
                text(
                    "INSERT INTO password_credentials (user_id, email, password_hash)"
                    " VALUES (:id, 'existing@example.com', 'not-a-real-hash')"
                ),
                {"id": user_id},
            )

        command.upgrade(config, "head")

        with engine.connect() as conn:
            reserved = conn.execute(
                text("SELECT user_id FROM account_emails WHERE email = 'existing@example.com'")
            ).scalar()
    finally:
        engine.dispose()
    assert reserved == user_id


def test_existing_pictures_are_recorded_for_every_revision_when_migration_0022_runs(
    empty_database: tuple[str, str],
) -> None:
    """Migration 0022 fills revision_assets for revisions saved before it, frozen ones included."""
    owner_url, _ = empty_database
    config = alembic_config(owner_url)
    command.upgrade(config, "0021")
    org, other_org, user = new_id(), new_id(), new_id()
    own_a, own_b, foreign, unknown = new_id(), new_id(), new_id(), new_id()
    master, version = new_id(), new_id()
    working, frozen = new_id(), new_id()

    def picture(asset: object) -> dict[str, object]:
        return {"kind": "image", "asset_id": str(asset), "alt_text": "x"}

    content_frozen = {
        "stem": [picture(own_a), picture("not-an-id"), picture(foreign)],
        "options": [{"id": "A", "content": [picture(own_b), picture(unknown)]}],
    }
    content_working = {"stem": [picture(own_a)], "note": {"asset_id": str(own_b)}}
    engine = create_engine(owner_url)
    try:
        with engine.begin() as conn:
            conn.execute(text("SELECT set_config('app.is_platform', 'true', true)"))
            for organization in (org, other_org):
                conn.execute(
                    text("INSERT INTO organizations (id, display_name) VALUES (:id, 'C')"),
                    {"id": organization},
                )
            conn.execute(
                text("INSERT INTO users (id, display_name) VALUES (:id, 'U')"), {"id": user}
            )
            for organization, assets in ((org, (own_a, own_b)), (other_org, (foreign,))):
                conn.execute(
                    text("SELECT set_config('app.org_id', :o, true)"), {"o": str(organization)}
                )
                for asset in assets:
                    conn.execute(
                        text(
                            "INSERT INTO assets (id, organization_id, kind, content_type,"
                            " byte_size, sha256, width, height, storage_key, created_by)"
                            " VALUES (:id, :org, 'IMAGE', 'image/png', 1, :sha, 1, 1, :key, :user)"
                        ),
                        {
                            "id": asset,
                            "org": organization,
                            "sha": "0" * 64,
                            "key": f"org/{organization}/image/{asset}",
                            "user": user,
                        },
                    )
            conn.execute(text("SELECT set_config('app.org_id', :o, true)"), {"o": str(org)})
            conn.execute(
                text(
                    "INSERT INTO public_codes (code, entity_type, organization_id)"
                    " VALUES ('ABCD2345', 'question', :org)"
                ),
                {"org": org},
            )
            conn.execute(
                text(
                    "INSERT INTO question_masters (id, organization_id, code, created_by)"
                    " VALUES (:id, :org, 'ABCD2345', :user)"
                ),
                {"id": master, "org": org, "user": user},
            )
            conn.execute(
                text(
                    "INSERT INTO question_versions (id, organization_id, master_id, number)"
                    " VALUES (:id, :org, :master, 1)"
                ),
                {"id": version, "org": org, "master": master},
            )
            for revision_id, number, content, is_frozen in (
                (frozen, 1, content_frozen, True),
                (working, 2, content_working, False),
            ):
                conn.execute(
                    text(
                        "INSERT INTO question_revisions (id, organization_id, version_id, number,"
                        " content, content_hash, author_id, frozen_at) VALUES (:id, :org,"
                        " :version, :number, CAST(:content AS jsonb), :hash, :user, :frozen)"
                    ),
                    {
                        "id": revision_id,
                        "org": org,
                        "version": version,
                        "number": number,
                        "content": json.dumps(content),
                        "hash": "1" * 64 if is_frozen else None,
                        "user": user,
                        "frozen": datetime.now(UTC) if is_frozen else None,
                    },
                )

        command.upgrade(config, "head")

        with engine.begin() as conn:
            conn.execute(text("SELECT set_config('app.org_id', :o, true)"), {"o": str(org)})
            rows = conn.execute(text("SELECT revision_id, asset_id FROM revision_assets")).all()
    finally:
        engine.dispose()
    # Only the coaching's own pictures that a revision names are recorded: not the other
    # coaching's, not an unknown id, not an unreadable one, and not a field that is not a block.
    assert sorted((str(r), str(a)) for r, a in rows) == sorted(
        [(str(frozen), str(own_a)), (str(frozen), str(own_b)), (str(working), str(own_a))]
    )
