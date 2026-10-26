from decimal import Decimal
from app.categorizer.categories import (
    INVENTORY, SHIPPING, SOFTWARE, MARKETING, RENT, SALARIES, BANKFEES, SALESINCOME, NOTSPENDING, NEEDSREVIEW
)
from app.categorizer.context import Context
from app.categorizer.brain import categorize

def runcase(desc: str, amount: str, expectedcat: str, expectedroute: str) -> None:
    txn = {"descriptionraw": desc, "amount": Decimal(amount)}
    ctx = Context(userrules={"SAVED RULE MERCHANT": SOFTWARE}, counterparties={}, recurring={}, reversals=set())
    res = categorize(txn, ctx)
    assert res["category"] == expectedcat
    assert res["route"] == expectedroute

def testbrain30cases() -> None:
    cases = [
        ("IBFT TO TELEMART PVT LTD", "-185000.00", INVENTORY, "scored"),
        ("TCS COD SETTLEMENT", "45000.00", SALESINCOME, "scored"),
        ("FACEBK ADS 7731", "-12500.00", MARKETING, "scored"),
        ("K-ELECTRIC BILL", "-15000.00", RENT, "scored"),
        ("SALARY ALI", "-55000.00", SALARIES, "scored"),
        ("SMS ALERT CHARGES", "-150.00", BANKFEES, "scored"),
        ("WHT ON CASH", "-500.00", BANKFEES, "scored"),
        ("MICROSOFT 365", "-25000.00", SOFTWARE, "scored"),
        ("SELF TRANSFER TO SAVINGS", "-50000.00", NOTSPENDING, "notspending"),
        ("OWNER CAPITAL INTRODUCED", "500000.00", NOTSPENDING, "notspending"),
        ("DARAZ PK", "-12000.00", NEEDSREVIEW, "ambiguous"),
        ("ATM WITHDRAWAL", "-10000.00", NEEDSREVIEW, "ambiguous"),
        ("SAVED RULE MERCHANT", "-5000.00", SOFTWARE, "userrule"),
        ("CZONE", "-45000.00", INVENTORY, "scored"),
        ("POSTEX COURIER", "-2000.00", SHIPPING, "scored"),
        ("ADOBE CLOUD", "-15000.00", SOFTWARE, "scored"),
        ("GOOGLE ADS", "-80000.00", MARKETING, "scored"),
        ("PTCL INTERNET", "-4500.00", RENT, "scored"),
        ("WAGES CASH", "-35000.00", SALARIES, "scored"),
        ("ANNUAL FEE", "-5000.00", BANKFEES, "scored"),
        ("CUSTOMER PAYMENT", "120000.00", SALESINCOME, "scored"),
        ("CREDIT CARD PAYMENT", "-40000.00", NOTSPENDING, "notspending"),
        ("CASH DEPOSIT", "15000.00", NEEDSREVIEW, "ambiguous")
    ]

    for desc, amt, expcat, exproute in cases:
        runcase(desc, amt, expcat, exproute)

def testrefundcategories() -> None:
    txn1 = {"descriptionraw": "RMA REFUND TELEMART", "amount": Decimal("50000.00")}
    ctx = Context(userrules={}, counterparties={"TELEMART": "supplier"}, recurring={}, reversals=set())
    res1 = categorize(txn1, ctx)
    assert res1["category"] == INVENTORY
    assert res1["isrefund"] is True