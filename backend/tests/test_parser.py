
from pathlib import Path

import pytest

from app.parser.csv_parser import ParseError, parse_csv

SAMPLE = Path(__file__).resolve().parents[2] / "sample_data" / "fake_statement.csv"


def test_valid_csv():
    data = b"date,description,amount\n2026-10-01,ADOBE CREATIVE CLOUD,-54.99\n"
    txns, skipped = parse_csv(data)
    assert len(txns) == 1
    assert skipped == []
    assert txns[0].id == "row-2"
    assert txns[0].amount == -54.99
    assert txns[0].currency == "USD"  # default


def test_empty_file_raises():
    with pytest.raises(ParseError, match="empty"):
        parse_csv(b"")


def test_missing_columns_raises():
    with pytest.raises(ParseError, match="Missing columns"):
        parse_csv(b"date,description\n2026-10-01,ADOBE\n")


def test_non_utf8_raises():
    with pytest.raises(ParseError):
        parse_csv(b"\xff\xfe\x00")


def test_bad_rows_are_skipped_not_hidden():
    data = (
        b"date,description,amount\n"
        b"not-a-date,BAD,-5\n"
        b"2026-10-01,,-5\n"
        b"2026-10-01,OK ROW,abc\n"
        b"2026-10-01,GOOD ROW,-5\n"
    )
    txns, skipped = parse_csv(data)
    assert len(txns) == 1
    assert [s.row for s in skipped] == [2, 3, 4]


def test_header_case_and_bom_are_handled():
    data = "\ufeffDate,Description,Amount\n2026-10-01,ADOBE,-5\n".encode("utf-8")
    txns, _ = parse_csv(data)
    assert len(txns) == 1


def test_currency_column_is_read():
    data = b"date,description,amount,currency\n2026-10-01,ADOBE,-5,eur\n"
    txns, _ = parse_csv(data)
    assert txns[0].currency == "EUR"


def test_sample_file_counts():
    txns, skipped = parse_csv(SAMPLE.read_bytes())
    assert len(txns) == 34
    assert len(skipped) == 2