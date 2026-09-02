"""FastAPI application: credit-gated DeepSeek chat proxy and wallet API."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any
from uuid import UUID

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse

from backend.config import Settings, get_settings, redact_database_url, database_url_source
from backend.credits import calculate_credit_cost
from backend.db import (
    InsufficientCreditsError,
    WalletNotFoundError,
    apply_api_usage,
    close_pool,
    connect_pool,
    fetch_recent_transactions,
    fetch_wallet,
    get_pool,
)
from backend.migrate import apply_schema
from backend.schemas import ChatCompletionRequest, TransactionOut, WalletBalanceOut

logger = logging.getLogger("uvicorn.error")
MIN_PREFLIGHT_CREDITS = 1000


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.db_ready = False
    app.state.db_error = None
    timeout = httpx.Timeout(settings.http_timeout_seconds)
    app.state.http = httpx.AsyncClient(timeout=timeout)

    # Schema must run at runtime (DB available), never during Nixpacks image build.
    # Soft-fail on Railway misconfig so the container stays up and /health explains it.
    try:
        await apply_schema(seed=settings.seed_demo_user, settings=settings)
        await connect_pool(settings)
        app.state.db_ready = True
        logger.info(
            "Database ready (%s)%s",
            redact_database_url(settings.database_url),
            " + demo seed" if settings.seed_demo_user else "",
        )
    except Exception as exc:  # noqa: BLE001 - keep process alive with clear /health status
        app.state.db_ready = False
        app.state.db_error = str(exc)
        logger.error("Database startup failed; API routes will return 503.\n%s", exc)

    try:
        yield
    finally:
        await app.state.http.aclose()
        if app.state.db_ready:
            await close_pool()


app = FastAPI(
    title="API Compute Credit Marketplace",
    version="0.1.0",
    description="Spend platform credits (1 USD = 1,000,000 credits) on DeepSeek LLM calls.",
    lifespan=lifespan,
)


def require_database(request: Request) -> None:
    if not getattr(request.app.state, "db_ready", False):
        detail = getattr(request.app.state, "db_error", None) or "Database is not ready"
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
        )


def _parse_user_id(raw: str | None) -> str:
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Platform-User-Id header",
        )
    try:
        return str(UUID(raw.strip()))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-Platform-User-Id must be a UUID",
        ) from exc


async def authenticate_user(
    x_platform_user_id: str | None = Header(default=None, alias="X-Platform-User-Id"),
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> str:
    """Identify the caller by X-Platform-User-Id.

    When PLATFORM_API_KEY is configured, Authorization: Bearer <key> is also required.
    """
    if settings.platform_api_key:
        if not authorization or not authorization.lower().startswith("bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing Authorization Bearer token",
            )
        token = authorization.split(" ", 1)[1].strip()
        if token != settings.platform_api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
            )
    return _parse_user_id(x_platform_user_id)


@app.get("/health")
async def health(request: Request) -> dict[str, Any]:
    settings = get_settings()
    ready = bool(getattr(request.app.state, "db_ready", False))
    payload: dict[str, Any] = {
        "status": "ok" if ready else "degraded",
        "database": "ready" if ready else "not_ready",
        "database_url_source": database_url_source(),
        "database_url_host": redact_database_url(settings.database_url),
    }
    if not ready:
        payload["database_error"] = getattr(request.app.state, "db_error", None)
    return payload


@app.get("/wallet/balance", response_model=WalletBalanceOut)
async def wallet_balance(
    user_id: str = Depends(authenticate_user),
    settings: Settings = Depends(get_settings),
    _: None = Depends(require_database),
) -> WalletBalanceOut:
    pool = get_pool()
    async with pool.acquire() as conn:
        wallet = await fetch_wallet(conn, user_id)
        if wallet is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unknown platform user",
            )
        rows = await fetch_recent_transactions(
            conn, user_id, settings.recent_transactions_limit
        )
    return WalletBalanceOut(
        user_id=wallet["user_id"],
        email=wallet["email"],
        credit_balance=int(wallet["credit_balance"]),
        updated_at=wallet["updated_at"],
        recent_transactions=[
            TransactionOut(
                id=row["id"],
                amount=int(row["amount"]),
                type=row["type"],
                description=row["description"],
                created_at=row["created_at"],
            )
            for row in rows
        ],
    )


@app.post("/v1/chat/completions")
async def chat_completions(
    payload: ChatCompletionRequest,
    request: Request,
    user_id: str = Depends(authenticate_user),
    settings: Settings = Depends(get_settings),
    _: None = Depends(require_database),
) -> JSONResponse:
    """Proxy OpenAI-compatible chat completions through a credit gate."""
    if payload.stream:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Streaming is not supported in Phase 1; omit stream or set stream=false",
        )
    if not settings.deepseek_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="DeepSeek API key is not configured",
        )

    pool = get_pool()
    async with pool.acquire() as conn:
        wallet = await fetch_wallet(conn, user_id)
        if wallet is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unknown platform user",
            )
        balance = int(wallet["credit_balance"])
        # Pre-flight: require a positive working balance above the minimum reserve.
        if balance <= settings.min_preflight_credits:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=(
                    f"Insufficient credits: balance {balance} must be greater than "
                    f"{settings.min_preflight_credits}"
                ),
            )

    upstream_body = payload.model_dump(exclude_none=True)
    try:
        upstream = await request.app.state.http.post(
            settings.deepseek_base_url,
            headers={
                "Authorization": f"Bearer {settings.deepseek_api_key}",
                "Content-Type": "application/json",
            },
            json=upstream_body,
        )
    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="DeepSeek API request timed out; no credits were deducted",
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to reach DeepSeek API; no credits were deducted",
        ) from exc

    # Provider errors must never debit the ledger.
    if upstream.is_error:
        try:
            err_body: Any = upstream.json()
        except ValueError:
            err_body = {"error": upstream.text}
        return JSONResponse(
            status_code=upstream.status_code,
            content=err_body,
            headers={"X-Credits-Deducted": "0"},
        )

    try:
        completion = upstream.json()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="DeepSeek returned a non-JSON body; no credits were deducted",
        ) from exc

    usage = completion.get("usage") or {}
    try:
        prompt_tokens = int(usage.get("prompt_tokens") or 0)
        completion_tokens = int(usage.get("completion_tokens") or 0)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="DeepSeek usage object is invalid; no credits were deducted",
        ) from exc

    model_name = str(completion.get("model") or payload.model)
    credits_deducted = calculate_credit_cost(model_name, prompt_tokens, completion_tokens)
    description = (
        f"api_usage {model_name}: {prompt_tokens} prompt + {completion_tokens} completion tokens"
    )

    try:
        async with pool.acquire() as conn:
            remaining = await apply_api_usage(
                conn,
                user_id=user_id,
                model=model_name,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                credits=credits_deducted,
                description=description,
            )
    except WalletNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unknown platform user",
        ) from exc
    except InsufficientCreditsError as exc:
        # Provider call already succeeded; we refuse to go negative.
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=(
                "Credits were insufficient after the provider call completed. "
                f"Required {exc.required}, available {exc.balance}. "
                "No ledger debit was applied."
            ),
        ) from exc

    return JSONResponse(
        content=completion,
        headers={
            "X-Credits-Deducted": str(credits_deducted),
            "X-Credits-Remaining": str(remaining),
        },
    )
