from decimal import Decimal as D
from pathlib import Path

import pytest

from app.parser import ParseError, parse_amount, parse_date, parse_statement

SAMPLE = Path(__file__).parent.parent / "sample_data" / "fake_statement.csv"


@pytest.mark.parametrize("raw, expected", [
    ("54.99", D("54.99")),
    ("-54.99", D("-54.99")),
    ("$1,234.50", D("1234.50")),
    ("-$12.00", D("-12.00")),
    ("(45.00)", D("-45.00")),
    ("45.00-", D("-45.00")),
    (" 7 ", D("7")),
])
def test_amount_formats(raw, expected):
    assert parse_amount(raw) == expected


@pytest.mark.parametrize("raw", ["", "abc", "NaN", "Infinity", "12.3.4"])
def test_bad_amounts_rejected(raw):
    with pytest.raises(ParseError):
        parse_amount(raw)


@pytest.mark.parametrize("raw, expected", [
    ("2026-09-01", "2026-09-01"),
    ("09/01/2026", "2026-09-01"),
    ("09/01/26", "2026-09-01"),
    ("01-Sep-2026", "2026-09-01"),
])
def test_date_formats(raw, expected):
    assert parse_date(raw) == expected


def test_bad_date_rejected():
    with pytest.raises(ParseError):
        parse_date("not-a-date")


def test_sample_file_parses_fully():
    txns, skipped = parse_statement(SAMPLE.read_bytes())
    assert len(txns) == 8
    assert skipped == []
    assert txns[0].description == "ADOBE CREATIVE CLOUD"
    assert txns[0].amount == D("-54.99")


def test_card_sign_convention_flips():
    data = b"Date,Description,Amount\n2026-09-01,ADOBE,54.99\n2026-09-02,REFUND,-5.00\n"
    txns, _ = parse_statement(data, charges_positive=True)
    assert txns[0].amount == D("-54.99")   # purchase -> money out
    assert txns[1].amount == D("5.00")     # credit -> money in


def test_debit_credit_columns():
    data = (b"Date,Description,Debit,Credit\n"
            b"2026-09-01,ADOBE,54.99,\n"
            b"2026-09-02,STRIPE PAYOUT,,2400.00\n")
    txns, skipped = parse_statement(data)
    assert [t.amount for t in txns] == [D("-54.99"), D("2400.00")]
    assert skipped == []


def test_alternative_header_names():
    data = b"Posted Date,Memo,Amount\n2026-09-01,ADOBE,-5\n"
    txns, _ = parse_statement(data)
    assert txns[0].description == "ADOBE"


def test_bad_rows_reported_not_dropped():
    data = (b"Date,Description,Amount\n"
            b"not-a-date,X,5\n"
            b"2026-09-01,ADOBE,-5\n"
            b"2026-09-02,,-5\n"
            b"2026-09-03,ZOOM,abc\n")
    txns, skipped = parse_statement(data)
    assert len(txns) == 1
    assert len(skipped) == 3
    assert {s["error"].split(":")[0] for s in skipped} == {
        "bad date", "empty description", "bad amount"}


def test_blank_lines_ignored():
    data = b"Date,Description,Amount\n\n2026-09-01,ADOBE,-5\n,,\n"
    txns, skipped = parse_statement(data)
    assert len(txns) == 1 and skipped == []


def test_excel_bom_is_handled():
    data = b"\xef\xbb\xbfDate,Description,Amount\n2026-09-01,ADOBE,-5\n"
    txns, _ = parse_statement(data)
    assert len(txns) == 1


def test_missing_columns_raises_clear_error():
    with pytest.raises(ParseError, match="Could not find"):
        parse_statement(b"Foo,Bar\n1,2\n")


def test_empty_file_raises():
    with pytest.raises(ParseError):
        parse_statement(b"")