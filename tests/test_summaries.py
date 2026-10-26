"""Tests for the financial summary computation."""


from decimal import Decimal
from datetime import date

from backend.models import (
    CategorizedTransaction, TransactionType, BusinessCategory,
    ReviewStatus, Confidence,
)
from backend.summaries import compute_summary


def _make_cat_tx(
    tx_type: TransactionType,
    biz_cat: BusinessCategory,
    amount: str,
    review: ReviewStatus = ReviewStatus.AUTO_CATEGORIZED,
    idx: int = 1,
) -> CategorizedTransaction:
    return CategorizedTransaction(
        id=idx,
        date=date(2024, 1, 15),
        description="Test",
        amount=Decimal(amount),
        transaction_type=tx_type,
        business_category=biz_cat,
        review_status=review,
        confidence=Confidence.HIGH,
        explanation="Test",
        rule_id="T001",
    )


class TestSummaryComputation:
    def test_income_totals(self):
        txs = [
            _make_cat_tx(TransactionType.INCOME, BusinessCategory.CLIENT_INCOME, "1000.00", idx=1),
            _make_cat_tx(TransactionType.INCOME, BusinessCategory.CLIENT_INCOME, "2000.00", idx=2),
        ]
        summary = compute_summary(txs)
        assert summary.total_income == Decimal("3000.00")

    def test_negative_income_does_not_distort_total(self):
        """Negative amounts marked as income must NOT reduce operating revenue."""
        txs = [
            _make_cat_tx(TransactionType.INCOME, BusinessCategory.CLIENT_INCOME, "1000.00", idx=1),
            _make_cat_tx(TransactionType.INCOME, BusinessCategory.CLIENT_INCOME, "-50.00", idx=2),
        ]
        summary = compute_summary(txs)
        assert summary.total_income == Decimal("1000.00")

    def test_matched_refunds_reduce_net_expenses(self):
        txs = [
            _make_cat_tx(TransactionType.EXPENSE, BusinessCategory.SOFTWARE, "-100.00", idx=1),
            _make_cat_tx(
                TransactionType.REFUND, BusinessCategory.SOFTWARE, "20.00",
                review=ReviewStatus.AUTO_CATEGORIZED, idx=2
            ),
        ]
        summary = compute_summary(txs)
        assert summary.total_expenses == Decimal("100.00")
        assert summary.total_refunds == Decimal("20.00")
        assert summary.matched_refunds == Decimal("20.00")
        assert summary.net_expenses == Decimal("80.00")

    def test_unmatched_refunds_do_not_reduce_net_expenses(self):
        """Unmatched refunds in Needs Review must NOT automatically reduce business expenses."""
        txs = [
            _make_cat_tx(TransactionType.EXPENSE, BusinessCategory.SOFTWARE, "-100.00", idx=1),
            _make_cat_tx(
                TransactionType.REFUND, BusinessCategory.UNKNOWN, "30.00",
                review=ReviewStatus.NEEDS_REVIEW, idx=2
            ),
        ]
        summary = compute_summary(txs)
        assert summary.total_expenses == Decimal("100.00")
        assert summary.total_refunds == Decimal("30.00")
        assert summary.unmatched_refunds == Decimal("30.00")
        assert summary.matched_refunds == Decimal("0.00")
        # Net expenses should stay 100.00 because refund is unmatched!
        assert summary.net_expenses == Decimal("100.00")

    def test_transfers_excluded_from_operating_result(self):
        txs = [
            _make_cat_tx(TransactionType.INCOME, BusinessCategory.CLIENT_INCOME, "1000.00", idx=1),
            _make_cat_tx(TransactionType.TRANSFER, BusinessCategory.INTERNAL_TRANSFER, "-500.00", idx=2),
            _make_cat_tx(TransactionType.TRANSFER, BusinessCategory.INTERNAL_TRANSFER, "300.00", idx=3),
        ]
        summary = compute_summary(txs)
        assert summary.total_income == Decimal("1000.00")
        assert summary.total_transfers == Decimal("800.00")
        assert summary.net_operating_result == Decimal("1000.00")

    def test_net_operating_result_formula(self):
        """net_operating_result = income - net_expenses - fees"""
        txs = [
            _make_cat_tx(TransactionType.INCOME, BusinessCategory.CLIENT_INCOME, "1000.00", idx=1),
            _make_cat_tx(TransactionType.EXPENSE, BusinessCategory.SOFTWARE, "-100.00", idx=2),
            _make_cat_tx(TransactionType.REFUND, BusinessCategory.SOFTWARE, "20.00", idx=3),
            _make_cat_tx(TransactionType.FEE, BusinessCategory.BANK_FEES, "-10.00", idx=4),
        ]
        summary = compute_summary(txs)
        assert summary.net_expenses == Decimal("80.00")
        assert summary.net_operating_result == Decimal("910.00")
