"""Pydantic request/response models."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ChatCompletionRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    model: str
    messages: list[dict[str, Any]]
    stream: bool = False


class TransactionOut(BaseModel):
    id: UUID
    amount: int
    type: str
    description: str | None
    created_at: datetime


class WalletBalanceOut(BaseModel):
    user_id: UUID
    email: str
    credit_balance: int
    updated_at: datetime
    recent_transactions: list[TransactionOut] = Field(default_factory=list)
