import codecs
from datetime import date
from decimal import Decimal

import pytest

from app.parser import StatementParseError, parse_amount, parse_date, parse_statement

D = Decimal


def parse(text: str, **kwargs):
    return parse_statement(text.encode("utf-8"), **kwargs)


# ---------------------------------------------------------------- amounts


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("1,234.50", D("1234.50")),
        ("12,345,678.00", D("12345678.00")),
        ("(500.00)", D("-500.00")),  # accountant's negative
        ("Rs 1,200", D("1200")),
        ("PKR 5,200.00", D("5200.00")),
        ("$12", D("12")),
        ("-45.10", D("-45.10")),
        ("45.10-", D("-45.10")),  # trailing minus
        ("+45.10", D("45.10")),
        ("1.234,56", D("1234.56")),  # European
        ("12,50", D("12.50")),
        ("1,234", D("1234")),  # thousands, not a decimal comma
        ("500.00 DR", D("-500.00")),
        ("500.00 CR", D("500.00")),
        ("0.10", D("0.10")),
        ("", None),
        ("   ", None),
        (None, None),
    ],
)
def test_parse_amount(raw, expected):
    assert parse_amount(raw) == expected


@pytest.mark.parametrize(
    "raw", ["abc", "nan", "NaN", "inf", "-Infinity", "1e5", "12.345", "1,2,3", "12.34.56", "9" * 14]
)
def test_parse_amount_rejects_garbage(raw):
    with pytest.raises(ValueError):
        parse_amount(raw)


def test_amounts_are_exact_decimals():
    assert parse_amount("0.1") + parse_amount("0.2") == D("0.3")


# ---------------------------------------------------------------- dates


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("01/10/2026", date(2026, 10, 1)),  # day first
        ("13/10/2026", date(2026, 10, 13)),
        ("01-10-2026", date(2026, 10, 1)),
        ("01.10.2026", date(2026, 10, 1)),
        ("1 Oct 2026", date(2026, 10, 1)),
        ("2026-10-01", date(2026, 10, 1)),  # ISO must NOT be read day-first (Jan 10)
        ("2026-10-01 14:30:00", date(2026, 10, 1)),
        ("01/10/26", date(2026, 10, 1)),
    ],
)
def test_parse_date(raw, expected):
    assert parse_date(raw) == expected


@pytest.mark.parametrize("raw", ["", "   ", "garbage", "31/02/2026", "2026-02-31", "10/2026", None])
def test_parse_date_rejects(raw):
    with pytest.raises(ValueError):
        parse_date(raw)


# ---------------------------------------------------------------- columns


def test_debit_and_credit_columns():
    result = parse(
        "Date,Description,Debit,Credit\n01/10/2026,SHELL,500.00,\n02/10/2026,PAYOUT,,900\n"
    )
    assert [t.amount for t in result.transactions] == [D("-500.00"), D("900")]
    assert [t.row for t in result.transactions] == [2, 3]


def test_single_amount_column_keeps_sign():
    result = parse("Date,Narration,Amount\n01/10/2026,SHELL,-500.00\n02/10/2026,PAYOUT,900.00\n")
    assert [t.amount for t in result.transactions] == [D("-500.00"), D("900.00")]


def test_credit_card_style_purchases_positive():
    text = (
        "Date,Description,Amount\n01/10/2026,SHELL,500.00\n02/10/2026,PAYMENT THANK YOU,-500.00\n"
    )
    result = parse(text, purchases_positive=True)
    assert [t.amount for t in result.transactions] == [D("-500.00"), D("500.00")]


def test_header_aliases_and_currency_suffix_in_header():
    result = parse(
        "Transaction Date,Details,Withdrawal (PKR),Deposit (PKR)\n01/10/2026,SHELL,500,\n"
    )
    assert result.transactions[0].amount == D("-500")


def test_debits_printed_as_negatives_still_mean_money_out():
    result = parse("Date,Description,Debit,Credit\n01/10/2026,SHELL,-500.00,\n")
    assert result.transactions[0].amount == D("-500.00")


def test_header_is_found_below_account_info_lines():
    text = (
        "Account Statement\nAccount: 0000-1111\nPeriod: Oct 2026\n\n"
        "Date,Description,Debit,Credit\n01/10/2026,SHELL,500,\n"
    )
    result = parse(text)
    assert len(result.transactions) == 1
    assert result.transactions[0].row == 6


def test_semicolon_delimiter_with_decimal_commas():
    result = parse(
        "Date;Description;Debit;Credit\n01/10/2026;SHELL;1.234,50;\n02/10/2026;PAYOUT;;99,90\n"
    )
    assert [t.amount for t in result.transactions] == [D("-1234.50"), D("99.90")]


def test_tab_delimiter():
    result = parse("Date\tDescription\tAmount\n01/10/2026\tSHELL\t-5\n")
    assert result.transactions[0].amount == D("-5")


