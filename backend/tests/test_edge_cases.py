"""
Unit tests for critical edge cases:
1. Refunds are money back, NOT income.
2. Transfers/Autopay are non-expense balance sheet movements, NOT spending.
3. Currency symbol variations ($1,234.56, negative parentheses).
4. Tax summary calculations with 50% meals rule.
"""

from app.brain.categorizer import categorize_transaction
from app.brain.taxonomy import Category
from app.brain.parser import clean_currency_amount
from app.main import _build_tax_summary
from app.models import TransactionItem


def test_refund_is_not_income():
    # Prompt explicit rule: A refund is money back, not income.
    res1 = categorize_transaction("AMZN MKTPLACE REFUND ORDER 112-94819", 42.50, transaction_type="CREDIT")
    assert res1.category == Category.REFUND_REVERSAL
    assert res1.is_income is False

    res2 = categorize_transaction("RETURN: BEST BUY ELECTRONICS REFUND", 89.99, transaction_type="CREDIT")
    assert res2.category == Category.REFUND_REVERSAL
    assert res2.is_income is False


def test_transfers_and_autopay_are_not_spending():
    # Autopay payment on credit card
    res1 = categorize_transaction("AUTOPAY PAYMENT - THANK YOU", 1250.00, transaction_type="CREDIT")
    assert res1.category == Category.TRANSFER_OWNER_DRAW
    assert res1.is_expense is False

    # Transfer to savings
    res2 = categorize_transaction("ONLINE BANKING TRANSFER TO SAVINGS", -1000.00, transaction_type="DEBIT")
    assert res2.category == Category.TRANSFER_OWNER_DRAW
    assert res2.is_expense is False

    # Owner draw via Zelle
    res3 = categorize_transaction("ZELLE TRANSFER TO OWNER PERSONAL DRAW", -800.00, transaction_type="DEBIT")
    assert res3.category == Category.TRANSFER_OWNER_DRAW
    assert res3.is_expense is False


def test_currency_amount_parsing():
    assert clean_currency_amount("$1,299.00") == 1299.00
    assert clean_currency_amount("-$54.99") == -54.99
    assert clean_currency_amount("(150.00)") == -150.00
    assert clean_currency_amount("42.50CR") == 42.50
    assert clean_currency_amount(" 1,000.50- ") == -1000.50


def test_tax_summary_deductibility_math():
    # Verify statutory 50% limit on business meals and refund offset
    txs = [
        # Software: $100 -> 100% deductible = $100
        TransactionItem(
            id="tx1", date="2024-10-01", raw_description="ADOBE", amount=-100.0,
            transaction_type="DEBIT", cleaned_merchant="ADOBE", category=Category.SOFTWARE_SAAS,
            confidence=0.98, reason="SaaS", needs_review=False, schedule_c_line="Software",
            deductibility_pct=1.0, deductible_amount=100.0, is_expense=True, is_income=False,
            tax_note="", color="#000", user_overridden=False, notes=None
        ),
        # Business Meals: $100 -> 50% deductible = $50
        TransactionItem(
            id="tx2", date="2024-10-02", raw_description="STARBUCKS", amount=-100.0,
            transaction_type="DEBIT", cleaned_merchant="STARBUCKS", category=Category.BUSINESS_MEALS,
            confidence=0.88, reason="Meals", needs_review=False, schedule_c_line="Meals",
            deductibility_pct=0.5, deductible_amount=50.0, is_expense=True, is_income=False,
            tax_note="", color="#000", user_overridden=False, notes=None
        ),
        # Refund: $20 -> reduces expense, not income!
        TransactionItem(
            id="tx3", date="2024-10-03", raw_description="AMAZON REFUND", amount=20.0,
            transaction_type="CREDIT", cleaned_merchant="AMAZON", category=Category.REFUND_REVERSAL,
            confidence=0.96, reason="Refund", needs_review=False, schedule_c_line="Refund",
            deductibility_pct=0.0, deductible_amount=0.0, is_expense=False, is_income=False,
            tax_note="", color="#000", user_overridden=False, notes=None
        ),
        # Income: $500
        TransactionItem(
            id="tx4", date="2024-10-04", raw_description="CLIENT INVOICE", amount=500.0,
            transaction_type="CREDIT", cleaned_merchant="CLIENT", category=Category.GROSS_INCOME,
            confidence=0.96, reason="Income", needs_review=False, schedule_c_line="Gross Receipts",
            deductibility_pct=0.0, deductible_amount=0.0, is_expense=False, is_income=True,
            tax_note="", color="#000", user_overridden=False, notes=None
        ),
    ]

    summary = _build_tax_summary(txs)
    assert summary.gross_income == 500.0
    assert summary.total_raw_expenses == 200.0
    # Total deductible = 100 (SaaS) + 50 (Meals 50%) = 150.0
    assert summary.total_deductible_expenses == 150.0
    assert summary.total_refunds_offset == 20.0
    # Net taxable profit = 500 - (150 - 20) = 370.0
    assert summary.net_taxable_profit == 370.0
