"""Async PostgreSQL pool and ledger operations."""

from __future__ import annotations

from typing import Any

import asyncpg

from backend.config import Settings

_pool: asyncpg.Pool | None = None


async def connect_pool(settings: Settings) -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            dsn=settings.database_url,
            min_size=1,
            max_size=10,
            command_timeout=30,
        )
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("Database pool is not initialized")
    return _pool


async def fetch_wallet(conn: asyncpg.Connection, user_id: str) -> asyncpg.Record | None:
    return await conn.fetchrow(
        """
        SELECT u.id AS user_id, u.email, w.credit_balance, w.updated_at
        FROM users u
        JOIN wallets w ON w.user_id = u.id
        WHERE u.id = $1::uuid
        """,
        user_id,
    )


async def fetch_recent_transactions(
    conn: asyncpg.Connection, user_id: str, limit: int
) -> list[asyncpg.Record]:
    return await conn.fetch(
        """
        SELECT id, amount, type::text AS type, description, created_at
        FROM credit_transactions
        WHERE user_id = $1::uuid
        ORDER BY created_at DESC
        LIMIT $2
        """,
        user_id,
        limit,
    )


async def apply_api_usage(
    conn: asyncpg.Connection,
    *,
    user_id: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    credits: int,
    description: str,
) -> int:
    """Atomically debit the wallet and write ledger + usage rows.

    Raises InsufficientCreditsError if the reserved balance is gone.
    """
    async with conn.transaction():
        wallet = await conn.fetchrow(
            """
            SELECT credit_balance
            FROM wallets
            WHERE user_id = $1::uuid
            FOR UPDATE
            """,
            user_id,
        )
        if wallet is None:
            raise WalletNotFoundError(user_id)
        if wallet["credit_balance"] < credits:
            raise InsufficientCreditsError(int(wallet["credit_balance"]), credits)

        updated = await conn.fetchrow(
            """
            UPDATE wallets
            SET credit_balance = credit_balance - $2
            WHERE user_id = $1::uuid
            RETURNING credit_balance
            """,
            user_id,
            credits,
        )
        await conn.execute(
            """
            INSERT INTO credit_transactions (user_id, amount, type, description)
            VALUES ($1::uuid, $2, 'api_usage', $3)
            """,
            user_id,
            -credits,
            description,
        )
        await conn.execute(
            """
            INSERT INTO api_logs (
                user_id, model, prompt_tokens, completion_tokens, total_credits_deducted
            )
            VALUES ($1::uuid, $2, $3, $4, $5)
            """,
            user_id,
            model,
            prompt_tokens,
            completion_tokens,
            credits,
        )
        return int(updated["credit_balance"])


class WalletNotFoundError(Exception):
    def __init__(self, user_id: str) -> None:
        super().__init__(f"No wallet for user {user_id}")
        self.user_id = user_id


class InsufficientCreditsError(Exception):
    def __init__(self, balance: int, required: int) -> None:
        super().__init__(f"Balance {balance} is below required {required}")
        self.balance = balance
        self.required = required


def record_to_dict(record: asyncpg.Record) -> dict[str, Any]:
    return dict(record)
