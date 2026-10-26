"""Comprehensive unit tests for the categorization engine.

Verifies all 20 required acceptance criteria from Phase 1 specification:
1. Recognized software merchant.
2. Recognized cloud hosting merchant.
3. Recognized internet provider.
4. Recognized bank fee.
5. Clearly described business income transaction.
6. Explicit refund.
7. Explicit reversal.
8. Possible internal transfer (confirmed and ambiguous).
9. Unknown merchant.
10. Ambiguous merchant description.
11. Case-insensitive matching where intended.
12. Whitespace normalization.
13. Empty or missing descriptions.
14. Invalid monetary input handling.
15. Positive, negative, and zero amounts.
16. Confidence values remaining in the valid range [0.0, 1.0].
17. Review recommendations at confidence thresholds.
18. Explanations being present and meaningful.
19. Original descriptions remaining unchanged.
20. Decimal monetary precision.
"""

from decimal import Decimal
import pytest

from app.schemas.category import DefaultCategory
from app.schemas.transaction import TransactionInput
from app.services.categorizer import CategorizationEngine


# -----------------------------------------------------------------------------
# 1. Recognized Software Merchant
# -----------------------------------------------------------------------------
def test_criterion_01_recognized_software_merchant(engine: CategorizationEngine):
    """Test recognized developer software tools (GitHub, JetBrains, Docker, Cursor)."""
    tx = TransactionInput(
        original_description="JETBRAINS ALL PRODUCTS PACK",
        amount=Decimal("-28.90"),
    )
    result = engine.categorize(tx)

    assert result.category == DefaultCategory.SOFTWARE.value
    assert result.confidence_score >= 0.80
    assert result.review_required is False
    assert "JetBrains" in result.explanation
    assert result.normalized_description == "JETBRAINS ALL PRODUCTS PACK"


# -----------------------------------------------------------------------------
# 2. Recognized Cloud Hosting Merchant
# -----------------------------------------------------------------------------
def test_criterion_02_recognized_cloud_hosting_merchant(engine: CategorizationEngine):
    """Test recognized cloud hosting providers (AWS, DigitalOcean, Vercel, Heroku)."""
    tx = TransactionInput(
        original_description="AWS*BILLING SERVICES US",
        amount=Decimal("-84.20"),
    )
    result = engine.categorize(tx)

    assert result.category == DefaultCategory.CLOUD_HOSTING.value
    assert result.confidence_score >= 0.80
    assert result.review_required is False
    assert "cloud hosting" in result.explanation.lower()


# -----------------------------------------------------------------------------
# 3. Recognized Internet Provider
# -----------------------------------------------------------------------------
def test_criterion_03_recognized_internet_provider(engine: CategorizationEngine):
    """Test recognized internet service providers (Comcast, Verizon, AT&T, Starlink)."""
    tx = TransactionInput(
        original_description="COMCAST CABLE INTERNET",
        amount=Decimal("-79.99"),
    )
    result = engine.categorize(tx)

    assert result.category == DefaultCategory.INTERNET_AND_TELECOM.value
    assert result.confidence_score >= 0.80
    assert result.review_required is False
    assert "internet" in result.explanation.lower()


# -----------------------------------------------------------------------------
# 4. Recognized Bank Fee
# -----------------------------------------------------------------------------
def test_criterion_04_recognized_bank_fee(engine: CategorizationEngine):
    """Test recognized bank service fees."""
    tx = TransactionInput(
        original_description="MONTHLY SERVICE FEE CHK",
        amount=Decimal("-15.00"),
    )
    result = engine.categorize(tx)

    assert result.category == DefaultCategory.BANK_FEES.value
    assert result.confidence_score >= 0.80
    assert result.review_required is False
    assert "fee" in result.explanation.lower()


