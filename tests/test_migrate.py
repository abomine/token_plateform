import os

import pytest

from backend.config import Settings, get_settings
from backend.migrate import DatabaseConfigError, _assert_database_reachable_config


def test_railway_missing_database_url_uses_clear_message(monkeypatch):
    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
    for key in (
        "DATABASE_URL",
        "DATABASE_PRIVATE_URL",
        "POSTGRES_URL",
        "DATABASE_PUBLIC_URL",
        "PGHOST",
    ):
        monkeypatch.delenv(key, raising=False)
    get_settings.cache_clear()
    settings = Settings(database_url="postgresql://postgres:postgres@localhost:5432/credits")
    with pytest.raises(DatabaseConfigError, match="DATABASE_URL is NOT set"):
        _assert_database_reachable_config(settings)
    get_settings.cache_clear()


def test_railway_localhost_database_url_is_rejected(monkeypatch):
    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/credits",
    )
    get_settings.cache_clear()
    settings = Settings(database_url="postgresql://postgres:postgres@localhost:5432/credits")
    with pytest.raises(DatabaseConfigError, match="still points at localhost"):
        _assert_database_reachable_config(settings)
    get_settings.cache_clear()


def test_local_localhost_database_url_is_allowed(monkeypatch):
    monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
    monkeypatch.delenv("RAILWAY_SERVICE_ID", raising=False)
    settings = Settings(database_url="postgresql://postgres:postgres@localhost:5432/credits")
    _assert_database_reachable_config(settings)
