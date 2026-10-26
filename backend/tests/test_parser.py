from decimal import Decimal

import pytest

from app.parser import StatementError, parse_amount, parse_statement


def csv_bytes(text):
    return text.strip().encode()


def test_basic_charges_positive():
    result = parse_statement(csv_bytes("Date,Description,Amount\n2026-09-01,ADOBE,10.00"))
    assert result.rows[0].amount == Decimal("-10.00")
    assert result.rows[0].date == "2026-09-01"


def test_charges_negative_option():
    result = parse_statement(
        csv_bytes("Date,Description,Amount\n2026-09-01,ADOBE,-10.00"),
        charges_are_positive=False,
    )
    assert result.rows[0].amount == Decimal("-10.00")


def test_debit_credit_columns():
    result = parse_statement(csv_bytes(
        "Date,Details,Debit,Credit\n2026-09-01,ADOBE,10.00,\n2026-09-02,REFUND,,10.00"))
    assert [r.amount for r in result.rows] == [Decimal("-10.00"), Decimal("10.00")]


def test_amount_formats():
    assert parse_amount("$1,234.50") == Decimal("1234.50")
    assert parse_amount("(20.00)") == Decimal("-20.00")
    assert parse_amount("") is None
    with pytest.raises(ValueError):
        parse_amount("abc")


def test_day_month_format_is_detected():
    # 25/09 can only be day/month, so the whole file is read that way
    result = parse_statement(csv_bytes(
        "Date,Description,Amount\n25/09/2026,A,1\n03/09/2026,B,1"))
    assert [r.date for r in result.rows] == ["2026-09-25", "2026-09-03"]


def test_bad_rows_are_reported_not_fatal():
    result = parse_statement(csv_bytes(
        "Date,Description,Amount\n2026-09-01,OK,1\nnot-a-date,BAD,1\n2026-09-02,BAD2,abc"))
    assert len(result.rows) == 1
    assert [e["row_number"] for e in result.errors] == [3, 4]


def test_missing_columns():
    with pytest.raises(StatementError, match="Missing column"):
        parse_statement(csv_bytes("Foo,Bar\n1,2"))


def test_empty_file():
    with pytest.raises(StatementError):
        parse_statement(b"   ")


def test_headers_only():
    with pytest.raises(StatementError):
        parse_statement(csv_bytes("Date,Description,Amount"))
