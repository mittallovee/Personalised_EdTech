"""M2 PR 8a: Google sign-in is configured with a client ID and secret, together or not at all."""

import pytest
from pydantic import ValidationError

from qbank.core.config import AppEnv, Settings


def settings(**values: str) -> Settings:
    return Settings(app_env=AppEnv.TEST, database_url="postgresql+psycopg://x/y", **values)  # type: ignore[arg-type]


def test_google_is_off_by_default() -> None:
    config = settings()
    assert config.google_client_id is None
    assert config.google_client_secret is None


def test_blank_values_count_as_not_set() -> None:
    # `.env` files and compose pass empty strings for unset values.
    config = settings(google_client_id="", google_client_secret="")
    assert config.google_client_id is None
    assert config.google_client_secret is None


def test_both_values_together_turn_it_on() -> None:
    config = settings(
        google_client_id="id.apps.googleusercontent.com", google_client_secret="s3cret"
    )
    assert config.google_client_secret is not None
    assert config.google_client_secret.get_secret_value() == "s3cret"


@pytest.mark.parametrize("only", [{"google_client_id": "id"}, {"google_client_secret": "s3cret"}])
def test_one_without_the_other_is_refused(only: dict[str, str]) -> None:
    with pytest.raises(ValidationError, match="must be set together"):
        settings(**only)


def test_the_secret_does_not_show_in_the_settings_text() -> None:
    config = settings(google_client_id="id", google_client_secret="s3cret-value")
    assert "s3cret-value" not in repr(config)
    assert "s3cret-value" not in str(config)