# -----------------------------------------------------------------------------
# 5. Clearly Described Business Income Transaction
# -----------------------------------------------------------------------------
def test_criterion_05_business_income(engine: CategorizationEngine):
    """Test incoming freelance client payment with positive amount."""
    tx = TransactionInput(
        original_description="CLIENT PAYMENT - ACME ENTERPRISES",
        amount=Decimal("3200.00"),
    )
    result = engine.categorize(tx)

    assert result.category == DefaultCategory.BUSINESS_INCOME.value
    assert result.confidence_score >= 0.80
    assert result.review_required is False
    assert "payment" in result.explanation.lower() or "income" in result.explanation.lower()


def test_business_income_not_assigned_when_amount_negative(engine: CategorizationEngine):
    """Verify an income pattern is NOT classified as income when amount is negative."""
    tx = TransactionInput(
        original_description="CLIENT PAYMENT ADJUSTMENT",
        amount=Decimal("-50.00"),
    )
    result = engine.categorize(tx)

    assert result.category != DefaultCategory.BUSINESS_INCOME.value


# -----------------------------------------------------------------------------
# 6. Explicit Refund
# -----------------------------------------------------------------------------
def test_criterion_06_explicit_refund(engine: CategorizationEngine):
    """Test explicit refund with positive amount."""
    tx = TransactionInput(
        original_description="REFUND CLOUDHOST SERVICES",
        amount=Decimal("25.00"),
    )
    result = engine.categorize(tx)

    assert result.category == DefaultCategory.REFUND.value
    assert result.confidence_score >= 0.80
    assert result.review_required is False
    assert "refund" in result.explanation.lower()


def test_refund_keyword_with_negative_amount_requires_review(engine: CategorizationEngine):
    """Test anomalous refund keyword on a debit charge flags for review."""
    tx = TransactionInput(
        original_description="REFUND PROCESSING FEE",
        amount=Decimal("-5.00"),
    )
    result = engine.categorize(tx)

    assert result.category == DefaultCategory.NEEDS_REVIEW.value
    assert result.review_required is True


# -----------------------------------------------------------------------------
# 7. Explicit Reversal
# -----------------------------------------------------------------------------
def test_criterion_07_explicit_reversal(engine: CategorizationEngine):
    """Test explicit cancellation / reversal indicator."""
    tx = TransactionInput(
        original_description="TRANSACTION REVERSED BY ISSUER",
        amount=Decimal("45.00"),
    )
    result = engine.categorize(tx)

    assert result.category == DefaultCategory.REVERSAL.value
    assert result.confidence_score >= 0.80
    assert result.review_required is False
    assert "reversal" in result.explanation.lower()


def test_subword_not_falsely_matched_as_reversal(engine: CategorizationEngine):
    """Ensure subwords like 'REVOLUTION' or 'RESERVE' do not trigger Reversal rule."""
    tx = TransactionInput(
        original_description="REVOLUTION FITNESS CLUB",
        amount=Decimal("-40.00"),
    )
    result = engine.categorize(tx)

    assert result.category != DefaultCategory.REVERSAL.value


# -----------------------------------------------------------------------------
# 8. Possible Internal Transfer (Confirmed vs Ambiguous)
# -----------------------------------------------------------------------------
def test_criterion_08_confirmed_internal_transfer(engine: CategorizationEngine):
    """Test movement between user's own accounts (e.g. to savings)."""
    tx = TransactionInput(
        original_description="TRANSFER TO SAVINGS ACCT",
        amount=Decimal("-500.00"),
    )
    result = engine.categorize(tx)

    assert result.category == DefaultCategory.INTERNAL_TRANSFER.value
    assert result.confidence_score >= 0.80
    assert result.review_required is False
    assert "internal transfer" in result.explanation.lower()


