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
    database_url_source,
    get_settings,
    is_railway_runtime,
    redact_database_url,
    resolve_database_url_from_env,
)

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "sql" / "schema.sql"
SEED_PATH = ROOT / "sql" / "seed.sql"

_RAILWAY_MISSING_DB_HELP = """
DATABASE_URL is NOT set on this Railway web service.
The app fell back to the local default (localhost), which cannot work on Railway.

Do this now:
1. In the same Railway project: + New → Database → Add PostgreSQL
   (skip if Postgres already exists in the project canvas).
2. Open your **web** service → Variables → + New Variable → Add Variable Reference.
3. Pick the Postgres service → choose DATABASE_PRIVATE_URL (preferred) or DATABASE_URL.
4. Name the variable exactly: DATABASE_URL
5. Wait for redeploy, then open /health — database should be "ready".

Detected: {hints}
""".strip()

_RAILWAY_LOCALHOST_DB_HELP = """
DATABASE_URL is set but still points at localhost (host={host}).
Redacted value: {redacted}

You still have a local/dev DSN in Variables (often pasted from .env.example).

Fix:
1. Web service → Variables → edit DATABASE_URL
2. Delete the localhost value
3. Use Add Variable Reference → Postgres → DATABASE_PRIVATE_URL (or DATABASE_URL)
4. Redeploy

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
    """Fail fast with a clear hint when DATABASE_URL is missing/localhost on Railway."""
    if not is_railway_runtime():
        return

    host = database_host(settings.database_url)
    if host not in {"localhost", "127.0.0.1", ""}:
        return

    hints = database_url_env_hints(settings.database_url)
    if resolve_database_url_from_env() is None or database_url_source() == "app_default_localhost":
        raise DatabaseConfigError(_RAILWAY_MISSING_DB_HELP.format(hints=hints))

    raise DatabaseConfigError(
        _RAILWAY_LOCALHOST_DB_HELP.format(
            host=host or "?",
            redacted=redact_database_url(settings.database_url),
            hints=hints,
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
