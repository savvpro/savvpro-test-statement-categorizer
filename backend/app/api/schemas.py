"""Request and response shapes for the HTTP API."""

from datetime import datetime

from pydantic import BaseModel, field_validator

from ..categories import Category, Kind
from ..models import RowIssue, Summary, Transaction


class CategoryInfo(BaseModel):
    name: Category
    kind: Kind


class StatementOut(BaseModel):
    id: str
    filename: str
    currency: str
    categories: list[CategoryInfo]  # every category with its kind, so the UI has one source
    created_at: datetime
    transactions: list[Transaction]
    skipped: list[RowIssue]
    warnings: list[RowIssue]
    summary: Summary


class FixRequest(BaseModel):
    category: Category

    @field_validator("category")
    @classmethod
    def _real_category(cls, value: Category) -> Category:
        if value is Category.NEEDS_REVIEW:
            raise ValueError("Pick a real category.")
        return value


class FixResponse(BaseModel):
    statement: StatementOut
    updated_ids: list[str]  # other rows the brain re-categorised because of this fix
