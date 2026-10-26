"""Tests for CSV parser."""

from __future__ import annotations

import io
import pytest

from app.parsers.csv_parser import CsvParser
from app.parsers.base import ParseError


class TestCsvParser:
    def _make_csv(self, content: str) -> io.BytesIO:
        return io.BytesIO(content.encode("utf-8"))

    def test_basic_parse(self):
        csv_content = (
            "Date,Description,Amount\n"
            "01/04/2026,ADOBE CREATIVE CLOUD,-59.99\n"
            "01/05/2026,PAYMENT THANK YOU,1500.00\n"
        )
        parser = CsvParser()
        rows = parser.parse(self._make_csv(csv_content))
        assert len(rows) == 2
        assert rows[0].raw_description == "ADOBE CREATIVE CLOUD"
        assert rows[0].amount_cents == -5999
        assert rows[1].amount_cents == 150000

    def test_separate_debit_credit_columns(self):
        csv_content = (
            "Transaction Date,Details,Debit,Credit\n"
            "01/04/2026,DIRECT DEPOSIT ACME LLC,,4500.00\n"
            "01/06/2026,ONLINE TRANSFER TO SAVINGS,1000.00,\n"
        )
        parser = CsvParser()
        rows = parser.parse(self._make_csv(csv_content), account_type="checking")
        assert len(rows) == 2
        # Credit → positive
        assert rows[0].amount_cents == 450000
        # Debit → negative
        assert rows[1].amount_cents == -100000

    def test_unknown_headers_raise_parse_error(self):
        csv_content = "Col1,Col2,Col3\na,b,c\n"
        parser = CsvParser()
        with pytest.raises(ParseError) as exc_info:
            parser.parse(self._make_csv(csv_content))
        assert exc_info.value.available_columns is not None

    def test_empty_file(self):
        parser = CsvParser()
        with pytest.raises(ParseError, match="empty"):
            parser.parse(self._make_csv(""))

    def test_can_handle(self):
        parser = CsvParser()
        assert parser.can_handle("statement.csv")
        assert parser.can_handle("statement.CSV")
        assert not parser.can_handle("statement.pdf")

    def test_date_formats(self):
        # ISO format
        csv_content = (
            "Date,Description,Amount\n"
            "2026-01-04,ADOBE,-59.99\n"
        )
        parser = CsvParser()
        rows = parser.parse(self._make_csv(csv_content))
        assert len(rows) == 1
        assert rows[0].posted_date.month == 1
        assert rows[0].posted_date.day == 4

    def test_dollar_sign_amounts(self):
        csv_content = (
            "Date,Description,Amount\n"
            "01/04/2026,ADOBE,$-59.99\n"
        )
        parser = CsvParser()
        rows = parser.parse(self._make_csv(csv_content))
        assert rows[0].amount_cents == -5999

    def test_skip_zero_amount(self):
        csv_content = (
            "Date,Description,Amount\n"
            "01/04/2026,PENDING,0.00\n"
            "01/05/2026,ADOBE,-59.99\n"
        )
        parser = CsvParser()
        rows = parser.parse(self._make_csv(csv_content))
        assert len(rows) == 1

    def test_column_mapping(self):
        csv_content = (
            "PostedOn,Memo,Total\n"
            "01/04/2026,ADOBE CREATIVE CLOUD,-59.99\n"
        )
        parser = CsvParser()
        rows = parser.parse(
            self._make_csv(csv_content),
            column_mapping={
                "date_col": "PostedOn",
                "description_col": "Memo",
                "amount_col": "Total",
            },
        )
        assert len(rows) == 1
        assert rows[0].raw_description == "ADOBE CREATIVE CLOUD"
