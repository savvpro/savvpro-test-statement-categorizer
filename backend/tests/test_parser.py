from decimal import Decimal

import pytest

from app.parser import ParseError, parse_statement


def test_preamble_and_mixed_dates():
    text = """
Studio North
Account ending 4242

Posted Date,Description,Amount
01/02/2026,ADOBE *CREATIVE CLOUD,54.99
2026-01-03,FIGMA,$15.00
"""
    result = parse_statement(text, "credit_card")
    assert [row.date for row in result.rows] == ["2026-01-02", "2026-01-03"]
    assert result.rows[0].amount == Decimal("54.99")
    assert result.rows[1].amount == Decimal("15.00")


def test_bank_account_flips_the_bank_sign():
    text = "Date,Description,Amount\n2026-01-01,CLIENT PAYMENT,500.00\n2026-01-02,ADOBE CREATIVE CLOUD,-54.99\n"
    result = parse_statement(text, "bank")
    assert result.rows[0].amount == Decimal("-500.00")
    assert result.rows[1].amount == Decimal("54.99")


def test_debit_and_credit_columns():
    text = "Date,Memo,Debit,Credit\n01/02/2026,ADOBE,54.99,\n01/05/2026,PAYMENT THANK YOU,,1200\n"
    result = parse_statement(text, "credit_card")
    assert result.direction_source == "debit_credit"
    assert result.rows[0].amount == Decimal("54.99")
    assert result.rows[1].amount == Decimal("-1200.00")


def test_credit_suffix_parentheses_and_trailing_minus():
    text = "Date,Description,Amount\n01/02/2026,ADOBE,54.99CR\n01/03/2026,STAPLES,\"$1,200.50\"\n01/04/2026,ZOOM,(15.00)\n01/05/2026,LYFT,18.00-\n"
    result = parse_statement(text, "credit_card")
    amounts = [row.amount for row in result.rows]
    assert amounts == [Decimal("-54.99"), Decimal("1200.50"), Decimal("-15.00"), Decimal("-18.00")]


def test_semicolon_file_and_skipped_junk_rows():
    text = "Date;Description;Amount\n01/02/2026;CANVA;12.99\nnot-a-date;MYSTERY;oops\nTotal;;1.00\n"
    result = parse_statement(text, "credit_card")
    assert len(result.rows) == 1
    assert result.rows[0].description == "CANVA"
    assert len(result.warnings) == 2
    assert any("totals" in warning for warning in result.warnings)


def test_pending_flag_and_quoted_comma():
    text = 'Date,Description,Amount\n02-Jan-2026,"MOO, INC",40.00\n01/03/2026,PENDING UBER *TRIP,19.00\n'
    result = parse_statement(text, "credit_card")
    assert result.rows[0].date == "2026-01-02"
    assert result.rows[0].description == "MOO, INC"
    assert result.rows[1].pending is True


def test_missing_header_is_an_error():
    with pytest.raises(ParseError):
        parse_statement("hello\nthis is not a statement\n", "credit_card")


def test_sample_file_keeps_the_real_rows():
    from pathlib import Path

    text = (Path(__file__).resolve().parents[1] / "sample_statements" / "studio_north_january.csv").read_text(
        encoding="utf-8"
    )
    result = parse_statement(text, "credit_card")
    assert len(result.rows) == 44
    assert result.warnings
