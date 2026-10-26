"""Rule-based transaction categorizer for freelance design business expenses."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.models import (
    CategorizedTransaction,
    Category,
    CategorySummary,
    Confidence,
    Transaction,
)


@dataclass(frozen=True)
class RuleMatch:
    category: Category
    confidence: Confidence
    reason: str


# (pattern, category, confidence, reason template)
MERCHANT_RULES: list[tuple[re.Pattern[str], Category, Confidence, str]] = [
    (re.compile(r"ADOBE|CREATIVE\s*CLOUD|FIGMA|CANVA|SKETCH|INVISION", re.I), Category.SOFTWARE, "high", "Known design software vendor"),
    (re.compile(r"GITHUB|GITLAB|JETBRAINS|NOTION|DROPBOX|GOOGLE\s*WORKSPACE|MICROSOFT\s*365|OFFICE\s*365", re.I), Category.SOFTWARE, "high", "Software or productivity subscription"),
    (re.compile(r"UBER\s*\*?\s*TRIP|LYFT|AIRBNB|DELTA|UNITED\s*AIR|AMERICAN\s*AIR|SOUTHWEST|HERTZ|ENTERPRISE\s*RENT", re.I), Category.TRAVEL, "high", "Travel or transportation vendor"),
    (re.compile(r"STAPLES|OFFICE\s*DEPOT|OFFICEMAX|AMAZON\s*MKT|AMZN\s*Mktp", re.I), Category.OFFICE, "medium", "Office or general supplies retailer"),
    (re.compile(r"STARBUCKS|COFFEE|RESTAURANT|DOORDASH|GRUBHUB|UBER\s*\*?\s*EATS|MCDONALD", re.I), Category.MEALS, "medium", "Food or dining merchant pattern"),
    (re.compile(r"UPWORK|FIVERR|LEGALZOOM|ACCOUNTANT|CPA\b|QUICKBOOKS", re.I), Category.PROFESSIONAL, "high", "Professional or contractor service"),
    (re.compile(r"GOOGLE\s*ADS|FACEBOOK\s*ADS|META\s*ADS|MAILCHIMP|HOOTSUITE", re.I), Category.MARKETING, "high", "Marketing or advertising platform"),
    (re.compile(r"APPLE\s*STORE|BEST\s*BUY|B&H\s*PHOTO|CDW", re.I), Category.EQUIPMENT, "high", "Hardware or equipment retailer"),
    (re.compile(r"COMCAST|XFINITY|VERIZON|AT&T|T-MOBILE|SPECTRUM", re.I), Category.UTILITIES, "high", "Telecom or utility provider"),
]

TRANSFER_PATTERN = re.compile(
    r"TRANSFER\s+TO|TRANSFER\s+FROM|PAYMENT\s+THANK\s+YOU|AUTOPAY|CREDIT\s+CARD\s+PAYMENT|"
    r"PAY\s+FROM\s+CHK|SAVINGS|INTERNAL\s+TRANSFER|ONLINE\s+BANKING\s+TRANSFER",
    re.I,
)
REFUND_PATTERN = re.compile(
    r"REFUND|RETURNED|REVERSAL|CHARGEBACK|CREDIT\s+ADJUSTMENT|MERCHANT\s+CREDIT",
    re.I,
)
INCOME_PATTERN = re.compile(
    r"PAYROLL|DIRECT\s+DEP|CLIENT\s+PAYMENT|INVOICE\s+PAID|ACH\s+CREDIT",
    re.I,
)


def _normalize_description(description: str) -> str:
    text = description.upper().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def _match_merchant_rules(description: str) -> RuleMatch | None:
    for pattern, category, confidence, reason in MERCHANT_RULES:
        if pattern.search(description):
            return RuleMatch(category=category, confidence=confidence, reason=reason)
    return None


def categorize_transaction(tx: Transaction) -> CategorizedTransaction:
    desc_norm = _normalize_description(tx.description)
    amount = tx.amount

    if TRANSFER_PATTERN.search(desc_norm):
        return _build(tx, Category.NOT_SPENDING, "high", "Identified as transfer or card payment (not a business expense)")

    if REFUND_PATTERN.search(desc_norm):
        return _build(tx, Category.REFUND, "high", "Refund or reversal — money back, not new spending")

    if amount > 0 and INCOME_PATTERN.search(desc_norm):
        return _build(tx, Category.NOT_SPENDING, "high", "Incoming payment — not a deductible expense")

    if amount > 0 and not REFUND_PATTERN.search(desc_norm):
        # Credit on a card statement without clear refund wording — ask the user
        if abs(amount) >= 500:
            return _build(
                tx,
                Category.NEEDS_REVIEW,
                "low",
                "Large credit without a clear refund keyword — verify before categorizing",
            )
        return _build(tx, Category.REFUND, "medium", "Positive amount on statement — treated as refund/credit")

    if re.search(r"\b\d{4,}\s*$", desc_norm):
        merchant = _match_merchant_rules(desc_norm)
        if merchant and merchant.confidence == "high":
            return _build(tx, merchant.category, merchant.confidence, merchant.reason)
        return _build(
            tx,
            Category.NEEDS_REVIEW,
            "unknown",
            "Generic merchant with store ID — no confident category match",
        )

    merchant = _match_merchant_rules(desc_norm)
    if merchant:
        if merchant.confidence == "medium":
            return _build(tx, merchant.category, merchant.confidence, f"{merchant.reason} (verify merchant)")
        return _build(tx, merchant.category, merchant.confidence, merchant.reason)

    if re.search(r"\d{4,}$", desc_norm.replace(" ", "")):
        return _build(
            tx,
            Category.NEEDS_REVIEW,
            "unknown",
            "Generic merchant with store ID — no confident category match",
        )

    if len(desc_norm) < 4:
        return _build(tx, Category.NEEDS_REVIEW, "unknown", "Description too short to classify safely")

    return _build(
        tx,
        Category.NEEDS_REVIEW,
        "unknown",
        "No rule matched this merchant — manual review recommended",
    )


def _build(
    tx: Transaction,
    category: Category,
    confidence: Confidence,
    reason: str,
) -> CategorizedTransaction:
    return CategorizedTransaction(
        id=tx.id,
        date=tx.date,
        description=tx.description,
        amount=tx.amount,
        raw_amount=tx.raw_amount,
        category=category,
        confidence=confidence,
        reason=reason,
    )


def categorize_all(transactions: list[Transaction]) -> list[CategorizedTransaction]:
    return [categorize_transaction(t) for t in transactions]


def summarize_by_category(transactions: list[CategorizedTransaction]) -> list[CategorySummary]:
    totals: dict[Category, tuple[float, int]] = {}
    for tx in transactions:
        cat = tx.effective_category
        prev_total, prev_count = totals.get(cat, (0.0, 0))
        totals[cat] = (prev_total + tx.amount, prev_count + 1)

    summaries = [
        CategorySummary(category=cat, total=round(total, 2), count=count)
        for cat, (total, count) in totals.items()
    ]
    summaries.sort(key=lambda s: s.category.value)
    return summaries
