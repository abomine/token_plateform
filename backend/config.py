"""Runtime configuration loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


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


@lru_cache
def get_settings() -> Settings:
    return Settings()
