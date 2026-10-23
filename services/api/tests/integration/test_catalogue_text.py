"""M3 PR 2b: text in the catalogues has no control characters (a NUL would crash the database)."""

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from qbank.core.config import AppEnv, Settings
from qbank.core.db import Database
from qbank.main import create_app
from tests.integration.conftest import MigratedDatabase, make_member, sign_in

NODES = "/api/v1/taxonomy/nodes"
CONCEPTS = "/api/v1/taxonomy/concepts"
EXAMS = "/api/v1/exams"
SOURCES = "/api/v1/sources"


@pytest.fixture
def client(migrated_database: MigratedDatabase) -> Iterator[TestClient]:
    settings = Settings(
        app_env=AppEnv.TEST,
        database_url=migrated_database.app_url,
        session_cookie_secure=False,
    )
    with TestClient(create_app(settings)) as test_client:
        yield test_client


@pytest.fixture
def headers(client: TestClient, owner_db: Database) -> dict[str, str]:
    return sign_in(client, make_member(owner_db, "ADMIN").email)


@pytest.fixture
def subject(client: TestClient, headers: dict[str, str]) -> str:
    cls = client.post(NODES, json={"kind": "CLASS", "name": "Class 11"}, headers=headers).json()
    body = {"kind": "SUBJECT", "parent_id": cls["id"], "name": "Physics"}
    return client.post(NODES, json=body, headers=headers).json()["id"]


BAD = ["\x00", "a\x00b", "line one\nline two", "tab\there", "bell\x07", "\x7f"]


@pytest.mark.parametrize("bad", BAD, ids=["nul", "nul-inside", "newline", "tab", "bell", "delete"])
def test_names_labels_aliases_and_codes_with_control_characters_are_a_400_not_a_500(
    client: TestClient, headers: dict[str, str], subject: str, bad: str
) -> None:
    requests: list[tuple[str, dict[str, Any]]] = [
        (NODES, {"kind": "CLASS", "name": bad}),
        (NODES, {"kind": "CLASS", "name": "Class 12", "labels": {"hi": bad}}),
        (CONCEPTS, {"subject_id": subject, "name": bad}),
        (CONCEPTS, {"subject_id": subject, "name": "Work", "labels": {"hi": bad}}),
        (CONCEPTS, {"subject_id": subject, "name": "Energy", "aliases": [bad]}),
        (EXAMS, {"name": bad}),
        (EXAMS, {"name": "JEE Main", "short_code": bad}),
        (SOURCES, {"kind": "BOOK", "name": bad}),
    ]

    for path, body in requests:
        response = client.post(path, json=body, headers=headers)
        assert (response.status_code, response.json()["error"]["code"]) == (
            400,
            "MALFORMED_REQUEST",
        ), (path, body)


def test_renames_and_searches_with_control_characters_are_a_400_too(
    client: TestClient, headers: dict[str, str], subject: str
) -> None:
    concept = client.post(
        CONCEPTS, json={"subject_id": subject, "name": "Work"}, headers=headers
    ).json()
    exam = client.post(EXAMS, json={"name": "JEE Main"}, headers=headers).json()
    stale = {**headers, "If-Match": '"rev-1"'}

    responses = [
        client.patch(f"{CONCEPTS}/{concept['id']}", json={"name": "a\x00b"}, headers=stale),
        client.patch(f"{CONCEPTS}/{concept['id']}", json={"aliases": ["\x00"]}, headers=stale),
        client.patch(f"{EXAMS}/{exam['id']}", json={"short_code": "\x00"}, headers=stale),
        client.get(CONCEPTS, params={"q": "a\x00b"}),
    ]

    assert [response.status_code for response in responses] == [400, 400, 400, 400]


def test_ordinary_names_in_any_script_are_still_accepted(
    client: TestClient, headers: dict[str, str]
) -> None:
    names = ["Class 11", "कक्षा ११", "Résumé — naïve", "質量とエネルギー", "a‍b"]  # joiner too

    for name in names:
        response = client.post(NODES, json={"kind": "CLASS", "name": name}, headers=headers)
        assert response.status_code == 201, name
