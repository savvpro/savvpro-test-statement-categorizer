from decimal import Decimal

import pytest

from app.parser import StatementError, parse_amount, parse_statement


@pytest.mark.parametrize(
    "text,expected",
    [
        ("12.50", "12.50"),
        ("-12.50", "-12.50"),
        ("(45.00)", "-45.00"),
        ("$1,234.56", "1234.56"),
        ("-$1,234.56", "-1234.56"),
        ("45.00 DR", "-45.00"),
        ("45.00 CR", "45.00"),
        ("−10.00", "-10.00"),
    ],
)
def test_parse_amount_formats(text, expected):
    assert parse_amount(text) == Decimal(expected)


@pytest.mark.parametrize("text", ["", "abc", "NaN", "1.2.3"])
def test_parse_amount_rejects_garbage(text):
    with pytest.raises(ValueError):
        parse_amount(text)


def csv_bytes(*lines):
    return "\n".join(lines).encode()


def test_basic_parse_and_bad_rows_are_reported_not_guessed():
    result = parse_statement(
        csv_bytes(
            "Date,Description,Amount",
            "2024-03-01,ADOBE,-10.00",
            "not a date,FOO,-1.00",
            "2024-03-02,BAR,abc",
            "2024-03-03,,-5.00",
            "2024-03-04,ZERO,0.00",
            "2024-03-05,TOTAL,-99.00",
            ",,",
        )
    )
    assert len(result.transactions) == 1
    assert [i.line for i in result.issues] == [3, 4, 5, 6, 7]


def test_debit_credit_columns():
    result = parse_statement(
        csv_bytes(
            "Posted Date,Details,Debit,Credit",
            "2024-03-01,COFFEE,4.00,",
            "2024-03-02,CLIENT,,100.00",
            "2024-03-03,BOTH,1.00,2.00",
        )
    )
    assert [t.amount for t in result.transactions] == [Decimal("-4.00"), Decimal("100.00")]
    assert len(result.issues) == 1


def test_positive_is_charge_flips_signs():
    result = parse_statement(
        csv_bytes("Date,Description,Amount", "2024-03-01,ADOBE,10.00", "2024-03-02,REFUND,-10.00"), True
    )
    assert [t.amount for t in result.transactions] == [Decimal("-10.00"), Decimal("10.00")]


def test_day_first_dates_detected_from_whole_file():
    result = parse_statement(csv_bytes("Date,Description,Amount", "25/03/2024,A,-1", "03/04/2024,B,-1"))
    assert result.transactions[1].date.isoformat() == "2024-04-03"
    assert not result.warnings


def test_ambiguous_dates_warn():
    result = parse_statement(csv_bytes("Date,Description,Amount", "03/04/2024,A,-1"))
    assert result.transactions[0].date.isoformat() == "2024-03-04"
    assert result.warnings


def test_missing_columns_rejected():
    with pytest.raises(StatementError):
        parse_statement(csv_bytes("Foo,Bar", "1,2"))


def test_empty_file_rejected():
    with pytest.raises(StatementError):
        parse_statement(b"")


def test_handles_bom_and_latin1():
    data = "﻿Date,Description,Amount\n2024-03-01,CAFÉ X,-3.00".encode("utf-8")
    assert parse_statement(data).transactions[0].description == "CAFÉ X"
    latin = "Date,Description,Amount\n2024-03-01,CAFÉ X,-3.00".encode("cp1252")
    assert parse_statement(latin).transactions[0].description == "CAFÉ X"


def test_warns_when_sign_convention_looks_wrong():
    lines = ["Date,Description,Amount"] + [f"2024-03-0{d},SHOP,{d}.00" for d in range(1, 7)]
    wrong = parse_statement(csv_bytes(*lines))
    assert any("tick" in w for w in wrong.warnings)
    fixed = parse_statement(csv_bytes(*lines), True)
    assert not fixed.warnings


def test_warns_to_untick_when_flip_was_unneeded():
    lines = ["Date,Description,Amount"] + [f"2024-03-0{d},SHOP,-{d}.00" for d in range(1, 7)]
    assert any("Untick" in w for w in parse_statement(csv_bytes(*lines), True).warnings)
