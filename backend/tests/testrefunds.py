from decimal import Decimal
from app.categorizer.context import Context
from app.categorizer.refunds import isrefundtxn

def testrefundskw() -> None:
    ctx = Context(userrules={}, counterparties={}, recurring={})
    assert isrefundtxn(Decimal("-5000.00"), "CUSTOMER REFUND", ctx) is True
    assert isrefundtxn(Decimal("5000.00"), "RMA REFUND", ctx) is True

def testrefundstwoway() -> None:
    ctx = Context(userrules={}, counterparties={"TWOWAY TRADER": "twoway"}, recurring={})
    assert isrefundtxn(Decimal("-5000.00"), "TWOWAY TRADER", ctx) is True
    assert isrefundtxn(Decimal("5000.00"), "TWOWAY TRADER", ctx) is True

def testrefundssupplier() -> None:
    ctx = Context(userrules={}, counterparties={"TELEMART": "supplier"}, recurring={})
    assert isrefundtxn(Decimal("5000.00"), "TELEMART", ctx) is True