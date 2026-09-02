"""Apply sql/schema.sql (and optional seed) against DATABASE_URL.

Usage:
  python -m backend.migrate
  python -m backend.migrate --seed
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

import asyncpg

from backend.config import get_settings

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "sql" / "schema.sql"
SEED_PATH = ROOT / "sql" / "seed.sql"


async def apply_sql(path: Path) -> None:
    settings = get_settings()
    sql = path.read_text(encoding="utf-8")
    connect_kwargs = {
        "dsn": settings.database_url,
    }
    if settings.asyncpg_connect_kwargs().get("ssl"):
        connect_kwargs["ssl"] = True
    conn = await asyncpg.connect(**connect_kwargs)
    try:
        await conn.execute(sql)
        print(f"Applied {path.relative_to(ROOT)}")
    finally:
        await conn.close()


async def main(seed: bool) -> None:
    await apply_sql(SCHEMA_PATH)
    if seed:
        await apply_sql(SEED_PATH)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Apply marketplace SQL migrations")
    parser.add_argument(
        "--seed",
        action="store_true",
        help="Also load sql/seed.sql (demo user + wallet)",
    )
    args = parser.parse_args()
    asyncio.run(main(seed=args.seed))
