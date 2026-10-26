"""The brain engine – pure function, no DB, no I/O.

categorize(batch, ctx) -> list[Decision]
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from app.brain.kinds import detect_kind
from app.brain.normalize import normalize_merchant
from app.brain.scorer import score_candidates
from app.brain.taxonomy import TxKind


@dataclass
class RawTransaction:
    """Input to the brain – comes from the ingest layer."""
    id: str  # client-generated fingerprint or row index
    description_raw: str
    amount_cents: int  # negative = outflow, positive = inflow
    posted_date: date
    account_type: str = "checking"  # or "credit_card"


@dataclass
class Decision:
    """Output of the brain for one transaction."""
    id: str
    merchant: str
    kind: TxKind
    category_slug: str | None
    confidence: float
    status: str  # "auto" | "needs_review"
    reasons: list[str] = field(default_factory=list)
    review_reason: str | None = None
    linked_id: str | None = None  # refund → original, transfer pair


@dataclass
class BrainContext:
    """External context provided to the brain (not derived from the batch itself)."""
    user_rules: list[dict[str, Any]] = field(default_factory=list)
    prior_debits_by_merchant: dict[str, list[dict[str, Any]]] = field(default_factory=dict[str, Any])
    review_threshold: float = 0.75
    review_margin: float = 0.15
    equipment_demin_cents: int = 250_000
    account_type: str = "checking"


def categorize(batch: list[RawTransaction], ctx: BrainContext) -> list[Decision]:
    """Categorize a batch of raw transactions. Pure – no DB, no I/O."""
    # Build a local debit index for refund matching within the same batch
    batch_debit_index: dict[str, list[RawTransaction]] = {}
    for tx in batch:
        if tx.amount_cents < 0:
            merchant = normalize_merchant(tx.description_raw)
            batch_debit_index.setdefault(merchant, []).append(tx)

    decisions: list[Decision] = []

    for tx in batch:
        decision = _categorize_one(tx, ctx, batch_debit_index)
        decisions.append(decision)

    return decisions


def _categorize_one(
    tx: RawTransaction,
    ctx: BrainContext,
    batch_debit_index: dict[str, list[RawTransaction]],
) -> Decision:
    reasons: list[str] = []

    # 1. Normalize
    merchant = normalize_merchant(tx.description_raw)
    if merchant != tx.description_raw.upper().strip():
        reasons.append(f"Normalized '{tx.description_raw.strip()}' → '{merchant}'")

    # 2. Check if we have prior debits at this merchant (for refund detection)
    prior_debits = (
        ctx.prior_debits_by_merchant.get(merchant, [])
        + ([x for x in batch_debit_index.get(merchant, []) if x.id != tx.id])
    )
    has_prior_debits = len(prior_debits) > 0

    # 3. Detect kind
    kind = detect_kind(
        tx.description_raw,
        tx.amount_cents,
        account_type=ctx.account_type,
        prior_debits_at_merchant=has_prior_debits,
    )
    reasons.append(f"Kind detected: {kind}")

    # 4. Non-P&L kinds → auto-assign, high confidence, no scoring needed
    if kind in {
        TxKind.TRANSFER, TxKind.CC_PAYMENT, TxKind.OWNER_DRAW,
        TxKind.OWNER_CONTRIB, TxKind.TAX_PAYMENT, TxKind.LOAN_PAYMENT,
    }:
        nonpl_review: str | None = None
        if kind == TxKind.OWNER_DRAW:
            # Owner draws always need a quick look
            nonpl_review = "Owner draw / ATM withdrawal, verify business vs personal"
        return Decision(
            id=tx.id,
            merchant=merchant,
            kind=kind,
            category_slug="non_pl",
            confidence=0.95,
            status="needs_review" if kind == TxKind.OWNER_DRAW else "auto",
            reasons=reasons,
            review_reason=nonpl_review,
        )

    # 5. Unknown income (credit that didn't match income patterns)
    if kind == TxKind.UNKNOWN:
        reasons.append("Unknown inflow, could be income, gift, loan, or refund")
        return Decision(
            id=tx.id,
            merchant=merchant,
            kind=kind,
            category_slug=None,
            confidence=0.0,
            status="needs_review",
            reasons=reasons,
            review_reason="Unknown credit, please classify (income, refund, transfer, or personal)",
        )

    # 6. Score candidates
    candidates, mixed_use, always_review = score_candidates(
        merchant,
        kind,
        tx.amount_cents,
        user_rules=ctx.user_rules,
        account_type=ctx.account_type,
        equipment_demin_cents=ctx.equipment_demin_cents,
    )

    if not candidates:
        reasons.append("No category match found")
        return Decision(
            id=tx.id,
            merchant=merchant,
            kind=kind,
            category_slug=None,
            confidence=0.0,
            status="needs_review",
            reasons=reasons,
            review_reason=f"No matching category for '{merchant}'",
        )

    top_slug, top_conf, top_reasons = candidates[0]
    reasons.extend(top_reasons)

    # 7. Determine status
    status = "auto"
    review_reason: str | None = None

    needs_review_reasons: list[str] = []

    # User rule (conf 0.99) is an explicit override – bypasses margin and mixed-use checks
    user_rule_hit = top_conf >= 0.99

    if top_conf < ctx.review_threshold:
        needs_review_reasons.append(
            f"Confidence {top_conf:.2f} below threshold {ctx.review_threshold}"
        )

    if not user_rule_hit and len(candidates) >= 2:
        margin = top_conf - candidates[1][1]
        if margin < ctx.review_margin:
            needs_review_reasons.append(
                f"Top-2 margin {margin:.2f} below {ctx.review_margin} "
                f"(conflict: {top_slug} vs {candidates[1][0]})"
            )

    if mixed_use and not user_rule_hit:
        from app.brain.merchants import MERCHANT_DICT
        entry = MERCHANT_DICT.get(merchant)
        note = entry.note if entry else "mixed personal/business use"
        needs_review_reasons.append(f"Mixed-use merchant: {note}")

    if always_review:
        needs_review_reasons.append("Category flagged for review regardless of confidence")

    if kind == TxKind.REFUND and not has_prior_debits:
        needs_review_reasons.append("Refund without a matching prior purchase")

    if needs_review_reasons:
        status = "needs_review"
        review_reason = "; ".join(needs_review_reasons)
        reasons.append(f"Needs Review: {review_reason}")

    return Decision(
        id=tx.id,
        merchant=merchant,
        kind=kind,
        category_slug=top_slug,
        confidence=top_conf,
        status=status,
        reasons=reasons,
        review_reason=review_reason,
    )
