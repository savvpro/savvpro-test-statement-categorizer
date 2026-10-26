from decimal import Decimal
from app.categorizer.counterparties import buildcounterparties

def testcounterparties() -> None:
    txns = [
        {"descriptionraw": "TELEMART", "amount": Decimal("-50000.00")},
        {"descriptionraw": "TELEMART", "amount": Decimal("-40000.00")},
        {"descriptionraw": "TELEMART", "amount": Decimal("-20000.00")},
        {"descriptionraw": "CUSTOMER ALI", "amount": Decimal("10000.00")},
        {"descriptionraw": "CUSTOMER ALI", "amount": Decimal("15000.00")},
        {"descriptionraw": "TWOWAY TRADER", "amount": Decimal("-5000.00")},
        {"descriptionraw": "TWOWAY TRADER", "amount": Decimal("5000.00")}
    ]
    res = buildcounterparties(txns)
    assert res.get("TELEMART") == "supplier"
    assert res.get("CUSTOMER ALI") == "customer"
    assert res.get("TWOWAY TRADER") == "twoway"