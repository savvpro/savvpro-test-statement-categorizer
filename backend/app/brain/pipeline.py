"""
Brain pipeline – orchestrates all stages in order.

Pure Python.  Input: list of NormalizedRow + list of user rules.
Output: list of BrainResult with category, confidence, status, reason, flags.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field

from app.brain.dictionary import check_dictionary
from app.brain.keywords import check_keywords
from app.brain.normalize import NormalizedRow
from app.brain.pipeline_types import Proposal
from app.brain.refunds import check_refund
from app.brain.scoring import (
    apply_scoring,
    determine_status,
    get_deductible_pct_for_category,
)
from app.brain.transfers import check_exclusions, detect_transfer_pairs
from app.config import CONFIDENCE_USER_RULE, TRANSFER_PAIR_DAYS


@dataclass
class UserRuleSpec:
    """Lightweight representation of a user rule (no ORM dependency)."""
    id: int
    match_type: str       # exact | contains | regex
    pattern: str
    category: str
    min_cents: int | None = None
    max_cents: int | None = None


@dataclass
class BrainResult:
    """Final output for one row."""
    row_index: int
    category: str
    confidence: float
    status: str             # auto | suggested | needs_review
    reason: str
    rule_id: int | None = None
    flags: list[str] = field(default_factory=list)
    linked_row_index: int | None = None
    deductible_pct: int = 100


def run_pipeline(
    rows: list[NormalizedRow],
    user_rules: list[UserRuleSpec] | None = None,
) -> list[BrainResult]:
    """
    Run the full brain pipeline on a list of normalized rows.

    Stages (in order):
      1. Hard exclusions (transfers, CC payments, owner draws)
      2. User rules
      3. Merchant dictionary (exact + fuzzy)
      4. Keyword patterns
      5. Refund / sign / context logic (for credits)
      6. Scoring (conflict, outlier, large purchase adjustments)
    """
    user_rules = user_rules or []
    results: list[BrainResult] = []

    # Pre-compute merchant amount distributions for outlier detection
    merchant_amounts: dict[str, list[int]] = defaultdict(list)
    for r in rows:
        if r.merchant_key:
            merchant_amounts[r.merchant_key].append(abs(r.amount_cents))

    # Detect transfer pairs across all rows
    transfer_pairs = detect_transfer_pairs(rows, max_days=TRANSFER_PAIR_DAYS)
    paired_indices: set[int] = set()
    for d_idx, c_idx in transfer_pairs:
        paired_indices.add(d_idx)
        paired_indices.add(c_idx)

    # Index rows by row_index for refund lookback
    proposals_by_idx: dict[int, Proposal] = {}

    for row in rows:
        proposals: list[Proposal] = []

        # ── Stage 1: Hard exclusions ─────────────────────────────────────
        if row.row_index in paired_indices:
            proposals.append(Proposal(
                category="transfer",
                confidence=0.97,
                reason="Transfer pair detected (matching debit/credit within 3 days)",
                stage="exclusions",
                flags=["transfer_pair"],
            ))
        else:
            exc = check_exclusions(row)
            if exc:
                proposals.append(exc)

        # If a high-confidence exclusion was found, skip further stages
        if proposals and proposals[0].confidence >= 0.90:
            best = proposals[0]
            proposals_by_idx[row.row_index] = best
            results.append(BrainResult(
                row_index=row.row_index,
                category=best.category,
                confidence=best.confidence,
                status="auto",
                reason=best.reason,
                flags=best.flags,
                deductible_pct=0,
            ))
            continue

        # ── Stage 2: User rules ──────────────────────────────────────────
        user_match = _check_user_rules(row, user_rules)
        if user_match:
            proposals.append(user_match[0])
            rule_id = user_match[1]
        else:
            rule_id = None

        # ── Stage 3: Merchant dictionary ─────────────────────────────────
        dict_proposal = check_dictionary(row)
        if dict_proposal:
            proposals.append(dict_proposal)

        # ── Stage 4: Keyword patterns ────────────────────────────────────
        kw_proposal = check_keywords(row)
        if kw_proposal:
            proposals.append(kw_proposal)

        # ── Stage 5: Refund / sign / context ─────────────────────────────
        if row.amount_cents > 0:
            refund_proposal = check_refund(row, rows, proposals_by_idx)
            if refund_proposal:
                proposals.append(refund_proposal)

        # ── Stage 6: Scoring ─────────────────────────────────────────────
        best = apply_scoring(row, proposals, dict(merchant_amounts))
        status = determine_status(best.confidence)
        deductible_pct = get_deductible_pct_for_category(best.category)

        proposals_by_idx[row.row_index] = best

        results.append(BrainResult(
            row_index=row.row_index,
            category=best.category,
            confidence=round(best.confidence, 2),
            status=status,
            reason=best.reason,
            rule_id=rule_id,
            flags=best.flags,
            linked_row_index=best.linked_row_index,
            deductible_pct=deductible_pct,
        ))

    return results


def _check_user_rules(
    row: NormalizedRow,
    rules: list[UserRuleSpec],
) -> tuple[Proposal, int] | None:
    """Check user rules and return (proposal, rule_id) if matched."""
    for rule in rules:
        matched = False

        if rule.match_type == "exact":
            matched = row.merchant_key == rule.pattern.upper()
        elif rule.match_type == "contains":
            matched = rule.pattern.upper() in row.merchant_key
        elif rule.match_type == "regex":
            try:
                matched = bool(re.search(rule.pattern, row.merchant_key, re.I))
            except re.error:
                continue

        if matched:
            # Amount range check
            if rule.min_cents is not None and abs(row.amount_cents) < rule.min_cents:
                continue
            if rule.max_cents is not None and abs(row.amount_cents) > rule.max_cents:
                continue

            return (
                Proposal(
                    category=rule.category,
                    confidence=CONFIDENCE_USER_RULE,
                    reason=f"User rule #{rule.id}: {rule.match_type} match on '{rule.pattern}' → {rule.category}",
                    stage="user_rules",
                ),
                rule.id,
            )

    return None
