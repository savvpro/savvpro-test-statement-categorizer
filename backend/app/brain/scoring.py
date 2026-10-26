"""
Stage 6 – Scoring: final confidence adjustments, status assignment, flags.
"""

from __future__ import annotations

from statistics import median

from app.brain.categories import CATEGORIES, get_deductible_pct
from app.brain.normalize import NormalizedRow
from app.brain.pipeline_types import Proposal
from app.config import (
    CONFIDENCE_AUTO,
    CONFIDENCE_SUGGESTED,
    CONFLICT_PENALTY,
    LARGE_PURCHASE_CENTS,
    OUTLIER_MULTIPLIER,
    OUTLIER_PENALTY,
)


def apply_scoring(
    row: NormalizedRow,
    proposals: list[Proposal],
    merchant_amounts: dict[str, list[int]],
) -> Proposal:
    """
    Pick the best proposal, apply adjustments (conflict, outlier, large purchase),
    and set final flags.

    Returns a single Proposal with the final category, confidence, reason, flags.
    """
    if not proposals:
        return Proposal(
            category="needs_review",
            confidence=0.0,
            reason="No stage produced a proposal",
            stage="scoring",
        )

    # Sort by confidence descending; first one wins
    proposals.sort(key=lambda p: p.confidence, reverse=True)
    best = proposals[0]

    # ── Conflict detection ───────────────────────────────────────────────
    flags = list(best.flags)
    if len(proposals) >= 2:
        second = proposals[1]
        if (
            second.confidence > 0
            and second.category != best.category
            and second.confidence >= best.confidence * 0.7
        ):
            best.confidence = max(0, best.confidence - CONFLICT_PENALTY)
            flags.append("conflict")
            best.reason += f" [CONFLICT: {second.stage} suggested {second.category}]"

    # ── Outlier detection ────────────────────────────────────────────────
    if row.merchant_key and row.merchant_key in merchant_amounts:
        amounts = merchant_amounts[row.merchant_key]
        if len(amounts) >= 3:
            med = median(amounts)
            if med > 0 and abs(row.amount_cents) > med * OUTLIER_MULTIPLIER:
                best.confidence = max(0, best.confidence - OUTLIER_PENALTY)
                flags.append("amount_outlier")

    # ── Large purchase ───────────────────────────────────────────────────
    if abs(row.amount_cents) >= LARGE_PURCHASE_CENTS:
        flags.append("large_purchase")

    # ── Meals 50% deductible note ────────────────────────────────────────
    if best.category == "meals":
        flags.append("meals_50pct_deductible")

    best.flags = flags
    return best


def determine_status(confidence: float) -> str:
    """Map confidence to a TxnStatus string."""
    if confidence >= CONFIDENCE_AUTO:
        return "auto"
    elif confidence >= CONFIDENCE_SUGGESTED:
        return "suggested"
    else:
        return "needs_review"


def get_deductible_pct_for_category(category: str) -> int:
    """Look up the deductible percentage from category metadata."""
    return get_deductible_pct(category)
