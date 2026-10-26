"""
Release Gate: Financial Correctness Checklist Tests (9 of 9).

Explicitly validates each item specified in the assessment requirements:
1. Vendor invoice with a negative amount
2. Refund with no matching purchase
3. Payment to a contractor through Venmo
4. Stripe processing fee
5. Unrelated merchant containing "aws"
6. NaN, infinity, malformed rows, and invalid UTF-8
7. Duplicate transaction
8. User changes a transaction category
9. Transfers between verified own accounts
"""

import pytest
from decimal import Decimal
from datetime import date

from backend.models import (
    RawTransaction, TransactionType, BusinessCategory,
    ReviewStatus, Confidence, CategorizedTransaction,
)
from backend.parser import parse_csv
from backend.categorizer import categorize_transactions
from backend.summaries import compute_summary


def _make_raw(desc: str, amount: str, dt_str: str = "2024-01-15") -> RawTransaction:
    return RawTransaction(
        date=date.fromisoformat(dt_str),
        description=desc,
        amount=Decimal(amount),
    )


# ---------------------------------------------------------------------------
# Item 1: Vendor invoice with a negative amount
# Must not be classified as client income just because the description contains "invoice".
# ---------------------------------------------------------------------------
def test_item_1_vendor_invoice_with_negative_amount_not_income():
    tx = _make_raw("Invoice from Vendor", "-50.00")
    categorized, _ = categorize_transactions([tx])
    summary = compute_summary(categorized)

    assert categorized[0].transaction_type != TransactionType.INCOME
    assert categorized[0].business_category != BusinessCategory.CLIENT_INCOME
    # Operating income must not be corrupted with -$50
    assert summary.total_income == Decimal("0.00")


# ---------------------------------------------------------------------------
# Item 2: Refund with no matching purchase
# Must be flagged for review rather than automatically reducing expenses.
# ---------------------------------------------------------------------------
def test_item_2_refund_with_no_matching_purchase():
    tx = _make_raw("REFUND - RANDOM MYSTERY VENDOR", "45.00")
    categorized, _ = categorize_transactions([tx])
    summary = compute_summary(categorized)

    assert categorized[0].transaction_type == TransactionType.REFUND
    assert categorized[0].business_category == BusinessCategory.UNKNOWN
    assert categorized[0].review_status == ReviewStatus.NEEDS_REVIEW
    # Unmatched refund must NOT reduce operating expenses
    assert summary.unmatched_refunds == Decimal("45.00")
    assert summary.matched_refunds == Decimal("0.00")
    assert summary.net_expenses == Decimal("0.00")
    assert summary.is_provisional is True


# ---------------------------------------------------------------------------
# Item 3: Payment to a contractor through Venmo
# Must not automatically be excluded as an internal transfer.
# ---------------------------------------------------------------------------
def test_item_3_payment_to_contractor_through_venmo():
    tx = _make_raw("Venmo payment to contractor for design", "-450.00")
    categorized, _ = categorize_transactions([tx])
    summary = compute_summary(categorized)

    assert categorized[0].transaction_type == TransactionType.EXPENSE
    assert categorized[0].business_category == BusinessCategory.CONTRACTOR_EXPENSE
    # Must be counted as a business expense, not excluded as transfer
    assert summary.total_expenses == Decimal("450.00")
    assert summary.total_transfers == Decimal("0.00")


# ---------------------------------------------------------------------------
# Item 4: Stripe processing fee
# Must match Payment Processing rather than the broader Bank Fees rule.
# ---------------------------------------------------------------------------
def test_item_4_stripe_processing_fee_matches_payment_processing():
    tx = _make_raw("STRIPE PROCESSING FEE", "-45.00")
    categorized, _ = categorize_transactions([tx])

    assert categorized[0].transaction_type == TransactionType.FEE
    assert categorized[0].business_category == BusinessCategory.PAYMENT_PROCESSING
    assert categorized[0].rule_id == "R025"  # specific payment processing fee rule


# ---------------------------------------------------------------------------
# Item 5: Unrelated merchant containing "aws"
# Must not be incorrectly categorized as cloud hosting.
# ---------------------------------------------------------------------------
def test_item_5_unrelated_merchant_containing_aws():
    # 'lawson' contains 'aws' as a substring
    tx1 = _make_raw("LAWSON STATIONERY", "-35.00")
    # 'flaws' contains 'aws'
    tx2 = _make_raw("NO FLAWS DRY CLEANERS", "-20.00")

    categorized, _ = categorize_transactions([tx1, tx2])
    for item in categorized:
        assert item.business_category != BusinessCategory.SOFTWARE
        assert item.review_status == ReviewStatus.NEEDS_REVIEW


