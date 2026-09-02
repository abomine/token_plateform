"""Pydantic request/response models."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ChatCompletionRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    model: str = "deepseek-chat"
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


class TopUpRequest(BaseModel):
    amount: int = Field(..., gt=0, description="Credits to add (simulated Stripe purchase)")


class TopUpOut(BaseModel):
    credit_balance: int
    added: int


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=160)
    description: str = Field(..., min_length=8, max_length=4000)
    reward_credits: int = Field(..., gt=0)
    category: Literal["Scraping", "Prompting", "Bug Fix"] = "Prompting"


class TaskOut(BaseModel):
    id: UUID
    title: str
    description: str
    reward_credits: int
    category: str
    status: str
    created_by: UUID
    completed_by: UUID | None = None
    created_at: datetime
    completed_at: datetime | None = None
