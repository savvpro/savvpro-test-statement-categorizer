import pytest
from app.parsing import ParseError, parse_amount, parse_date, parse_statement


def test_amount_formats():
    assert parse_amount("$1,234.50") == 1234.5
    assert parse_amount("(45.00)") == -45.0
    assert parse_amount("-3") == -3.0


def test_date_formats():
    assert parse_date("09/05/2026") == "2026-09-05"
    assert parse_date("2026-09-05") == "2026-09-05"
    with pytest.raises(ValueError):
        parse_date("garbage")


def test_debit_credit_columns():
    rows, _ = parse_statement("Date,Details,Debit,Credit\n2026-01-02,GITHUB,4.00,\n2026-01-03,CLIENT DEPOSIT,,100\n")
    assert [r.amount for r in rows] == [-4.0, 100.0]


def test_spending_positive_file_is_flipped():
    csv_text = "Date,Description,Amount\n2026-01-02,GITHUB,4.00\n2026-01-03,AUTOPAY PAYMENT THANK YOU,-4.00\n"
    rows, warnings = parse_statement(csv_text)
    assert rows[0].amount == -4.0 and any("flipped" in w for w in warnings)


def test_bad_rows_skipped_with_warning():
    rows, warnings = parse_statement("Date,Description,Amount\nnot-a-date,X,1\n2026-01-02,GITHUB,-4\n")
    assert len(rows) == 1 and len(warnings) >= 1


def test_missing_columns():
    with pytest.raises(ParseError):
        parse_statement("foo,bar\n1,2\n")
