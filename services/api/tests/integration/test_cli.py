import pytest

from qbank import cli
from tests.integration.conftest import MigratedDatabase


@pytest.fixture
def owner_env(monkeypatch: pytest.MonkeyPatch, migrated_database: MigratedDatabase) -> None:
    monkeypatch.setenv("MIGRATION_DATABASE_URL", migrated_database.owner_url)
    monkeypatch.setattr(cli.getpass, "getpass", lambda _prompt: "a-long-enough-password")


@pytest.mark.usefixtures("owner_env")
def test_create_platform_admin_once(capsys: pytest.CaptureFixture[str]) -> None:
    args = ["create-platform-admin", "--email", "boss@example.com", "--name", "Boss"]

    assert cli.main(args) == 0
    assert "Platform admin created: boss@example.com" in capsys.readouterr().out
    assert cli.main(args) == 1  # same email again
    assert "already exists" in capsys.readouterr().err


@pytest.mark.usefixtures("owner_env")
def test_create_platform_admin_rejects_bad_email() -> None:
    assert cli.main(["create-platform-admin", "--email", "not-an-email", "--name", "X"]) == 2
