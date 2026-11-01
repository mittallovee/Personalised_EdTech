"""M3 PR 3b-5: a question's labels are checked against its own coaching's lists (D-15, C-04).

The pure rules are in ``tests/unit/test_question_catalogue_checks.py``; here the lookup reads the
real tables, including row-level security (another coaching's ids are simply not found).
"""

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from qbank.core.config import AppEnv, Settings
from qbank.core.db import Database
from qbank.core.ids import new_id
from qbank.core.tenancy import TenantContext
from qbank.main import create_app
from qbank.modules.taxonomy.models import Concept, TaxonomyNode
from tests.integration.conftest import Member, MigratedDatabase, make_member, sign_in
from tests.integration.question_support import Catalogue, ready_for, seed_catalogue, seed_exam

PATH = "/api/v1/questions"


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
def author(owner_db: Database) -> Member:
    return make_member(owner_db, "FACULTY")


@pytest.fixture
def catalogue(owner_db: Database, author: Member) -> Catalogue:
    return seed_catalogue(owner_db, author.org_id)


def start(client: TestClient, author: Member, content: dict[str, Any]) -> dict[str, Any]:
    headers = sign_in(client, author.email)
    response = client.post(PATH, json={"content": content}, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def findings(question: dict[str, Any]) -> list[tuple[str, str, str]]:
    return [(f["path"], f["code"], f["level"]) for f in question["findings"]]


def test_labels_from_the_coachings_own_lists_have_no_findings(
    client: TestClient, author: Member, catalogue: Catalogue
) -> None:
    assert start(client, author, ready_for(catalogue))["findings"] == []


def test_another_coachings_ids_are_not_found(
    client: TestClient, owner_db: Database, author: Member
) -> None:
    other = make_member(owner_db, "OWNER", coaching_name="Other Coaching")
    theirs = seed_catalogue(owner_db, other.org_id)
    question = start(client, author, ready_for(theirs))
    assert [code for _, code, _ in findings(question)] == ["CATALOGUE_ID_UNKNOWN"] * 5
    assert {level for _, _, level in findings(question)} == {"error"}


def test_an_id_of_the_wrong_kind_and_a_mixed_up_branch(
    client: TestClient, owner_db: Database, author: Member, catalogue: Catalogue
) -> None:
    content = ready_for(catalogue)
    content["metadata"]["topic_id"] = str(catalogue.chapter_id)
    assert findings(start(client, author, content)) == [
        ("metadata.topic_id", "CATALOGUE_KIND_WRONG", "error")
    ]

    other_chapter = new_id()
    with owner_db.transaction(TenantContext(organization_id=author.org_id)) as session:
        other_subject = new_id()
        for node_id, kind, parent, parent_kind, name in (
            (other_subject, "SUBJECT", catalogue.class_id, "CLASS", "Chemistry"),
            (other_chapter, "CHAPTER", other_subject, "SUBJECT", "Atoms"),
        ):
            session.add(
                TaxonomyNode(
                    id=node_id,
                    organization_id=author.org_id,
                    kind=kind,
                    parent_id=parent,
                    parent_kind=parent_kind,
                    name=name,
                    name_key=name.lower(),
                )
            )
            session.flush()
        stranger_concept = new_id()
        session.add(
            Concept(
                id=stranger_concept,
                organization_id=author.org_id,
                subject_id=other_subject,
                name="Mole",
                name_key="mole",
            )
        )
    content = ready_for(catalogue)
    content["metadata"]["chapter_id"] = str(other_chapter)  # a Chemistry chapter under Physics
    content["metadata"]["primary_concept_id"] = str(stranger_concept)
    assert findings(start(client, author, content)) == [
        ("metadata.chapter_id", "HIERARCHY_MISMATCH", "error"),
        ("metadata.topic_id", "HIERARCHY_MISMATCH", "error"),
        ("metadata.primary_concept_id", "CONCEPT_SUBJECT_MISMATCH", "error"),
    ]


def test_a_retired_item_warns_on_the_next_read_and_nothing_is_stored(
    client: TestClient, owner_db: Database, author: Member, catalogue: Catalogue
) -> None:
    question = start(client, author, ready_for(catalogue))
    assert question["findings"] == []
    with owner_db.transaction(TenantContext(organization_id=author.org_id)) as session:
        session.execute(
            text("UPDATE taxonomy_nodes SET state = 'DEPRECATED' WHERE id = :id"),
            {"id": catalogue.chapter_id},
        )
    read = client.get(f"{PATH}/{question['id']}").json()
    assert findings(read) == [("metadata.chapter_id", "DEPRECATED_REFERENCE", "warning")]
    assert read["content"] == question["content"]  # the labels it was written with are kept


def test_exam_and_source_are_checked_and_the_list_counts_the_findings(
    client: TestClient, owner_db: Database, author: Member, catalogue: Catalogue
) -> None:
    exam = seed_exam(owner_db, author.org_id)
    content = ready_for(catalogue)
    content["metadata"].update({"is_pyq": True, "exam_id": str(exam), "exam_year": 2024})
    assert start(client, author, content)["findings"] == []
    content["metadata"]["exam_id"] = str(new_id())
    bad = start(client, author, content)
    assert findings(bad) == [("metadata.exam_id", "CATALOGUE_ID_UNKNOWN", "error")]
    rows = client.get(PATH).json()["data"]
    assert [row["finding_counts"]["error"] for row in rows] == [1, 0]  # newest first
