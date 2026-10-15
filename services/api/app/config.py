from __future__ import annotations

import re
from enum import StrEnum
from functools import lru_cache
from urllib.parse import urlparse

from pydantic_settings import BaseSettings, SettingsConfigDict

# Only true loopback addresses are considered local.  0.0.0.0 and *.local are NOT.
_LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})


class AppEnvironment(StrEnum):
    LOCAL = "local"
    TEST = "test"
    PRODUCTION = "production"


def _is_loopback_database(url: str) -> bool:
    """Return True only when the database host is a loopback address."""
    try:
        normalised = re.sub(r"^postgresql(\+\w+)?://", "postgresql://", url)
        host = urlparse(normalised).hostname or ""
        return host in _LOOPBACK_HOSTS
    except Exception:
        return False


def _normalise_supabase_url(url: str) -> str:
    """Strip trailing slashes; raise if the URL is not an https:// URL."""
    stripped = url.rstrip("/")
    if stripped and not stripped.startswith("https://"):
        raise ValueError(f"SUPABASE_URL must start with https://, got: {stripped!r}")
    return stripped


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://nosh:nosh_dev@localhost:5432/nosh_dev"

    # Environment — controls which auth adapters are allowed.
    # Allowed values: local | test | production
    app_environment: AppEnvironment = AppEnvironment.LOCAL

    # Auth — UUID bypass is only permitted in local/test environments.
    auth_local_dev: bool = False

    # Supabase credentials.
    # SUPABASE_URL is required for all production-mode auth (both HS256 and RS256)
    # because the issuer must be validated against it.
    supabase_url: str = ""

    # JWT Secret (HS256 legacy mode): from Supabase → Settings → API → JWT Secret.
    # When set alongside SUPABASE_URL, HS256 is used.
    # When empty, RS256 via JWKS is used (preferred for new projects).
    supabase_jwt_secret: str = ""

    # CORS — comma-separated list of allowed origins.
    # A native mobile app does not need CORS; leave empty to disable entirely.
    cors_origins: str = ""

    # App
    api_version: str = "0.1.0"
    log_level: str = "INFO"

    # ------------------------------------------------------------------ #
    # Derived properties
    # ------------------------------------------------------------------ #

    @property
    def async_database_url(self) -> str:
        url = self.database_url
        url = re.sub(r"^postgresql(\+\w+)?://", "postgresql+asyncpg://", url)
        return url

    @property
    def sync_database_url(self) -> str:
        url = self.database_url
        url = re.sub(r"^postgresql(\+\w+)?://", "postgresql+psycopg2://", url)
        return url

    @property
    def normalised_supabase_url(self) -> str:
        """Supabase URL with trailing slash removed."""
        return self.supabase_url.rstrip("/")

    @property
    def allowed_origins(self) -> list[str]:
        if not self.cors_origins:
            return []
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def supabase_issuer(self) -> str:
        """Expected JWT issuer: {normalised_SUPABASE_URL}/auth/v1"""
        base = self.normalised_supabase_url
        return f"{base}/auth/v1" if base else ""

    @property
    def supabase_jwks_url(self) -> str:
        base = self.normalised_supabase_url
        return f"{base}/auth/v1/.well-known/jwks.json" if base else ""

    # ------------------------------------------------------------------ #
    # Startup validation
    # ------------------------------------------------------------------ #

    def validate_auth_config(self) -> None:
        """Raise at startup when the configuration is unsafe or incomplete.

        Rules:
        - UUID-bypass auth (auth_local_dev=True) is only allowed when
          app_environment is LOCAL or TEST *and* DATABASE_URL is a loopback.
        - Production mode requires both SUPABASE_URL and either
          SUPABASE_JWT_SECRET (HS256) or SUPABASE_URL alone (RS256 via JWKS).
        - SUPABASE_URL must be an https:// URL.
        """
        is_local_env = self.app_environment in (AppEnvironment.LOCAL, AppEnvironment.TEST)

        if self.auth_local_dev:
            if not is_local_env:
                raise RuntimeError(
                    "AUTH_LOCAL_DEV=true requires APP_ENVIRONMENT=local or test. "
                    f"Current environment: {self.app_environment.value!r}"
                )
            if not _is_loopback_database(self.database_url):
                raise RuntimeError(
                    "AUTH_LOCAL_DEV=true is not permitted when DATABASE_URL points to a "
                    "non-loopback host (only localhost, 127.0.0.1, and ::1 are allowed). "
                    "Set APP_ENVIRONMENT=production and supply SUPABASE_URL."
                )
            return  # local dev permitted; skip further checks

        # Production path
        if not self.normalised_supabase_url:
            raise RuntimeError(
                "SUPABASE_URL must be set in production mode. "
                "Without it, the JWT issuer cannot be verified."
            )

        # Validate the URL is syntactically correct.
        try:
            _normalise_supabase_url(self.normalised_supabase_url)
        except ValueError as exc:
            raise RuntimeError(str(exc)) from exc


@lru_cache
def get_settings() -> Settings:
    return Settings()
