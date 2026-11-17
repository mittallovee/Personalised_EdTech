"""K-08: the load-test seeder builds a bank the app reads exactly like one built through the API.

It inserts rows with plain SQL for speed, so these tests check that the database triggers accepted
every step, that the bank index it builds is the one the questions module would write, and that the
seeded people can sign in and see the bank.
"""

from collections import Counter
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from qbank.core.config import AppEnv, Settings
from qbank.core.db import Database
from qbank.core.security import hash_password
from qbank.core.tenancy import TenantContext
from qbank.main import create_app
from qbank.modules.questions.public import reindex_bank
from tests.integration.conftest import ORIGIN, MigratedDatabase
from tests.load import seed_bank

PASSWORD = "load test password 1"


def test_a_seeded_bank_is_a_real_bank(
    owner_db: Database, migrated_database: MigratedDatabase
) -> None:
    summary = seed_bank.seed(owner_db, questions=400, seed=5, password_hash=hash_password(PASSWORD))
    org = UUID(summary["organization_id"])
    assert (summary["questions"], summary["indexed"]) == (400, 400)

    with owner_db.transaction(TenantContext(organization_id=org)) as session:
        states = Counter(
            session.scalars(
                text("SELECT state FROM bank_index WHERE organization_id = :org"), {"org": org}
            )
        )
        before = session.execute(
            text("SELECT * FROM bank_index WHERE organization_id = :org ORDER BY code"),
            {"org": org},
        ).all()
        reindex_bank(session, org)  # rebuilding again changes nothing
        after = session.execute(
            text("SELECT * FROM bank_index WHERE organization_id = :org ORDER BY code"),
            {"org": org},
        ).all()
        empty_text = session.scalar(
            text("SELECT count(*) FROM bank_index WHERE organization_id = :org AND stem_text = ''"),
            {"org": org},
        )
    assert set(states) == {
        "PUBLISHED",
        "APPROVED",
        "QC_PASSED",
        "IN_REVIEW",
        "CHANGES_REQUESTED",
        "DRAFT",
    }
    assert states["PUBLISHED"] > 200
    assert before == after
    assert empty_text == 0

    settings = Settings(
        app_env=AppEnv.TEST, database_url=migrated_database.app_url, session_cookie_secure=False
    )
    with TestClient(create_app(settings)) as client:
        owner = next(u for u in summary["users"] if u["name"] == "owner")
        signed = client.post(
            "/api/v1/auth/login",
            json={"email": owner["email"], "password": PASSWORD},
            headers=ORIGIN,
        )
        assert signed.status_code == 200, signed.text
        page = client.get("/api/v1/bank/questions", params={"limit": 5}).json()
        found = client.get("/api/v1/bank/questions", params={"q": "velocity", "limit": 5}).json()
    with owner_db.transaction(TenantContext(organization_id=org)) as session:
        live = session.scalar(
            text(
                "SELECT count(*) FROM bank_index WHERE organization_id = :org AND NOT is_archived"
            ),
            {"org": org},
        )
    assert page["total"] == live  # the owner reads every live question, drafts included
    assert len(found["data"]) > 0


def test_the_seeder_refuses_a_database_that_is_not_for_load_tests(
    migrated_database: MigratedDatabase, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("MIGRATION_DATABASE_URL", migrated_database.owner_url)  # qbank_test_...
    monkeypatch.setenv("LOAD_TEST_PASSWORD", PASSWORD)
    assert seed_bank.main(["--questions", "1", "--users-out", str(tmp_path / "u.json")]) == 2
    assert not (tmp_path / "u.json").exists()


def test_the_seeder_needs_a_long_enough_password(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("MIGRATION_DATABASE_URL", "postgresql+psycopg://u:p@localhost/x_load")
    monkeypatch.setenv("LOAD_TEST_PASSWORD", "short")
    assert seed_bank.main(["--users-out", str(tmp_path / "u.json")]) == 2
