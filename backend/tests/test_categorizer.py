from app.brain.categorizer import categorize_transaction, summarize_by_category
from app.models import Category, Transaction


def _tx(desc: str, amount: float) -> Transaction:
    return Transaction(id="1", date="2025-01-01", description=desc, amount=amount)


def test_adobe_is_software():
    result = categorize_transaction(_tx("ADOBE CREATIVE CLOUD", -52.99))
    assert result.category == Category.SOFTWARE
    assert result.confidence == "high"


def test_uber_trip_is_travel():
    result = categorize_transaction(_tx("UBER *TRIP 9921", -18.40))
    assert result.category == Category.TRAVEL


def test_transfer_not_spending():
    result = categorize_transaction(_tx("TRANSFER TO SAVINGS", -500.0))
    assert result.category == Category.NOT_SPENDING


def test_unknown_cafe_needs_review():
    result = categorize_transaction(_tx("JOES CAFE 9921", -12.50))
    assert result.category == Category.NEEDS_REVIEW


def test_refund_keyword():
    result = categorize_transaction(_tx("ADOBE REFUND", 52.99))
    assert result.category == Category.REFUND


def test_positive_amount_without_refund_medium_confidence():
    result = categorize_transaction(_tx("MISC CREDIT", 15.00))
    assert result.category == Category.REFUND
    assert result.confidence == "medium"


def test_summaries_use_user_override():
    from app.models import CategorizedTransaction

    txs = [
        CategorizedTransaction(
            id="a",
            date="2025-01-01",
            description="X",
            amount=-10,
            category=Category.NEEDS_REVIEW,
            confidence="unknown",
            reason="test",
            user_category=Category.OFFICE,
        )
    ]
    summaries = summarize_by_category(txs)
    assert any(s.category == Category.OFFICE for s in summaries)
