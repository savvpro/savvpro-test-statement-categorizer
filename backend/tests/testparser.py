from decimal import Decimal
from datetime import date
from app.parsers.csvparser import parsecontent

def testparseemptyfile() -> None:
    try:
        parsecontent(b"")
        assert False
    except ValueError as e:
        assert str(e) == "empty file"

def testparseunknownheader() -> None:
    try:
        parsecontent(b"col1,col2\nval1,val2")
        assert False
    except ValueError as e:
        assert str(e) == "unknown header format"

def testparselayouta() -> None:
    csvdata = b"Date,Narration,Chq/Ref No,Debit,Credit,Balance\n03/09/2026,IBFT TELEMART,,185000.00,,412300.50\n"
    result = parsecontent(csvdata)
    assert len(result["transactions"]) == 1
    txn = result["transactions"][0]
    assert txn["date"] == date(2026, 9, 3)
    assert txn["descriptionraw"] == "IBFT TELEMART"
    assert txn["amount"] == Decimal("-185000.00")
    assert txn["balance"] == Decimal("412300.50")
    assert txn["sourcerow"] == 2

def testparselayoutb() -> None:
    csvdata = b"Transaction Date,Description,Amount,Running Balance,Status\n05-Sep-2026,TCS COD,45600.00,549900.50,Posted\n"
    result = parsecontent(csvdata)
    assert len(result["transactions"]) == 1
    txn = result["transactions"][0]
    assert txn["date"] == date(2026, 9, 5)
    assert txn["amount"] == Decimal("45600.00")

def testparselayoutc() -> None:
    csvdata = b"Value Date,Transaction Details,Withdrawal,Deposit,Balance\n2026-09-07,BANK CHARGES,\"1,200.00\",,\"536,200.50\"\n"
    result = parsecontent(csvdata)
    assert len(result["transactions"]) == 1
    txn = result["transactions"][0]
    assert txn["date"] == date(2026, 9, 7)
    assert txn["amount"] == Decimal("-1200.00")

def testskipblankandpending() -> None:
    csvdata = b"Transaction Date,Description,Amount,Running Balance,Status\n\n06-Sep-2026,ADS,-12500.00,537400.50,Pending\n"
    result = parsecontent(csvdata)
    assert len(result["transactions"]) == 0
    assert len(result["skippedrows"]) == 2
    assert result["skippedrows"][0]["row"] == 2
    assert result["skippedrows"][0]["reason"] == "blank row"
    assert result["skippedrows"][1]["row"] == 3
    assert result["skippedrows"][1]["reason"] == "status pending"

def testbomanddrcrsuffixes() -> None:
    csvdata = b"\xef\xbb\xbfDate,Narration,Chq/Ref No,Debit,Credit,Balance\n03/09/2026,TELEMART,,185000 DR,,412300 CR\n"
    result = parsecontent(csvdata)
    assert len(result["transactions"]) == 1
    txn = result["transactions"][0]
    assert txn["amount"] == Decimal("-185000.00")
    assert txn["balance"] == Decimal("412300.00")