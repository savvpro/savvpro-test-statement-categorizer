import re
from typing import Optional, Tuple, Dict, Any, List
from difflib import SequenceMatcher

from ..models.schemas import (
    Transaction,
    TransactionType,
    CategoryName,
    TaxDeductibility
)
from .normalizer import MerchantNormalizer
from .rules import (
    CATEGORY_TAXONOMY,
    INTERNAL_TRANSFER_PATTERNS,
    INCOME_PATTERNS,
    REFUND_KEYWORDS
)
from .memory import user_rule_memory


class CategorizationBrain:
    """
    Deterministic rule & heuristic categorization engine.
    Does NOT use external LLMs. Decides categories through multi-stage:
    1. Normalization & user learned memory
    2. Internal transfers & owner draws detection
    3. Refund vs Income disambiguation (refunds are expense offsets, NOT income)
    4. Exact merchant database lookup
    5. Regex pattern & token scoring
    6. Fuzzy similarity matching
    7. Ambiguity detection & 'Needs Review' escalation
    """

    CONFIDENCE_THRESHOLD = 0.80  # Anything below this is flagged for user review

    @classmethod
    def categorize_transaction(
        cls,
        tx_id: str,
        date: str,
        raw_description: str,
        amount: float,
        tx_type: Optional[TransactionType] = None
    ) -> Transaction:
        """
        Takes raw transaction inputs, applies deterministic logic,
        and returns a fully categorized Transaction object with confidence score.
        """
        raw_desc = (raw_description or "").strip()
        clean_merchant, clean_key = MerchantNormalizer.clean(raw_desc)

        # Standardize transaction type if not provided
        # Convention: positive amount = expense/outflow (DEBIT), negative amount = inflow/refund/credit (CREDIT)
        if tx_type is None:
            if amount < 0:
                tx_type = TransactionType.CREDIT
            else:
                tx_type = TransactionType.DEBIT

        # Stage 1: Check Learned User Overrides (Highest Priority for personalization)
        user_override = user_rule_memory.lookup(clean_merchant) or user_rule_memory.lookup(clean_key)
        if user_override:
            category, tax_status, note = user_override
            return Transaction(
                id=tx_id,
                date=date,
                raw_description=raw_desc,
                clean_merchant=clean_merchant,
                amount=amount,
                transaction_type=tx_type,
                category=category,
                confidence=1.0,
                needs_review=False,
                review_reason=note,
                tax_status=tax_status,
                user_edited=True
            )

        # Stage 2: Detect Internal Transfers / Owner Draws / Credit Card Payments
        # These are NOT deductible expenses and NOT business income
        is_transfer, transfer_reason = cls._check_transfer(raw_desc, clean_key)
        if is_transfer:
            return Transaction(
                id=tx_id,
                date=date,
                raw_description=raw_desc,
                clean_merchant=clean_merchant,
                amount=amount,
                transaction_type=tx_type,
                category=CategoryName.INTERNAL_TRANSFER,
                confidence=1.0,
                needs_review=False,
                review_reason=transfer_reason,
                tax_status=TaxDeductibility.NON_DEDUCTIBLE,
                user_edited=False
            )

        # Stage 3: Detect Refunds vs Gross Income
        # A refund is a credit or negative expense that cancels out a previous purchase.
        # It is NOT taxable business income.
        is_refund, refund_reason = cls._check_refund(raw_desc, clean_key, amount, tx_type)
        if is_refund:
            return Transaction(
                id=tx_id,
                date=date,
                raw_description=raw_desc,
                clean_merchant=clean_merchant,
                amount=amount,
                transaction_type=TransactionType.CREDIT,
                category=CategoryName.REFUND_CREDIT,
                confidence=0.96,
                needs_review=False,
                review_reason=refund_reason,
                tax_status=TaxDeductibility.EXPENSE_OFFSET,
                user_edited=False
            )

        # Stage 4: Detect Business Income (Client payments, Stripe payouts, Wire in)
        is_income, income_reason = cls._check_income(raw_desc, clean_key, amount, tx_type)
        if is_income:
            return Transaction(
                id=tx_id,
                date=date,
                raw_description=raw_desc,
                clean_merchant=clean_merchant,
                amount=amount,
                transaction_type=TransactionType.CREDIT,
                category=CategoryName.GROSS_INCOME,
                confidence=0.98,
                needs_review=False,
                review_reason=income_reason,
                tax_status=TaxDeductibility.TAXABLE_INCOME,
                user_edited=False
            )

        # Stage 5: Exact Merchant Lookup
        exact_category, exact_tax, match_name = cls._check_exact_merchants(clean_key)
        if exact_category:
            return Transaction(
                id=tx_id,
                date=date,
                raw_description=raw_desc,
                clean_merchant=clean_merchant,
                amount=amount,
                transaction_type=tx_type,
                category=exact_category,
                confidence=0.99,
                needs_review=False,
                review_reason=f"Matched exact verified merchant: {match_name}",
                tax_status=exact_tax,
                user_edited=False
            )

        # Stage 6: Keyword & Pattern Scoring with Ambiguity Detection
        category_scores, weak_matches = cls._score_categories(raw_desc, clean_key)
        if category_scores:
            top_category, top_score = category_scores[0]

            # Ambiguity check: If 2nd category score is very close to top score
            if len(category_scores) > 1 and (top_score - category_scores[1][1]) < 0.15:
                runner_up = category_scores[1][0]
                return Transaction(
                    id=tx_id,
                    date=date,
                    raw_description=raw_desc,
                    clean_merchant=clean_merchant,
                    amount=amount,
                    transaction_type=tx_type,
                    category=CategoryName.NEEDS_REVIEW,
                    confidence=0.55,
                    needs_review=True,
                    review_reason=f"Ambiguous category match: could be '{top_category.value}' or '{runner_up.value}'. Please confirm.",
                    tax_status=TaxDeductibility.PENDING_REVIEW,
                    user_edited=False
                )

            if top_score >= cls.CONFIDENCE_THRESHOLD:
                tax_status = CATEGORY_TAXONOMY[top_category]["tax_status"]
                return Transaction(
                    id=tx_id,
                    date=date,
                    raw_description=raw_desc,
                    clean_merchant=clean_merchant,
                    amount=amount,
                    transaction_type=tx_type,
                    category=top_category,
                    confidence=round(top_score, 2),
                    needs_review=False,
                    review_reason=f"Identified via keyword/service patterns for {top_category.value}",
                    tax_status=tax_status,
                    user_edited=False
                )

        # If weak matches occurred (e.g. generic 'cafe' or 'diner')
        if weak_matches:
            weak_cat, weak_score = weak_matches[0]
            return Transaction(
                id=tx_id,
                date=date,
                raw_description=raw_desc,
                clean_merchant=clean_merchant,
                amount=amount,
                transaction_type=tx_type,
                category=CategoryName.NEEDS_REVIEW,
                confidence=round(weak_score, 2),
                needs_review=True,
                review_reason=f"Possible '{weak_cat.value}' but unrecognized venue '{clean_merchant}'. Please confirm.",
                tax_status=TaxDeductibility.PENDING_REVIEW,
                user_edited=False
            )

        # Stage 7: Fuzzy Similarity Matching against known merchants
        fuzzy_category, fuzzy_tax, fuzzy_score, fuzzy_name = cls._check_fuzzy_merchants(clean_key)
        if fuzzy_category and fuzzy_score >= 0.85:
            return Transaction(
                id=tx_id,
                date=date,
                raw_description=raw_desc,
                clean_merchant=clean_merchant,
                amount=amount,
                transaction_type=tx_type,
                category=fuzzy_category,
                confidence=round(fuzzy_score, 2),
                needs_review=False,
                review_reason=f"Fuzzy matched to merchant '{fuzzy_name}' ({int(fuzzy_score * 100)}% match)",
                tax_status=fuzzy_tax,
                user_edited=False
            )

        # Stage 8: Unknown Merchant -> Needs Review ("A wrong guess is worse than asking")
        return Transaction(
            id=tx_id,
            date=date,
            raw_description=raw_desc,
            clean_merchant=clean_merchant,
            amount=amount,
            transaction_type=tx_type,
            category=CategoryName.NEEDS_REVIEW,
            confidence=0.10,
            needs_review=True,
            review_reason=f"Unrecognized merchant '{clean_merchant}'. Please assign a tax category.",
            tax_status=TaxDeductibility.PENDING_REVIEW,
            user_edited=False
        )

    # ---------------- Helper Heuristics ----------------

    @staticmethod
    def _check_transfer(raw_text: str, clean_key: str) -> Tuple[bool, str]:
        text = raw_text.lower()
        for pattern in INTERNAL_TRANSFER_PATTERNS:
            if re.search(pattern, text) or re.search(pattern, clean_key):
                return True, "Internal transfer or credit card payoff. Excluded from tax expenses."
        return False, ""

    @staticmethod
    def _check_refund(raw_text: str, clean_key: str, amount: float, tx_type: TransactionType) -> Tuple[bool, str]:
        text = raw_text.lower()
        has_refund_kw = any(re.search(kw, text) for kw in REFUND_KEYWORDS)
        
        # If it explicitly says REFUND or RETURN
        if has_refund_kw:
            return True, "Merchant refund / return credit. Excluded from income; treated as expense reduction."

        # If negative amount or CREDIT on known merchant that is typically an expense
        if amount < 0 or tx_type == TransactionType.CREDIT:
            for cat, data in CATEGORY_TAXONOMY.items():
                for merchant in data["exact_merchants"]:
                    if merchant in clean_key or clean_key in merchant:
                        return True, f"Credit back from {clean_merchant_name(clean_key)}. Recorded as expense offset."

        return False, ""

    @staticmethod
    def _check_income(raw_text: str, clean_key: str, amount: float, tx_type: TransactionType) -> Tuple[bool, str]:
        text = raw_text.lower()
        for pattern in INCOME_PATTERNS:
            if re.search(pattern, text) or re.search(pattern, clean_key):
                return True, "Client invoice or service platform payout. Classified as Gross Income."

        # If it's a credit and labeled deposit
        if (amount < 0 or tx_type == TransactionType.CREDIT) and ("deposit" in text or "direct dep" in text):
            return True, "Direct deposit or account credit received. Classified as Gross Income."

        return False, ""

    @staticmethod
    def _check_exact_merchants(clean_key: str) -> Tuple[Optional[CategoryName], Optional[TaxDeductibility], str]:
        for category, config in CATEGORY_TAXONOMY.items():
            for merchant in config["exact_merchants"]:
                if clean_key == merchant or clean_key.startswith(merchant + " ") or f" {merchant} " in f" {clean_key} ":
                    return category, config["tax_status"], merchant.title()
        return None, None, ""

    @staticmethod
    def _score_categories(raw_text: str, clean_key: str) -> Tuple[List[Tuple[CategoryName, float]], List[Tuple[CategoryName, float]]]:
        combined_text = f"{raw_text} {clean_key}".lower()
        scores: Dict[CategoryName, float] = {}
        weak_scores: Dict[CategoryName, float] = {}

        for category, config in CATEGORY_TAXONOMY.items():
            cat_score = 0.0
            for kw_pattern in config.get("keywords", []):
                if re.search(kw_pattern, combined_text):
                    cat_score += 0.85

            for weak_pattern in config.get("weak_keywords", []):
                if re.search(weak_pattern, combined_text):
                    weak_scores[category] = 0.60

            if cat_score > 0:
                scores[category] = min(0.94, cat_score)

        sorted_scores = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        sorted_weak = sorted(weak_scores.items(), key=lambda item: item[1], reverse=True)
        return sorted_scores, sorted_weak

    @staticmethod
    def _check_fuzzy_merchants(clean_key: str) -> Tuple[Optional[CategoryName], Optional[TaxDeductibility], float, str]:
        best_match = None
        best_score = 0.0
        best_tax = None
        matched_name = ""

        for category, config in CATEGORY_TAXONOMY.items():
            for merchant in config["exact_merchants"]:
                similarity = SequenceMatcher(None, clean_key, merchant).ratio()
                if similarity > best_score:
                    best_score = similarity
                    best_match = category
                    best_tax = config["tax_status"]
                    matched_name = merchant.title()

        return best_match, best_tax, best_score, matched_name


def clean_merchant_name(name: str) -> str:
    return name.title() if name else "Merchant"
