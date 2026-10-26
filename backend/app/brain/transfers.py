"""
Stage 1 – Hard exclusions: transfers, credit-card payments, owner draws.

Pure functions operating on NormalizedRow lists.
"""

from __future__ import annotations

import re
from datetime import timedelta

from app.brain.normalize import NormalizedRow
from app.brain.pipeline_types import Proposal

# ── Keywords ────────────────────────────────────────────────────────────────

_TRANSFER_KW = re.compile(
    r"\b(TRANSFER|XFER|ONLINE TRANSFER|ACH TRANSFER|WIRE TRANSFER|ZELLE\s*(TO SELF)?)\b",
    re.I,
)

_CC_PAYMENT_KW = re.compile(
    r"\b(PAYMENT\s*-?\s*THANK\s*YOU|AUTOPAY|AUTO\s*PAY|CARD\s*PAYMENT|"
    r"ONLINE\s*PAYMENT|PAYMENT\s*RECEIVED|PAYOFF)\b",
    re.I,
)

_OWNER_DRAW_KW = re.compile(
    r"\b(OWNER\s*DRAW|OWNER\s*CONTRIBUTION|CAPITAL\s*CONTRIBUTION|DISTRIBUTION)\b",
    re.I,
)

_ATM_KW = re.compile(
    r"\b(ATM\s*WITHDRAWAL|ATM\s*CASH|CASH\s*WITHDRAWAL|ATM)\b",
    re.I,
)


def check_exclusions(row: NormalizedRow) -> Proposal | None:
    """Return a Proposal if the row is a non-spending movement, else None."""
    desc = row.merchant_key

    if _CC_PAYMENT_KW.search(desc) or _CC_PAYMENT_KW.search(row.raw_description):
        return Proposal(
            category="credit_card_payment",
            confidence=0.97,
            reason="Matched credit card payment keyword",
            stage="exclusions",
        )

    if _TRANSFER_KW.search(desc) or _TRANSFER_KW.search(row.raw_description):
        return Proposal(
            category="transfer",
            confidence=0.90,
            reason="Matched transfer keyword",
            stage="exclusions",
        )

    if _OWNER_DRAW_KW.search(desc) or _OWNER_DRAW_KW.search(row.raw_description):
        return Proposal(
            category="owner_draw_contribution",
            confidence=0.90,
            reason="Matched owner draw / contribution keyword",
            stage="exclusions",
        )

    if _ATM_KW.search(desc) or _ATM_KW.search(row.raw_description):
        return Proposal(
            category="needs_review",
            confidence=0.0,
            reason="ATM / cash withdrawal – purpose unknown",
            stage="exclusions",
            flags=["atm_withdrawal"],
        )

    return None


def detect_transfer_pairs(
    rows: list[NormalizedRow],
    max_days: int = 3,
) -> list[tuple[int, int]]:
    """
    Find debit/credit pairs of equal magnitude within *max_days* apart.

    Returns list of (debit_row_index, credit_row_index) pairs.
    Only works when both accounts' statements are uploaded together.
    """
    pairs: list[tuple[int, int]] = []
    debits = [(r.row_index, r) for r in rows if r.amount_cents < 0]
    credits = [(r.row_index, r) for r in rows if r.amount_cents > 0]

    matched_credit_idxs: set[int] = set()
    delta = timedelta(days=max_days)

    for d_idx, d_row in debits:
        for c_idx, c_row in credits:
            if c_idx in matched_credit_idxs:
                continue
            if abs(d_row.amount_cents) == c_row.amount_cents:
                if abs(d_row.posted_date - c_row.posted_date) <= delta:
                    pairs.append((d_idx, c_idx))
                    matched_credit_idxs.add(c_idx)
                    break

    return pairs