def test_criterion_08_ambiguous_external_transfer_requires_review(engine: CategorizationEngine):
    """Test unconfirmed transfer target requires manual review."""
    tx = TransactionInput(
        original_description="WIRE TRANSFER TO SUPPLIER CORP",
        amount=Decimal("-1200.00"),
    )
    result = engine.categorize(tx)

    assert result.category == DefaultCategory.NEEDS_REVIEW.value
    assert result.review_required is True
    assert "cannot be confirmed as internal" in result.explanation.lower()


# -----------------------------------------------------------------------------
# 9. Unknown Merchant
# -----------------------------------------------------------------------------
def test_criterion_09_unknown_merchant(engine: CategorizationEngine):
    """Test unrecognized merchant description defaults to Needs Review with zero confidence."""
    tx = TransactionInput(
        original_description="MYSTERY BOUTIQUE #98721",
        amount=Decimal("-34.50"),
    )
    result = engine.categorize(tx)

    assert result.category == DefaultCategory.NEEDS_REVIEW.value
    assert result.confidence_score == 0.0
    assert result.review_required is True
    assert result.explanation == "No sufficiently reliable categorization rule matched this description."


def test_unknown_incoming_positive_is_not_treated_as_income(engine: CategorizationEngine):
    """Verify unknown incoming money is NOT automatically treated as business income."""
    tx = TransactionInput(
        original_description="UNKNOWN DEPOSIT FROM SOMEONE",
        amount=Decimal("450.00"),
    )
    result = engine.categorize(tx)

    assert result.category == DefaultCategory.NEEDS_REVIEW.value
    assert result.confidence_score == 0.0
    assert result.review_required is True


# -----------------------------------------------------------------------------
# 10. Ambiguous Merchant Description
# -----------------------------------------------------------------------------
def test_criterion_10_ambiguous_merchant_retailer(engine: CategorizationEngine):
    """Test broad multi-category merchant (e.g. Amazon retail, Target) flags Needs Review."""
    tx = TransactionInput(
        original_description="AMAZON.COM*MEMBER RETAIL",
        amount=Decimal("-65.00"),
    )
    result = engine.categorize(tx)

    assert result.category == DefaultCategory.NEEDS_REVIEW.value
    assert result.review_required is True
    assert result.confidence_score <= 0.50
    assert "ambiguous" in result.explanation.lower()


def test_ambiguous_merchant_not_confused_with_specific_aws(engine: CategorizationEngine):
    """Verify Amazon Web Services resolves to Cloud Hosting rather than generic retailer."""
    tx = TransactionInput(
        original_description="AMAZON WEB SERVICES BILLING",
        amount=Decimal("-125.00"),
    )
    result = engine.categorize(tx)

    assert result.category == DefaultCategory.CLOUD_HOSTING.value
    assert result.confidence_score >= 0.80
    assert result.review_required is False


# -----------------------------------------------------------------------------
# 11. Case-Insensitive Matching
# -----------------------------------------------------------------------------
def test_criterion_11_case_insensitive_matching(engine: CategorizationEngine):
    """Verify lower, mixed, and uppercase variations match the same rule."""
    tx_lower = TransactionInput(original_description="github copilot", amount=Decimal("-10.00"))
    tx_upper = TransactionInput(original_description="GITHUB COPILOT", amount=Decimal("-10.00"))
    tx_mixed = TransactionInput(original_description="GiThUb CoPiLoT", amount=Decimal("-10.00"))

    res_lower = engine.categorize(tx_lower)
    res_upper = engine.categorize(tx_upper)
    res_mixed = engine.categorize(tx_mixed)

    assert res_lower.category == res_upper.category == res_mixed.category == DefaultCategory.SOFTWARE.value
    assert res_lower.confidence_score == res_upper.confidence_score == res_mixed.confidence_score


