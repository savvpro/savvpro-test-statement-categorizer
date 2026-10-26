from datetime import date

import pytest

from app.parsing.csv_parser import (
    CSVParseError,
    detect_date_order,
    parse_amount,
    parse_date,
    parse_statement,
)

# ---------------------------------------------------------------- sample files


@pytest.mark.parametrize(
    ("name", "expected_rows"),
    [("bank_a", 40), ("bank_b", 40), ("messy", 37)],
)
def test_sample_files_parse(sample_dir, name, expected_rows):
    result = parse_statement((sample_dir / f"{name}.csv").read_bytes())
    assert len(result.transactions) == expected_rows


def test_bank_a_date_amount_columns(sample_dir):
    first = parse_statement((sample_dir / "bank_a.csv").read_bytes()).transactions[0]
    assert first.date == date(2026, 5, 1)
    assert first.description == "ADOBE CREATIVE CLOUD"
    assert first.amount == -54.99
    assert first.row_number == 2


def test_bank_b_debit_credit_columns_become_signed_amount(sample_dir):
    txns = parse_statement((sample_dir / "bank_b.csv").read_bytes()).transactions
    by_desc = {t.description: t for t in txns}
    assert by_desc["PAYPAL *ADOBE"].amount == -54.99  # debit -> money out
    assert by_desc["ADOBE REFUND"].amount == 20.0  # credit -> money in
    assert by_desc["PAYPAL *ADOBE"].date == date(2026, 6, 1)


def test_messy_file_preamble_skipped_rows_and_warnings(sample_dir):
    result = parse_statement((sample_dir / "messy.csv").read_bytes())
    assert result.date_order == "day-first"
    assert result.warnings == [
        "Row 12 skipped: amount is missing",
        "Row 23 skipped: 'not a date' is not a date",
        "Row 25 skipped: 'abc' is not a number",
        "Row 46 skipped: 'Total' is not a date",
    ]


def test_messy_three_date_formats_are_the_same_day(sample_dir):
    txns = parse_statement((sample_dir / "messy.csv").read_bytes()).transactions
    first_three = [t.date for t in txns[:3]]  # 03/05/2026, 2026-05-03, 3 May 2026
    assert first_three == [date(2026, 5, 3)] * 3


def test_messy_amount_formats(sample_dir):
    txns = parse_statement((sample_dir / "messy.csv").read_bytes()).transactions
    by_row = {t.row_number: t.amount for t in txns}
    assert by_row[5] == -54.99  # (54.99)
    assert by_row[9] == -48.20  # $-48.20
    assert by_row[11] == -1250.00  # "-1,250.00"
    assert by_row[14] == 30.00  # +30.00


# ---------------------------------------------------------------- amounts


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1,250.00", 1250.0),
        ("$54.99", 54.99),
        ("(54.99)", -54.99),
        ("-54.99", -54.99),
        ("54.99-", -54.99),
        ("54.99 CR", 54.99),
        ("54.99 DR", -54.99),
        ("+30.00", 30.0),
        ("€12.00", 12.0),
        ("USD 15.00", 15.0),
        ("  7 ", 7.0),
    ],
)
def test_parse_amount(raw, expected):
    assert parse_amount(raw) == expected


@pytest.mark.parametrize("raw", ["", "   ", None])
def test_parse_amount_empty_is_none(raw):
    assert parse_amount(raw) is None


@pytest.mark.parametrize("raw", ["abc", "12.3.4", "--5"])
def test_parse_amount_junk_raises(raw):
    with pytest.raises(ValueError):
        parse_amount(raw)


# ---------------------------------------------------------------- dates


def test_iso_dates_are_never_flipped_by_day_first():
    assert parse_date("2026-05-03", day_first=True) == date(2026, 5, 3)
    assert parse_date("2026-05-03", day_first=False) == date(2026, 5, 3)


def test_text_and_slash_dates():
    assert parse_date("5 Mar 2026", day_first=False) == date(2026, 3, 5)
    assert parse_date("03/05/2026", day_first=False) == date(2026, 3, 5)
    assert parse_date("03/05/2026", day_first=True) == date(2026, 5, 3)


