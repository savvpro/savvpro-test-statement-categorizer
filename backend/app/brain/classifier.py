"""Categorization brain: deterministic rule-based transaction classifier.

Pipeline:
  1. normalize(description)
  2. User overrides -> confidence 1.0
  3. Structural rules: Transfer, Refund, Income
  4. Merchant rules from config/rules.yaml
  5. Ambiguity check -> Needs Review
"""

import os
import re
from dataclasses import dataclass

import yaml

from app.brain import constants
from app.brain.normalizer import normalize
from app.brain.overrides import OverrideStore


@dataclass
class ClassificationResult:
    category: str
    confidence: float
    reason: str
    needs_review: bool


def _load_rules() -> tuple[list[dict], list[str]]:
    base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    rules_path = os.path.join(base, "config", "rules.yaml")
    with open(rules_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("merchants", []), data.get("ambiguous_merchants", [])


_MERCHANTS, _AMBIGUOUS = _load_rules()


def _matches_merchant(normalized: str, merchant: dict) -> bool:
    name = merchant["name"].upper()
    if merchant.get("match_type") == "exact":
        return normalized == name
    return re.search(rf"(?<![A-Z0-9]){re.escape(name)}(?![A-Z0-9])", normalized) is not None




def classify(
    description: str, amount: float, overrides: OverrideStore
) -> ClassificationResult:
    """Classify a single transaction.

    Args:
        description: Raw transaction description from the statement.
        amount: Transaction amount (negative = spending, positive = money in).
        overrides: OverrideStore for user corrections.

    Returns:
        ClassificationResult with category, confidence, reason, needs_review.
    """
    raw_upper = (description or "").upper().strip()
    normalized = normalize(description)

    # --- Step 2: User overrides (before structural rules) ---
    if normalized:
        override_cat = overrides.get(normalized)
        if override_cat:
            return ClassificationResult(
                category=override_cat,
                confidence=constants.CONFIDENCE_OVERRIDE,
                reason="user correction",
                needs_review=False,
            )

    # --- Blank description ---
    if not normalized:
        return ClassificationResult(
            category="Needs Review",
            confidence=0.0,
            reason="blank description",
            needs_review=True,
        )

    # --- Step 3: Structural rules ---
    for kw in constants.TRANSFER_KEYWORDS:
        if kw in normalized:
            return ClassificationResult(
                category="Transfer",
                confidence=constants.CONFIDENCE_STRUCTURAL,
                reason=f"structural rule: {kw}",
                needs_review=False,
            )

    if amount > 0:
        refund_kw = next(
            (kw for kw in constants.REFUND_KEYWORDS if kw in normalized), None
        )
        merchant_name = _find_merchant_name(normalized)
        if refund_kw or merchant_name:
            reason = "refund"
            if merchant_name:
                reason += f" from {merchant_name}"
            return ClassificationResult(
                category="Refund",
                confidence=constants.CONFIDENCE_STRUCTURAL,
                reason=reason,
                needs_review=False,
            )

    if amount > 0:
        income_kw = next(
            (kw for kw in constants.INCOME_KEYWORDS if kw in normalized), None
        )
        if income_kw:
            return ClassificationResult(
                category="Income",
                confidence=constants.CONFIDENCE_STRUCTURAL,
                reason=f"structural rule: {income_kw}",
                needs_review=False,
            )

    # --- Step 4: Merchant rules ---
    matches = _find_merchant_matches(normalized)
    if matches:
        matches.sort(key=lambda m: m.get("confidence", 0), reverse=True)
        best = matches[0]
        second = matches[1] if len(matches) > 1 else None
        best_conf = best.get("confidence", 0)

        if second is not None:
            gap = round(best_conf - second.get("confidence", 0), 2)
            if gap < constants.CONFIDENCE_GAP_MAX:
                return ClassificationResult(
                    category="Needs Review",
                    confidence=best_conf,
                    reason=(
                        f"ambiguous: '{best['name']}' and '{second['name']}' "
                        f"too close (gap {gap:.2f})"
                    ),
                    needs_review=True,
                )

        if best_conf < constants.CONFIDENCE_MIN:
            return ClassificationResult(
                category="Needs Review",
                confidence=best_conf,
                reason=(
                    f"confidence {best_conf} below threshold "
                    f"{constants.CONFIDENCE_MIN}"
                ),
                needs_review=True,
            )

        return ClassificationResult(
            category=best["category"],
            confidence=best_conf,
            reason=f"merchant match: {best['name']}",
            needs_review=False,
        )

    # --- Step 5: Nothing matches -> Needs Review ---
    ambiguous_hit = next((a for a in _AMBIGUOUS if a in raw_upper), None)
    if ambiguous_hit:
        return ClassificationResult(
            category="Needs Review",
            confidence=0.0,
            reason=f"ambiguous merchant: {ambiguous_hit}",
            needs_review=True,
        )

    return ClassificationResult(
        category="Needs Review",
        confidence=0.0,
        reason="no matching category rule found",
        needs_review=True,
    )

def _find_merchant_matches(normalized: str) -> list[dict]:
    return [m for m in _MERCHANTS if _matches_merchant(normalized, m)]


def _find_merchant_name(normalized: str) -> str | None:
    for m in _MERCHANTS:
        if _matches_merchant(normalized, m):
            return m["name"]
    return None