# -----------------------------------------------------------------------------
# 12. Whitespace Normalization
# -----------------------------------------------------------------------------
def test_criterion_12_whitespace_normalization_in_engine(engine: CategorizationEngine):
    """Verify repeated whitespace and tabs are normalized without breaking rule matching."""
    tx = TransactionInput(
        original_description="  DIGITALOCEAN  \t\t  CLOUD   VPS  ",
        amount=Decimal("-15.00"),
    )
    result = engine.categorize(tx)

    assert result.category == DefaultCategory.CLOUD_HOSTING.value
    assert result.normalized_description == "DIGITALOCEAN CLOUD VPS"


# -----------------------------------------------------------------------------
# 13. Empty or Missing Descriptions
# -----------------------------------------------------------------------------
def test_criterion_13_empty_descriptions(engine: CategorizationEngine):
    """Verify empty or blank descriptions assign Needs Review safely."""
    tx_empty = TransactionInput(original_description="", amount=Decimal("-10.00"))
    tx_spaces = TransactionInput(original_description="     ", amount=Decimal("-10.00"))

    res_empty = engine.categorize(tx_empty)
    res_spaces = engine.categorize(tx_spaces)

    assert res_empty.category == DefaultCategory.NEEDS_REVIEW.value
    assert res_empty.confidence_score == 0.0
    assert res_empty.review_required is True

    assert res_spaces.category == DefaultCategory.NEEDS_REVIEW.value
    assert res_spaces.confidence_score == 0.0
    assert res_spaces.review_required is True


# -----------------------------------------------------------------------------
# 14. Invalid Monetary Input
# -----------------------------------------------------------------------------
def test_criterion_14_invalid_monetary_input():
    """Verify malformed amounts cannot enter the categorizer and raise exceptions."""
    with pytest.raises(Exception):
        TransactionInput(original_description="TEST", amount="not-a-number")


# -----------------------------------------------------------------------------
# 15. Positive, Negative, and Zero Amounts
# -----------------------------------------------------------------------------
def test_criterion_15_positive_negative_and_zero_amounts(engine: CategorizationEngine):
    """Test behavior across positive, negative, and zero amounts."""
    # Positive amount with income pattern
    tx_pos = TransactionInput(original_description="INVOICE PAYMENT #101", amount=Decimal("1200.00"))
    res_pos = engine.categorize(tx_pos)
    assert res_pos.category == DefaultCategory.BUSINESS_INCOME.value

    # Negative amount with expense pattern
    tx_neg = TransactionInput(original_description="SLACK SUBSCRIPTION", amount=Decimal("-15.00"))
    res_neg = engine.categorize(tx_neg)
    assert res_neg.category == DefaultCategory.SOFTWARE.value

    # Zero amount requires manual review per policy
    tx_zero = TransactionInput(original_description="GITHUB TRIAL VERIFICATION", amount=Decimal("0.00"))
    res_zero = engine.categorize(tx_zero)
    assert res_zero.category == DefaultCategory.NEEDS_REVIEW.value
    assert res_zero.review_required is True
    assert "Zero-amount" in res_zero.explanation


# -----------------------------------------------------------------------------
# 16. Confidence Values Remaining in Valid Range [0.0, 1.0]
# -----------------------------------------------------------------------------
def test_criterion_16_confidence_values_within_bounds(engine: CategorizationEngine):
    """Verify confidence score is always strictly between 0.0 and 1.0."""
    test_descriptions = [
        "GITHUB *COPILOT",
        "DIGITALOCEAN",
        "COMCAST INTERNET",
        "MONTHLY SERVICE FEE",
        "CLIENT PAYMENT",
        "REFUND HOSTING",
        "TRANSACTION REVERSED",
        "TRANSFER TO SAVINGS",
        "AMAZON.COM",
        "RANDOM UNKNOWN MERCHANT 123",
        "",
    ]
    for desc in test_descriptions:
        tx = TransactionInput(original_description=desc, amount=Decimal("-10.00"))
        res = engine.categorize(tx)
        assert 0.0 <= res.confidence_score <= 1.0, f"Score out of bounds for {desc}: {res.confidence_score}"


