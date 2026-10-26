import pytest

from backend.app.main import Review


@pytest.mark.parametrize(
    "kind,category,purpose,percent",
    [
        ("expense", "Own-account transfer", "business", 100),
        ("transfer", "Groceries", "excluded", 0),
        ("card_payment", "Card payment", "personal", 0),
        ("cash", "Cash withdrawal", "business", 100),
        ("income", "Entertainment", "business", 100),
    ],
)
def test_incompatible_type_category_purpose_cannot_be_confirmed(kind, category, purpose, percent):
    with pytest.raises(ValueError):
        Review(kind=kind, category=category, purpose=purpose, business_percent=percent)


def test_remembered_outgoing_family_support_does_not_classify_incoming_transfer():
    from backend.app.engine import classify

    rule = {
        "match_text": "IBFT TO RECIPIENT",
        "kind": "expense",
        "category": "Family support",
        "purpose": "personal",
        "business_percent": 0,
    }
    assert classify("IBFT TO RECIPIENT", -10000, [rule])["needs_review"]


def test_unsupported_encoding_returns_a_validation_error():
    from backend.app.parsers import ImportProblem, extract

    with pytest.raises(ImportProblem, match="encoding"):
        extract("test.csv", b"Date,Description,Amount\n2026-09-01,\x81,1\n")
