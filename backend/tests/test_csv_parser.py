import pytest

from app.parsing import NeedsUserChoice, UnsupportedFile, clean_rows
from app.parsing.csv_parser import parse_csv


def clean(text, **choices):
    return clean_rows(parse_csv(text.encode()), **choices)


def test_bank_export_with_preamble_and_debit_credit_columns():
    result = clean(
        "Bank,Demo\nAccount,0000\n\n"
        "Date,Narration,Withdrawal,Deposit,Balance\n"
        "01/03/2026,Opening Balance,,,1000.00\n"
        "02/03/2026,GITHUB.COM,120.00,,880.00\n"
        "13/03/2026,UPWORK,,500.00,1380.00\n",
        currency_choice="PKR",
    )
    assert [r.amount for r in result.rows] == [-120, 500]
    assert result.skipped[0].reason.startswith("Balance or total line")
    assert result.rows[0].flags == []


def test_signed_amount_column_with_currency_column():
    result = clean("Transaction Date,Details,Amount,Currency\n2026-04-01,ADOBE,-54.99,USD\n")
    assert result.rows[0].amount < 0
    assert result.currency == "USD"


def test_type_column_marks_debits():
    result = clean("Date,Description,Amount,Dr/Cr\n2026-04-01,ADOBE,54.99,DR\n2026-04-02,UPWORK,100,CR\n",
                   currency_choice="USD")
    assert [str(r.amount) for r in result.rows] == ["-54.99", "100"]


def test_currency_in_header_brackets_is_used():
    result = clean("Date,Description,Debit (USD),Credit (USD)\n2026-04-01,ADOBE,54.99,\n")
    assert result.currency == "USD"


def test_missing_currency_asks_the_user():
    with pytest.raises(NeedsUserChoice, match="PKR or USD"):
        clean("Date,Description,Amount\n2026-04-01,ADOBE,-54.99\n")


def test_unreadable_rows_are_reported_not_dropped():
    result = clean(
        "Date,Description,Amount\n"
        "2026-04-01,ADOBE,-54.99\n"
        "2026-04-02,AWS,31.2O\n"
        "not a date,GITHUB,-10.00\n"
        "2026-04-04,,-3.00\n",
        currency_choice="USD",
    )
    assert len(result.rows) == 1
    assert [e.source_row for e in result.errors] == ["row 3", "row 4", "row 5"]
    assert "31.2O" in result.errors[0].reason


def test_row_with_both_debit_and_credit_is_an_error():
    result = clean("Date,Description,Debit,Credit\n2026-04-01,ODD ROW,5.00,6.00\n", currency_choice="PKR")
    assert "both a debit and a credit" in result.errors[0].reason


def test_newest_first_statements_are_put_in_date_order():
    result = clean(
        "Date,Description,Amount,Balance\n"
        "2026-04-03,B,-10.00,80.00\n"
        "2026-04-01,A,-10.00,90.00\n",
        currency_choice="USD",
    )
    assert [r.description for r in result.rows] == ["A", "B"]
    assert result.rows[1].flags == []  # 90 - 10 = 80 checks out once the order is right


def test_running_balance_mismatch_flags_the_row():
    result = clean(
        "Date,Description,Amount,Balance\n"
        "2026-04-01,A,-10.00,90.00\n"
        "2026-04-02,B,-10.00,75.00\n",
        currency_choice="USD",
    )
    assert "running balance doesn't add up" in result.rows[1].flags[0]


def test_repeated_row_in_one_file_is_flagged_not_deleted():
    line = "2026-04-01,FOODPANDA ORDER 5512,-2350.00\n"
    result = clean("Date,Description,Amount\n" + line + line, currency_choice="PKR")
    assert len(result.rows) == 2
    assert "duplicate" in result.rows[1].flags[0]


def test_ambiguous_dates_need_a_choice():
    with pytest.raises(NeedsUserChoice, match="day-first or month-first"):
        clean("Date,Description,Amount\n03/04/2026,A,-1\n", currency_choice="PKR")


def test_missing_columns_are_named():
    with pytest.raises(UnsupportedFile, match="header row"):
        parse_csv(b"When,What,How much\n2026-04-01,A,-1\n")
    with pytest.raises(UnsupportedFile, match="amount"):
        parse_csv(b"Date,Description,Notes\n2026-04-01,A,x\n")


def test_amount_and_debit_credit_together_is_refused():
    with pytest.raises(NeedsUserChoice):
        parse_csv(b"Date,Description,Amount,Debit,Credit\n2026-04-01,A,-1,1,\n")


def test_binary_file_named_csv_is_refused():
    with pytest.raises(UnsupportedFile):
        parse_csv(b"\x00\x01\x02 not text")
