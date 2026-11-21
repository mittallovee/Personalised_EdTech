"""M5 PR 5a-1: a coaching's AI provider keys (H-02, ADR-0023; test T43).

A key goes in write-only and is sealed with a master key that is not in the database: the stored
column never contains the clear key, no response or audit entry shows more than its last four
characters, only admins manage keys, one coaching never sees or opens another's, and a rotation
reseals what is stored.
"""

import base64
from collections.abc import Iterator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from qbank.core.config import AppEnv, Settings
from qbank.core.db import Database
from qbank.core.secretbox import Keyring, KeyUnreadable, build_keyring
from qbank.core.tenancy import TenantContext
from qbank.main import create_app
from qbank.modules.ai.public import Provider, open_key, reseal_all
from qbank.modules.audit.models import AuditEvent
from tests.integration.conftest import Member, MigratedDatabase, make_member, sign_in

KEYS = "/api/v1/ai/keys"
MASTER = base64.b64encode(bytes(range(32))).decode()
SECOND = base64.b64encode(bytes(range(1, 33))).decode()
CLEAR = "sk-ant-api03-ABCDEFGHIJKLMNOP-wXyZ"


def make_client(migrated_database: MigratedDatabase, master: str | None) -> Iterator[TestClient]:
    settings = Settings(
        app_env=AppEnv.TEST,
        database_url=migrated_database.app_url,
        session_cookie_secure=False,
        ai_keys_master_key=master,  # type: ignore[arg-type]
    )
    with TestClient(create_app(settings)) as test_client:
        yield test_client


@pytest.fixture
def client(migrated_database: MigratedDatabase) -> Iterator[TestClient]:
    yield from make_client(migrated_database, MASTER)


@pytest.fixture
def team(owner_db: Database) -> dict[str, Member]:
    owner = make_member(owner_db, "OWNER")
    return {
        "owner": owner,
        "admin": make_member(owner_db, "ADMIN", org_id=owner.org_id),
        "faculty": make_member(owner_db, "FACULTY", org_id=owner.org_id, grants=["EDIT_OTHERS"]),
    }


def keyring(master: str = MASTER, *, previous: str | None = None, key_id: str = "k1") -> Keyring:
    built = build_keyring(master, key_id, previous)
    assert built is not None
    return built


def events(owner_db: Database, org_id: UUID) -> list[AuditEvent]:
    with owner_db.transaction(TenantContext(organization_id=org_id)) as session:
        return list(
            session.scalars(
                select(AuditEvent)
                .where(
                    AuditEvent.organization_id == org_id,
                    AuditEvent.entity_type == "ai_provider_key",
                )
                .order_by(AuditEvent.created_at)
            )
        )


# --- Storing and showing --------------------------------------------------------------------


def test_a_key_is_stored_and_only_its_last_four_characters_come_back(
    client: TestClient, team: dict[str, Member]
) -> None:
    headers = sign_in(client, team["admin"].email)
    before = client.get(KEYS, headers=headers)
    assert before.status_code == 200
    assert before.json()["encryption_ready"] is True
    assert [(k["provider"], k["configured"]) for k in before.json()["data"]] == [
        ("ANTHROPIC", False),
        ("OPENAI", False),
        ("GOOGLE", False),
        ("OPENROUTER", False),
    ]

    stored = client.put(f"{KEYS}/ANTHROPIC", json={"key": f"  {CLEAR}  "}, headers=headers)
    assert stored.status_code == 200, stored.text
    assert stored.json()["configured"] is True
    assert stored.json()["last4"] == CLEAR[-4:]
    assert CLEAR not in stored.text

    after = client.get(KEYS, headers=headers)
    assert CLEAR not in after.text
    anthropic = next(k for k in after.json()["data"] if k["provider"] == "ANTHROPIC")
    assert anthropic["configured"] is True
    assert anthropic["last4"] == CLEAR[-4:]
    assert anthropic["updated_at"] is not None
    assert next(k for k in after.json()["data"] if k["provider"] == "OPENAI")["configured"] is False


