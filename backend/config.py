"""Normalize and expose runtime settings for local + Railway."""

from functools import lru_cache
from urllib.parse import urlparse

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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
            host = urlparse(self.database_url).hostname or ""
            # Local compose/dev hosts stay plaintext; managed hosts enable SSL.
            use_ssl = host not in {"localhost", "127.0.0.1", "postgres", "db"}
        if use_ssl:
            kwargs["ssl"] = True
        return kwargs


@lru_cache
def get_settings() -> Settings:
    return Settings()
