"""Categorization engine service.

Applies deterministic rules, confidence scoring, direction checking,
and edge-case handling for refunds, reversals, transfers, and ambiguous merchants.
"""

from decimal import Decimal
import re
from typing import List, Optional

from app.rules.default_rules import DEFAULT_MERCHANT_RULES, MerchantRule
from app.schemas.category import DefaultCategory
from app.schemas.transaction import CategorizationResult, TransactionInput
from app.services.confidence import (
    DEFAULT_REVIEW_THRESHOLD,
    ConfidenceLevel,
    evaluate_confidence,
)
from app.services.transaction_normalizer import normalize_description

# Reversal indicators: must match entire words to avoid partial-word false positives
# like "REVOLUTION" or "RESERVE" or "UNIVERSAL".
REVERSAL_REGEX = re.compile(
    r"\b(REVERSAL|CHARGEBACK|REV\s*PYMT|TRANSACTION\s+REVERSED|CANCELLED\s+TRANSACTION|PAYMENT\s+REVERSAL)\b",
    re.IGNORECASE,
)

# Refund indicators: explicit money returned to account
REFUND_REGEX = re.compile(
    r"\b(REFUND|RETURN\s+REFUND|CREDIT\s+REFUND|REIMBURSEMENT|MERCHANT\s+REFUND)\b",
    re.IGNORECASE,
)

# Internal transfer indicators where destination account is clearly user-owned
INTERNAL_TRANSFER_CONFIRMED_REGEX = re.compile(
    r"\b(TRANSFER\s+(?:TO|FROM)\s+(?:SAVINGS|CHECKING|MONEY\s+MARKET|ACCT\s*\*\d+)|INTERNAL\s+(?:TRANSFER|XFER)|AUTOPAY\s+TO\s+SAVINGS)\b",
    re.IGNORECASE,
)

# Ambiguous transfer indicators where target account is unverified
TRANSFER_AMBIGUOUS_REGEX = re.compile(
    r"\b(TRANSFER|WIRE\s+TRANSFER|EXTERNAL\s+TRANSFER|ZELLE\s+TRANSFER|FUNDS\s+TRANSFER)\b",
    re.IGNORECASE,
)

# Merchants that sell across multiple categories without specific department
AMBIGUOUS_RETAILERS_REGEX = re.compile(
    r"\b(AMAZON(?:\.COM)?|WALMART|TARGET|COSTCO)\b",
    re.IGNORECASE,
)


