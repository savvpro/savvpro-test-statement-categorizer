"""Unit tests for category schema and source of truth."""

import pytest
from app.schemas.category import (
    DEFAULT_CATEGORIES,
    DefaultCategory,
    get_all_category_names,
    get_category_metadata,
    is_valid_category,
)


def test_default_categories_count():
    """Verify exactly 16 default categories are defined as required."""
    all_names = get_all_category_names()
    assert len(all_names) == 16
    assert len(DEFAULT_CATEGORIES) == 16


def test_all_16_required_categories_present():
    """Verify all 16 specific category names exist in the source of truth."""
    expected = [
        "Software",
        "Cloud Hosting",
        "Office Supplies",
        "Hardware and Equipment",
        "Internet and Telecommunications",
        "Advertising and Marketing",
        "Professional Services",
        "Travel",
        "Meals",
        "Bank Fees",
        "Business Income",
        "Refund",
        "Reversal",
        "Internal Transfer",
        "Personal Expense",
        "Needs Review",
    ]
    for category_name in expected:
        assert is_valid_category(category_name) is True, f"Missing category: {category_name}"


def test_category_metadata_completeness():
    """Ensure every category has a description and example."""
    for cat_enum, meta in DEFAULT_CATEGORIES.items():
        assert meta.name == cat_enum.value
        assert len(meta.description.strip()) > 0
        assert len(meta.example.strip()) > 0
        assert meta.is_system_category is True


def test_get_category_metadata_lookup():
    """Test lookup by enum and string."""
    meta_from_enum = get_category_metadata(DefaultCategory.SOFTWARE)
    meta_from_str = get_category_metadata("Software")

    assert meta_from_enum is not None
    assert meta_from_str is not None
    assert meta_from_enum == meta_from_str
    assert meta_from_enum.name == "Software"

    assert get_category_metadata("Nonexistent Category") is None
