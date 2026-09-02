from backend.config import normalize_database_url, Settings


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
