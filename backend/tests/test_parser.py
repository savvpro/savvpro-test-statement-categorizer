"""Tests for the CSV parser: column variants, messy rows, furniture rows."""

import pytest

from app.parser.statement_parser import ParseError, parse_statement

HEADER_SIMPLE = "Date,Description,Amount\n2026-03-01,ADOBE,-54.99\n"
HEADER_VARIANTS = "Transaction Date,Name,Transaction Amount\n01/03/2026,ADOBE,-54.99\n"
HEADER_DEBIT_CREDIT = (
    "Date,Description,Debit,Credit\n"
    "2026-03-01,ADOBE,54.99,\n"
    "2026-03-02,STRIPE PAYOUT,,1450.00\n"
)
HEADER_TYPE = "Date,Description,Amount,Type\n2026-03-01,ADOBE,54.99,DEBIT\n"


def test_simple_signed_amounts():
    txns, meta, _ = parse_statement(HEADER_SIMPLE)
    assert len(txns) == 1 and txns[0].amount == -54.99
    assert meta.rows_kept == 1


def test_alternate_header_names():
    txns, _, _ = parse_statement(HEADER_VARIANTS)
    assert txns[0].description == "ADOBE"
    assert txns[0].amount == -54.99
    assert txns[0].date == "2026-01-03"  # US month-first by default


def test_debit_credit_columns():
    txns, _, _ = parse_statement(HEADER_DEBIT_CREDIT)
    assert txns[0].amount == -54.99   # debit -> money out
    assert txns[1].amount == 1450.00  # credit -> money in


def test_type_column_signs_the_amount():
    txns, _, _ = parse_statement(HEADER_TYPE)
    assert txns[0].amount == -54.99


def test_accounting_parentheses_are_negative():
    text = "Date,Description,Amount\n2026-03-01,ADOBE,(54.99)\n"
    txns, _, _ = parse_statement(text)
    assert txns[0].amount == -54.99


def test_thousands_separators_and_currency_symbols():
    text = 'Date,Description,Amount\n2026-03-01,BIG BUY,"$1,250.00"\n'
    txns, _, _ = parse_statement(text)
    assert txns[0].amount == 1250.00


def test_summary_rows_are_skipped():
    text = ("Date,Description,Amount\n"
            "2026-03-01,ADOBE,-54.99\n"
            "2026-03-31,Total,\n"
            "2026-03-31,Ending Balance,5400.00\n")
    txns, meta, warnings = parse_statement(text)
    assert len(txns) == 1 and meta.rows_skipped == 2
    assert any("Skipped 2" in w for w in warnings)


def test_bad_date_is_kept_and_flagged():
    text = "Date,Description,Amount\n05/99/2026,ADOBE,-54.99\n"
    txns, _, warnings = parse_statement(text)
    assert txns[0].date is None
    assert "unreadable date" in txns[0].issues
    assert len(warnings) == 1


def test_missing_amount_is_flagged_not_crash():
    text = "Date,Description,Amount\n2026-03-01,ADOBE,\n"
    txns, _, warnings = parse_statement(text)
    assert txns[0].amount == 0.0
    assert "missing amount" in txns[0].issues


def test_blank_lines_are_ignored():
    text = "Date,Description,Amount\n2026-03-01,ADOBE,-1.00\n\n\n"
    _, meta, _ = parse_statement(text)
    assert meta.rows_read == 1


def test_empty_file_raises():
    with pytest.raises(ParseError):
        parse_statement("")


def test_no_header_raises():
    with pytest.raises(ParseError):
        parse_statement("just some text without columns\nmore text\n")


def test_missing_required_column_raises():
    with pytest.raises(ParseError):
        parse_statement("Date,Place\n2026-03-01,SF\n")
