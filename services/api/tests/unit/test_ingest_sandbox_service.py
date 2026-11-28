"""M6 PR 6a, test T59: the document worker's compose service keeps its sandbox settings (K-17).

Parsing untrusted files is only safe in a worker that cannot reach anything. These tests read
``compose.yaml`` and fail if one of those settings is loosened, so the sandbox cannot be weakened
by accident in a later change.
"""

from pathlib import Path
from typing import Any

import pytest
import yaml

COMPOSE = Path(__file__).resolve().parents[4] / "compose.yaml"


@pytest.fixture(scope="module")
def compose() -> dict[str, Any]:
    document: dict[str, Any] = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
    return document


@pytest.fixture(scope="module")
def sandbox(compose: dict[str, Any]) -> dict[str, Any]:
    service: dict[str, Any] = compose["services"]["ingest-worker"]
    return service


def test_the_sandbox_runs_the_document_worker_and_nothing_else(sandbox: dict[str, Any]) -> None:
    assert sandbox["command"] == ["python", "-m", "qbank.ingest_worker"]


def test_the_sandbox_has_no_route_out(compose: dict[str, Any], sandbox: dict[str, Any]) -> None:
    assert sandbox["networks"] == ["ingest"]  # only the internal network, not the default one
    assert compose["networks"]["ingest"]["internal"] is True
    assert "ports" not in sandbox
    # The database is the only other thing on that network.
    on_ingest = [
        name
        for name, service in compose["services"].items()
        if "ingest" in (service.get("networks") or [])
    ]
    assert sorted(on_ingest) == ["ingest-worker", "postgres"]


def test_the_sandbox_has_a_read_only_filesystem_and_no_privileges(sandbox: dict[str, Any]) -> None:
    assert sandbox["read_only"] is True
    assert sandbox["cap_drop"] == ["ALL"]
    assert "no-new-privileges:true" in sandbox["security_opt"]
    assert all(tmp.startswith("/tmp:") for tmp in sandbox["tmpfs"])  # noqa: S108  # only a scratch folder


def test_the_sandbox_has_resource_caps(sandbox: dict[str, Any]) -> None:
    assert sandbox["mem_limit"] == "1g"
    assert float(sandbox["cpus"]) <= 1.0
    assert 0 < int(sandbox["pids_limit"]) <= 256


def test_the_sandbox_connects_with_its_own_restricted_role(sandbox: dict[str, Any]) -> None:
    url = sandbox["environment"]["DATABASE_URL"]
    assert url.startswith("postgresql+psycopg://qbank_ingest:")


def test_the_sandbox_gets_no_secrets_it_does_not_need(sandbox: dict[str, Any]) -> None:
    names = set(sandbox["environment"])
    assert not {n for n in names if n.startswith(("AI_", "GOOGLE_"))}


@pytest.mark.parametrize("name", ["api", "worker", "ingest-worker"])
def test_every_service_that_touches_uploaded_files_sees_the_same_storage(
    compose: dict[str, Any], name: str
) -> None:
    """The api stores originals, the sandbox makes page pictures, the worker sends them to the AI:
    all three must share one place (a worker without it would find every picture missing)."""
    service = compose["services"][name]
    assert service["environment"]["STORAGE_DIR"] == "/data/storage"
    assert "assetdata:/data/storage" in service["volumes"]
    assert "STORAGE_BACKEND" in service["environment"]
