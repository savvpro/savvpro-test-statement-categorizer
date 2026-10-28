from decimal import Decimal

import pytest

from app.ingest.parsing import StatementError, parse_amount, parse_csv, parse_date


@pytest.mark.parametrize(
    "text,expected",
    [
        ("$1,234.56", "1234.56"),
        ("-12.00", "-12.00"),
        ("(45.10)", "-45.10"),
        ("12.34-", "-12.34"),
        ("99.00 CR", "99.00"),
        ("5.00 DR", "-5.00"),
        ("-$5", "-5"),
    ],
)
def test_parse_amount_formats(text, expected):
    assert parse_amount(text) == Decimal(expected)


def test_parse_amount_rejects_garbage():
    assert parse_amount("n/a") is None
    assert parse_amount("") is None


@pytest.mark.parametrize("text", ["2026-09-03", "09/03/2026", "09/03/26", "Sep 03, 2026", "03-Sep-2026"])
def test_parse_date_formats(text):
    assert parse_date(text).isoformat() == "2026-09-03"


def test_bank_file_with_preamble_total_and_bad_row(sample):
    result = parse_csv(sample("checking_bank_style.csv"))
    assert result.sign_mode == "bank"
    reasons = [s["reason"] for s in result.skipped]
    assert any("Unreadable date" in r for r in reasons)
    assert any("Summary line" in r for r in reasons)
    payout = result.transactions[0]
    assert payout.amount == Decimal("1284.50")  # money in stays positive


def test_card_file_flips_signs(sample):
    result = parse_csv(sample("credit_card_style.csv"))
    assert result.sign_mode == "card"
    by_desc = {t.description: t.amount for t in result.transactions}
    assert by_desc["TESLA SUPERCHARGER US"] < 0  # purchase becomes money out
    assert by_desc["PAYMENT THANK YOU-MOBILE"] > 0
    assert any(t.pending for t in result.transactions)


def test_autopay_bill_does_not_make_a_bank_file_look_like_a_card():
    csv = b"Date,Description,Amount\n09/01/2026,T-MOBILE AUTOPAY,-85.00\n09/02/2026,SHELL,-40.00\n"
    assert parse_csv(csv).sign_mode == "bank"


def test_debit_credit_columns(sample):
    result = parse_csv(sample("debit_credit_columns.csv"))
    amounts = {t.description: t.amount for t in result.transactions}
    assert amounts["INSTACART SHOPPER EARNINGS"] == Decimal("410.00")
    assert amounts["PEP BOYS 0912"] == Decimal("-149.00")  # "(149.00)" in the debit column is still money out


def test_sign_override():
    csv = b"Date,Description,Amount\n09/01/2026,SHELL,40.00\n"
    assert parse_csv(csv, sign="card").transactions[0].amount == Decimal("-40.00")


def test_zero_amount_rows_are_skipped():
    csv = b"Date,Description,Amount\n09/01/2026,HOLD,0.00\n09/02/2026,SHELL,-40.00\n"
    result = parse_csv(csv)
    assert len(result.transactions) == 1
    assert "Zero amount" in result.skipped[0]["reason"]


@pytest.mark.parametrize(
    "content,message",
    [
        (b"", "empty"),
        (b"Foo,Bar\n1,2\n", "header row"),
        (b"Date,Description\n09/01/2026,SHELL\n", "Amount"),
        (b"Date,Description,Amount\n", "No transactions"),
    ],
)
def test_unreadable_files_raise_clear_errors(content, message):
    with pytest.raises(StatementError, match=message):
        parse_csv(content)
