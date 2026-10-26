import datetime as dt
from decimal import Decimal
from pathlib import Path

import pytest

from app.parsing.csv_parser import (
    StatementFormatError,
    parse_amount,
    parse_date,
    parse_statement,
)

DATA = Path(__file__).parent.parent / "data"


def _key(result):
    return [(t.date, t.description, t.amount) for t in result.transactions]


def test_both_bank_formats_parse_to_the_same_transactions():
    a = parse_statement((DATA / "bank_a.csv").read_bytes())
    b = parse_statement((DATA / "bank_b.csv").read_bytes())
    assert not a.errors and not b.errors
    assert len(a.transactions) > 0
    assert _key(a) == _key(b)


@pytest.mark.parametrize(
    "text, expected",
    [
        ("1500.00", Decimal("1500.00")),
        ("-12.50", Decimal("-12.50")),
        ("$1,234.50", Decimal("1234.50")),
        ("(12.00)", Decimal("-12.00")),
        ("12.00-", Decimal("-12.00")),
    ],
)
def test_parse_amount(text, expected):
    assert parse_amount(text) == expected


@pytest.mark.parametrize("text", ["", "abc", "nan", "1.2.3"])
def test_parse_amount_rejects_garbage(text):
    with pytest.raises(ValueError):
        parse_amount(text)


@pytest.mark.parametrize(
    "text", ["2025-03-09", "03/09/2025", "03/09/25", "09-Mar-2025", "Mar 09, 2025"]
)
def test_parse_date_formats(text):
    assert parse_date(text) == dt.date(2025, 3, 9)


def test_parse_date_rejects_garbage():
    with pytest.raises(ValueError):
        parse_date("not-a-date")


def test_bad_row_is_reported_but_does_not_stop_the_file():
    csv_text = (
        "Date,Description,Amount\n"
        "01/05/2025,RENT,1500.00\n"
        "not-a-date,OOPS,5.00\n"
        "\n"
        "01/07/2025,WATER,-40.00\n"
    )
    result = parse_statement(csv_text)
    assert len(result.transactions) == 2
    assert len(result.errors) == 1
    assert result.errors[0].row_number == 3


def test_missing_columns_raises_clear_error():
    with pytest.raises(StatementFormatError):
        parse_statement("Foo,Bar\n1,2\n")


def test_empty_file_raises():
    with pytest.raises(StatementFormatError):
        parse_statement("")


def test_excel_bom_is_handled():
    content = "\ufeffDate,Description,Amount\n01/05/2025,RENT,1500.00\n".encode("utf-8")
    result = parse_statement(content)
    assert len(result.transactions) == 1


def test_debit_credit_layout_and_negative_debits():
    csv_text = (
        "Date,Details,Debit,Credit\n"
        "2025-01-01,RENT IN,,1500.00\n"
        "2025-01-02,WATER,40.00,\n"
        "2025-01-03,POWER,-60.00,\n"
    )
    amounts = [t.amount for t in parse_statement(csv_text).transactions]
    assert amounts == [Decimal("1500.00"), Decimal("-40.00"), Decimal("-60.00")]