def test_the_stored_column_never_holds_the_clear_key_and_the_server_can_open_it(
    client: TestClient,
    team: dict[str, Member],
    owner_db: Database,
) -> None:
    headers = sign_in(client, team["admin"].email)
    client.put(f"{KEYS}/OPENAI", json={"key": CLEAR}, headers=headers)
    with owner_db.transaction(TenantContext(organization_id=team["owner"].org_id)) as session:
        row = session.execute(
            text(
                "SELECT ciphertext, nonce, key_id, last4 FROM ai_provider_keys"
                " WHERE organization_id = :org"
            ),
            {"org": team["owner"].org_id},
        ).one()
        assert CLEAR.encode() not in bytes(row.ciphertext)
        assert b"ABCDEFGHIJ" not in bytes(row.ciphertext)
        assert len(bytes(row.nonce)) == 12
        assert (row.key_id, row.last4) == ("k1", CLEAR[-4:])
        # The server's own call path opens it; a wrong master key and a missing one do not.
        assert open_key(session, keyring(), team["owner"].org_id, Provider.OPENAI) == CLEAR
        with pytest.raises(KeyUnreadable):
            open_key(session, keyring(SECOND), team["owner"].org_id, Provider.OPENAI)
        with pytest.raises(KeyUnreadable):
            open_key(session, None, team["owner"].org_id, Provider.OPENAI)
        assert open_key(session, keyring(), team["owner"].org_id, Provider.GOOGLE) is None


def test_replacing_a_key_keeps_one_row_and_changes_what_opens(
    client: TestClient, team: dict[str, Member], owner_db: Database
) -> None:
    headers = sign_in(client, team["admin"].email)
    client.put(f"{KEYS}/GOOGLE", json={"key": "AIza-first-key-0001"}, headers=headers)
    replaced = client.put(f"{KEYS}/GOOGLE", json={"key": "AIza-second-key-0002"}, headers=headers)
    assert replaced.json()["last4"] == "0002"
    with owner_db.transaction(TenantContext(organization_id=team["owner"].org_id)) as session:
        assert (
            session.scalar(
                text("SELECT count(*) FROM ai_provider_keys WHERE organization_id = :org"),
                {"org": team["owner"].org_id},
            )
            == 1
        )
        assert (
            session.scalar(
                text("SELECT revision FROM ai_provider_keys WHERE organization_id = :org"),
                {"org": team["owner"].org_id},
            )
            == 2
        )
        opened = open_key(session, keyring(), team["owner"].org_id, Provider.GOOGLE)
    assert opened == "AIza-second-key-0002"


def test_deleting_a_key_removes_it_and_a_second_delete_is_not_found(
    client: TestClient, team: dict[str, Member]
) -> None:
    headers = sign_in(client, team["owner"].email)
    client.put(f"{KEYS}/OPENROUTER", json={"key": "sk-or-v1-abcdef0123"}, headers=headers)
    assert client.delete(f"{KEYS}/OPENROUTER", headers=headers).status_code == 204
    listed = client.get(KEYS, headers=headers).json()["data"]
    assert next(k for k in listed if k["provider"] == "OPENROUTER")["configured"] is False
    again = client.delete(f"{KEYS}/OPENROUTER", headers=headers)
    assert again.status_code == 404
    assert again.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.parametrize(
    "bad",
    ["short", "has a space inside it 12345", "line\nbreak-1234567", "k" * 513, "  ", "é" * 12],
)
def test_something_that_is_not_an_api_key_is_refused_and_not_echoed(
    client: TestClient, team: dict[str, Member], bad: str
) -> None:
    headers = sign_in(client, team["admin"].email)
    response = client.put(f"{KEYS}/ANTHROPIC", json={"key": bad}, headers=headers)
    assert response.status_code == 422
    if response.json()["error"]["code"] == "AI_KEY_INVALID":
        assert bad.strip() == "" or bad.strip() not in response.text
    listed = client.get(KEYS, headers=headers).json()["data"]
    assert not any(k["configured"] for k in listed)


