"""Transaction input and categorization result schemas.

Preserves the original description, enforces Decimal monetary precision,
and validates confidence scores between 0.0 and 1.0.
"""

import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class TransactionInput(BaseModel):
    """Input model for raw financial statement transactions.

    Attributes:
        original_description: Raw transaction text as received from statement.
            Preserved exactly as provided without modification.
        amount: Monetary amount represented as Decimal.
            Negative represents money leaving account (outflow/expense).
            Positive represents money entering account (inflow/income).
            Zero requires validation/manual review.
        date: Transaction date, if available.
        currency: 3-letter currency code, if available (defaults to USD).
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    original_description: str = Field(..., description="Original transaction description")
    amount: Decimal = Field(..., description="Monetary transaction amount as Decimal")
    date: Optional[datetime.date] = Field(default=None, description="Transaction date if available")
    currency: Optional[str] = Field(default="USD", description="Currency code (e.g. USD)")

    @field_validator("amount", mode="before")
    @classmethod
    def validate_amount(cls, v: Any) -> Decimal:
        """Validate that amount is a finite, decimal-safe monetary value.

        Rejects malformed strings, None, NaN, and Infinity.
        """
        if v is None:
            raise ValueError("Amount cannot be None or empty")

        if isinstance(v, str):
            cleaned = v.strip()
            if not cleaned:
                raise ValueError("Amount cannot be an empty string")
            try:
                dec = Decimal(cleaned)
            except (InvalidOperation, TypeError) as exc:
                raise ValueError(f"Invalid monetary amount format: '{v}'") from exc
        elif isinstance(v, (int, float)):
            try:
                dec = Decimal(str(v))
            except (InvalidOperation, TypeError) as exc:
                raise ValueError(f"Invalid numeric amount: {v}") from exc
        elif isinstance(v, Decimal):
            dec = v
        else:
            raise ValueError(f"Unsupported amount type: {type(v).__name__}")

        if dec.is_nan() or dec.is_infinite():
            raise ValueError(f"Monetary amount must be finite, received: {dec}")

        return dec

    @field_validator("original_description")
    @classmethod
    def validate_description(cls, v: Any) -> str:
        """Ensure original description is a string and preserved as-is."""
        if not isinstance(v, str):
            raise ValueError("Original description must be a string")
        return v


class CategorizationResult(BaseModel):
    """Output result produced by the categorization engine.

    Attributes:
        category: The assigned category name (one of default categories).
        confidence_score: Rule-based confidence score between 0.0 and 1.0.
        explanation: Human-readable explanation of why this category was assigned.
        review_required: Flag indicating if manual human review is recommended.
        normalized_description: Normalized text used for merchant matching.
    """

    model_config = ConfigDict(frozen=True)

    category: str = Field(..., description="Assigned category name")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence between 0.0 and 1.0")
    explanation: str = Field(..., description="Classification rationale and match explanation")
    review_required: bool = Field(..., description="Whether manual review is required")
    normalized_description: str = Field(..., description="Normalized text used during rule evaluation")

    @property
    def classification_reason(self) -> str:
        """Alias for explanation for compatibility across application layers."""
        return self.explanation
