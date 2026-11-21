"""Shared setup for the AI run tests: a coaching with an author, an admin, a catalogue, one draft
question, a stored (fake) key, one priced model and a scripted fake provider."""

import base64
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from qbank.core.config import AppEnv, Settings
from qbank.core.db import Database
from qbank.core.tenancy import TenantContext
from qbank.main import create_app
from qbank.modules.ai.models import AiModel, LedgerEntry, OperationSetting
from qbank.modules.ai.providers.base import StructuredRequest, StructuredResult
from qbank.modules.ai.providers.fake import FakeProvider
from tests.integration.conftest import Member, MigratedDatabase, make_member, sign_in
from tests.integration.question_support import Catalogue, ready_for, seed_catalogue

QUESTIONS = "/api/v1/questions"
MASTER = base64.b64encode(bytes(range(32))).decode()
KEY = "sk-test-0123456789abcdef"
D = Decimal


class HookedProvider(FakeProvider):
    """A fake that can do something while the provider 'is thinking' (another save, say)."""

    def __init__(self) -> None:
        super().__init__()
        self.during: Callable[[], None] | None = None

    def generate_structured(self, api_key: str, request: StructuredRequest) -> StructuredResult:
        if self.during is not None:
            self.during()
        return super().generate_structured(api_key, request)


@dataclass
class World:
    client: TestClient
    provider: HookedProvider
    owner_db: Database
    org_id: UUID
    author: Member
    admin: Member
    catalogue: Catalogue
    first_model: UUID
    author_headers: dict[str, str]
    question: dict[str, Any]

    def run(
        self, body: dict[str, Any] | None = None, *, headers: dict[str, str] | None = None
    ) -> Any:
        return self.client.post(
            f"{QUESTIONS}/{self.question['id']}/ai/runs",
            json={"operation": "TAG", **(body or {})},
            headers=headers or self.author_headers,
        )

    def labels(self) -> dict[str, Any]:
        response = self.client.get(
            f"{QUESTIONS}/{self.question['id']}", headers=self.author_headers
        )
        assert response.status_code == 200, response.text
        metadata: dict[str, Any] = response.json()["content"]["metadata"]
        return metadata

    def answer(self, **changes: Any) -> StructuredResult:
        data: dict[str, Any] = {
            "chapter_id": str(self.catalogue.chapter_id),
            "topic_id": str(self.catalogue.topic_id),
            "primary_concept_id": str(self.catalogue.concept_id),
            "difficulty": 7,
            "bloom_level": "ANALYZE",
        }
        data.update(changes)
        return StructuredResult(data, 1000, 200)

    def ledger(self, run_id: str) -> list[LedgerEntry]:
        with self.owner_db.transaction(TenantContext(organization_id=self.org_id)) as session:
            return list(
                session.scalars(
                    select(LedgerEntry)
                    .where(LedgerEntry.run_id == UUID(run_id))
                    .order_by(LedgerEntry.created_at)
                )
            )

    def add_model(self, model_id: str, *, enabled: bool = True) -> UUID:
        with self.owner_db.transaction(TenantContext(organization_id=self.org_id)) as session:
            row = AiModel(
                organization_id=self.org_id,
                provider="OPENAI",
                model_id=model_id,
                display_name=model_id,
                supports_json=True,
                overlay_price_in=D(1),
                overlay_price_out=D(2),
                enabled=enabled,
            )
            session.add(row)
            session.flush()
            return row.id

    def set_operation(self, default: UUID | None, fallback: UUID | None = None) -> None:
        with self.owner_db.transaction(TenantContext(organization_id=self.org_id)) as session:
            for row in session.scalars(select(OperationSetting)):
                session.delete(row)
            session.flush()
            for operation in ("TAG", "TRANSLATE", "SOLVE", "VERIFY"):
                session.add(
                    OperationSetting(
                        organization_id=self.org_id,
                        operation=operation,
                        default_model_id=default,
                        fallback_1_id=fallback,
                        updated_by=self.admin.user_id,
                    )
                )


@pytest.fixture
def world(migrated_database: MigratedDatabase, owner_db: Database) -> Iterator[World]:
    settings = Settings(
        app_env=AppEnv.TEST,
        database_url=migrated_database.app_url,
        session_cookie_secure=False,
        ai_keys_master_key=MASTER,  # type: ignore[arg-type]
    )
    with TestClient(create_app(settings)) as client:
        provider = HookedProvider()
        client.app.state.ai_providers = lambda _provider: provider  # type: ignore[attr-defined]
        author = make_member(owner_db, "FACULTY")
        admin = make_member(owner_db, "ADMIN", org_id=author.org_id)
        catalogue = seed_catalogue(owner_db, author.org_id)
        author_headers = sign_in(client, author.email)
        created = client.post(
            QUESTIONS, json={"content": ready_for(catalogue)}, headers=author_headers
        )
        assert created.status_code == 201, created.text
        world = World(
            client,
            provider,
            owner_db,
            author.org_id,
            author,
            admin,
            catalogue,
            UUID(int=0),
            author_headers,
            created.json(),
        )
        admin_client = TestClient(client.app)
        stored = admin_client.put(
            "/api/v1/ai/keys/OPENAI",
            json={"key": KEY},
            headers=sign_in(admin_client, admin.email),
        )
        assert stored.status_code == 200, stored.text
        world.first_model = world.add_model("fake-small")
        world.set_operation(world.first_model)
        yield world
