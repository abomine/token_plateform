"""Async PostgreSQL pool and ledger operations."""

from __future__ import annotations

from typing import Any

import asyncpg

from backend.config import Settings

_pool: asyncpg.Pool | None = None


async def connect_pool(settings: Settings) -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(**settings.asyncpg_connect_kwargs())
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


async def apply_topup(
    conn: asyncpg.Connection,
    *,
    user_id: str,
    amount: int,
    description: str,
) -> int:
    """Credit the wallet for a simulated purchase."""
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
        updated = await conn.fetchrow(
            """
            UPDATE wallets
            SET credit_balance = credit_balance + $2
            WHERE user_id = $1::uuid
            RETURNING credit_balance
            """,
            user_id,
            amount,
        )
        await conn.execute(
            """
            INSERT INTO credit_transactions (user_id, amount, type, description)
            VALUES ($1::uuid, $2, 'purchase', $3)
            """,
            user_id,
            amount,
            description,
        )
        return int(updated["credit_balance"])


async def list_tasks(conn: asyncpg.Connection, *, status: str | None = "open") -> list[asyncpg.Record]:
    if status:
        return await conn.fetch(
            """
            SELECT id, title, description, reward_credits, category::text AS category,
                   status::text AS status, created_by, completed_by, created_at, completed_at
            FROM tasks
            WHERE status = $1::task_status
            ORDER BY created_at DESC
            """,
            status,
        )
    return await conn.fetch(
        """
        SELECT id, title, description, reward_credits, category::text AS category,
               status::text AS status, created_by, completed_by, created_at, completed_at
        FROM tasks
        ORDER BY created_at DESC
        """
    )


async def create_task(
    conn: asyncpg.Connection,
    *,
    user_id: str,
    title: str,
    description: str,
    reward_credits: int,
    category: str,
) -> asyncpg.Record:
    return await conn.fetchrow(
        """
        INSERT INTO tasks (title, description, reward_credits, category, created_by)
        VALUES ($1, $2, $3, $4::task_category, $5::uuid)
        RETURNING id, title, description, reward_credits, category::text AS category,
                  status::text AS status, created_by, completed_by, created_at, completed_at
        """,
        title,
        description,
        reward_credits,
        category,
        user_id,
    )


async def complete_task_with_reward(
    conn: asyncpg.Connection,
    *,
    task_id: str,
    user_id: str,
) -> tuple[asyncpg.Record, int]:
    """Mark a task completed and credit the worker atomically."""
    async with conn.transaction():
        task = await conn.fetchrow(
            """
            SELECT id, title, reward_credits, status::text AS status
            FROM tasks
            WHERE id = $1::uuid
            FOR UPDATE
            """,
            task_id,
        )
        if task is None:
            raise TaskNotFoundError(task_id)
        if task["status"] != "open":
            raise TaskNotOpenError(task_id)

        updated_task = await conn.fetchrow(
            """
            UPDATE tasks
            SET status = 'completed',
                completed_by = $2::uuid,
                completed_at = NOW()
            WHERE id = $1::uuid
            RETURNING id, title, description, reward_credits, category::text AS category,
                      status::text AS status, created_by, completed_by, created_at, completed_at
            """,
            task_id,
            user_id,
        )

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

        reward = int(task["reward_credits"])
        updated_wallet = await conn.fetchrow(
            """
            UPDATE wallets
            SET credit_balance = credit_balance + $2
            WHERE user_id = $1::uuid
            RETURNING credit_balance
            """,
            user_id,
            reward,
        )
        await conn.execute(
            """
            INSERT INTO credit_transactions (user_id, amount, type, description)
            VALUES ($1::uuid, $2, 'task_reward', $3)
            """,
            user_id,
            reward,
            f"task_reward: {task['title']}",
        )
        return updated_task, int(updated_wallet["credit_balance"])


class WalletNotFoundError(Exception):
    def __init__(self, user_id: str) -> None:
        super().__init__(f"No wallet for user {user_id}")
        self.user_id = user_id


class InsufficientCreditsError(Exception):
    def __init__(self, balance: int, required: int) -> None:
        super().__init__(f"Balance {balance} is below required {required}")
        self.balance = balance
        self.required = required


class TaskNotFoundError(Exception):
    def __init__(self, task_id: str) -> None:
        super().__init__(f"No task {task_id}")
        self.task_id = task_id


class TaskNotOpenError(Exception):
    def __init__(self, task_id: str) -> None:
        super().__init__(f"Task {task_id} is not open")
        self.task_id = task_id


def record_to_dict(record: asyncpg.Record) -> dict[str, Any]:
    return dict(record)