def test_an_unknown_provider_is_a_validation_error(
    client: TestClient, team: dict[str, Member]
) -> None:
    headers = sign_in(client, team["admin"].email)
    response = client.put(f"{KEYS}/MISTRAL", json={"key": CLEAR}, headers=headers)
    assert response.status_code == 400  # not one of the four providers


# --- The audit trail -------------------------------------------------------------------------


def test_every_change_is_audited_with_the_last_four_characters_and_never_the_key(
    client: TestClient, team: dict[str, Member], owner_db: Database
) -> None:
    headers = sign_in(client, team["admin"].email)
    client.put(f"{KEYS}/ANTHROPIC", json={"key": CLEAR}, headers=headers)
    client.put(f"{KEYS}/ANTHROPIC", json={"key": CLEAR[:-4] + "9999"}, headers=headers)
    client.delete(f"{KEYS}/ANTHROPIC", headers=headers)
    found = events(owner_db, team["owner"].org_id)
    assert [e.action for e in found] == ["AI_KEY_SET", "AI_KEY_REPLACED", "AI_KEY_DELETED"]
    assert all(e.actor_user_id == team["admin"].user_id for e in found)
    assert found[1].before == {"configured": True, "last4": CLEAR[-4:]}
    assert found[1].after == {"provider": "ANTHROPIC", "configured": True, "last4": "9999"}
    dumped = " ".join(str(e.before) + str(e.after) for e in found)
    assert "ABCDEFGH" not in dumped
    assert CLEAR not in dumped


# --- Who may ---------------------------------------------------------------------------------


def test_faculty_and_signed_out_visitors_cannot_manage_keys(
    client: TestClient, team: dict[str, Member]
) -> None:
    admin = sign_in(client, team["admin"].email)
    client.put(f"{KEYS}/ANTHROPIC", json={"key": CLEAR}, headers=admin)
    faculty = sign_in(client, team["faculty"].email)  # edit-others is not an AI right
    assert client.get(KEYS, headers=faculty).status_code == 403
    assert client.put(f"{KEYS}/ANTHROPIC", json={"key": CLEAR}, headers=faculty).status_code == 403
    assert client.delete(f"{KEYS}/ANTHROPIC", headers=faculty).status_code == 403
    client.cookies.clear()
    assert client.get(KEYS).status_code == 401


def test_one_coaching_never_sees_or_opens_anothers_key(
    client: TestClient, team: dict[str, Member], owner_db: Database
) -> None:
    admin = sign_in(client, team["admin"].email)
    client.put(f"{KEYS}/ANTHROPIC", json={"key": CLEAR}, headers=admin)
    stranger = make_member(owner_db, "ADMIN", coaching_name="Other Coaching")
    headers = sign_in(client, stranger.email)
    assert not any(k["configured"] for k in client.get(KEYS, headers=headers).json()["data"])
    assert client.delete(f"{KEYS}/ANTHROPIC", headers=headers).status_code == 404

    with owner_db.transaction(TenantContext(organization_id=stranger.org_id)) as session:
        assert open_key(session, keyring(), stranger.org_id, Provider.ANTHROPIC) is None
    # Even a ciphertext copied into the other coaching's row does not open there: the coaching is
    # part of what the key was sealed for.
    with owner_db.transaction(TenantContext(organization_id=team["owner"].org_id)) as session:
        row = session.execute(
            text(
                "SELECT ciphertext, nonce, key_id FROM ai_provider_keys"
                " WHERE organization_id = :org"
            ),
            {"org": team["owner"].org_id},
        ).one()
    with owner_db.transaction(TenantContext(organization_id=stranger.org_id)) as session:
        session.execute(
            text(
                "INSERT INTO ai_provider_keys (id, organization_id, provider, ciphertext, nonce,"
                " key_id, last4, created_by) VALUES (gen_random_uuid(), :org, 'ANTHROPIC', :c, :n,"
                " :k, 'wXyZ', :u)"
            ),
            {
                "org": stranger.org_id,
                "c": bytes(row.ciphertext),
                "n": bytes(row.nonce),
                "k": row.key_id,
                "u": stranger.user_id,
            },
        )
        with pytest.raises(KeyUnreadable):
            open_key(session, keyring(), stranger.org_id, Provider.ANTHROPIC)