# ---------------------------------------------------------------------------
# Item 6: NaN, infinity, malformed rows, and invalid UTF-8
# Must produce clear validation errors rather than invalid totals or server errors.
# ---------------------------------------------------------------------------
def test_item_6_nan_infinity_malformed_and_invalid_utf8():
    # NaN
    nan_csv = "Date,Description,Amount\n2024-01-01,Test,NaN\n2024-01-02,Good,50.00\n"
    txs, warnings = parse_csv(nan_csv)
    assert len(txs) == 1
    assert any("not a finite" in w.lower() or "not a valid" in w.lower() for w in warnings)

    # Infinity
    inf_csv = "Date,Description,Amount\n2024-01-01,Test,Infinity\n2024-01-02,Good,50.00\n"
    txs, warnings = parse_csv(inf_csv)
    assert len(txs) == 1
    assert any("not a finite" in w.lower() or "not a valid" in w.lower() for w in warnings)

    # Invalid UTF-8 (Latin-1 encoded Café)
    latin1_bytes = b"Date,Description,Amount\n2024-01-01,Caf\xe9 Supplies,-45.00\n"
    txs, warnings = parse_csv(latin1_bytes)
    assert len(txs) == 1
    assert "Caf" in txs[0].description

    # Missing required header
    with pytest.raises(ValueError, match="required column"):
        parse_csv("Date,Amount\n2024-01-01,10.00\n")


# ---------------------------------------------------------------------------
# Item 7: Duplicate transaction
# Must be flagged without silently deleting either record.
# ---------------------------------------------------------------------------
def test_item_7_duplicate_transaction_flagged_without_deleting():
    tx1 = _make_raw("JOES CAFE 9921", "-18.40", "2024-01-10")
    tx2 = _make_raw("Joes Cafe  9921", "-18.40", "2024-01-10")  # normalized match

    categorized, warnings = categorize_transactions([tx1, tx2])
    summary = compute_summary(categorized)

    assert len(categorized) == 2  # neither record deleted
    assert categorized[0].is_possible_duplicate is True
    assert categorized[1].is_possible_duplicate is True
    assert summary.duplicate_count == 2
    assert any("duplicate" in w.lower() for w in warnings)


# ---------------------------------------------------------------------------
# Item 8: User changes a transaction category
# The displayed summary and exported state must reflect the correction.
# ---------------------------------------------------------------------------
def test_item_8_user_changes_transaction_category():
    tx = _make_raw("JOES CAFE 9921", "-18.40")
    categorized, _ = categorize_transactions([tx])
    summary_before = compute_summary(categorized)

    # Initially in Needs Review
    assert summary_before.needs_review_count == 1
    assert summary_before.is_provisional is True
    assert "Meals & Entertainment" not in summary_before.category_totals

    # User corrects category to Meals & Entertainment
    corrected_tx = categorized[0].model_copy(
        update={
            "transaction_type": TransactionType.EXPENSE,
            "business_category": BusinessCategory.MEALS,
            "review_status": ReviewStatus.USER_CORRECTED,
        }
    )
    summary_after = compute_summary([corrected_tx])

    # Now reconciled
    assert summary_after.needs_review_count == 0
    assert summary_after.is_provisional is False
    assert summary_after.total_expenses == Decimal("18.40")
    assert summary_after.category_totals["Meals & Entertainment"] == Decimal("18.40")


# ---------------------------------------------------------------------------
# Item 9: Transfers between verified own accounts
# Must be excluded from operating income and expenses.
# ---------------------------------------------------------------------------
def test_item_9_transfers_between_verified_own_accounts():
    income_tx = _make_raw("CLIENT PAYMENT", "1000.00")
    transfer_out = _make_raw("TRANSFER TO SAVINGS", "-500.00")
    transfer_in = _make_raw("TRANSFER FROM CHECKING", "300.00")

    categorized, _ = categorize_transactions([income_tx, transfer_out, transfer_in])
    summary = compute_summary(categorized)

    # Transfers are recorded in total_transfers
    assert summary.total_transfers == Decimal("800.00")
    # Operating result must strictly exclude transfers
    assert summary.total_income == Decimal("1000.00")
    assert summary.total_expenses == Decimal("0.00")
    assert summary.net_operating_result == Decimal("1000.00")
