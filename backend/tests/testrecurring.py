from decimal import Decimal
from datetime import date
from app.categorizer.recurring import buildrecurring

def testrecurringmonthly() -> None:
    txns = [
        {"descriptionraw": "SHOP RENT KHALID", "amount": Decimal("-85000.00"), "date": date(2026, 1, 1)},
        {"descriptionraw": "SHOP RENT KHALID", "amount": Decimal("-85000.00"), "date": date(2026, 1, 31)},
        {"descriptionraw": "SHOP RENT KHALID", "amount": Decimal("-85000.00"), "date": date(2026, 3, 2)},
        {"descriptionraw": "SHOP RENT KHALID", "amount": Decimal("-85000.00"), "date": date(2026, 4, 1)}
    ]
    res = buildrecurring(txns)
    assert "SHOP RENT KHALID" in res
    assert res["SHOP RENT KHALID"]["pattern"] == "monthly"
    assert res["SHOP RENT KHALID"]["median"] == Decimal("85000.00")