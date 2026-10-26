"""Unit tests for transaction schemas and Decimal monetary validation."""

from datetime import date
from decimal import Decimal
import pytest
from pydantic import ValidationError

from app.schemas.transaction import CategorizationResult, TransactionInput


def test_transaction_input_valid():
    """Verify standard valid transaction input with Decimal amount and date."""
    tx = TransactionInput(
        original_description="GITHUB *COPILOT",
        amount=Decimal("-10.00"),
        date=date(2026, 8, 1),
        currency="USD",
    )
    assert tx.original_description == "GITHUB *COPILOT"
    assert tx.amount == Decimal("-10.00")
    assert tx.date == date(2026, 8, 1)
    assert tx.currency == "USD"


def test_original_description_is_preserved_intact():
    """Verify that original description is not stripped or altered during model instantiation."""
    raw = "   Spaces   MixedCase   Special*#   "
    tx = TransactionInput(
        original_description=raw,
        amount=Decimal("-50.00"),
    )
    # Must preserve exact original description
    assert tx.original_description == raw


def test_monetary_amounts_positive_negative_and_zero():
    """Verify positive, negative, and zero Decimal amounts are supported."""
    tx_pos = TransactionInput(original_description="Client Pmt", amount=Decimal("1250.50"))
    assert tx_pos.amount == Decimal("1250.50")

    tx_neg = TransactionInput(original_description="Server Bill", amount=Decimal("-45.99"))
    assert tx_neg.amount == Decimal("-45.99")

    tx_zero = TransactionInput(original_description="Auth Hold", amount=Decimal("0.00"))
    assert tx_zero.amount == Decimal("0.00")


def test_monetary_amount_string_conversion():
    """Verify amount string is safely converted into Decimal without float loss."""
    tx = TransactionInput(original_description="Hosting", amount="19.99")
    assert isinstance(tx.amount, Decimal)
    assert tx.amount == Decimal("19.99")


@pytest.mark.parametrize("invalid_amount", [
    "invalid",
    "abc",
    "12.34.56",
    "",
    "   ",
    None,
    Decimal("NaN"),
    Decimal("Infinity"),
    Decimal("-Infinity"),
])
def test_invalid_monetary_amounts_rejected(invalid_amount):
    """Verify malformed monetary values raise ValidationError rather than defaulting to zero."""
    with pytest.raises((ValidationError, ValueError)):
        TransactionInput(
            original_description="Test Merchant",
            amount=invalid_amount,  # type: ignore
        )


def test_categorization_result_valid():
    """Verify CategorizationResult creation and properties."""
    result = CategorizationResult(
        category="Software",
        confidence_score=0.95,
        explanation="Known software pattern matched.",
        review_required=False,
        normalized_description="GITHUB",
    )
    assert result.category == "Software"
    assert result.confidence_score == 0.95
    assert result.explanation == "Known software pattern matched."
    assert result.classification_reason == "Known software pattern matched."
    assert result.review_required is False
    assert result.normalized_description == "GITHUB"


def test_categorization_result_confidence_score_bounds():
    """Verify confidence score must be between 0.0 and 1.0."""
    with pytest.raises(ValidationError):
        CategorizationResult(
            category="Software",
            confidence_score=1.5,
            explanation="Invalid score",
            review_required=False,
            normalized_description="TEST",
        )

    with pytest.raises(ValidationError):
        CategorizationResult(
            category="Software",
            confidence_score=-0.1,
            explanation="Invalid score",
            review_required=False,
            normalized_description="TEST",
        )