# -----------------------------------------------------------------------------
# 17. Review Recommendations at Confidence Thresholds
# -----------------------------------------------------------------------------
def test_criterion_17_review_recommendations_at_threshold():
    """Verify review_required flag is set correctly at and around the threshold."""
    # Custom threshold at 0.85
    engine_custom = CategorizationEngine(review_threshold=0.85)

    # A rule with 0.90 confidence -> no review required
    tx_high = TransactionInput(original_description="GITHUB *COPILOT", amount=Decimal("-10.00"))
    res_high = engine_custom.categorize(tx_high)
    assert res_high.review_required is False

    # A rule with 0.70 confidence -> review required
    tx_ambig = TransactionInput(original_description="AMAZON RETAIL", amount=Decimal("-10.00"))
    res_ambig = engine_custom.categorize(tx_ambig)
    assert res_ambig.review_required is True


# -----------------------------------------------------------------------------
# 18. Explanations Present and Meaningful
# -----------------------------------------------------------------------------
def test_criterion_18_explanations_present_and_meaningful(engine: CategorizationEngine):
    """Verify every result contains a non-empty, descriptive explanation."""
    test_cases = [
        ("GITHUB COPILOT", Decimal("-10.00")),
        ("DIGITALOCEAN", Decimal("-20.00")),
        ("CLIENT PAYMENT", Decimal("1000.00")),
        ("REFUND HOSTING", Decimal("20.00")),
        ("RANDOM UNKNOWN", Decimal("-5.00")),
        ("", Decimal("-5.00")),
        ("AUTH HOLD", Decimal("0.00")),
    ]
    for desc, amt in test_cases:
        tx = TransactionInput(original_description=desc, amount=amt)
        res = engine.categorize(tx)
        assert len(res.explanation.strip()) > 10, f"Explanation too short or empty for {desc}"
        assert res.classification_reason == res.explanation


# -----------------------------------------------------------------------------
# 19. Original Descriptions Remaining Unchanged
# -----------------------------------------------------------------------------
def test_criterion_19_original_description_unchanged(engine: CategorizationEngine):
    """Verify that categorization does not alter the input transaction's original_description."""
    raw = "   Mixed Case  \t Description  With   Symbols *#   "
    tx = TransactionInput(original_description=raw, amount=Decimal("-12.50"))
    result = engine.categorize(tx)

    # Input object remains untouched
    assert tx.original_description == raw
    # Result object contains normalized version
    assert result.normalized_description == "MIXED CASE DESCRIPTION WITH SYMBOLS *#"


# -----------------------------------------------------------------------------
# 20. Decimal Monetary Precision
# -----------------------------------------------------------------------------
def test_criterion_20_decimal_monetary_precision(engine: CategorizationEngine):
    """Verify that calculations and amount handling preserve Decimal exactness without float drift."""
    # Ensure standard floating-point inexact values (e.g. 0.1 + 0.2 != 0.3) are handled as exact Decimals
    amt = Decimal("0.10") + Decimal("0.20")
    assert amt == Decimal("0.30")

    tx = TransactionInput(original_description="CLIENT PAYMENT - ACME", amount=amt)
    assert tx.amount == Decimal("0.30")
    assert type(tx.amount) is Decimal

    result = engine.categorize(tx)
    assert result.category == DefaultCategory.BUSINESS_INCOME.value


# -----------------------------------------------------------------------------
# Extra Edge Case: Unexpected positive amount on expense merchant
# -----------------------------------------------------------------------------
def test_unexpected_positive_on_software_merchant_requires_review(engine: CategorizationEngine):
    """If an expense merchant receives positive money without refund indicator, flag for review."""
    tx = TransactionInput(original_description="GITHUB INC", amount=Decimal("50.00"))
    result = engine.categorize(tx)

    assert result.category == DefaultCategory.NEEDS_REVIEW.value
    assert result.review_required is True
    assert "positive amount received without explicit refund indicator" in result.explanation
