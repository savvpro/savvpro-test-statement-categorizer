"""
The Brain: Core Decision Engine for Bank & Credit Card Statement Categorization.
100% deterministic & heuristic algorithmic classification. Zero external LLM calls.
"""

import re
import difflib
from typing import Dict, Any, Optional

from app.brain.taxonomy import Category, TAX_METADATA
from app.brain.normalizer import normalize_description, NormalizedDescription
from app.brain.rules import (
    HIGH_CONFIDENCE_RULES,
    AMBIGUOUS_RETAILERS,
    CANONICAL_MERCHANTS,
    MEAL_PATTERNS,
)

KNOWN_MEAL_CHAINS = {
    "STARBUCKS", "PEETS", "BLUE BOTTLE", "DUNKIN",
    "SWEETGREEN", "CHIPOTLE", "PANERA", "SHAKE SHACK",
    "DOORDASH", "UBER EATS", "GRUBHUB", "POSTMATES", "CAVIAR"
}


class CategorizationResult:
    def __init__(
        self,
        category: str,
        confidence: float,
        reason: str,
        cleaned_merchant: str,
        suggested_category: Optional[str] = None,
    ):
        self.category = category
        self.confidence = round(confidence, 2)
        self.reason = reason
        self.cleaned_merchant = cleaned_merchant
        self.suggested_category = suggested_category
        self.needs_review = (category == Category.NEEDS_REVIEW)

        # Pull tax metadata
        meta = TAX_METADATA.get(category, TAX_METADATA[Category.NEEDS_REVIEW])
        self.schedule_c_line = meta["schedule_c_line"]
        self.deductibility_pct = meta["deductibility_pct"]
        self.is_expense = meta["is_expense"]
        self.is_income = meta["is_income"]
        self.tax_note = meta["tax_note"]
        self.color = meta["color"]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "confidence": self.confidence,
            "needs_review": self.needs_review,
            "reason": self.reason,
            "cleaned_merchant": self.cleaned_merchant,
            "suggested_category": self.suggested_category,
            "schedule_c_line": self.schedule_c_line,
            "deductibility_pct": self.deductibility_pct,
            "is_expense": self.is_expense,
            "is_income": self.is_income,
            "tax_note": self.tax_note,
            "color": self.color,
        }


def _fuzzy_match(cleaned: str) -> Optional[tuple[str, str, float]]:
    """
    Compares cleaned tokens against known canonical merchants using SequenceMatcher.
    Returns (canonical_name, category, similarity_score) if a candidate has similarity >= 0.65.
    """
    words = cleaned.split()
    best_candidate = None
    best_score = 0.0
    best_cat = None

    for target_name, cat in CANONICAL_MERCHANTS.items():
        # Match against full cleaned string or individual tokens
        scores = [
            difflib.SequenceMatcher(None, target_name, cleaned).ratio(),
            difflib.SequenceMatcher(None, target_name, " ".join(words[:2])).ratio(),
        ]
        for w in words:
            scores.append(difflib.SequenceMatcher(None, target_name, w).ratio())

        max_s = max(scores)
        if max_s > best_score:
            best_score = max_s
            best_candidate = target_name
            best_cat = cat

    if best_candidate and best_score >= 0.65:
        return best_candidate, best_cat, best_score
    return None


