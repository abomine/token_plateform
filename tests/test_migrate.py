import os

import pytest

from backend.config import Settings
from backend.migrate import DatabaseConfigError, _assert_database_reachable_config


def test_railway_localhost_database_url_is_rejected(monkeypatch):
    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
    settings = Settings(database_url="postgresql://postgres:postgres@localhost:5432/credits")
    with pytest.raises(DatabaseConfigError, match="still points at localhost"):
        _assert_database_reachable_config(settings)


def test_local_localhost_database_url_is_allowed(monkeypatch):
    monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
    monkeypatch.delenv("RAILWAY_SERVICE_ID", raising=False)
    settings = Settings(database_url="postgresql://postgres:postgres@localhost:5432/credits")
    _assert_database_reachable_config(settings)
