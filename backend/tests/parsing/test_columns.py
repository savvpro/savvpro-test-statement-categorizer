import pytest

from app.parsing import HeaderNotFoundError
from app.parsing.columns import detect_header, map_columns
from app.parsing.readers import SourceRow
from tests.parsing.helpers import parse_lines


@pytest.mark.parametrize(
    ("header", "field"),
    [
        ("Date", "date"),
        ("Transaction Date", "date"),
        ("Trans. Date", "date"),
        ("Posted Date", "date"),
        ("POSTING DATE", "date"),
        ("Description", "description"),
        ("Transaction Description", "description"),
        ("Details", "description"),
        ("Merchant", "description"),
        ("Payee", "description"),
        ("Name", "description"),
        ("Amount", "amount"),
        ("Transaction Amount", "amount"),
        ("Debit", "debit"),
        ("Withdrawals", "debit"),
        ("Money Out", "debit"),
        ("Charges", "debit"),
        ("Credit", "credit"),
        ("Deposits", "credit"),
        ("Money In", "credit"),
        ("Payments", "credit"),
        ("Status", "status"),
        ("Type", "type"),
        ("Dr/Cr", "type"),
        ("  Amount ($) ", "amount"),  # punctuation and symbols are ignored
        ("Amt", None),  # abbreviations are not guessed
    ],
)
def test_synonyms(header: str, field: str | None) -> None:
    fields = map_columns([header])
    assert fields == ({field: 0} if field else {})


def test_matching_ignores_case_punctuation_and_spaces() -> None:
    assert map_columns(["  TRANSACTION   date: ", "Desc", "*Amount*"]) == {"date": 0, "amount": 2}


def test_transaction_date_beats_post_date() -> None:
    assert map_columns(["Post Date", "Transaction Date"])["date"] == 1
    assert map_columns(["Posting Date", "Date"])["date"] == 1


def test_header_found_below_junk_lines() -> None:
    rows = [
        SourceRow(1, ["Business Checking ****9876"]),
        SourceRow(2, ["Period", "Jan 2026", "Description"]),
        SourceRow(3, []),
        SourceRow(4, ["Date", "Description", "Amount", "Balance"]),
    ]
    header = detect_header(rows)

    assert header.position == 3
    assert header.line_no == 4
    assert header.describe() == {"date": "Date", "description": "Description", "amount": "Amount"}


def test_unmapped_columns_kept_in_raw() -> None:
    result = parse_lines(
        "Date,Description,Memo,Amount,Category,Balance",
        "01/05/2026,FAKE VENDOR,net 30,-10.00,Office,990.00",
    )

    assert result.rows[0].raw == {
        "Date": "01/05/2026",
        "Description": "FAKE VENDOR",
        "Memo": "net 30",
        "Amount": "-10.00",
        "Category": "Office",
        "Balance": "990.00",
    }


def test_header_not_found_lists_expected_names() -> None:
    with pytest.raises(HeaderNotFoundError) as info:
        parse_lines("when,what,how much", "01/05/2026,FAKE,1.00")

    message = str(info.value)
    for name in ['"date"', '"transaction date"', '"description"', '"amount"', '"debit"']:
        assert name in message


def test_header_needs_an_amount_column() -> None:
    with pytest.raises(HeaderNotFoundError):
        parse_lines("Date,Description,Debit", "01/05/2026,FAKE,1.00")


def test_header_beyond_scan_window_not_found() -> None:
    junk = [f"junk line {i}" for i in range(30)]
    with pytest.raises(HeaderNotFoundError, match="first 30 rows"):
        parse_lines(*junk, "Date,Description,Amount", "01/05/2026,FAKE,1.00")
