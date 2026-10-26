"""
Categorization engine.

Applies rules from rules.py in priority order with direction awareness,
regex word boundaries, unmatched refund safety, P2P disambiguation,
and normalized duplicate detection.
"""

import re
from decimal import Decimal
from backend.models import (
    RawTransaction, CategorizedTransaction,
    TransactionType, BusinessCategory,
    ReviewStatus, Confidence,
)
from backend.rules import RULES, FALLBACK_RULE


# Sort rules by priority once at import time
_SORTED_RULES = sorted(RULES, key=lambda r: r["priority"])

# Pre-compile rule regex patterns for performance and correctness
_COMPILED_RULES = []
for rule in _SORTED_RULES:
    compiled_patterns = [re.compile(p, re.IGNORECASE) for p in rule["patterns"]]
    _COMPILED_RULES.append({**rule, "_compiled": compiled_patterns})


def _normalize_description(desc: str) -> str:
    """Normalize description for duplicate detection and consistent matching."""
    cleaned = re.sub(r"[^\w\s]", " ", desc.lower())
    return " ".join(cleaned.split())


def _match_rule(description: str, amount: Decimal) -> dict | None:
    """
    Find the first matching rule, taking amount direction into account.
    """
    for rule in _COMPILED_RULES:
        expected_sign = rule.get("expected_sign", "any")

        # Direction check
        if expected_sign == "positive" and amount <= 0:
            continue
        if expected_sign == "negative" and amount >= 0:
            continue

        for pattern in rule["_compiled"]:
            if pattern.search(description):
                return rule

    return None


def _refine_refund_category(description: str) -> BusinessCategory:
    """
    Try to figure out which expense category a refund relates to.
    E.g. 'REFUND - ADOBE CREATIVE CLOUD' → Software.
    Uses regex word boundaries for precise matching.
    """
    expense_rules = [r for r in _COMPILED_RULES if r["priority"] >= 60]
    for rule in expense_rules:
        for pattern in rule["_compiled"]:
            if pattern.search(description):
                return rule["business_category"]

    return BusinessCategory.UNKNOWN


def _find_matching_prior_expense(
    tx_idx: int,
    description: str,
    amount: Decimal,
    all_raw: list[RawTransaction],
) -> int | None:
    """
    Try to link a refund (positive amount) to an original expense (negative amount).
    Returns 1-based transaction ID of original purchase if found, or None.
    """
    target_amount = -abs(amount)
    desc_norm = _normalize_description(description)

    # Search in preceding transactions
    for prev_idx in range(tx_idx - 1, -1, -1):
        prev = all_raw[prev_idx]
        if prev.amount == target_amount:
            prev_desc_norm = _normalize_description(prev.description)
            # Check for token overlap (e.g. 'adobe' in both)
            tokens_current = set(desc_norm.split())
            tokens_prev = set(prev_desc_norm.split())
            common_tokens = tokens_current.intersection(tokens_prev) - {"refund", "reversal", "credit"}
            if common_tokens:
                return prev_idx + 1

    return None


def _check_ambiguous_p2p(description: str, amount: Decimal) -> bool:
    """Check if description has ambiguous P2P transfer words like generic Venmo/Zelle."""
    desc_lower = description.lower()
    p2p_keywords = ["venmo", "zelle", "cashapp", "cash app"]
    return any(k in desc_lower for k in p2p_keywords)


def _determine_fallback(description: str, amount: Decimal) -> dict:
    """
    Assign fallback type/category for transactions that don't match any rule.
    Does NOT blindly classify by sign.
    """
    # Check if it was an ambiguous P2P payment
    if _check_ambiguous_p2p(description, amount):
        return {
            "transaction_type": TransactionType.UNKNOWN,
            "business_category": BusinessCategory.UNKNOWN,
            "review_status": ReviewStatus.NEEDS_REVIEW,
            "confidence": Confidence.LOW,
            "explanation": (
                f"'{description}' is a peer-to-peer payment (Venmo/Zelle). "
                f"Cannot automatically determine if it is a contractor expense or personal draw."
            ),
            "rule_id": "R002-AMBIGUOUS",
        }

    # Check if description mentions refund with negative amount (outflow)
    if any(k in description.lower() for k in ["refund", "reversal"]) and amount < 0:
        return {
            "transaction_type": TransactionType.UNKNOWN,
            "business_category": BusinessCategory.UNKNOWN,
            "review_status": ReviewStatus.NEEDS_REVIEW,
            "confidence": Confidence.LOW,
            "explanation": (
                f"'{description}' mentions refund but has a negative amount ({amount}). "
                f"May represent a refund paid out to a customer; routed to Needs Review."
            ),
            "rule_id": "R010-NEGATIVE",
        }

    # Check for income keywords with negative amounts
    if any(k in description.lower() for k in ["invoice", "client", "payment received"]) and amount < 0:
        return {
            "transaction_type": TransactionType.UNKNOWN,
            "business_category": BusinessCategory.UNKNOWN,
            "review_status": ReviewStatus.NEEDS_REVIEW,
            "confidence": Confidence.LOW,
            "explanation": (
                f"'{description}' contains invoice/client terms but has a negative amount ({amount}). "
                f"Could be a vendor bill or reversal; routed to Needs Review."
            ),
            "rule_id": "R030-CONTRADICTION",
        }

    return {
        "transaction_type": TransactionType.UNKNOWN,
        "business_category": BusinessCategory.UNKNOWN,
        "review_status": ReviewStatus.NEEDS_REVIEW,
        "confidence": Confidence.LOW,
        "explanation": (
            f"No rule matched '{description}'. "
            f"Marked for manual review — could be income, expense, or other."
        ),
        "rule_id": FALLBACK_RULE["id"],
    }