class CategorizationEngine:
    """Deterministic, explainable transaction categorization engine."""

    def __init__(
        self,
        rules: Optional[List[MerchantRule]] = None,
        review_threshold: float = DEFAULT_REVIEW_THRESHOLD,
    ) -> None:
        """Initialize the engine with rules sorted by priority descending."""
        self.rules: List[MerchantRule] = sorted(
            rules or DEFAULT_MERCHANT_RULES,
            key=lambda r: r.priority,
            reverse=True,
        )
        self.review_threshold = review_threshold

    def categorize(self, transaction: TransactionInput) -> CategorizationResult:
        """Categorize a single transaction input deterministically.

        Order of evaluation:
        1. Check for zero amount (policy: manual verification required).
        2. Normalize description text.
        3. Check for empty or missing description (flag Needs Review).
        4. Detect explicit reversals and cancellations.
        5. Detect explicit refunds (positive direction required).
        6. Detect confirmed internal transfers vs ambiguous transfers.
        7. Evaluate high-priority rules (AWS / specialized merchants take precedence over generic retail).
        8. Detect ambiguous multi-category merchants.
        9. Evaluate remaining prioritized merchant rules with direction verification.
        10. Fallback to Unknown Merchant (Needs Review) with zero confidence.

        Args:
            transaction: Validated transaction input model.

        Returns:
            CategorizationResult with assigned category, score, explanation,
            review flag, and normalized description.
        """
        raw_description = transaction.original_description
        normalized = normalize_description(raw_description)
        amount = transaction.amount

        # 1. Zero-amount transaction policy
        if amount == Decimal("0"):
            score, review = evaluate_confidence(
                ConfidenceLevel.UNKNOWN, force_review=True, threshold=self.review_threshold
            )
            return CategorizationResult(
                category=DefaultCategory.NEEDS_REVIEW.value,
                confidence_score=score,
                explanation="Zero-amount transaction requires manual verification (possible card authorization hold or fee waiver).",
                review_required=review,
                normalized_description=normalized,
            )

        # 2. Empty description handling
        if not normalized:
            score, review = evaluate_confidence(
                ConfidenceLevel.UNKNOWN, force_review=True, threshold=self.review_threshold
            )
            return CategorizationResult(
                category=DefaultCategory.NEEDS_REVIEW.value,
                confidence_score=score,
                explanation="No transaction description provided.",
                review_required=review,
                normalized_description=normalized,
            )

        # 3. Explicit Reversals / Cancellations (priority over regular charges)
        if REVERSAL_REGEX.search(normalized):
            score, review = evaluate_confidence(
                ConfidenceLevel.HIGH_SPECIFIC, force_review=False, threshold=self.review_threshold
            )
            return CategorizationResult(
                category=DefaultCategory.REVERSAL.value,
                confidence_score=score,
                explanation="Explicit transaction reversal or cancellation indicator identified.",
                review_required=review,
                normalized_description=normalized,
            )

        # 4. Explicit Refunds
        if REFUND_REGEX.search(normalized):
            if amount > Decimal("0"):
                score, review = evaluate_confidence(
                    ConfidenceLevel.HIGH_SPECIFIC, force_review=False, threshold=self.review_threshold
                )
                return CategorizationResult(
                    category=DefaultCategory.REFUND.value,
                    confidence_score=score,
                    explanation="Explicit refund or credit return pattern matched with incoming funds.",
                    review_required=review,
                    normalized_description=normalized,
                )
            else:
                # Refund indicator on negative outflow is anomalous
                score, review = evaluate_confidence(
                    ConfidenceLevel.MODERATE, force_review=True, threshold=self.review_threshold
                )
                return CategorizationResult(
                    category=DefaultCategory.NEEDS_REVIEW.value,
                    confidence_score=score,
                    explanation="Refund keyword detected on an outgoing debit; manual review required to confirm.",
                    review_required=review,
                    normalized_description=normalized,
                )

        # 5. Internal Transfers (confirmed vs ambiguous)
        if INTERNAL_TRANSFER_CONFIRMED_REGEX.search(normalized):
            score, review = evaluate_confidence(
                0.90, force_review=False, threshold=self.review_threshold
            )
            return CategorizationResult(
                category=DefaultCategory.INTERNAL_TRANSFER.value,
                confidence_score=score,
                explanation="Internal transfer between user's own verified accounts identified.",
                review_required=review,
                normalized_description=normalized,
            )

        # High priority rules (priority >= 120, like AWS, DigitalOcean, Income)
        # must be evaluated before generic retailer checks so that "AMAZON WEB SERVICES"
        # resolves to Cloud Hosting rather than triggering the generic "AMAZON" ambiguity rule.
        for rule in self.rules:
            if rule.priority >= 120 and rule.matches(normalized):
                result = self._check_rule_match(rule, amount, normalized)
                if result is not None:
                    return result

        # 6. Ambiguous Retailers (e.g. Amazon retail, Walmart, Target)
        if AMBIGUOUS_RETAILERS_REGEX.search(normalized):
            score, review = evaluate_confidence(
                ConfidenceLevel.AMBIGUOUS, force_review=True, threshold=self.review_threshold
            )
            return CategorizationResult(
                category=DefaultCategory.NEEDS_REVIEW.value,
                confidence_score=score,
                explanation="Ambiguous merchant pattern matched: merchant sells items across multiple categories (e.g., Office Supplies, Hardware, or Personal Expense).",
                review_required=review,
                normalized_description=normalized,
            )

        # 7. Ambiguous transfers (target account not confirmed internal)
        if TRANSFER_AMBIGUOUS_REGEX.search(normalized):
            score, review = evaluate_confidence(
                0.60, force_review=True, threshold=self.review_threshold
            )
            return CategorizationResult(
                category=DefaultCategory.NEEDS_REVIEW.value,
                confidence_score=score,
                explanation="Transfer pattern identified but target account cannot be confirmed as internal.",
                review_required=review,
                normalized_description=normalized,
            )

        # 8. Remaining prioritized merchant rules
        for rule in self.rules:
            if rule.priority < 120 and rule.matches(normalized):
                result = self._check_rule_match(rule, amount, normalized)
                if result is not None:
                    return result

        # 9. Fallback: Unknown merchant
        score, review = evaluate_confidence(
            ConfidenceLevel.UNKNOWN, force_review=True, threshold=self.review_threshold
        )
        return CategorizationResult(
            category=DefaultCategory.NEEDS_REVIEW.value,
            confidence_score=score,
            explanation="No sufficiently reliable categorization rule matched this description.",
            review_required=review,
            normalized_description=normalized,
        )

    def _check_rule_match(
        self, rule: MerchantRule, amount: Decimal, normalized: str
    ) -> Optional[CategorizationResult]:
        """Verify amount direction and produce categorization result if valid."""
        # Direction checks
        if rule.expected_direction == "positive":
            if amount <= Decimal("0"):
                # Income rule matched, but amount is outgoing or zero -> skip rule
                return None
            score, review = evaluate_confidence(
                rule.confidence, force_review=False, threshold=self.review_threshold
            )
            return CategorizationResult(
                category=rule.category,
                confidence_score=score,
                explanation=rule.explanation,
                review_required=review,
                normalized_description=normalized,
            )

        if rule.expected_direction == "negative":
            if amount > Decimal("0"):
                # Expense merchant matched, but amount is incoming (without explicit refund keyword)
                score, review = evaluate_confidence(
                    0.50, force_review=True, threshold=self.review_threshold
                )
                return CategorizationResult(
                    category=DefaultCategory.NEEDS_REVIEW.value,
                    confidence_score=score,
                    explanation=f"Merchant pattern matched ({rule.id}) but positive amount received without explicit refund indicator.",
                    review_required=review,
                    normalized_description=normalized,
                )
            score, review = evaluate_confidence(
                rule.confidence, force_review=False, threshold=self.review_threshold
            )
            return CategorizationResult(
                category=rule.category,
                confidence_score=score,
                explanation=rule.explanation,
                review_required=review,
                normalized_description=normalized,
            )

        # Any direction
        score, review = evaluate_confidence(
            rule.confidence, force_review=False, threshold=self.review_threshold
        )
        return CategorizationResult(
            category=rule.category,
            confidence_score=score,
            explanation=rule.explanation,
            review_required=review,
            normalized_description=normalized,
        )
