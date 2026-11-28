"""M6 PR 6j, test T63: golden sets, and measuring a model's reading against them.

Admins freeze accepted questions into a named key. The measurement reads the key's pages again with
a model (here a scripted fake that returns exactly what is scripted) and scores the result; the
fake lets the harness itself be checked in CI, while the quality of a real model on real papers is
measured by the owner with ``qbank ingest-measure``.
"""

from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from sqlalchemy import select

from qbank.core.storage import LocalDiskStorage
from qbank.core.tenancy import TenantContext
from qbank.modules.ingestion.golden import live_reader, measure
from qbank.modules.ingestion.models import GoldenCase
from tests import ingest_samples as samples
from tests.integration import test_ingest_extract as extract_tests
from tests.integration.test_ingest_extract import INGEST, World, reading

# The document world (a stack with a scripted model) is shared with the extraction tests.
empty_queue = extract_tests.empty_queue
world = extract_tests.world

SETS = f"{INGEST}/golden-sets"


@pytest.fixture
def key_ready(world: World) -> tuple[World, str, list[dict[str, Any]]]:
    """A rendered and read document, both of its page-1 questions accepted by Anita."""
    file_id = world.upload_and_render(samples.pdf())
    world.provider.script.append(reading("What is 2 + 3?", "What is 4 + 5?"))
    world.extract(file_id)
    world.run_worker()
    found = world.candidates(file_id)
    for candidate in found:
        done = world.client.post(
            f"{INGEST}/candidates/{candidate['id']}/accept", headers=world.headers("faculty")
        )
        assert done.status_code == 200, done.text
    return world, file_id, found


def make_set(world: World, name: str = "Unit tests") -> str:
    made = world.client.post(SETS, json={"name": name}, headers=world.headers("owner"))
    assert made.status_code == 201, made.text
    return str(made.json()["id"])


def test_only_admins_keep_golden_sets_and_names_are_unique(world: World) -> None:
    denied = world.client.post(SETS, json={"name": "x"}, headers=world.headers("faculty"))
    assert denied.status_code == 403
    set_id = make_set(world)
    again = world.client.post(SETS, json={"name": " Unit   tests "}, headers=world.headers("owner"))
    assert again.status_code == 409 and again.json()["error"]["code"] == "GOLDEN_SET_EXISTS"
    assert world.client.get(SETS, headers=world.headers("faculty")).status_code == 403
    listed = world.client.get(SETS, headers=world.headers("owner")).json()["data"]
    assert [(s["id"], s["name"], s["cases"]) for s in listed] == [(set_id, "Unit tests", 0)]
    assert world.client.get(SETS, headers=world.headers("stranger")).status_code == 403


def test_only_an_accepted_question_joins_the_key_once(
    key_ready: tuple[World, str, list[dict[str, Any]]],
) -> None:
    world, file_id, found = key_ready
    set_id = make_set(world)
    add = f"{SETS}/{set_id}/cases"
    # A fresh candidate (not accepted): read the document again for one.
    world.provider.script.append(reading("A new one"))
    world.extract(file_id)
    world.run_worker()
    waiting = [c for c in world.candidates(file_id) if c["state"] == "NEW"]
    assert waiting
    refused = world.client.post(
        add, json={"candidate_id": waiting[0]["id"]}, headers=world.headers("owner")
    )
    assert refused.status_code == 409 and refused.json()["error"]["code"] == "GOLDEN_NOT_ACCEPTED"
    assert (
        world.client.post(
            add, json={"candidate_id": found[0]["id"]}, headers=world.headers("faculty")
        ).status_code
        == 403
    )
    added = world.client.post(
        add, json={"candidate_id": found[0]["id"]}, headers=world.headers("owner")
    )
    assert added.status_code == 201 and added.json()["page_no"] == 1
    twice = world.client.post(
        add, json={"candidate_id": found[0]["id"]}, headers=world.headers("owner")
    )
    assert twice.status_code == 409 and twice.json()["error"]["code"] == "GOLDEN_CASE_EXISTS"
    listed = world.client.get(SETS, headers=world.headers("owner")).json()["data"]
    assert listed[0]["cases"] == 1
    # Another coaching's admin sees none of it.
    assert world.client.post(
        f"{SETS}/{set_id}/cases",
        json={"candidate_id": found[0]["id"]},
        headers=world.headers("stranger"),
    ).status_code in (403, 404)


def test_a_case_freezes_what_the_person_finished(
    key_ready: tuple[World, str, list[dict[str, Any]]],
) -> None:
    world, _file_id, found = key_ready
    set_id = make_set(world)
    world.client.post(
        f"{SETS}/{set_id}/cases",
        json={"candidate_id": found[0]["id"]},
        headers=world.headers("owner"),
    )
    org = world.team["owner"].org_id
    with world.owner_db.transaction(TenantContext(organization_id=org)) as session:
        case = session.scalars(select(GoldenCase).where(GoldenCase.set_id == UUID(set_id))).one()
        assert case.expected["stem"][0]["text"] == "What is 2 + 3?"
        assert case.page_no == 1 and str(case.candidate_id) == found[0]["id"]


def measured(world: World, set_id: str, storage_dir: Path) -> Any:
    org = world.team["owner"].org_id
    with world.owner_db.transaction(TenantContext(organization_id=org)) as session:
        cases = list(session.scalars(select(GoldenCase).where(GoldenCase.set_id == UUID(set_id))))
        reader = live_reader(
            session, LocalDiskStorage(storage_dir), world.provider, "fake-key", "fake-vision"
        )
        return measure(cases, reader)


def test_the_harness_scores_the_fake_model_on_known_cases(
    key_ready: tuple[World, str, list[dict[str, Any]]],
) -> None:
    world, _file_id, found = key_ready
    set_id = make_set(world)
    for candidate in found:
        world.client.post(
            f"{SETS}/{set_id}/cases",
            json={"candidate_id": candidate["id"]},
            headers=world.headers("owner"),
        )
    calls_before = len(world.provider.calls)

    # A model that reads page 1 exactly as the key says: everything right, the page read once.
    world.provider.script.append(reading("What is 2 + 3?", "What is 4 + 5?"))
    report = measured(world, set_id, world.storage_dir)
    assert len(world.provider.calls) == calls_before + 1
    assert (report.cases, report.found, report.perfect, report.extra) == (2, 2, 2, 0)
    assert report.tokens_in == 900 and report.tokens_out == 300
    request = world.provider.calls[-1][1]
    assert request.images, "the page picture is sent"

    # A model that gets one answer wrong, misses one question and adds one that is not in the key.
    wrong = reading("What is 2 + 3?", "Something else entirely")
    wrong.data["questions"][0]["answer_text"] = "C"
    world.provider.script.append(wrong)
    report = measured(world, set_id, world.storage_dir)
    assert report.found == 1 and report.perfect == 0 and report.extra == 1
    assert report.right["answer"] == 0 and report.right["text"] == 1

    # A model that fails: the page is reported, nothing is found.
    world.provider.script.append(reading("x", questions="nope"))
    report = measured(world, set_id, world.storage_dir)
    assert report.found == 0 and report.pages_failed == 1
