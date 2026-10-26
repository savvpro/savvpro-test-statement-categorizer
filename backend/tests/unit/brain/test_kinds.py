"""Unit tests for kind detection."""
import pytest

from app.brain.kinds import detect_kind
from app.brain.taxonomy import TxKind


@pytest.mark.parametrize(
    "description, amount, expected_kind",
    [
        # CC payments
        ("PAYMENT THANK YOU", -50000, TxKind.CC_PAYMENT),
        ("AUTOPAY CITI CARD", -120000, TxKind.CC_PAYMENT),
        ("ONLINE PAYMENT", -75000, TxKind.CC_PAYMENT),
        # Transfers
        ("TRANSFER TO SAVINGS 1234", -10000, TxKind.TRANSFER),
        ("ONLINE TRANSFER TO CHECKING", -50000, TxKind.TRANSFER),
        ("ACH TRANSFER FUNDS", -25000, TxKind.TRANSFER),
        ("WIRE TRANSFER INTL", -200000, TxKind.TRANSFER),
        # Tax payments
        ("IRS USATAXPYMT", -25000, TxKind.TAX_PAYMENT),
        ("EFTPS TAX PAYMENT", -15000, TxKind.TAX_PAYMENT),
        # Owner draw
        ("ATM WITHDRAWAL BANK", -20000, TxKind.OWNER_DRAW),
        ("ATM CASH DISPENSED", -30000, TxKind.OWNER_DRAW),
        # Interest income
        ("INTEREST EARNED", 50, TxKind.INTEREST_INCOME),
        ("DIVIDEND PAYMENT", 200, TxKind.INTEREST_INCOME),
        # Interest expense
        ("INTEREST CHARGE", -800, TxKind.INTEREST_EXPENSE),
        ("FINANCE CHARGE", -500, TxKind.INTEREST_EXPENSE),
        # Fees
        ("MONTHLY SERVICE FEE", -1500, TxKind.FEE),
        ("FOREIGN TRANSACTION FEE", -350, TxKind.FEE),
        ("OVERDRAFT FEE", -3500, TxKind.FEE),
        # Refund (explicit keyword)
        ("AMAZON REFUND", 4500, TxKind.REFUND),
        ("RETURN CREDIT", 2000, TxKind.REFUND),
        ("REVERSAL CHARGE", 1000, TxKind.REFUND),
        # Refund (credit at merchant with prior debits)
        ("STARBUCKS", 850, TxKind.REFUND),  # prior_debits_at_merchant=True
        # Income
        ("STRIPE TRANSFER CLIENT PAYMENT", 150000, TxKind.INCOME),
        ("ACH CREDIT NEON BRANDS LLC", 95000, TxKind.INCOME),
        ("DIRECT DEPOSIT PAYROLL", 120000, TxKind.INCOME),
        # Unknown credit
        ("DEPOSIT 2839021", 50000, TxKind.UNKNOWN),
        # Expense (default for debit)
        ("ADOBE CREATIVE CLOUD", -5499, TxKind.EXPENSE),
        ("SQ *JOES CAFE", -2400, TxKind.EXPENSE),
    ],
)
def test_detect_kind(description: str, amount: int, expected_kind: TxKind) -> None:
    prior = description in {"STARBUCKS"}  # simulate prior debit for refund test
    result = detect_kind(description, amount, prior_debits_at_merchant=prior)
    assert result == expected_kind, (
        f"detect_kind({description!r}, {amount}) = {result!r}, expected {expected_kind!r}"
    )
