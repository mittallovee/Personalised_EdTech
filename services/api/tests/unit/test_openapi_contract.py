"""M1 exit test T12: the committed API contract (api/openapi.json) matches the code.

Every client (web app now, mobile apps and partners later) is built from that file, so an API
change must show up as a reviewed change to it. Regenerate with ``make openapi``.
"""

from pathlib import Path

from qbank.cli import main
from qbank.contract import OPENAPI_FILE, render_openapi


def test_committed_contract_matches_the_code() -> None:
    assert OPENAPI_FILE.read_text(encoding="utf-8") == render_openapi(), (
        "The API changed: run `make openapi` and commit api/openapi.json"
    )


def test_export_writes_the_contract(tmp_path: Path) -> None:
    target = tmp_path / "openapi.json"

    assert main(["export-openapi", "--output", str(target)]) == 0
    assert target.read_text(encoding="utf-8") == render_openapi()


def test_check_fails_when_the_contract_is_stale(tmp_path: Path) -> None:
    stale = tmp_path / "openapi.json"
    stale.write_text("{}\n", encoding="utf-8")

    assert main(["export-openapi", "--check", "--output", str(stale)]) == 1
    assert main(["export-openapi", "--check", "--output", str(tmp_path / "missing.json")]) == 1