@pytest.mark.parametrize("raw", ["", "not a date", "2026-13-45"])
def test_bad_dates_raise(raw):
    with pytest.raises(ValueError):
        parse_date(raw, day_first=False)


def test_detect_date_order():
    assert detect_date_order(["13/05/2026", "03/05/2026"]) == ("day-first", False)
    assert detect_date_order(["05/13/2026", "03/05/2026"]) == ("month-first", False)
    assert detect_date_order(["03/05/2026"]) == ("month-first", True)
    assert detect_date_order(["2026-05-03"]) == ("month-first", False)


def test_ambiguous_dates_produce_warning_and_note():
    csv = "Date,Description,Amount\n03/05/2026,ADOBE,-1\n04/04/2026,FIGMA,-2\n"
    result = parse_statement(csv)
    assert any("ambiguous" in w for w in result.warnings)
    assert result.transactions[0].notes == ["Date '03/05/2026' is ambiguous; read as month/day"]
    assert result.transactions[1].notes == []  # 04/04 reads the same either way


# ---------------------------------------------------------------- structure


@pytest.mark.parametrize(
    "header",
    [
        "Date,Description,Amount",
        "Txn Date,Details,Amount",
        "Transaction Date,Merchant,Transaction Amount",
        "Posting Date,Payee,Amount (USD)",
        "  DATE , DESCRIPTION , AMOUNT ",
    ],
)
def test_column_aliases(header):
    result = parse_statement(f"{header}\n2026-05-01,ADOBE,-10.00\n")
    assert result.transactions[0].description == "ADOBE"
    assert result.transactions[0].amount == -10.0


def test_semicolon_delimiter_and_bom():
    content = "﻿Date;Description;Amount\n2026-05-01;ADOBE;-10.00\n".encode()
    assert parse_statement(content).transactions[0].amount == -10.0


def test_cp1252_encoding():
    content = "Date,Description,Amount\n2026-05-01,CAFÉ ROMA,-10.00\n".encode("cp1252")
    assert parse_statement(content).transactions[0].description == "CAFÉ ROMA"


def test_both_debit_and_credit_filled_uses_difference_with_note():
    csv = "Date,Description,Debit,Credit\n2026-05-01,ODD ROW,10.00,4.00\n"
    txn = parse_statement(csv).transactions[0]
    assert txn.amount == -6.0
    assert "both a debit and a credit" in txn.notes[0]


def test_debit_credit_both_empty_row_skipped():
    csv = "Date,Description,Debit,Credit\n2026-05-01,EMPTY,,\n2026-05-02,ADOBE,5.00,\n"
    result = parse_statement(csv)
    assert len(result.transactions) == 1
    assert result.warnings == ["Row 2 skipped: both debit and credit are empty"]


def test_currency_column_is_read():
    csv = "Date,Description,Amount,Currency\n2026-05-01,ADOBE,-10.00,eur\n"
    assert parse_statement(csv).transactions[0].currency == "EUR"


def test_missing_description_row_skipped():
    csv = "Date,Description,Amount\n2026-05-01,,-10.00\n2026-05-02,ADOBE,-1\n"
    result = parse_statement(csv)
    assert result.warnings == ["Row 2 skipped: description is missing"]


# ---------------------------------------------------------------- file errors


@pytest.mark.parametrize("content", [b"", b"   \n\n", ""])
def test_empty_file_raises_clear_error(content):
    with pytest.raises(CSVParseError, match="The file is empty"):
        parse_statement(content)


def test_header_only_file():
    with pytest.raises(CSVParseError, match="No transactions found"):
        parse_statement("Date,Description,Amount\n")


def test_all_rows_broken():
    with pytest.raises(CSVParseError, match="No transactions found"):
        parse_statement("Date,Description,Amount\nxx,ADOBE,abc\n")


@pytest.mark.parametrize(
    ("header", "message"),
    [
        ("Foo,Description,Amount", "date column"),
        ("Date,Foo,Amount", "description column"),
        ("Date,Description,Foo", "amount column"),
    ],
)
def test_missing_columns(header, message):
    with pytest.raises(CSVParseError, match=message):
        parse_statement(f"{header}\n2026-05-01,ADOBE,-1\n")
