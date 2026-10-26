"""Tests for the categorization engine."""

from decimal import Decimal
from datetime import date

from backend.models import (
    RawTransaction, TransactionType, BusinessCategory,
    ReviewStatus, Confidence,
)
from backend.categorizer import categorize_transactions


def _make_tx(description: str, amount: str, dt: str = "2024-01-15") -> RawTransaction:
    return RawTransaction(
        date=date.fromisoformat(dt),
        description=description,
        amount=Decimal(amount),
    )


class TestTransferRules:
    def test_verified_transfer_to_savings(self):
        txs, _ = categorize_transactions([_make_tx("TRANSFER TO SAVINGS", "-500.00")])
        assert txs[0].transaction_type == TransactionType.TRANSFER
        assert txs[0].business_category == BusinessCategory.INTERNAL_TRANSFER

    def test_verified_transfer_from_checking(self):
        txs, _ = categorize_transactions([_make_tx("TRANSFER FROM CHECKING", "300.00")])
        assert txs[0].transaction_type == TransactionType.TRANSFER

    def test_atm_withdrawal(self):
        txs, _ = categorize_transactions([_make_tx("ATM WITHDRAWAL", "-200.00")])
        assert txs[0].transaction_type == TransactionType.TRANSFER
        assert txs[0].business_category == BusinessCategory.CASH_WITHDRAWAL

    def test_generic_venmo_routes_to_needs_review(self):
        """Ambiguous P2P payment should NOT be automatically assumed to be internal transfer."""
        txs, _ = categorize_transactions([_make_tx("VENMO PAYMENT", "-75.00")])
        assert txs[0].review_status == ReviewStatus.NEEDS_REVIEW
        assert txs[0].confidence == Confidence.LOW

    def test_venmo_to_contractor_is_expense(self):
        """P2P payment to contractor/freelancer must be treated as expense, not internal transfer."""
        txs, _ = categorize_transactions([_make_tx("VENMO PAYMENT TO CONTRACTOR", "-350.00")])
        assert txs[0].transaction_type == TransactionType.EXPENSE
        assert txs[0].business_category == BusinessCategory.CONTRACTOR_EXPENSE


class TestRefundRules:
    def test_matched_refund_reduces_expenses_not_income(self):
        txs, _ = categorize_transactions([_make_tx("REFUND - ADOBE CREATIVE CLOUD", "54.99")])
        assert txs[0].transaction_type == TransactionType.REFUND
        assert txs[0].business_category == BusinessCategory.SOFTWARE
        assert txs[0].review_status == ReviewStatus.AUTO_CATEGORIZED

    def test_unmatched_refund_routes_to_needs_review(self):
        """Unmatched refund must NOT be assumed to reduce expenses blindly."""
        txs, _ = categorize_transactions([_make_tx("REFUND - UNKNOWN VENDOR XYZ", "25.00")])
        assert txs[0].transaction_type == TransactionType.REFUND
        assert txs[0].business_category == BusinessCategory.UNKNOWN
        assert txs[0].review_status == ReviewStatus.NEEDS_REVIEW
        assert txs[0].confidence == Confidence.LOW

    def test_negative_refund_routes_to_needs_review(self):
        """A negative amount described as refund is an outflow (e.g. paying back a client)."""
        txs, _ = categorize_transactions([_make_tx("REFUND TO CUSTOMER", "-100.00")])
        assert txs[0].review_status == ReviewStatus.NEEDS_REVIEW
        assert "negative" in txs[0].explanation.lower()

    def test_links_refund_to_prior_purchase(self):
        """When an original purchase exists, the refund should link to its transaction ID."""
        purchase = _make_tx("ADOBE CREATIVE CLOUD", "-54.99", "2024-01-05")
        refund = _make_tx("REFUND - ADOBE CREATIVE CLOUD", "54.99", "2024-01-16")
        txs, _ = categorize_transactions([purchase, refund])
        assert txs[1].linked_transaction_id == 1


class TestFeePriorityConflict:
    def test_stripe_fee_matches_payment_processing_not_bank_fee(self):
        """Payment processing fee (R025) must win over general bank fee (R020)."""
        txs, _ = categorize_transactions([_make_tx("STRIPE PROCESSING FEE", "-45.00")])
        assert txs[0].transaction_type == TransactionType.FEE
        assert txs[0].business_category == BusinessCategory.PAYMENT_PROCESSING
        assert txs[0].rule_id == "R025"

    def test_general_bank_fee(self):
        txs, _ = categorize_transactions([_make_tx("MONTHLY SERVICE FEE", "-12.00")])
        assert txs[0].transaction_type == TransactionType.FEE
        assert txs[0].business_category == BusinessCategory.BANK_FEES


class TestIncomeAndVendorInvoices:
    def test_client_payment_income(self):
        txs, _ = categorize_transactions([_make_tx("CLIENT PAYMENT - WEBFLOW PROJECT", "1800.00")])
        assert txs[0].transaction_type == TransactionType.INCOME
        assert txs[0].business_category == BusinessCategory.CLIENT_INCOME

    def test_vendor_invoice_with_negative_amount_not_income(self):
        """'Invoice from Vendor' with negative amount must NOT be classified as Client Income!"""
        txs, _ = categorize_transactions([_make_tx("INVOICE FROM VENDOR", "-50.00")])
        assert txs[0].transaction_type != TransactionType.INCOME
        assert txs[0].business_category != BusinessCategory.CLIENT_INCOME

    def test_negative_invoice_routes_to_expense_or_review(self):
        txs, _ = categorize_transactions([_make_tx("INVOICE PAYMENT TO SUPPLIER", "-120.00")])
        assert txs[0].transaction_type == TransactionType.EXPENSE


class TestWordBoundaries:
    def test_aws_matches_word_boundary(self):
        txs, _ = categorize_transactions([_make_tx("AWS CLOUD HOSTING", "-85.00")])
        assert txs[0].transaction_type == TransactionType.EXPENSE
        assert txs[0].business_category == BusinessCategory.SOFTWARE

    def test_aws_does_not_match_flaws_or_lawson(self):
        """Short pattern 'aws' must NOT match substring within unrelated words."""
        txs, _ = categorize_transactions([_make_tx("LAWSON HARDWARE", "-30.00")])
        assert txs[0].business_category != BusinessCategory.SOFTWARE
        assert txs[0].review_status == ReviewStatus.NEEDS_REVIEW


class TestDuplicateDetection:
    def test_normalizes_description_for_duplicates(self):
        """Differences in case or extra whitespace should still be flagged as duplicates."""
        tx1 = _make_tx("JOES CAFE 9921", "-18.40", "2024-01-10")
        tx2 = _make_tx("Joes Cafe  9921", "-18.40", "2024-01-10")
        txs, warnings = categorize_transactions([tx1, tx2])
        assert txs[0].is_possible_duplicate is True
        assert txs[1].is_possible_duplicate is True
        assert any("duplicate" in w.lower() for w in warnings)
