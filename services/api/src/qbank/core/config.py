"""Application settings, read from environment variables (see ``.env.example``)."""

from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# services/api/ — the folder holding alembic.ini and migrations/.
SERVICE_ROOT = Path(__file__).resolve().parents[3]


class AppEnv(StrEnum):
    LOCAL = "local"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Process configuration. Required values have no default: startup fails if one is missing."""

    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    app_env: AppEnv = AppEnv.LOCAL
    log_level: str = "INFO"

    # Runtime connection: the restricted `qbank_app` role (never the table owner). See ADR-0005.
    database_url: str = Field(min_length=1)

    migrations_dir: Path = SERVICE_ROOT / "migrations"


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings, parsed once."""
    return Settings()
