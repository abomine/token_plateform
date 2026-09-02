import os

from backend.config import (
    Settings,
    get_settings,
    normalize_database_url,
    resolve_database_url_from_env,
)


def test_normalize_postgres_scheme():
    assert (
        normalize_database_url("postgres://user:pass@host:5432/db")
        == "postgresql://user:pass@host:5432/db"
    )


def test_normalize_driver_suffix():
    assert (
        normalize_database_url("postgresql+asyncpg://user:pass@host:5432/db")
        == "postgresql://user:pass@host:5432/db"
    )


def test_ssl_enabled_for_remote_hosts():
    settings = Settings(
        database_url="postgresql://user:pass@containers-us-west-1.railway.app:5432/railway"
    )
    assert settings.asyncpg_connect_kwargs()["ssl"] is True


def test_ssl_disabled_for_localhost():
    settings = Settings(database_url="postgresql://postgres:postgres@localhost:5432/credits")
    assert "ssl" not in settings.asyncpg_connect_kwargs()


def test_ssl_disabled_for_railway_private_host():
    settings = Settings(
        database_url="postgresql://user:pass@postgres.railway.internal:5432/railway"
    )
    assert "ssl" not in settings.asyncpg_connect_kwargs()


def test_resolve_prefers_database_private_url(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv(
        "DATABASE_PRIVATE_URL",
        "postgres://user:pass@postgres.railway.internal:5432/railway",
    )
    assert resolve_database_url_from_env() == (
        "postgresql://user:pass@postgres.railway.internal:5432/railway"
    )
    settings = get_settings()
    assert "railway.internal" in settings.database_url
    get_settings.cache_clear()


def test_resolve_from_pg_env(monkeypatch):
    get_settings.cache_clear()
    for key in (
        "DATABASE_URL",
        "DATABASE_PRIVATE_URL",
        "POSTGRES_URL",
        "DATABASE_PUBLIC_URL",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("PGHOST", "postgres.railway.internal")
    monkeypatch.setenv("PGUSER", "postgres")
    monkeypatch.setenv("PGPASSWORD", "secret")
    monkeypatch.setenv("PGPORT", "5432")
    monkeypatch.setenv("PGDATABASE", "railway")
    assert resolve_database_url_from_env() == (
        "postgresql://postgres:secret@postgres.railway.internal:5432/railway"
    )
    get_settings.cache_clear()
