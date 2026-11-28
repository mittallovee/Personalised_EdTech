"""Application settings, read from environment variables (see ``.env.example``)."""

import re
from enum import StrEnum
from functools import lru_cache
from ipaddress import IPv4Network, IPv6Network
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from qbank.core.secretbox import Keyring, build_keyring
from qbank.core.storage import LocalDiskStorage, S3Storage, Storage

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
    # Port for the Prometheus /metrics page (ADR-0019); 0 = off. Never published to the host.
    metrics_port: int = Field(default=0, ge=0, le=65535)
    # Traces go to this OTLP/HTTP address (the OpenTelemetry Collector) when set; off when empty.
    otel_exporter_otlp_endpoint: str = ""
    otel_traces_sample_ratio: float = Field(default=1.0, ge=0, le=1)

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

    # Syllabus import uploads (ADR-0018, K-10a): per signed-in user, and how many files this API
    # process reads at the same time. One parse costs up to about 3 s of a processor and 25 MB.
    import_uploads_per_user: int = Field(default=10, ge=1)
    import_upload_window_seconds: int = Field(default=600, ge=1)
    import_parses_at_once: int = Field(default=2, ge=1)

    # Document uploads (M6 6b, G-01): per signed-in user, and how many files of one coaching may be
    # waiting or being read at once. Documents are only stored here, never parsed (ADR-0024).
    ingest_uploads_per_user: int = Field(default=10, ge=1)
    ingest_upload_window_seconds: int = Field(default=600, ge=1)
    ingest_files_in_flight: int = Field(default=20, ge=1)

    # Free-text search of the bank (F-03): per signed-in user, and how long the database may spend
    # on one search before it stops it (a very common word over a very large bank).
    searches_per_user: int = Field(default=60, ge=1)
    search_window_seconds: int = Field(default=60, ge=1)
    search_timeout_ms: int = Field(default=5000, ge=100)

    # Where uploaded files are kept (ADR-0012): a folder, in production a mounted volume. Picture
    # uploads (D-07) are limited per signed-in user, and pictures decoded at the same time (one
    # decode costs a processor for up to about a second and up to 160 MB for a 40-megapixel one).
    storage_dir: Path = SERVICE_ROOT / ".storage"
    # "local" (the folder above) or "s3" (a private bucket, ADR-0025; credentials come from the
    # server's role, never from settings).
    storage_backend: Literal["local", "s3"] = "local"
    storage_s3_bucket: str | None = None
    storage_s3_region: str | None = None
    asset_uploads_per_user: int = Field(default=60, ge=1)
    asset_upload_window_seconds: int = Field(default=600, ge=1)
    image_decodes_at_once: int = Field(default=2, ge=1)

    # Google sign-in (B-02) is off until both are set; see docs/operations/google-login.md. The
    # secret never appears in logs or reprs (SecretStr) and must never be committed.
    google_client_id: str | None = None
    google_client_secret: SecretStr | None = None

    # The master encryption key for coaching AI keys (ADR-0023): 32 random bytes as base64, kept
    # outside the database and its backups. Without it the app runs and AI keys cannot be stored.
    # Earlier keys, still needed to open keys sealed before a rotation: "id=base64,id=base64".
    ai_keys_master_key: SecretStr | None = None
    ai_keys_master_key_id: str = "k1"
    ai_keys_previous: SecretStr | None = None

    # Answer every AI call with the built-in demo provider instead of a real one (no network, no
    # real key): for trying the screens and for the browser tests. Refused outside local development
    # and tests, so a hosted system can never silently serve made-up answers.
    ai_demo_provider: bool = False

    # Web addresses allowed to send changes (POST/PUT/PATCH/DELETE) from a browser; see
    # core/origin.py. JSON list, e.g. ALLOWED_ORIGINS='["https://app.example.com"]'.
    allowed_origins: list[str] = Field(default=["http://localhost:3000"], min_length=1)

    # Who the client is, for per-IP sign-in limits (core/clientip.py, ADR-0014). Behind a proxy
    # that sets a header clients cannot forge (Cloudflare: CF-Connecting-IP), name it here; it is
    # believed only from TRUSTED_PROXIES addresses. Unset: the connection's own address is used.
    client_ip_header: str | None = None
    trusted_proxies: list[IPv4Network | IPv6Network] = Field(
        default=[IPv4Network("127.0.0.1/32"), IPv6Network("::1/128")]
    )

    @field_validator(
        "client_ip_header",
        "google_client_id",
        "google_client_secret",
        "ai_keys_master_key",
        "ai_keys_previous",
        mode="before",
    )
    @classmethod
    def _blank_means_none(cls, value: object) -> object:
        return None if isinstance(value, str) and not value.strip() else value

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
    def _ai_keys_are_well_formed(self) -> Settings:
        """A wrong master key must stop the app at start, not fail later on someone's key. The
        message names the setting and never the value."""
        try:
            self.ai_keyring()
        except ValueError as problem:
            raise ValueError(f"AI_KEYS_MASTER_KEY / AI_KEYS_PREVIOUS: {problem}") from None
        return self

    def ai_keyring(self) -> Keyring | None:
        """The master keys of this process, or None when AI keys are not set up (ADR-0023)."""
        master, previous = self.ai_keys_master_key, self.ai_keys_previous
        return build_keyring(
            master.get_secret_value() if master else None,
            self.ai_keys_master_key_id,
            previous.get_secret_value() if previous else None,
        )

    def storage(self) -> Storage:
        """Where uploaded files live: the folder, or the S3 bucket when so configured."""
        if self.storage_backend == "s3":
            return S3Storage(self.storage_s3_bucket or "", self.storage_s3_region)
        return LocalDiskStorage(self.storage_dir)

    @model_validator(mode="after")
    def _s3_needs_a_bucket(self) -> Settings:
        if self.storage_backend == "s3" and not self.storage_s3_bucket:
            raise ValueError("STORAGE_S3_BUCKET must be set when STORAGE_BACKEND=s3")
        return self

    @model_validator(mode="after")
    def _google_needs_both_values(self) -> Settings:
        if (self.google_client_id is None) != (self.google_client_secret is None):
            raise ValueError("GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set together")
        return self

    @model_validator(mode="after")
    def _refuse_unsafe_production_settings(self) -> Settings:
        hosted = self.app_env in (AppEnv.STAGING, AppEnv.PRODUCTION)
        if hosted and not self.session_cookie_secure:
            raise ValueError("SESSION_COOKIE_SECURE must be true outside local development")
        if hosted and any(not origin.startswith("https://") for origin in self.allowed_origins):
            raise ValueError("ALLOWED_ORIGINS must use https outside local development")
        if hosted and self.ai_demo_provider:
            raise ValueError("AI_DEMO_PROVIDER must not be set outside local development")
        return self


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings, parsed once."""
    return Settings()