# --- A server without a master key ----------------------------------------------------------


def test_without_a_master_key_keys_cannot_be_stored_and_the_screen_can_say_so(
    migrated_database: MigratedDatabase, team: dict[str, Member]
) -> None:
    for plain in make_client(migrated_database, None):
        headers = sign_in(plain, team["admin"].email)
        listed = plain.get(KEYS, headers=headers)
        assert listed.json()["encryption_ready"] is False
        refused = plain.put(f"{KEYS}/ANTHROPIC", json={"key": CLEAR}, headers=headers)
        assert refused.status_code == 409
        assert refused.json()["error"]["code"] == "AI_NOT_CONFIGURED"
        assert CLEAR not in refused.text


# --- Rotation --------------------------------------------------------------------------------


def test_a_rotation_reseals_every_key_under_the_new_master_key(
    client: TestClient, team: dict[str, Member], owner_db: Database
) -> None:
    admin = sign_in(client, team["admin"].email)
    client.put(f"{KEYS}/ANTHROPIC", json={"key": CLEAR}, headers=admin)
    client.put(f"{KEYS}/OPENAI", json={"key": "sk-proj-0123456789abcdef"}, headers=admin)
    org = team["owner"].org_id
    rotated = keyring(SECOND, previous=f"k1={MASTER}", key_id="k2")

    with owner_db.transaction(TenantContext(organization_id=org)) as session:
        assert reseal_all(session, rotated, org) == (2, 0)
    with owner_db.transaction(TenantContext(organization_id=org)) as session:
        assert session.scalars(
            text("SELECT key_id FROM ai_provider_keys WHERE organization_id = :org"), {"org": org}
        ).all() == ["k2", "k2"]
        assert open_key(session, rotated, org, Provider.ANTHROPIC) == CLEAR
        # The new master key alone now opens them: the old one can be removed.
        only_new = keyring(SECOND, key_id="k2")
        assert open_key(session, only_new, org, Provider.OPENAI) == "sk-proj-0123456789abcdef"
        with pytest.raises(KeyUnreadable):
            open_key(session, keyring(), org, Provider.ANTHROPIC)
    # Running it again changes nothing.
    with owner_db.transaction(TenantContext(organization_id=org)) as session:
        assert reseal_all(session, rotated, org) == (0, 2)


def test_a_rotation_that_cannot_open_a_key_changes_nothing(
    client: TestClient, team: dict[str, Member], owner_db: Database
) -> None:
    admin = sign_in(client, team["admin"].email)
    client.put(f"{KEYS}/ANTHROPIC", json={"key": CLEAR}, headers=admin)
    org = team["owner"].org_id
    forgot_previous = keyring(SECOND, key_id="k2")  # the old master key was not given
    with (
        pytest.raises(KeyUnreadable),
        owner_db.transaction(TenantContext(organization_id=org)) as s,
    ):
        reseal_all(s, forgot_previous, org)
    with owner_db.transaction(TenantContext(organization_id=org)) as session:
        assert session.scalars(
            text("SELECT key_id FROM ai_provider_keys WHERE organization_id = :org"), {"org": org}
        ).all() == ["k1"]
        assert open_key(session, keyring(), org, Provider.ANTHROPIC) == CLEAR