def categorize_transaction(
    raw_description: str,
    amount: float,
    transaction_type: Optional[str] = None,
    user_rules: Optional[Dict[str, str]] = None,
) -> CategorizationResult:
    """
    Categorizes a single transaction through the 7-layer Brain.
    
    Parameters:
    - raw_description: Original transaction string from bank/card statement.
    - amount: Dollar amount (can be signed: negative for debit/expense, positive for deposit/credit).
    - transaction_type: Optional explicit 'DEBIT' or 'CREDIT'.
    - user_rules: Optional user-defined mapping (e.g. {'JOES CAFE': 'Business Meals & Dining'}).
    """
    norm: NormalizedDescription = normalize_description(raw_description)
    cleaned = norm.cleaned
    merchant = norm.clean_merchant

    # Layer 0: User Custom Rule Override (Highest priority, learning from session)
    if user_rules:
        for pattern, custom_cat in user_rules.items():
            if re.search(r"\b" + re.escape(pattern.strip().upper()) + r"\b", raw_description.upper()):
                return CategorizationResult(
                    category=custom_cat,
                    confidence=1.0,
                    reason=f"Applied user custom rule for '{pattern}'.",
                    cleaned_merchant=merchant,
                )

    # Layer 1: Direction & Flow Checks (Refunds, Transfers, Client Income)
    is_credit = False
    if transaction_type:
        is_credit = transaction_type.upper() in ["CREDIT", "CR", "DEPOSIT"]
    elif amount > 0:
        is_credit = True

    # 1A. Transfers & Credit Card Payments (Non-Expense)
    if norm.is_transfer_flag:
        return CategorizationResult(
            category=Category.TRANSFER_OWNER_DRAW,
            confidence=0.98,
            reason="Detected account transfer or credit card repayment. Excluded from tax deductions.",
            cleaned_merchant=merchant,
        )

    # 1B. Refunds & Reversals (Money back, NOT income!)
    if norm.is_refund_flag or (is_credit and any(w in raw_description.upper() for w in ["REFUND", "RETURN", "REVERSAL", "CREDIT VOUCHER"])):
        return CategorizationResult(
            category=Category.REFUND_REVERSAL,
            confidence=0.96,
            reason="Refund or return credit detected. Reduces business expenses rather than counting as gross taxable income.",
            cleaned_merchant=merchant,
        )

    # 1C. Gross Business Income (Client deposits, payouts)
    if norm.is_income_flag or (is_credit and any(w in raw_description.upper() for w in ["PAYOUT", "CLIENT", "INVOICE", "CONSULTING"])):
        return CategorizationResult(
            category=Category.GROSS_INCOME,
            confidence=0.96,
            reason="Client payment or revenue payout detected. Counted towards Gross Business Income.",
            cleaned_merchant=merchant,
        )

    # Layer 2: Ambiguous Retailers (Flag immediately to Needs Review!)
    for ambig_key, ambig_reason in AMBIGUOUS_RETAILERS.items():
        if re.search(r"\b" + re.escape(ambig_key) + r"\b", cleaned):
            # Check if it has specific AWS or digital cues
            if ambig_key in ["AMAZON", "AMZN MKTP"] and any(w in cleaned for w in ["AWS", "WEB SERVICES", "PRIME VIDEO", "CLOUD"]):
                # Let it fall through to AWS rule
                pass
            else:
                return CategorizationResult(
                    category=Category.NEEDS_REVIEW,
                    confidence=0.50,
                    reason=f"Ambiguous merchant ({ambig_key}): {ambig_reason}",
                    cleaned_merchant=merchant,
                    suggested_category=Category.OFFICE_SUPPLIES,
                )

    # Layer 3: High-Confidence Deterministic Regex Rules
    for regex_pat, cat, conf, match_reason in HIGH_CONFIDENCE_RULES:
        if re.search(regex_pat, cleaned) or re.search(regex_pat, raw_description.upper()):
            return CategorizationResult(
                category=cat,
                confidence=conf,
                reason=match_reason,
                cleaned_merchant=merchant,
            )

    # Layer 4: Meals & Dining Heuristic (IRS 50% Tax Rule)
    is_meal = False
    for meal_pat in MEAL_PATTERNS:
        if re.search(meal_pat, cleaned) or re.search(meal_pat, raw_description.upper()):
            is_meal = True
            break

    if is_meal:
        # Check if it's a known nationwide chain
        is_known_chain = any(chain in cleaned for chain in KNOWN_MEAL_CHAINS)
        if is_known_chain:
            return CategorizationResult(
                category=Category.BUSINESS_MEALS,
                confidence=0.88,
                reason="Recognized food/dining chain. Note: Subject to statutory 50% IRS business meal limit.",
                cleaned_merchant=merchant,
            )
        else:
            # Unknown local restaurant/cafe like "JOES CAFE 9921" -> Needs Review!
            return CategorizationResult(
                category=Category.NEEDS_REVIEW,
                confidence=0.60,
                reason=f"Local dining/cafe venue detected ('{merchant}'). Requires confirmation of business client purpose.",
                cleaned_merchant=merchant,
                suggested_category=Category.BUSINESS_MEALS,
            )

    # Layer 5: Fuzzy Matching against Canonical Merchant Names
    fuzzy = _fuzzy_match(cleaned)
    if fuzzy:
        cand_name, cand_cat, score = fuzzy
        if score >= 0.85:
            return CategorizationResult(
                category=cand_cat,
                confidence=round(0.78 + (score * 0.12), 2),
                reason=f"Fuzzy matched to canonical vendor '{cand_name}' with {int(score * 100)}% similarity.",
                cleaned_merchant=cand_name,
            )
        else:
            # Score between 0.65 and 0.84: Flag for review with suggestion
            return CategorizationResult(
                category=Category.NEEDS_REVIEW,
                confidence=round(score, 2),
                reason=f"Resembles '{cand_name}' ({int(score * 100)}% match), but requires human verification.",
                cleaned_merchant=merchant,
                suggested_category=cand_cat,
            )

    # Layer 6: Default Fallback - The Safety Shield
    return CategorizationResult(
        category=Category.NEEDS_REVIEW,
        confidence=0.20,
        reason="Unrecognized merchant description. A wrong guess is worse than asking.",
        cleaned_merchant=merchant,
        suggested_category=None,
    )
