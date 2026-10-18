"""Application settings, read from environment variables (see ``.env.example``)."""

from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator
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

    # Sessions and login (B-01, B-11). Cookies are Secure except on plain-http local development.
    session_cookie_secure: bool = True
    session_idle_minutes: int = Field(default=12 * 60, ge=5)
    session_absolute_days: int = Field(default=7, ge=1)
    login_max_failures: int = Field(default=5, ge=1)
    login_lock_minutes: int = Field(default=15, ge=1)

    @model_validator(mode="after")
    def _refuse_unsafe_production_settings(self) -> Settings:
        if self.app_env in (AppEnv.STAGING, AppEnv.PRODUCTION) and not self.session_cookie_secure:
            raise ValueError("SESSION_COOKIE_SECURE must be true outside local development")
        return self


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings, parsed once."""
    return Settings()
