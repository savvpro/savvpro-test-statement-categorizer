from datetime import date
from decimal import Decimal

from app.brain import categorize
from app.models import CategorizationRule, Transaction


def transaction(description: str, amount: str = "10", direction: str = "expense") -> Transaction:
    return Transaction("1", date(2026, 1, 1), description, Decimal(amount), "USD", direction)  # type: ignore[arg-type]


def test_shared_rule_categorizes_known_merchant():
    result = categorize(transaction("ADOBE CREATIVE CLOUD 123"), [])
    assert result.category == "Software"
    assert result.rule_scope == "shared"
    assert result.needs_review is False


def test_special_case_transfer_beats_merchant_rules():
    result = categorize(transaction("TRANSFER TO SAVINGS"), [])
    assert result.category == "Transfer"
    assert result.confidence == 98


def test_personal_rule_overrides_shared_rule():
    rule = CategorizationRule("ADOBE CREATIVE CLOUD", "Personal Expense", "user", "user_correction", exact=False)
    result = categorize(transaction("ADOBE CREATIVE CLOUD"), [rule])
    assert result.category == "Personal Expense"
    assert result.rule_scope == "user"


def test_unknown_is_review():
    result = categorize(transaction("JOES CAFE 9921"))
    assert result.category == "Meals"
    assert result.needs_review is True


def test_dataset_categories_are_supported():
    assert categorize(transaction("Swiggy bought groceries")).category == "Food & Dining"
    assert categorize(transaction("Reliance Digital laptop purchase")).category == "Electronics"
    assert categorize(transaction("Apollo pharmacy")).category == "Health"
