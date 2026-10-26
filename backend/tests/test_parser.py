from decimal import Decimal as D

import pytest

from app.parser import StatementError, parse_amount, parse_date, parse_statement


@pytest.mark.parametrize("raw,expected", [
    ("-45.00", "-45.00"), ("(45.00)", "-45.00"), ("$1,200.50", "1200.50"),
    ("45.00-", "-45.00"), ("+10", "10"),
])
def test_parse_amount(raw, expected):
    assert parse_amount(raw) == D(expected)


@pytest.mark.parametrize("raw", ["", "abc", "NaN", "1.2.3", "9" * 20])
def test_parse_amount_invalid(raw):
    with pytest.raises(ValueError):
        parse_amount(raw)


@pytest.mark.parametrize("raw,expected", [
    ("2026-10-01", "2026-10-01"), ("01/10/2026", "2026-10-01"),
    ("13/10/2026", "2026-10-13"), ("1 Oct 2026", "2026-10-01"),
])
def test_parse_date(raw, expected):
    assert parse_date(raw) == expected


def test_parse_date_invalid():
    with pytest.raises(ValueError):
        parse_date("yesterday")


def test_bom_and_header_case():
    data = b"\xef\xbb\xbfDate, Description ,AMOUNT\n2026-10-01,ADOBE,-5\n"
    rows, errors = parse_statement(data)
    assert len(rows) == 1 and not errors


def test_missing_column():
    with pytest.raises(StatementError):
        parse_statement(b"date,description\n2026-10-01,ADOBE\n")


def test_empty_file():
    with pytest.raises(StatementError):
        parse_statement(b"   \n")


def test_bad_and_blank_rows_do_not_break_file():
    data = b"date,description,amount\n2026-10-01,ADOBE,-5\n,,\n2026-10-02,UBER,abc\n"
    rows, errors = parse_statement(data)
    assert len(rows) == 1
    assert errors[0]["line"] == 4