def categorize_transactions(
    raw_transactions: list[RawTransaction],
) -> tuple[list[CategorizedTransaction], list[str]]:
    """
    Categorize raw transactions in priority order.

    Returns:
        (categorized_transactions, warnings)
    """
    categorized: list[CategorizedTransaction] = []
    warnings: list[str] = []

    # Duplicate detection: group by (date, normalized description, amount)
    seen: dict[tuple, list[int]] = {}
    for idx, tx in enumerate(raw_transactions):
        key = (tx.date, _normalize_description(tx.description), tx.amount)
        seen.setdefault(key, []).append(idx)

    # Identify duplicate groups
    duplicate_groups: dict[int, int] = {}
    group_counter = 0
    for key, indices in seen.items():
        if len(indices) > 1:
            group_counter += 1
            for idx in indices:
                duplicate_groups[idx] = group_counter

    for idx, tx in enumerate(raw_transactions):
        rule = _match_rule(tx.description, tx.amount)
        linked_tx_id = None

        if rule is not None:
            tx_type = rule["transaction_type"]
            biz_cat = rule["business_category"]
            confidence = rule["confidence"]
            rule_id = rule["id"]
            explanation = rule["explanation_template"].format(description=tx.description)

            # Special refund handling & validation
            if tx_type == TransactionType.REFUND:
                # If amount is negative, a "refund" is an outflow (e.g. paying back a customer)
                if tx.amount <= 0:
                    tx_type = TransactionType.UNKNOWN
                    biz_cat = BusinessCategory.UNKNOWN
                    review_status = ReviewStatus.NEEDS_REVIEW
                    confidence = Confidence.LOW
                    explanation = (
                        f"'{tx.description}' mentions refund but has a negative amount ({tx.amount}). "
                        f"This may represent a customer refund payout. Routed to Needs Review."
                    )
                else:
                    # Refine category for positive refund
                    biz_cat = _refine_refund_category(tx.description)
                    linked_tx_id = _find_matching_prior_expense(
                        idx, tx.description, tx.amount, raw_transactions
                    )

                    if linked_tx_id is not None:
                        explanation += f" Linked to prior original purchase #{linked_tx_id}."

                    # Unmatched refund safety check
                    if biz_cat == BusinessCategory.UNKNOWN:
                        review_status = ReviewStatus.NEEDS_REVIEW
                        confidence = Confidence.LOW
                        explanation = (
                            f"Unmatched refund in '{tx.description}'. Unable to safely link to "
                            f"a specific expense category. Kept in Needs Review and excluded from "
                            f"expense deductions until confirmed."
                        )
                    else:
                        review_status = ReviewStatus.AUTO_CATEGORIZED
            else:
                review_status = (
                    ReviewStatus.AUTO_CATEGORIZED
                    if confidence in (Confidence.HIGH, Confidence.MEDIUM)
                    else ReviewStatus.NEEDS_REVIEW
                )

        else:
            fallback = _determine_fallback(tx.description, tx.amount)
            tx_type = fallback["transaction_type"]
            biz_cat = fallback["business_category"]
            explanation = fallback["explanation"]
            confidence = fallback["confidence"]
            rule_id = fallback["rule_id"]
            review_status = fallback["review_status"]

        is_dup = idx in duplicate_groups
        dup_group = duplicate_groups.get(idx)

        if is_dup:
            explanation += f" ⚠️ Possible duplicate detected (Group {dup_group})."
            if review_status == ReviewStatus.AUTO_CATEGORIZED:
                review_status = ReviewStatus.NEEDS_REVIEW
            warnings.append(
                f"Possible duplicate: '{tx.description}' on {tx.date} "
                f"for {tx.amount} (group {dup_group})."
            )

        categorized.append(
            CategorizedTransaction(
                id=idx + 1,
                date=tx.date,
                description=tx.description,
                amount=tx.amount,
                transaction_type=tx_type,
                business_category=biz_cat,
                review_status=review_status,
                confidence=confidence,
                explanation=explanation,
                rule_id=rule_id,
                is_possible_duplicate=is_dup,
                duplicate_group_id=dup_group,
                linked_transaction_id=linked_tx_id,
            )
        )

    return categorized, warnings
