"""Category catalog for a freelance designer's tax-time review.

Buckets control the totals. Only "expense" rows enter the deductible figure,
and only after a refund has been subtracted from the category it offsets.
"""

from __future__ import annotations

CATEGORIES: list[tuple[str, str, str]] = [
    ("software", "Software", "expense"),
    ("travel", "Travel", "expense"),
    ("meals", "Meals", "expense"),
    ("supplies", "Office supplies", "expense"),
    ("equipment", "Equipment", "expense"),
    ("contractors", "Contract labor", "expense"),
    ("marketing", "Marketing", "expense"),
    ("professional", "Professional services", "expense"),
    ("utilities", "Utilities and internet", "expense"),
    ("education", "Education", "expense"),
    ("fees", "Interest and fees", "expense"),
    ("refund", "Refund", "refund"),
    ("income", "Client income", "income"),
    ("card_payment", "Card payment", "excluded"),
    ("transfer", "Transfer", "excluded"),
    ("personal", "Personal", "personal"),
    ("needs_review", "Needs review", "review"),
]

LABELS = {category_id: label for category_id, label, _bucket in CATEGORIES}
BUCKETS = {category_id: bucket for category_id, _label, bucket in CATEGORIES}
EXPENSE_IDS = {category_id for category_id, _label, bucket in CATEGORIES if bucket == "expense"}
SELECTABLE_IDS = [category_id for category_id, _label, _bucket in CATEGORIES if category_id != "needs_review"]


def label(category_id: str | None) -> str | None:
    if category_id is None:
        return None
    return LABELS.get(category_id, category_id)


def bucket(category_id: str | None) -> str | None:
    if category_id is None:
        return None
    return BUCKETS.get(category_id)


def public_categories() -> list[dict[str, str]]:
    return [
        {"id": category_id, "label": category_label, "bucket": category_bucket}
        for category_id, category_label, category_bucket in CATEGORIES
        if category_id != "needs_review"
    ]