def test_quoted_thousands_separator_in_comma_file():
    result = parse('Date,Description,Debit,Credit\n01/10/2026,PSO,"5,200.00",\n')
    assert result.transactions[0].amount == D("-5200.00")


# ---------------------------------------------------------------- encodings


def test_excel_utf8_bom():
    result = parse_statement(codecs.BOM_UTF8 + b"Date,Description,Amount\n01/10/2026,SHELL,-5\n")
    assert len(result.transactions) == 1


def test_windows_1252_file():
    raw = "Date,Description,Amount\n01/10/2026,CAFÉ ZEE,-5\n".encode("cp1252")
    assert parse_statement(raw).transactions[0].description == "CAFÉ ZEE"


def test_utf16_file():
    raw = "Date,Description,Amount\n01/10/2026,SHELL,-5\n".encode("utf-16")
    assert len(parse_statement(raw).transactions) == 1


# ---------------------------------------------------------------- bad input


@pytest.mark.parametrize("content", [b"", b"   \n\n  "])
def test_empty_file(content):
    with pytest.raises(StatementParseError, match="empty"):
        parse_statement(content)


def test_binary_file_is_refused():
    with pytest.raises(StatementParseError, match="binary"):
        parse_statement(b"PK\x03\x04" + b"\x00" * 100)


def test_missing_columns_error_names_what_was_found():
    with pytest.raises(StatementParseError, match="Could not find the columns") as info:
        parse("Name,Colour\nAli,Red\n")
    assert "Name" in str(info.value)


def test_header_without_any_money_column_is_not_a_header():
    with pytest.raises(StatementParseError):
        parse("Date,Description\n01/10/2026,SHELL\n")


def test_file_with_only_bad_rows_is_an_error():
    with pytest.raises(StatementParseError, match="No usable transactions"):
        parse("Date,Description,Amount\nnot a date,SHELL,-5\n")


def test_row_limit():
    rows = "\n".join(f"01/10/2026,ITEM {i},-1" for i in range(6))
    with pytest.raises(StatementParseError, match="more than 5 rows"):
        parse("Date,Description,Amount\n" + rows, max_rows=5)


# ---------------------------------------------------------------- bad rows


def test_a_bad_row_is_skipped_with_its_row_number_and_the_rest_survive():
    text = (
        "Date,Description,Debit,Credit\n"
        "01/10/2026,GOOD,100,\n"
        "99/99/2026,BAD DATE,100,\n"
        "03/10/2026,BAD AMOUNT,abc,\n"
        "04/10/2026,,100,\n"
        "05/10/2026,NO MONEY,,\n"
        "06/10/2026,BOTH,100,200\n"
        "07/10/2026,ZERO,0.00,\n"
        "08/10/2026,ALSO GOOD,,50\n"
    )
    result = parse(text)
    assert [t.description for t in result.transactions] == ["GOOD", "ALSO GOOD"]
    assert [s.row for s in result.skipped] == [3, 4, 5, 6, 7, 8]
    reasons = " | ".join(s.message for s in result.skipped)
    for expected in [
        "not a valid date",
        "not a valid amount",
        "missing description",
        "no debit or credit",
        "both Debit and Credit",
        "zero",
    ]:
        assert expected in reasons


def test_blank_lines_are_ignored_silently():
    result = parse("Date,Description,Amount\n\n01/10/2026,SHELL,-5\n,,\n\n")
    assert len(result.transactions) == 1
    assert result.skipped == []


def test_balance_and_total_lines_are_skipped_but_total_parco_is_not():
    text = (
        "Date,Description,Debit,Credit\n"
        "01/10/2026,OPENING BALANCE,,10000\n"
        "02/10/2026,TOTAL PARCO FUEL,500,\n"
        "03/10/2026,TOTAL,500,\n"
        "04/10/2026,CLOSING BALANCE,,9500\n"
    )
    result = parse(text)
    assert [t.description for t in result.transactions] == ["TOTAL PARCO FUEL"]
    assert len(result.skipped) == 3


def test_description_with_newline_keeps_row_numbers_right():
    text = 'Date,Description,Amount\n01/10/2026,"SHELL\nSTATION",-5\n02/10/2026,PSO,-6\n'
    result = parse(text)
    assert result.transactions[0].description == "SHELL STATION"
    assert result.transactions[1].row == 4  # the file really has the PSO row on line 4


def test_identical_rows_are_kept_but_flagged():
    text = "Date,Description,Amount\n01/10/2026,TOLL,-5\n01/10/2026,TOLL,-5\n02/10/2026,TOLL,-5\n"
    result = parse(text)
    assert len(result.transactions) == 3
    assert len(result.warnings) == 1
    assert "2, 3" in result.warnings[0].message


def test_very_long_description_is_truncated():
    result = parse(f"Date,Description,Amount\n01/10/2026,{'X' * 1000},-5\n")
    assert len(result.transactions[0].description) == 300
