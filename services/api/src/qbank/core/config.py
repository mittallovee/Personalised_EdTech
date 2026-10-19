"""Application settings, read from environment variables (see ``.env.example``)."""

import re
from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# services/api/ — the folder holding alembic.ini and migrations/.
SERVICE_ROOT = Path(__file__).resolve().parents[3]

# An origin is scheme://host[:port], nothing else (no path, no trailing slash, no wildcard).
_ORIGIN = re.compile(r"https?://[a-z0-9.-]+(:[0-9]{1,5})?")
_DEFAULT_PORTS = {"http": "80", "https": "443"}


def without_default_port(origin: str) -> str:
    """Browsers omit a scheme's default port (https://x, never https://x:443); so do we."""
    scheme, _, rest = origin.partition("://")
    host, _, port = rest.partition(":")
    return f"{scheme}://{host}" if port == _DEFAULT_PORTS.get(scheme) else origin


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
    # Throttle before any lookup or password hashing (protects CPU/memory from login floods).
    login_attempts_per_ip: int = Field(default=20, ge=1)
    login_attempts_per_email: int = Field(default=10, ge=1)
    login_rate_window_seconds: int = Field(default=300, ge=1)

    # Web addresses allowed to send changes (POST/PUT/PATCH/DELETE) from a browser; see
    # core/origin.py. JSON list, e.g. ALLOWED_ORIGINS='["https://app.example.com"]'.
    allowed_origins: list[str] = Field(default=["http://localhost:3000"], min_length=1)

    @field_validator("allowed_origins")
    @classmethod
    def _plain_origins(cls, origins: list[str]) -> list[str]:
        normalised = [origin.lower() for origin in origins]
        for origin in normalised:
            if not _ORIGIN.fullmatch(origin):
                raise ValueError(
                    f"ALLOWED_ORIGINS entries must look like https://host[:port], got {origin!r}"
                )
        return [without_default_port(origin) for origin in normalised]

    @model_validator(mode="after")
    def _refuse_unsafe_production_settings(self) -> Settings:
        hosted = self.app_env in (AppEnv.STAGING, AppEnv.PRODUCTION)
        if hosted and not self.session_cookie_secure:
            raise ValueError("SESSION_COOKIE_SECURE must be true outside local development")
        if hosted and any(not origin.startswith("https://") for origin in self.allowed_origins):
            raise ValueError("ALLOWED_ORIGINS must use https outside local development")
        return self


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings, parsed once."""
    return Settings()
