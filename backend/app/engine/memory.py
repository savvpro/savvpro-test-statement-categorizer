from typing import Dict, Optional, Tuple
from ..models.schemas import CategoryName, TaxDeductibility


class UserRuleMemory:
    """
    In-memory rule store that remembers user overrides.
    When a user corrects a 'Needs Review' row or re-assigns a category,
    the brain learns the merchant association for subsequent classifications.
    """

    def __init__(self):
        # Maps normalized merchant string -> (CategoryName, TaxDeductibility, note)
        self._learned_overrides: Dict[str, Tuple[CategoryName, TaxDeductibility, str]] = {}

    def add_override(self, clean_merchant: str, category: CategoryName, tax_status: Optional[TaxDeductibility] = None):
        key = clean_merchant.strip().lower()
        if not tax_status:
            if category == CategoryName.MEALS_ENTERTAINMENT:
                tax_status = TaxDeductibility.PARTIALLY_DEDUCTIBLE
            elif category == CategoryName.GROSS_INCOME:
                tax_status = TaxDeductibility.TAXABLE_INCOME
            elif category == CategoryName.INTERNAL_TRANSFER:
                tax_status = TaxDeductibility.NON_DEDUCTIBLE
            elif category == CategoryName.REFUND_CREDIT:
                tax_status = TaxDeductibility.EXPENSE_OFFSET
            elif category == CategoryName.NEEDS_REVIEW:
                tax_status = TaxDeductibility.PENDING_REVIEW
            else:
                tax_status = TaxDeductibility.FULLY_DEDUCTIBLE

        self._learned_overrides[key] = (
            category,
            tax_status,
            f"Learned from user override: assigned to {category.value}"
        )

    def lookup(self, clean_merchant: str) -> Optional[Tuple[CategoryName, TaxDeductibility, str]]:
        key = clean_merchant.strip().lower()
        return self._learned_overrides.get(key)

    def clear(self):
        self._learned_overrides.clear()

    @property
    def total_learned_rules(self) -> int:
        return len(self._learned_overrides)


# Singleton instance for the application lifecycle
user_rule_memory = UserRuleMemory()
