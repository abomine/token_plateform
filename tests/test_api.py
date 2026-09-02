from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from uuid import UUID
from unittest.mock import AsyncMock

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from backend.config import get_settings
from backend.credits import calculate_credit_cost
from backend.db import InsufficientCreditsError
from backend.main import app

DEMO_USER = "00000000-0000-0000-0000-000000000001"


class FakeConn:
    pass


class FakePool:
    def __init__(self) -> None:
        self.conn = FakeConn()

    @asynccontextmanager
    async def acquire(self):
        yield self.conn


@pytest.fixture
def settings():
    get_settings.cache_clear()
    s = get_settings()
    s.deepseek_api_key = "test-deepseek-key"
    s.platform_api_key = ""
    s.min_preflight_credits = 1000
    s.deepseek_base_url = "https://api.deepseek.com/v1/chat/completions"
    yield s
    get_settings.cache_clear()


@pytest.fixture
def api_client(monkeypatch, settings):
    pool = FakePool()

    async def _connect(_settings):
        return pool

    async def _close():
        return None

    monkeypatch.setattr("backend.main.connect_pool", _connect)
    monkeypatch.setattr("backend.main.close_pool", _close)
    monkeypatch.setattr("backend.main.get_pool", lambda: pool)

    with TestClient(app) as client:
        client.pool = pool  # type: ignore[attr-defined]
        yield client


def _wallet_row(balance: int):
    return {
        "user_id": UUID(DEMO_USER),
        "email": "demo@marketplace.local",
        "credit_balance": balance,
        "updated_at": datetime.now(timezone.utc),
    }


def test_health(api_client: TestClient):
    response = api_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_missing_user_header_is_unauthorized(api_client: TestClient):
    response = api_client.get("/wallet/balance")
    assert response.status_code == 401


def test_wallet_balance(api_client: TestClient, monkeypatch):
    wallet = _wallet_row(5_000_000)
    tx = [
        {
            "id": UUID("00000000-0000-0000-0000-0000000000aa"),
            "amount": -198,
            "type": "api_usage",
            "description": "test debit",
            "created_at": datetime.now(timezone.utc),
        }
    ]
    monkeypatch.setattr("backend.main.fetch_wallet", AsyncMock(return_value=wallet))
    monkeypatch.setattr("backend.main.fetch_recent_transactions", AsyncMock(return_value=tx))

    response = api_client.get("/wallet/balance", headers={"X-Platform-User-Id": DEMO_USER})
    assert response.status_code == 200
    body = response.json()
    assert body["credit_balance"] == 5_000_000
    assert body["recent_transactions"][0]["amount"] == -198


def test_preflight_rejects_low_balance(api_client: TestClient, monkeypatch):
    monkeypatch.setattr("backend.main.fetch_wallet", AsyncMock(return_value=_wallet_row(1000)))
    response = api_client.post(
        "/v1/chat/completions",
        headers={"X-Platform-User-Id": DEMO_USER},
        json={"model": "deepseek-reasoner", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert response.status_code == 402


@respx.mock
def test_successful_proxy_debits_ledger(api_client: TestClient, monkeypatch, settings):
    monkeypatch.setattr("backend.main.fetch_wallet", AsyncMock(return_value=_wallet_row(5_000_000)))
    apply = AsyncMock(return_value=5_000_000 - 198)
    monkeypatch.setattr("backend.main.apply_api_usage", apply)

    completion = {
        "id": "chatcmpl-1",
        "model": "deepseek-reasoner",
        "choices": [{"index": 0, "message": {"role": "assistant", "content": "hello"}}],
        "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
    }
    respx.post(settings.deepseek_base_url).mock(return_value=httpx.Response(200, json=completion))

    response = api_client.post(
        "/v1/chat/completions",
        headers={"X-Platform-User-Id": DEMO_USER},
        json={"model": "deepseek-reasoner", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert response.status_code == 200
    expected = calculate_credit_cost("deepseek-reasoner", 100, 50)
    assert response.headers["x-credits-deducted"] == str(expected)
    assert response.headers["x-credits-remaining"] == str(5_000_000 - 198)
    assert response.json()["choices"][0]["message"]["content"] == "hello"
    apply.assert_awaited_once()
    kwargs = apply.await_args.kwargs
    assert kwargs["credits"] == expected
    assert kwargs["prompt_tokens"] == 100
    assert kwargs["completion_tokens"] == 50


@respx.mock
def test_provider_error_does_not_debit(api_client: TestClient, monkeypatch, settings):
    monkeypatch.setattr("backend.main.fetch_wallet", AsyncMock(return_value=_wallet_row(5_000_000)))
    apply = AsyncMock()
    monkeypatch.setattr("backend.main.apply_api_usage", apply)
    respx.post(settings.deepseek_base_url).mock(
        return_value=httpx.Response(500, json={"error": "upstream"})
    )

    response = api_client.post(
        "/v1/chat/completions",
        headers={"X-Platform-User-Id": DEMO_USER},
        json={"model": "deepseek-reasoner", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert response.status_code == 500
    assert response.headers["x-credits-deducted"] == "0"
    apply.assert_not_called()


@respx.mock
def test_timeout_does_not_debit(api_client: TestClient, monkeypatch, settings):
    monkeypatch.setattr("backend.main.fetch_wallet", AsyncMock(return_value=_wallet_row(5_000_000)))
    apply = AsyncMock()
    monkeypatch.setattr("backend.main.apply_api_usage", apply)
    respx.post(settings.deepseek_base_url).mock(side_effect=httpx.TimeoutException("slow"))

    response = api_client.post(
        "/v1/chat/completions",
        headers={"X-Platform-User-Id": DEMO_USER},
        json={"model": "deepseek-reasoner", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert response.status_code == 504
    apply.assert_not_called()


@respx.mock
def test_post_flight_insufficient_credits_does_not_hide_provider_success(
    api_client: TestClient, monkeypatch, settings
):
    monkeypatch.setattr("backend.main.fetch_wallet", AsyncMock(return_value=_wallet_row(5_000)))
    monkeypatch.setattr(
        "backend.main.apply_api_usage",
        AsyncMock(side_effect=InsufficientCreditsError(500, 198)),
    )
    respx.post(settings.deepseek_base_url).mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "chatcmpl-1",
                "model": "deepseek-reasoner",
                "usage": {"prompt_tokens": 100, "completion_tokens": 50},
            },
        )
    )
    response = api_client.post(
        "/v1/chat/completions",
        headers={"X-Platform-User-Id": DEMO_USER},
        json={"model": "deepseek-reasoner", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert response.status_code == 402
    assert "No ledger debit was applied" in response.json()["detail"]


def test_streaming_rejected(api_client: TestClient, monkeypatch):
    monkeypatch.setattr("backend.main.fetch_wallet", AsyncMock(return_value=_wallet_row(5_000_000)))
    response = api_client.post(
        "/v1/chat/completions",
        headers={"X-Platform-User-Id": DEMO_USER},
        json={"model": "deepseek-reasoner", "messages": [], "stream": True},
    )
    assert response.status_code == 400
