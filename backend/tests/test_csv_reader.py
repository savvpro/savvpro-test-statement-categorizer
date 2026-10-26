from decimal import Decimal

import pytest

from app.domain.errors import StatementError, UnsupportedFormatError
from app.ingestion.base import ReaderRegistry
from app.ingestion.csv_reader import CsvStatementReader, parse_amount

reader = CsvStatementReader()


@pytest.mark.parametrize("raw,expected", [
    ("£1,234.50", Decimal("1234.50")),
    ("(12.00)", Decimal("-12.00")),
    ("-7", Decimal("-7.00")),
    ("12.00 DR", Decimal("-12.00")),
    ("12.00 CR", Decimal("12.00")),
    ("", None),
])
def test_parse_amount_formats(raw, expected):
    assert parse_amount(raw) == expected


def test_signed_amount_column():
    parsed = reader.read(b"Date,Description,Amount\n2026-03-01,ADOBE,-54.99\n")
    assert parsed.transactions[0].amount == Decimal("-54.99") and not parsed.issues


def test_split_money_in_out_columns_and_uk_dates():
    parsed = reader.read(b"Date,Description,Money Out,Money In\n01/03/2026,ADOBE,54.99,\n02/03/2026,CLIENT,,100\n")
    assert [t.amount for t in parsed.transactions] == [Decimal("-54.99"), Decimal("100.00")]
    assert parsed.transactions[0].date.month == 3


def test_bad_rows_are_reported_not_fatal():
    parsed = reader.read(b"Date,Description,Amount\nnot-a-date,X,1\n2026-03-01,,1\n2026-03-01,OK,abc\n2026-03-01,GOOD,-1\n")
    assert len(parsed.transactions) == 1
    assert [i.row for i in parsed.issues] == [2, 3, 4]


def test_bom_and_blank_lines():
    parsed = reader.read("﻿Date,Description,Amount\n\n2026-03-01,X,-1\n".encode())
    assert len(parsed.transactions) == 1


def test_row_limit():
    with pytest.raises(StatementError):
        CsvStatementReader(max_rows=1).read(b"Date,Description,Amount\n2026-03-01,A,-1\n2026-03-01,B,-1\n")


@pytest.mark.parametrize("content", [b"", b"Foo,Bar\n1,2\n", b"Date,Description\n2026-01-01,X\n"])
def test_unreadable_statements_raise(content):
    with pytest.raises(StatementError):
        reader.read(content)


def test_registry_rejects_unknown_extension():
    with pytest.raises(UnsupportedFormatError):
        ReaderRegistry([reader]).for_filename("statement.pdf")
