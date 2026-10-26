import logging

from rapidfuzz import fuzz

from app.config import settings
from app.engine.edge_cases import (
    detect_duplicates,
    find_refund_matches,
    is_personal_business_ambiguous,
    is_refund_marker,
    is_transfer_marker,
)
from app.engine.normalizer import normalize_description
from app.engine.rules import (
    CANONICAL_MERCHANTS,
    EXACT_MERCHANTS,
    PATTERN_RULES,
)
from app.models.rule import CustomRule
from app.models.transaction import (
    CategorizedTransaction,
    RawTransaction,
    TransactionType,
)

logger = logging.getLogger(__name__)


class CategorizationBrain:
    """
    Deterministic Categorization Engine ("The Brain").
    Strictly zero AI / LLM calls. Fully transparent rule layers with calibrated confidence.
    """

    def __init__(self, custom_rules: list[CustomRule] | None = None):
        self.custom_rules = custom_rules or []
        self.confidence_threshold = settings.confidence_threshold
        self.fuzzy_threshold = settings.fuzzy_match_threshold

    def set_custom_rules(self, rules: list[CustomRule]) -> None:
        self.custom_rules = rules

    def categorize_batch(
        self, transactions: list[RawTransaction]
    ) -> list[CategorizedTransaction]:
        """Categorizes a batch of transactions from a statement."""
        if not transactions:
            return []

        # Step 1: Preprocess and normalize all descriptions
        normalized_descs = [
            normalize_description(tx.description) for tx in transactions
        ]

        # Step 2: Global batch edge-case analysis (duplicates and refund linking)
        duplicate_ids = detect_duplicates(transactions, normalized_descs)
        refund_links = find_refund_matches(transactions, normalized_descs)

        results: list[CategorizedTransaction] = []

        for tx, norm_desc in zip(transactions, normalized_descs, strict=False):
            is_dup = tx.id in duplicate_ids
            refund_parent = refund_links.get(tx.id)

            categorized = self._categorize_single(
                tx=tx,
                norm_desc=norm_desc,
                is_duplicate=is_dup,
                refund_parent_id=refund_parent,
            )
            results.append(categorized)

        return results

    def _categorize_single(
        self,
        tx: RawTransaction,
        norm_desc: str,
        is_duplicate: bool = False,
        refund_parent_id: str | None = None,
    ) -> CategorizedTransaction:
        category: str = "Needs Review"
        confidence: float = 0.0
        reason: str = ""
        is_transfer: bool = False
        is_refund: bool = False

        # ----------------------------------------------------
        # Layer 1: User-Defined Custom Rules (Highest Priority)
        # ----------------------------------------------------
        for rule in self.custom_rules:
            if not rule.is_active:
                continue
            rule_pat = rule.pattern.strip().upper()
            if rule_pat == norm_desc or rule_pat == tx.description.strip().upper():
                category = rule.category
                confidence = 1.0
                reason = f"User custom rule matched: '{rule.pattern}'"
                return CategorizedTransaction(
                    id=tx.id,
                    line_number=tx.line_number,
                    date=tx.date,
                    raw_description=tx.description,
                    normalized_description=norm_desc,
                    amount=tx.amount,
                    transaction_type=tx.transaction_type,
                    category=category,
                    confidence=confidence,
                    reason=reason,
                    needs_review=(category == "Needs Review"),
                    is_refund=is_refund,
                    refund_parent_id=refund_parent_id,
                    is_transfer=is_transfer,
                    is_duplicate=is_duplicate,
                    is_personal_ambiguous=False,
                    user_overridden=True,
                    currency=tx.currency,
                )

        # ----------------------------------------------------
        # Layer 2: Transfers & Card Payments (Non-spending)
        # ----------------------------------------------------
        if is_transfer_marker(norm_desc) or is_transfer_marker(tx.description):
            category = "Transfers & Card Payments"
            confidence = 0.98
            reason = "Internal transfer or credit card payment (non-spending / non-taxable)"
            return self._build_result(
                tx, norm_desc, category, confidence, reason,
                is_refund=False, refund_parent_id=None,
                is_transfer=True, is_duplicate=is_duplicate,
                is_personal_ambiguous=False, needs_review=False
            )

        # ----------------------------------------------------
        # Layer 3: Refunds and Reversals (Money back is NOT income)
        # ----------------------------------------------------
        if tx.transaction_type == TransactionType.CREDIT:
            if refund_parent_id is not None or is_refund_marker(norm_desc, tx.transaction_type):
                category = "Refunds & Reversals"
                confidence = 0.96
                link_msg = f" (linked to original charge #{refund_parent_id})" if refund_parent_id else ""
                reason = f"Merchant refund/reversal offset{link_msg} - not taxable revenue"
                return self._build_result(
                    tx, norm_desc, category, confidence, reason,
                    is_refund=True, refund_parent_id=refund_parent_id,
                    is_transfer=False, is_duplicate=is_duplicate,
                    is_personal_ambiguous=False, needs_review=False
                )

        # ----------------------------------------------------
        # Layer 4: Personal vs. Business Ambiguity Gate
        # ----------------------------------------------------
        if is_personal_business_ambiguous(norm_desc):
            category = "Needs Review"
            confidence = 0.50
            reason = "Personal vs Business Ambiguity: Mixed-use retailer. Verify business deductibility."
            return self._build_result(
                tx, norm_desc, category, confidence, reason,
                is_refund=False, refund_parent_id=None,
                is_transfer=False, is_duplicate=is_duplicate,
                is_personal_ambiguous=True, needs_review=True
            )

        # ----------------------------------------------------
        # Layer 5: Exact Merchant Dictionary Lookup
        # ----------------------------------------------------
        if norm_desc in EXACT_MERCHANTS:
            match_cat, match_conf = EXACT_MERCHANTS[norm_desc]
            category = match_cat
            confidence = match_conf
            reason = f"Exact merchant rule: '{norm_desc}'"
            return self._build_result(
                tx, norm_desc, category, confidence, reason,
                is_refund=False, refund_parent_id=None,
                is_transfer=False, is_duplicate=is_duplicate,
                is_personal_ambiguous=False, needs_review=False
            )

        # ----------------------------------------------------
        # Layer 6: Keyword & Regex Pattern Rules
        # ----------------------------------------------------
        for pattern, pat_cat, pat_conf, pat_reason in PATTERN_RULES:
            if pattern.search(norm_desc) or pattern.search(tx.description):
                if tx.transaction_type == TransactionType.CREDIT and pat_cat not in [
                    "Client Income & Revenue",
                    "Transfers & Card Payments",
                ]:
                    category = "Refunds & Reversals"
                    confidence = 0.90
                    reason = f"Credit from expense merchant ({pat_cat}) - tagged as refund/offset, not income"
                    is_refund = True
                else:
                    category = pat_cat
                    confidence = pat_conf
                    reason = pat_reason

                return self._build_result(
                    tx, norm_desc, category, confidence, reason,
                    is_refund=is_refund, refund_parent_id=refund_parent_id,
                    is_transfer=False, is_duplicate=is_duplicate,
                    is_personal_ambiguous=False, needs_review=(category == "Needs Review")
                )

        # ----------------------------------------------------
        # Layer 7: Fuzzy Matching (rapidfuzz WRatio / token_set_ratio)
        # ----------------------------------------------------
        best_canonical: str | None = None
        best_ratio: float = 0.0

        for canonical_name in CANONICAL_MERCHANTS:
            ratio = float(
                max(
                    fuzz.WRatio(norm_desc, canonical_name),
                    fuzz.token_set_ratio(norm_desc, canonical_name),
                )
            )
            if ratio > best_ratio:
                best_ratio = ratio
                best_canonical = canonical_name

        if best_ratio >= self.fuzzy_threshold and best_canonical:
            canon_cat = CANONICAL_MERCHANTS[best_canonical]
            scaled_conf = round(0.76 + (best_ratio - self.fuzzy_threshold) * 0.006, 2)
            category = canon_cat
            confidence = min(scaled_conf, 0.88)
            reason = f"Fuzzy match with '{best_canonical}' ({best_ratio:.0f}% similarity)"
            return self._build_result(
                tx, norm_desc, category, confidence, reason,
                is_refund=False, refund_parent_id=None,
                is_transfer=False, is_duplicate=is_duplicate,
                is_personal_ambiguous=False, needs_review=False
            )

        # ----------------------------------------------------
        # Layer 8: Default Fallback / Needs Review Gating
        # ----------------------------------------------------
        category = "Needs Review"
        confidence = 0.30
        if tx.transaction_type == TransactionType.CREDIT:
            reason = "Unidentified incoming deposit. Verify if client revenue, rebate, or personal transfer."
        else:
            reason = "Unknown merchant. Confidence below threshold. Requires manual tax classification."

        return self._build_result(
            tx, norm_desc, category, confidence, reason,
            is_refund=False, refund_parent_id=None,
            is_transfer=False, is_duplicate=is_duplicate,
            is_personal_ambiguous=False, needs_review=True
        )

    def _build_result(
        self,
        tx: RawTransaction,
        norm_desc: str,
        category: str,
        confidence: float,
        reason: str,
        is_refund: bool,
        refund_parent_id: str | None,
        is_transfer: bool,
        is_duplicate: bool,
        is_personal_ambiguous: bool,
        needs_review: bool,
    ) -> CategorizedTransaction:
        if is_duplicate:
            reason = f"[Duplicate Flag] {reason}"

        is_needs_review = needs_review or (category == "Needs Review") or (confidence < self.confidence_threshold)

        return CategorizedTransaction(
            id=tx.id,
            line_number=tx.line_number,
            date=tx.date,
            raw_description=tx.description,
            normalized_description=norm_desc,
            amount=tx.amount,
            transaction_type=tx.transaction_type,
            category=category,
            confidence=confidence,
            reason=reason,
            needs_review=is_needs_review,
            is_refund=is_refund,
            refund_parent_id=refund_parent_id,
            is_transfer=is_transfer,
            is_duplicate=is_duplicate,
            is_personal_ambiguous=is_personal_ambiguous,
            user_overridden=False,
            currency=tx.currency,
        )
