from datetime import date

import pytest

from app.models.transaction import TransactionType
from app.services.parser import StatementParseError, StatementParser


def test_parse_standard_csv():
    csv_data = b"""Date,Description,Amount
2024-03-01,GITHUB INC,-19.00
2024-03-02,AWS SERVICES,-152.40
2024-03-03,STRIPE PAYOUT,2500.00
"""
    txs = StatementParser.parse_csv(csv_data)
    assert len(txs) == 3
    assert txs[0].date == date(2024, 3, 1)
    assert txs[0].description == "GITHUB INC"
    assert txs[0].amount == 19.00
    assert txs[0].transaction_type == TransactionType.DEBIT

    assert txs[2].description == "STRIPE PAYOUT"
    assert txs[2].amount == 2500.00
    assert txs[2].transaction_type == TransactionType.CREDIT


def test_parse_split_debit_credit_columns():
    csv_data = b"""Transaction Date,Details,Debit,Credit
01/15/2024,JETBRAINS IDE,149.00,
01/18/2024,CLIENT CONSULTING PAYMENT,,4500.00
"""
    txs = StatementParser.parse_csv(csv_data)
    assert len(txs) == 2
    assert txs[0].amount == 149.00
    assert txs[0].transaction_type == TransactionType.DEBIT
    assert txs[1].amount == 4500.00
    assert txs[1].transaction_type == TransactionType.CREDIT


def test_parse_with_bank_preamble_and_summary_footer():
    csv_data = b"""Acme Business Checking Statement
Account Number: *******1234
Statement Period: Jan 1 - Jan 31 2024

Date,Description,Amount
2024-01-10,VERCEL PRO,-20.00
2024-01-12,DIGITALOCEAN,-12.00

Total: $32.00
Ending Balance: $10,450.00
"""
    txs = StatementParser.parse_csv(csv_data)
    assert len(txs) == 2
    assert txs[0].description == "VERCEL PRO"
    assert txs[1].description == "DIGITALOCEAN"


def test_parse_semicolon_and_thousand_separators():
    csv_data = b"""Date;Description;Amount
15/02/2024;APPLE STORE;"-$1,299.00"
16/02/2024;STRIPE DEPOSIT;"$3,500.00"
"""
    txs = StatementParser.parse_csv(csv_data)
    assert len(txs) == 2
    assert txs[0].amount == 1299.00
    assert txs[0].transaction_type == TransactionType.DEBIT
    assert txs[1].amount == 3500.00
    assert txs[1].transaction_type == TransactionType.CREDIT


def test_parse_empty_file_error():
    with pytest.raises(StatementParseError) as exc_info:
        StatementParser.parse_csv(b"")
    assert "empty" in str(exc_info.value).lower()


def test_parse_missing_headers_error():
    with pytest.raises(StatementParseError) as exc_info:
        StatementParser.parse_csv(b"Foo,Bar,Baz\n1,2,3")
    assert "column headers" in str(exc_info.value).lower()
