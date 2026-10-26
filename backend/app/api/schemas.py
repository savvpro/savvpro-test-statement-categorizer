"""Request/response contracts that are specific to the HTTP layer."""
from typing import List

from pydantic import BaseModel, Field

from ..domain.models import Category
from ..reporting.tax import TaxLine


class MerchantRuleIn(BaseModel):
    merchant: str = Field(min_length=1, max_length=120)
    category: Category


class MerchantRuleOut(BaseModel):
    merchant: str
    category: Category


class TaxEstimateRequest(BaseModel):
    transactions: List[TaxLine] = Field(max_length=50_000)
