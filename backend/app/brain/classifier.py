"""
Deterministic classification brain engine for bank transactions.
Applies 3-tier rules without LLM calls.
"""

import re
from typing import Optional, Tuple
from app.models.transaction import (
    TransactionRaw,
    TransactionCategorized,
    TransactionDirection,
    ReviewStatus,
)
from app.brain.categories import get_category_info, TAX_CATEGORIES
from app.brain.sanitizer import sanitize_merchant
from app.brain.direction import analyze_direction_and_type
from app.brain.rules import (
    HIGH_CONFIDENCE_VENDORS,
    MIXED_USE_VENDORS,
    MEAL_PATTERNS,
    AUTO_VERIFIED_MEAL_CHAINS,
)

AUTO_VERIFY_THRESHOLD = 0.85


class StatementBrain:
    """Core deterministic brain engine for classifying freelance tech transactions."""

    def __init__(self, auto_verify_threshold: float = AUTO_VERIFY_THRESHOLD):
        self.auto_verify_threshold = auto_verify_threshold

    def categorize_transaction(
        self,
        raw: TransactionRaw,
        is_credit_statement: bool = False,
    ) -> TransactionCategorized:
        """
        Categorize a single raw transaction into a verified or reviewable tax entry.
        """
        # Step 1: Sanitize merchant description
        clean_merchant = sanitize_merchant(raw.raw_description)

        # Step 2: Analyze cash flow direction and normalized amount
        direction, norm_amount, dir_reason = analyze_direction_and_type(
            raw.raw_description,
            clean_merchant,
            raw.amount,
            is_credit_statement=is_credit_statement,
        )

        category: str
        confidence: float
        status: ReviewStatus
        needs_review: bool
        review_reason: Optional[str] = None
        decision_rule: Optional[str] = None

        # Step 3: Handle Transfers (Internal transfers, credit card payoffs)
        if direction == TransactionDirection.TRANSFER:
            category = "Transfers & Non-Taxable"
            confidence = 0.98
            status = ReviewStatus.AUTO_VERIFIED
            needs_review = False
            decision_rule = f"Non-taxable transfer/payment: {dir_reason}"

        # Step 4: Handle Inflows (Business income vs unverified deposits)
        elif direction == TransactionDirection.INFLOW:
            if "Business revenue" in dir_reason:
                category = "Gross Business Income"
                confidence = 0.98
                status = ReviewStatus.AUTO_VERIFIED
                needs_review = False
                decision_rule = f"Verified revenue source: {dir_reason}"
            else:
                category = "Gross Business Income"
                confidence = 0.70
                status = ReviewStatus.NEEDS_REVIEW
                needs_review = True
                review_reason = (
                    "Unclassified deposit to business account. "
                    "Confirm if this is taxable client revenue or personal capital contribution."
                )
                decision_rule = "Deposit inflow without explicit revenue identifier"

        # Step 5: Handle Refunds / Expense Credits
        elif direction == TransactionDirection.REFUND:
            category = "Refund / Expense Reduction"
            confidence = 0.95
            status = ReviewStatus.AUTO_VERIFIED
            needs_review = False
            decision_rule = f"Vendor refund or credit: {dir_reason}"

        # Step 6: Handle Outflows (Expenses) through 3-tier rules
        else:
            cat, conf, st, nr, r_reason, rule = self._classify_outflow(
                clean_merchant, raw.raw_description
            )
            category = cat
            confidence = conf
            status = st
            needs_review = nr
            review_reason = r_reason
            decision_rule = rule

        # Step 7: Lookup tax metadata and calculate deductible amount
        cat_info = get_category_info(category)
        schedule_c_line = cat_info["schedule_c_line"]
        tax_deductible = cat_info["tax_deductible"]
        deductible_percentage = cat_info["deductible_percentage"]

        # Deductible amount calculation
        if tax_deductible and not needs_review:
            deductible_amount = round(norm_amount * deductible_percentage, 2)
        else:
            deductible_amount = 0.0

        return TransactionCategorized(
            id=raw.id,
            date=raw.date,
            raw_description=raw.raw_description,
            clean_merchant=clean_merchant,
            amount=norm_amount,
            direction=direction,
            category=category,
            schedule_c_line=schedule_c_line,
            tax_deductible=tax_deductible,
            deductible_percentage=deductible_percentage,
            deductible_amount=deductible_amount,
            confidence=confidence,
            status=status,
            needs_review=needs_review,
            review_reason=review_reason,
            decision_rule=decision_rule,
            notes=None,
        )

    def _classify_outflow(
        self,
        clean_merchant: str,
        raw_description: str,
    ) -> Tuple[str, float, ReviewStatus, bool, Optional[str], Optional[str]]:
        """
        Classify expense outflows using 3 tiers of deterministic rules.
        """
        merchant_upper = clean_merchant.upper()
        raw_upper = raw_description.upper()

        # --- Tier 1: High Confidence Vendors ---
        # Sort vendors by length descending to match specific vendors before general ones
        sorted_vendors = sorted(
            HIGH_CONFIDENCE_VENDORS.keys(), key=lambda v: len(v), reverse=True
        )

        for vendor_key in sorted_vendors:
            # Word-boundary or exact token containment match
            pattern = rf"\b{re.escape(vendor_key)}\b"
            if re.search(pattern, merchant_upper) or re.search(pattern, raw_upper):
                vendor_data = HIGH_CONFIDENCE_VENDORS[vendor_key]
                return (
                    vendor_data["category"],
                    vendor_data["confidence"],
                    ReviewStatus.AUTO_VERIFIED,
                    False,
                    None,
                    vendor_data["rule"],
                )

        # --- Tier 2: Mixed-Use Vendors ---
        for mixed_key, mixed_data in MIXED_USE_VENDORS.items():
            pattern = rf"\b{re.escape(mixed_key)}\b"
            if re.search(pattern, merchant_upper) or re.search(pattern, raw_upper):
                return (
                    mixed_data["suggested_category"],
                    mixed_data["confidence"],
                    ReviewStatus.NEEDS_REVIEW,
                    True,
                    mixed_data["reason"],
                    f"Tier 2 Mixed-Use Vendor: {mixed_key}",
                )

        # --- Tier 3: Meal Keywords ---
        combined_text = f"{merchant_upper} {raw_upper}"
        for pattern in MEAL_PATTERNS:
            if re.search(pattern, combined_text):
                # Check if it's a known nationwide chain
                is_chain = any(
                    re.search(rf"\b{re.escape(chain)}\b", combined_text)
                    for chain in AUTO_VERIFIED_MEAL_CHAINS
                )
                if is_chain:
                    return (
                        "Meals & Client Entertainment",
                        0.88,
                        ReviewStatus.AUTO_VERIFIED,
                        False,
                        None,
                        "Established dining chain meeting auto-approval threshold (50% IRS deductible)",
                    )
                else:
                    return (
                        "Meals & Client Entertainment",
                        0.72,
                        ReviewStatus.NEEDS_REVIEW,
                        True,
                        "Local dining expense. IRS requires documenting business purpose and client attendees for 50% deduction.",
                        f"Dining keyword detected: {pattern}",
                    )

        # --- Tier 4: Fallback / Unrecognized ---
        return (
            "Needs Review",
            0.25,
            ReviewStatus.NEEDS_REVIEW,
            True,
            "Unrecognized merchant description. Please assign an IRS Schedule C category.",
            "Default fallback: No match in deterministic rules engine",
        )
