"""Integration tests for the brain engine (pure, no DB)."""
from __future__ import annotations

from datetime import date

import pytest

from app.brain import BrainContext, RawTransaction, categorize
from app.brain.taxonomy import TxKind


def _make(desc: str, amount: int, *, txid: str = "t1", dt: date = date(2026, 1, 15)) -> RawTransaction:
    return RawTransaction(id=txid, description_raw=desc, amount_cents=amount, posted_date=dt)


DEFAULT_CTX = BrainContext()


@pytest.mark.parametrize(
    "description, amount, expected_category, expected_status",
    [
        # Clear software hits
        ("ADOBE CREATIVE CLOUD", -5499, "software", "auto"),
        ("FIGMA SUBSCRIPTION", -1500, "software", "auto"),
        ("GITHUB INC", -400, "software", "auto"),
        # Meals
        ("STARBUCKS STORE 12345", -850, "meals", "auto"),
        ("SQ *JOES CAFE 9921 BROOKLYN NY", -2400, "meals", "auto"),
        # Travel
        ("DELTA AIR LINES DL1234", -38500, "travel", "auto"),
        ("MARRIOTT HOTEL NYC", -24000, "travel", "auto"),
        # Advertising
        ("GOOGLE ADS CAMPAIGN", -15000, "advertising", "auto"),
        # Utilities
        ("VERIZON WIRELESS", -8500, "utilities", "auto"),
        # Rent
        ("WEWORK MONTHLY MEMBERSHIP", -55000, "rent_cowork", "auto"),
        # Commissions
        ("STRIPE FEE", -930, "commissions", "auto"),
        # Mixed-use → needs_review
        ("AMAZON MARKETPLACE", -4500, "supplies", "needs_review"),
        ("UBER TRIP 8X9K", -2200, "travel", "needs_review"),
        # Transfers
        ("TRANSFER TO SAVINGS 1234", -10000, "non_pl", "auto"),
        ("PAYMENT THANK YOU", -89000, "non_pl", "auto"),
        # Tax payment
        ("IRS USATAXPYMT", -25000, "non_pl", "auto"),
        # Income
        ("STRIPE TRANSFER APEX STUDIO", 150000, "client_income", "auto"),
        # Unknown credit
        ("DEPOSIT 2839021", 50000, None, "needs_review"),
    ],
)
def test_categorize_single(
    description: str,
    amount: int,
    expected_category: str | None,
    expected_status: str,
) -> None:
    txn = _make(description, amount)
    [decision] = categorize([txn], DEFAULT_CTX)
    assert decision.category_slug == expected_category, (
        f"For '{description}': expected category={expected_category!r}, got {decision.category_slug!r}\n"
        f"Reasons: {decision.reasons}"
    )
    assert decision.status == expected_status, (
        f"For '{description}': expected status={expected_status!r}, got {decision.status!r}\n"
        f"review_reason: {decision.review_reason}"
    )


def test_user_rule_overrides_dict() -> None:
    """User rule takes priority over built-in merchant dict."""
    ctx = BrainContext(
        user_rules=[
            {"match_type": "merchant_exact", "pattern": "STARBUCKS STORE",
             "category_slug": "education", "priority": 10, "enabled": True}
        ]
    )
    txn = _make("STARBUCKS STORE 12345", -850)
    [decision] = categorize([txn], ctx)
    assert decision.category_slug == "education"
    assert decision.status == "auto"


def test_equipment_above_threshold_always_review() -> None:
    # $2,950 > $2,500 de-minimis → always_review flag set by scorer
    txn = _make("B&H PHOTO VIDEO EQUIPMENT", -295000)
    [decision] = categorize([txn], DEFAULT_CTX)
    assert decision.status == "needs_review"
    # review_reason includes "Category flagged for review regardless of confidence"
    assert "review" in (decision.review_reason or "").lower()


def test_non_pl_transfer_excluded() -> None:
    txn = _make("ONLINE TRANSFER TO SAVINGS", -50000)
    [decision] = categorize([txn], DEFAULT_CTX)
    assert decision.kind == TxKind.TRANSFER
    assert decision.category_slug == "non_pl"
    assert decision.status == "auto"


def test_cc_payment_excluded() -> None:
    txn = _make("PAYMENT THANK YOU CITICARD", -120000)
    [decision] = categorize([txn], DEFAULT_CTX)
    assert decision.kind == TxKind.CC_PAYMENT
    assert decision.category_slug == "non_pl"


def test_refund_via_explicit_keyword() -> None:
    """A credit with REFUND keyword should always be detected as REFUND."""
    purchase = _make("STARBUCKS STORE 12345", -850, txid="t1", dt=date(2026, 1, 10))
    refund = _make("STARBUCKS STORE REFUND", 850, txid="t2", dt=date(2026, 1, 15))
    decisions = categorize([purchase, refund], DEFAULT_CTX)
    d_map = {d.id: d for d in decisions}
    assert d_map["t2"].kind == TxKind.REFUND


def test_refund_inherits_category_from_batch_same_merchant() -> None:
    """A credit at the same normalized merchant as a prior debit is REFUND."""
    purchase = _make("STARBUCKS STORE 12345", -850, txid="t1", dt=date(2026, 1, 10))
    # Same normalized merchant: "STARBUCKS STORE"
    refund = _make("STARBUCKS STORE", 850, txid="t2", dt=date(2026, 1, 15))
    decisions = categorize([purchase, refund], DEFAULT_CTX)
    d_map = {d.id: d for d in decisions}
    assert d_map["t2"].kind == TxKind.REFUND


def test_unknown_credit_flagged() -> None:
    txn = _make("DEPOSIT 2839021", 50000)
    [decision] = categorize([txn], DEFAULT_CTX)
    assert decision.status == "needs_review"
    assert decision.category_slug is None


def test_reasons_are_non_empty() -> None:
    txn = _make("ADOBE CREATIVE CLOUD", -5499)
    [decision] = categorize([txn], DEFAULT_CTX)
    assert len(decision.reasons) > 0


def test_confidence_range() -> None:
    txns = [_make(f"TXDESC {i}", -(i + 1) * 100, txid=str(i)) for i in range(5)]
    decisions = categorize(txns, DEFAULT_CTX)
    for d in decisions:
        assert 0.0 <= d.confidence <= 1.0
