"""Kind detection – determines the transaction KIND before category scoring.

Order: first matching rule wins (ordered from most-specific to least).
"""
from __future__ import annotations

import re

from app.brain.taxonomy import TxKind

_CC_PAYMENT_PATTERNS = [
    r"PAYMENT THANK YOU",
    r"AUTOPAY",
    r"ONLINE PAYMENT",
    r"PAYMENT - THANK",
    r"PAYMENT TO\s+\w",
    r"AUTO PAY",
    r"CARD PAYMENT",
    r"CREDIT CARD PAYMENT",
]

_TRANSFER_PATTERNS = [
    r"TRANSFER TO",
    r"TRANSFER FROM",
    r"ONLINE TRANSFER",
    r"FUNDS TRANSFER",
    r"ACH TRANSFER",
    r"WIRE TRANSFER",
    r"ZELLE TO SELF",
    r"INTRABANK TRANSFER",
]

_TAX_PAYMENT_PATTERNS = [
    r"IRS\s+USATAXPYMT",
    r"IRS\s+",
    r"EFTPS",
    r"STATE\s+TAX\s+PAYMENT",
    r"US TREASURY",
    r"FRANCHISE TAX",
    r"ESTIMATED TAX",
]

_OWNER_DRAW_PATTERNS = [
    r"ATM WITHDRAWAL",
    r"ATM CASH",
    r"CASH WITHDRAWAL",
    r"OWNER DRAW",
    r"OWNER DISTRIBUTION",
    r"PERSONAL TRANSFER",
    r"TRANSFER TO PERSONAL",
    r"TRANSFER TO SAVINGS",  # savings might be personal – flag for review
]

_INTEREST_INCOME_PATTERNS = [
    r"INTEREST EARNED",
    r"INTEREST PAID TO YOU",
    r"DIVIDEND",
    r"INTEREST CREDIT",
]

_INTEREST_EXPENSE_PATTERNS = [
    r"INTEREST CHARGE",
    r"INTEREST PAYMENT",
    r"FINANCE CHARGE",
    r"LOAN INTEREST",
]

_LOAN_PAYMENT_PATTERNS = [
    r"LOAN PAYMENT",
    r"MORTGAGE PAYMENT",
    r"AUTO LOAN",
    r"STUDENT LOAN",
    r"SBA LOAN",
]

_REFUND_KEYWORDS = {
    "REFUND", "RETURN", "REVERSAL", "CREDIT ADJ", "CREDIT ADJUSTMENT",
    "CHARGEBACK", "DISPUTE CREDIT",
}

_FEE_PATTERNS = [
    r"MONTHLY SERVICE FEE",
    r"ANNUAL FEE",
    r"FOREIGN TRANSACTION FEE",
    r"OVERDRAFT FEE",
    r"NSF FEE",
    r"WIRE FEE",
    r"ATM FEE",
    r"LATE FEE",
    r"RETURNED ITEM FEE",
]

_INCOME_PATTERNS = [
    r"STRIPE\s+TRANSFER",
    r"PAYPAL\s+TRANSFER",
    r"PAYPAL\s+PAYMENT\s+RECV",
    r"GUSTO\s+",  # payroll (sole prop pays self)
    r"CLIENT\s+PAYMENT",
    r"INVOICE\s+PAYMENT",
    r"DIRECT\s+DEPOSIT",
    r"ACH\s+CREDIT\s+\w",  # ACH CREDIT <company name> → income; bare "ACH CREDIT" alone → unknown
    r"WIRE\s+IN",
    r"SQUARE\s+PAYMENT",
    r"VENMO\s+PAYMENT\s+RECV",
    r"ZELLE\s+PAYMENT\s+RECV",
    # Note: bare "DEPOSIT" is NOT here – it's ambiguous (cash, transfer, income?)
]


def _matches_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(pat, text, re.I) for pat in patterns)


def _has_refund_keyword(text: str) -> bool:
    upper = text.upper()
    return any(kw in upper for kw in _REFUND_KEYWORDS)


def detect_kind(
    description: str,
    amount_cents: int,
    *,
    account_type: str = "checking",
    prior_debits_at_merchant: bool = False,
) -> TxKind:
    """Detect the transaction kind from description + amount.

    Args:
        description: raw bank description (already uppercased)
        amount_cents: signed cents (negative = outflow, positive = inflow)
        account_type: 'checking' or 'credit_card'
        prior_debits_at_merchant: True if there is a prior debit at this merchant
                                   (used to classify credit as refund)
    """
    text = description.upper()
    is_credit = amount_cents > 0
    is_debit = amount_cents < 0

    # 1. CC payment (outflow from checking or credit balance payment)
    if _matches_any(text, _CC_PAYMENT_PATTERNS):
        return TxKind.CC_PAYMENT

    # 2. Transfer (non-P&L move between accounts)
    if _matches_any(text, _TRANSFER_PATTERNS):
        return TxKind.TRANSFER

    # 3. Tax payment
    if _matches_any(text, _TAX_PAYMENT_PATTERNS):
        return TxKind.TAX_PAYMENT

    # 4. Loan payment
    if _matches_any(text, _LOAN_PAYMENT_PATTERNS):
        return TxKind.LOAN_PAYMENT

    # 5. Owner draw (ATM / transfer to personal)
    if _matches_any(text, _OWNER_DRAW_PATTERNS):
        return TxKind.OWNER_DRAW

    # 6. Interest income
    if is_credit and _matches_any(text, _INTEREST_INCOME_PATTERNS):
        return TxKind.INTEREST_INCOME

    # 7. Interest expense
    if is_debit and _matches_any(text, _INTEREST_EXPENSE_PATTERNS):
        return TxKind.INTEREST_EXPENSE

    # 8. Fee (bank charges)
    if _matches_any(text, _FEE_PATTERNS):
        return TxKind.FEE

    # 9. Refund: credit that explicitly says refund/return, OR credit at a merchant
    #    where we've seen prior debits
    if is_credit and (_has_refund_keyword(text) or prior_debits_at_merchant):
        return TxKind.REFUND

    # 10. Income (positive inflows that look like client payments/deposits)
    if is_credit and _matches_any(text, _INCOME_PATTERNS):
        return TxKind.INCOME

    # 11. Unknown credit – flag for review (could be income, gift, refund, etc.)
    if is_credit:
        return TxKind.UNKNOWN

    # 12. Default: expense (a debit that didn't match anything above)
    return TxKind.EXPENSE
