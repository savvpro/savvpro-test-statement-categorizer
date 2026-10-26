"""Pydantic models for API request / response shapes."""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel


class CategorizedTransaction(BaseModel):
    id: str
    date: Optional[str]
    description: str
    amount: Optional[float]
    category: str
    confidence: float
    reason: str
    is_review: bool
    original_category: Optional[str] = None  # set after user overrides


class UploadResponse(BaseModel):
    filename: str
    total: int
    transactions: list[CategorizedTransaction]


class OverrideRequest(BaseModel):
    id: str
    category: str


class SummaryItem(BaseModel):
    category: str
    count: int
    total: float


class SummaryResponse(BaseModel):
    summary: list[SummaryItem]
