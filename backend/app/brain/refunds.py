"""
Stage 5 (partial) – Refund matching and sign/context logic.

Matches credits to earlier debits by merchant_key within REFUND_LOOKBACK_DAYS.
"""

from __future__ import annotations

import re
from datetime import timedelta

from app.brain.normalize import NormalizedRow
from app.brain.pipeline_types import Proposal
from app.config import CONFIDENCE_INCOME, CONFIDENCE_REFUND, REFUND_LOOKBACK_DAYS

_REFUND_KW = re.compile(r"\b(REFUND|RETURN|REVERSAL|CREDIT ADJ|REBATE)\b", re.I)

_INCOME_KW = re.compile(
    r"\b(STRIPE\s*PAYOUT|STRIPE\s*TRANSFER|PAYPAL\s*TRANSFER|"
    r"ACH\s*DEPOSIT|DIRECT\s*DEPOSIT|INVOICE|CLIENT\s*PAYMENT|"
    r"PAYMENT\s*FROM)\b",
    re.I,
)


def check_refund(
    row: NormalizedRow,
    all_rows: list[NormalizedRow],
    existing_proposals: dict[int, Proposal],
) -> Proposal | None:
    """
    If *row* is a credit, try to match it to an earlier debit
    on the same merchant_key within the lookback window.
    """
    # Only look at credits
    if row.amount_cents <= 0:
        return None

    desc = row.merchant_key
    raw = row.raw_description

    # Explicit refund keyword?
    is_refund_kw = bool(_REFUND_KW.search(desc) or _REFUND_KW.search(raw))

    if is_refund_kw:
        # Try to find the original debit to link
        linked = _find_original_debit(row, all_rows)
        linked_idx = linked.row_index if linked else None
        orig_cat = ""
        if linked_idx is not None and linked_idx in existing_proposals:
            orig_cat = existing_proposals[linked_idx].category
        reason = "Refund keyword matched"
        if orig_cat:
            reason += f" → nets against {orig_cat}"
        return Proposal(
            category="refund_reimbursement",
            confidence=CONFIDENCE_REFUND,
            reason=reason,
            stage="refunds",
            linked_row_index=linked_idx,
        )

    # Non-keyword credit: is it income?
    if _INCOME_KW.search(desc) or _INCOME_KW.search(raw):
        return Proposal(
            category="business_income",
            confidence=CONFIDENCE_INCOME,
            reason="Matched income keyword (Stripe payout, ACH deposit, etc.)",
            stage="refunds",
        )

    # Unmatched credit with same merchant as an earlier debit → possible refund
    linked = _find_original_debit(row, all_rows)
    if linked is not None:
        return Proposal(
            category="refund_reimbursement",
            confidence=0.75,
            reason=f"Credit matches earlier debit on {row.merchant_key} – possible refund",
            stage="refunds",
            linked_row_index=linked.row_index,
        )

    # Completely unmatched credit → needs_review
    return Proposal(
        category="needs_review",
        confidence=0.0,
        reason="Unmatched credit – could not determine if income or refund",
        stage="refunds",
        flags=["unmatched_credit"],
    )


def _find_original_debit(
    credit_row: NormalizedRow,
    all_rows: list[NormalizedRow],
) -> NormalizedRow | None:
    """Find the most recent debit with the same merchant_key within the lookback."""
    lookback = timedelta(days=REFUND_LOOKBACK_DAYS)
    best: NormalizedRow | None = None

    for r in all_rows:
        if r.row_index == credit_row.row_index:
            continue
        if r.amount_cents >= 0:
            continue  # skip credits
        if r.merchant_key != credit_row.merchant_key:
            continue
        if not r.merchant_key:
            continue
        delta = credit_row.posted_date - r.posted_date
        if timedelta(0) <= delta <= lookback:
            if abs(r.amount_cents) >= credit_row.amount_cents:
                if best is None or r.posted_date > best.posted_date:
                    best = r
    return best
