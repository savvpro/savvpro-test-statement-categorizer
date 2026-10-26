from datetime import date
from decimal import Decimal

import pytest

from app.parser import parse_csv

HEADER = "Date,Description,Debit,Credit,Balance\n"


def test_sample_parses_without_errors(sample_text):
    result = parse_csv(sample_text)
    assert len(result.transactions) == 75
    assert result.errors == []


def test_credit_positive_debit_negative():
    result = parse_csv(
        HEADER
        + "01-09-2026,PAYONEER INC FUNDS TRF REF 88213,,385000,1227350\n"
        + "01-09-2026,RENT COWORKING - OFFICE HUB GULBERG LHR,35000,,1192350\n"
    )
    credit, debit = result.transactions
    assert credit.amount == Decimal(385000)
    assert debit.amount == Decimal(-35000)
    assert credit.date == date(2026, 9, 1)


def test_thousands_separators():
    result = parse_csv(
        HEADER + '02-09-2026,LESCO ONLINE BILL PAY 1234567890,"18,420.50",,"1,173,930"\n'
    )
    tx = result.transactions[0]
    assert tx.amount == Decimal("-18420.50")
    assert tx.balance == Decimal(1173930)


def test_bad_rows_reported_not_raised():
    result = parse_csv(
        HEADER
        + "32-13-2026,BAD DATE,100,,0\n"
        + "01-09-2026,BOTH CELLS,100,100,0\n"
        + "01-09-2026,NO AMOUNT,,,0\n"
        + "01-09-2026,NOT A NUMBER,abc,,0\n"
        + "01-09-2026,,100,,0\n"
        + "01-09-2026,NEGATIVE,-5,,0\n"
        + "01-09-2026,NAN,NaN,,0\n"
        + ",,,,\n"
        + "02-09-2026,SNGPL BILL PAYMENT,2150,,1171780\n"
    )
    assert [tx.description for tx in result.transactions] == ["SNGPL BILL PAYMENT"]
    assert len(result.errors) == 7


def test_empty_balance_is_none():
    assert (
        parse_csv(HEADER + "02-09-2026,SNGPL BILL PAYMENT,2150,,\n").transactions[0].balance is None
    )


def test_missing_column_raises():
    with pytest.raises(ValueError, match="Missing columns: balance"):
        parse_csv("Date,Description,Debit,Credit\n")


def test_bom_and_header_case():
    result = parse_csv(
        "﻿DATE,description,Debit,Credit,BALANCE\n02-09-2026,SNGPL BILL PAYMENT,2150,,1\n"
    )
    assert len(result.transactions) == 1
