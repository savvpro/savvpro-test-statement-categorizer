from pydantic import BaseModel, ConfigDict, Field

from app.core.domain import Category, Kind


class Decision(BaseModel):
    model_config = ConfigDict(frozen=True)

    category: Category
    kind: Kind
    confidence: float
    rule_id: str | None  # None when nothing matched
    reason: str
    needs_review: bool
    # What the brain would have said if it had been sure enough. Set when a trusted rule
    # was overruled by the confidence threshold or by an always-review rule.
    suggested_category: Category | None = None


class UserRule(BaseModel):
    """A correction the user asked to remember: this merchant always gets this category."""

    model_config = ConfigDict(frozen=True)

    merchant_key: str = Field(min_length=1)
    category: Category
    kind: Kind | None = None  # omitted: derived from the sign of the amount
