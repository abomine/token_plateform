"""Normalize and expose runtime settings for local + Railway."""

from __future__ import annotations

import os
from functools import lru_cache
from urllib.parse import quote_plus, urlparse

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Railway / Heroku-style names, checked in order when database_url is unset.
_DATABASE_URL_ENV_KEYS = (
    "DATABASE_URL",
    "DATABASE_PRIVATE_URL",
    "POSTGRES_URL",
    "DATABASE_PUBLIC_URL",
)


def normalize_database_url(url: str) -> str:
    """Make Railway / Heroku DATABASE_URL usable by asyncpg.

    - postgres:// -> postgresql://
    - strip +asyncpg / +psycopg2 driver suffixes if present
    """
    value = (url or "").strip()
    if not value:
        return value

    if value.startswith("postgres://"):
        value = "postgresql://" + value[len("postgres://") :]

    for suffix in ("+asyncpg", "+psycopg2", "+psycopg"):
        needle = f"postgresql{suffix}://"
        if value.startswith(needle):
            value = "postgresql://" + value[len(needle) :]
            break

    return value


def build_database_url_from_pg_env() -> str | None:
    """Build a DSN from PGHOST/PGUSER/... when Railway exposes discrete vars."""
    host = os.getenv("PGHOST")
    if not host:
        return None
    user = os.getenv("PGUSER") or "postgres"
    password = os.getenv("PGPASSWORD") or ""
    port = os.getenv("PGPORT") or "5432"
    database = os.getenv("PGDATABASE") or "railway"
    auth = quote_plus(user)
    if password:
        auth = f"{auth}:{quote_plus(password)}"
    return f"postgresql://{auth}@{host}:{port}/{database}"


def resolve_database_url_from_env() -> str | None:
    for key in _DATABASE_URL_ENV_KEYS:
        raw = os.getenv(key)
        if raw and raw.strip():
            return normalize_database_url(raw)
    built = build_database_url_from_pg_env()
    return normalize_database_url(built) if built else None


def redact_database_url(url: str) -> str:
    """Hide credentials while keeping scheme/host/db for debugging."""
    parsed = urlparse(normalize_database_url(url) or "")
    host = parsed.hostname or "?"
    port = f":{parsed.port}" if parsed.port else ""
    db = parsed.path or ""
    user = parsed.username or ""
    auth = f"{user}:***@" if user else ("***@" if parsed.password else "")
    return f"{parsed.scheme}://{auth}{host}{port}{db}"


def database_host(url: str) -> str:
    return (urlparse(normalize_database_url(url) or "").hostname or "").lower()


def is_railway_runtime() -> bool:
    return bool(os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_SERVICE_ID"))


def database_url_source() -> str:
    """Where the effective DATABASE_URL came from."""
    if resolve_database_url_from_env():
        return "environment"
    return "app_default_localhost"


def database_url_env_hints(settings_url: str | None = None) -> str:
    """Safe debug list of which DB-related env vars are present (no secrets)."""
    present = [key for key in _DATABASE_URL_ENV_KEYS if os.getenv(key)]
    pg = [key for key in ("PGHOST", "PGUSER", "PGDATABASE", "PGPORT") if os.getenv(key)]
    parts = [f"source: {database_url_source()}"]
    if present:
        parts.append("URL vars: " + ", ".join(present))
    else:
        parts.append("URL vars: (none)")
    if pg:
        parts.append("PG* vars: " + ", ".join(pg))
    else:
        parts.append("PG* vars: (none)")
    raw = settings_url or os.getenv("DATABASE_URL") or resolve_database_url_from_env()
    if raw:
        parts.append(f"parsed host: {database_host(raw) or '?'}")
        parts.append(f"redacted URL: {redact_database_url(raw)}")
    elif settings_url:
        parts.append(f"parsed host: {database_host(settings_url) or '?'}")
        parts.append(f"redacted URL: {redact_database_url(settings_url)}")
    return "; ".join(parts)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://postgres:postgres@localhost:5432/credits"
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1/chat/completions"
    # Optional shared secret. When set, clients must send Authorization: Bearer <key>.
    platform_api_key: str = ""
    min_preflight_credits: int = 1000
    http_timeout_seconds: float = 60.0
    recent_transactions_limit: int = 25
    # Railway / managed Postgres often require SSL.
    database_ssl: bool | None = None

    @model_validator(mode="before")
    @classmethod
    def _pull_railway_database_url(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        current = data.get("database_url") or data.get("DATABASE_URL")
        if isinstance(current, str) and current.strip():
            data["database_url"] = normalize_database_url(current)
            return data
        resolved = resolve_database_url_from_env()
        if resolved:
            data["database_url"] = resolved
        return data

    @field_validator("database_url", mode="before")
    @classmethod
    def _normalize_db_url(cls, value: object) -> object:
        if isinstance(value, str):
            return normalize_database_url(value)
        return value

    def asyncpg_connect_kwargs(self) -> dict:
        kwargs: dict = {
            "dsn": self.database_url,
            "min_size": 1,
            "max_size": 10,
            "command_timeout": 30,
        }
        use_ssl = self.database_ssl
        if use_ssl is None:
            host = (urlparse(self.database_url).hostname or "").lower()
            # Local / private Railway mesh stay plaintext; public proxies need SSL.
            if host.endswith(".railway.internal") or host in {
                "localhost",
                "127.0.0.1",
                "postgres",
                "db",
            }:
                use_ssl = False
            else:
                use_ssl = True
        if use_ssl:
            kwargs["ssl"] = True
        return kwargs


@lru_cache
def get_settings() -> Settings:
    overrides: dict[str, str] = {}
    resolved = resolve_database_url_from_env()
    if resolved:
        # Prefer explicit Railway/Postgres env over any stale local default.
        overrides["database_url"] = resolved
    return Settings(**overrides)
