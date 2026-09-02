"""Apply sql/schema.sql (and optional seed) against DATABASE_URL.

On Railway, schema is applied automatically at app startup (see backend.main).
Do NOT put this in a Procfile `release:` line — Nixpacks runs that during image
build, when Postgres is unreachable.

Manual / one-off (Railway shell or local):
  python -m backend.migrate
  python -m backend.migrate --seed
"""

from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path

import asyncpg

from backend.config import (
    Settings,
    database_host,
    database_url_env_hints,
    get_settings,
    redact_database_url,
)

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "sql" / "schema.sql"
SEED_PATH = ROOT / "sql" / "seed.sql"

_RAILWAY_DB_HELP = """
DATABASE_URL is set but still points at localhost (host={host}).
Redacted value: {redacted}

Your web service Variables currently contain a local/dev DSN, not Railway Postgres.

Fix in the Railway dashboard:
1. Open the PostgreSQL service → Variables, copy DATABASE_URL (or use Variable Reference).
2. Open your **web** service → Variables.
3. Edit DATABASE_URL — delete any value containing localhost / 127.0.0.1
   (often pasted from .env.example).
4. Set it via reference, e.g. DATABASE_URL = ${{Postgres.DATABASE_URL}}
   Use the real Postgres service name shown in Railway if it is not "Postgres".
5. Redeploy the web service.

Detected: {hints}
""".strip()


class DatabaseConfigError(RuntimeError):
    """Raised when DATABASE_URL is missing or still points at localhost on Railway."""


def _connect_kwargs(settings: Settings) -> dict:
    kwargs: dict = {"dsn": settings.database_url}
    if settings.asyncpg_connect_kwargs().get("ssl"):
        kwargs["ssl"] = True
    return kwargs


def _assert_database_reachable_config(settings: Settings) -> None:
    """Fail fast with a clear hint when DATABASE_URL still points at localhost."""
    host = database_host(settings.database_url)
    on_railway = bool(os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_SERVICE_ID"))
    if on_railway and host in {"localhost", "127.0.0.1", ""}:
        raise DatabaseConfigError(
            _RAILWAY_DB_HELP.format(
                host=host or "?",
                redacted=redact_database_url(settings.database_url),
                hints=database_url_env_hints(settings.database_url),
            )
        )


async def apply_sql(path: Path, settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    _assert_database_reachable_config(settings)
    sql = path.read_text(encoding="utf-8")
    conn = await asyncpg.connect(**_connect_kwargs(settings))
    try:
        await conn.execute(sql)
        print(f"Applied {path.relative_to(ROOT)}")
    finally:
        await conn.close()


async def apply_schema(*, seed: bool = False, settings: Settings | None = None) -> None:
    """Idempotent schema apply (CREATE IF NOT EXISTS). Safe on every boot."""
    settings = settings or get_settings()
    await apply_sql(SCHEMA_PATH, settings=settings)
    if seed:
        await apply_sql(SEED_PATH, settings=settings)


async def main(seed: bool) -> None:
    await apply_schema(seed=seed)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Apply marketplace SQL migrations")
    parser.add_argument(
        "--seed",
        action="store_true",
        help="Also load sql/seed.sql (demo user + wallet)",
    )
    args = parser.parse_args()
    asyncio.run(main(seed=args.seed))
