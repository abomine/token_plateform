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
from urllib.parse import urlparse

import asyncpg

from backend.config import Settings, database_url_env_hints, get_settings

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "sql" / "schema.sql"
SEED_PATH = ROOT / "sql" / "seed.sql"

_RAILWAY_DB_HELP = """
DATABASE_URL is missing or still set to localhost on Railway.

Fix in the Railway dashboard:
1. Create / open a PostgreSQL service in the same project.
2. Open your **web** service → Variables.
3. Delete any DATABASE_URL you pasted from .env.example (localhost).
4. Add a variable reference to Postgres, e.g.
   DATABASE_URL = ${{Postgres.DATABASE_URL}}
   (or DATABASE_PRIVATE_URL = ${{Postgres.DATABASE_PRIVATE_URL}})
5. Redeploy the web service.

Detected: {hints}
""".strip()


def _connect_kwargs(settings: Settings) -> dict:
    kwargs: dict = {"dsn": settings.database_url}
    if settings.asyncpg_connect_kwargs().get("ssl"):
        kwargs["ssl"] = True
    return kwargs


def _assert_database_reachable_config(settings: Settings) -> None:
    """Fail fast with a clear hint when DATABASE_URL still points at localhost."""
    host = (urlparse(settings.database_url).hostname or "").lower()
    on_railway = bool(os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_SERVICE_ID"))
    if on_railway and host in {"localhost", "127.0.0.1", ""}:
        raise RuntimeError(_RAILWAY_DB_HELP.format(hints=database_url_env_hints()))


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
