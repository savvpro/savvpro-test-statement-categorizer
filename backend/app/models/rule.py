from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class RuleType(StrEnum):
    EXACT = "EXACT"
    KEYWORD = "KEYWORD"
    REGEX = "REGEX"


class CustomRule(BaseModel):
    id: str
    pattern: str = Field(..., min_length=1, description="Merchant name or regex pattern")
    category: str = Field(..., min_length=1, description="Assigned tax category")
    rule_type: RuleType = RuleType.EXACT
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    notes: str | None = None


class RuleCreateRequest(BaseModel):
    pattern: str = Field(..., min_length=1)
    category: str = Field(..., min_length=1)
    rule_type: RuleType = RuleType.EXACT
    notes: str | None = None
