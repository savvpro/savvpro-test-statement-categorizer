import datetime as dt
from decimal import Decimal

from app.brain.categorizer import Categorizer
from app.models import RawTransaction


def tx(row: int) -> RawTransaction:
    return RawTransaction(
        row_number=row + 1,  # CSV line numbers start after the header
        date=dt.date(2025, 8, 22),
        description="LOCKSMITH EXPRESS 220",
        amount=Decimal("-85.00"),
    )


def test_duplicate_points_to_the_row_it_duplicates():
    first, second = Categorizer().categorize_all([tx(1), tx(2)])
    assert not first.is_duplicate
    assert second.is_duplicate
    assert f"row {first.id}" in second.explanation