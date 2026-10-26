"""
Transaction direction and cash-flow analyzer.
Determines whether a transaction is an INFLOW, OUTFLOW, REFUND, or TRANSFER,
normalizes amounts to positive magnitudes, and provides the audit reason.
"""

import re
from typing import Tuple
from app.models.transaction import TransactionDirection

# Transfer keywords (non-taxable equity / internal bank movements)
TRANSFER_KEYWORDS = [
    r"\bTRANSFER\s+TO\s+SAVINGS\b",
    r"\bTRANSFER\s+FROM\b",
    r"\bTRANSFER\s+TO\b",
    r"\bONLINE\s+TRANSFER\b",
    r"\bINTERNAL\s+TRANSFER\b",
    r"\bAUTOPAY\s+PAYMENT\b",
    r"\bCREDIT\s+CARD\s+PAYMENT\b",
    r"\bE-?PAYMENT\b",
    r"\bOWNER\s+DRAW\b",
    r"\bPAYMENT\s+THANK\s+YOU\b",
    r"\bPAYMENT\s*-\s*THANK\s+YOU\b",
    r"\bAUTOMATIC\s+PAYMENT\b",
    r"\bACCOUNT\s+TRANSFER\b",
    r"\bSAVINGS\s+TRANSFER\b",
    r"\bCHASE\s+CREDIT\s+CRD\s+EPAY\b",
]

# Refund keywords indicating vendor returns or expense credits
REFUND_KEYWORDS = [
    r"\bREFUND\b",
    r"\bRETURN\b",
    r"\bREVERSAL\b",
    r"\bCHARGEBACK\b",
    r"\bCREDIT\s+ADJ(?:USTMENT)?\b",
    r"\bEXPENSE\s+REVERSAL\b",
    r"\bMERCHANT\s+CREDIT\b",
]

# High confidence business income indicators for freelance tech consultants
INCOME_KEYWORDS = [
    r"\bSTRIPE\s+PAYOUT\b",
    r"\bSTRIPE\s+TRANSFER\b",
    r"\bUPWORK\b",
    r"\bCLIENT\s+PAYMENT\b",
    r"\bINVOICE\s+PAYMENT\b",
    r"\bDIRECT\s+DEPOSIT\b",
    r"\bPAYPAL\s+PAYOUT\b",
    r"\bFIVERR\b",
    r"\bCONSULTING\s+FEE\b",
    r"\bWIRE\s+TRANSFER\s+IN\b",
    r"\bCLIENT\s+WIRE\b",
    r"\bCUSTOMER\s+DEPOSIT\b",
    r"\bACH\s+DEPOSIT\s+CLIENT\b",
]

# Known expense vendors that should NEVER be classified as gross business income
# Even if the transaction is an inflow/credit (e.g. Amazon refund, AWS credit)
EXPENSE_VENDORS = {
    "AMAZON", "AWS", "GITHUB", "VERCEL", "HEROKU", "DIGITALOCEAN",
    "JETBRAINS", "OPENAI", "ADOBE", "FIGMA", "SLACK", "NOTION",
    "ZOOM", "1PASSWORD", "DATADOG", "SENTRY", "DOCKER", "APPLE",
    "BEST BUY", "MICRO CENTER", "TARGET", "WALMART", "UBER", "LYFT",
    "DELTA", "DELTA AIR", "UNITED AIRLINES", "AMTRAK", "AIRBNB",
    "COMCAST", "XFINITY", "VERIZON", "AT&T", "T-MOBILE", "GOOGLE ADS",
    "META ADS", "LINKEDIN ADS", "NAMECHEAP", "GODADDY", "LEGALZOOM",
}


def analyze_direction_and_type(
    raw_desc: str,
    clean_merchant: str,
    amount: float,
    is_credit_statement: bool = False,
) -> Tuple[TransactionDirection, float, str]:
    """
    Classify the cash-flow direction, normalize amount, and explain reason.
    
    Returns:
        (TransactionDirection, normalized_positive_amount, reason)
    """
    text = f"{raw_desc} {clean_merchant}".upper()
    norm_amount = round(abs(amount), 2)

    # 1. Check Transfer keywords first (highest priority for non-taxable flows)
    for pattern in TRANSFER_KEYWORDS:
        if re.search(pattern, text):
            return (
                TransactionDirection.TRANSFER,
                norm_amount,
                f"Transfer keyword match: {pattern}",
            )

    # 2. Check Refund keywords
    for pattern in REFUND_KEYWORDS:
        if re.search(pattern, text):
            return (
                TransactionDirection.REFUND,
                norm_amount,
                f"Refund keyword match: {pattern}",
            )

    # 3. Handle Credit Card vs Bank Account direction semantics
    if is_credit_statement:
        # Credit Card: positive amount = purchase/outflow; negative amount = payment/credit
        if amount < 0:
            # Payment or vendor credit
            if any(term in text for term in ["PAYMENT", "AUTOPAY", "EPAY", "THANK YOU"]):
                return (
                    TransactionDirection.TRANSFER,
                    norm_amount,
                    "Credit card payment received (balance payoff transfer)",
                )
            else:
                return (
                    TransactionDirection.REFUND,
                    norm_amount,
                    "Negative charge on credit statement treated as vendor refund/credit",
                )
        else:
            return (
                TransactionDirection.OUTFLOW,
                norm_amount,
                "Standard credit card expense charge",
            )
    else:
        # Checking/Bank Account: negative amount = outflow/expense; positive = inflow/deposit
        if amount > 0:
            # Inflow candidate
            # Check if this inflow comes from a known expense vendor (e.g. Amazon return deposited to checking)
            merchant_tokens = set(re.findall(r"\b\w+\b", clean_merchant.upper()))
            if merchant_tokens.intersection(EXPENSE_VENDORS):
                return (
                    TransactionDirection.REFUND,
                    norm_amount,
                    f"Deposit from expense vendor {clean_merchant} treated as vendor refund",
                )

            # Check income keywords
            for pattern in INCOME_KEYWORDS:
                if re.search(pattern, text):
                    return (
                        TransactionDirection.INFLOW,
                        norm_amount,
                        f"Business revenue match: {pattern}",
                    )

            # Inflow without explicit income keyword
            return (
                TransactionDirection.INFLOW,
                norm_amount,
                "Positive deposit to account (unclassified revenue source)",
            )
        else:
            # Outflow/expense
            return (
                TransactionDirection.OUTFLOW,
                norm_amount,
                "Standard bank account debit/withdrawal",
            )
