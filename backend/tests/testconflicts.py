from decimal import Decimal
from app.categorizer.categories import NEEDSREVIEW, SOFTWARE, SALESINCOME, INVENTORY
from app.categorizer.context import Context
from app.categorizer.brain import categorize

def testunrealisticamount() -> None:
    txn = {"descriptionraw": "ADOBE CREATIVE CLOUD", "amount": Decimal("-250000.00")}
    ctx = Context(userrules={}, counterparties={}, recurring={}, reversals=set())
    res = categorize(txn, ctx)
    assert res["category"] == NEEDSREVIEW
    assert res["suggestedcategory"] == SOFTWARE
    assert "amount exceeds expected range" in res["conflicts"]

def testdirectionconflict() -> None:
    txn = {"descriptionraw": "COD SETTLEMENT TCS", "amount": Decimal("-5000.00")}
    ctx = Context(userrules={}, counterparties={}, recurring={}, reversals=set())
    res = categorize(txn, ctx)
    assert res["category"] == NEEDSREVIEW
    assert "direction conflict" in res["conflicts"]