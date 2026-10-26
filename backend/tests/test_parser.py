import csv
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from app.ingest.formats import IngestError, UnsupportedFormatError
from app.ingest.parser import parse

SAMPLE_DIR = Path(__file__).resolve().parents[2] / "sample_data"
CLEAN_FILES = ["bank_a_card.csv", "bank_b_checking.csv"]
ALL_FILES = [*CLEAN_FILES, "messy_statement.csv"]
EXPECTED_PROFILE = {
    "bank_a_card.csv": "bank_a_card",
    "bank_b_checking.csv": "bank_b_checking",
    "messy_statement.csv": "bank_a_card",
}


def load_labels() -> list[dict[str, str]]:
    with (SAMPLE_DIR / "expected_labels.csv").open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def parse_sample(name: str):
    return parse((SAMPLE_DIR / name).read_bytes())


@pytest.mark.parametrize("name", ALL_FILES)
def test_profile_detected(name: str) -> None:
    assert parse_sample(name).profile_name == EXPECTED_PROFILE[name]


@pytest.mark.parametrize("name", ALL_FILES)
def test_every_physical_line_is_accounted_for(name: str) -> None:
    result = parse_sample(name)
    line_count = len((SAMPLE_DIR / name).read_text(encoding="utf-8").splitlines()) - 1
    numbers = (
        [r.row_number for r in result.rows]
        + [e.row_number for e in result.errors]
        + result.skipped
    )
    assert sorted(numbers) == list(range(1, line_count + 1))


@pytest.mark.parametrize("label", load_labels(), ids=lambda r: f"{r['file']}:{r['row_number']}")
def test_row_matches_expected_label(label: dict[str, str]) -> None:
    result = parse_sample(label["file"])
    n = int(label["row_number"])
    rows = {r.row_number: r for r in result.rows}
    errors = {e.row_number: e for e in result.errors}
    category, kind = label["expected_category"], label["expected_kind"]

    if category == "PARSE_ERROR":
        assert n in errors and n not in rows and n not in result.skipped
        assert errors[n].reason
    elif category == "SKIPPED":
        assert n in result.skipped and n not in rows and n not in errors
    else:
        assert n in rows, f"row {n} should parse but got: {errors.get(n)}"
        assert n not in errors and n not in result.skipped
        if kind in {"expense", "fee", "tax"}:
            assert rows[n].amount < 0
        elif kind == "income":
            assert rows[n].amount > 0


def test_clean_files_have_no_errors_or_skips() -> None:
    for name in CLEAN_FILES:
        result = parse_sample(name)
        assert result.errors == [] and result.skipped == []


def test_bank_a_values() -> None:
    first = parse_sample("bank_a_card.csv").rows[0]
    assert first.row_number == 1
    assert first.date == date(2026, 9, 1)
    assert first.raw_description == "ADOBE CREATIVE CLOUD SAN JOSE CA"
    assert first.amount == Decimal("-59.99")
    assert first.currency == "USD"
    assert first.account_type == "card"


def test_bank_b_debit_credit_signs_and_currency() -> None:
    rows = {r.row_number: r for r in parse_sample("bank_b_checking.csv").rows}
    assert rows[1].amount == Decimal("285400.00") and rows[1].date == date(2026, 9, 1)
    assert rows[2].amount == Decimal("-100000.00")
    assert all(r.currency == "PKR" for r in rows.values())
    assert all(r.account_type == "bank" for r in rows.values())


def test_messy_values_and_reasons() -> None:
    result = parse_sample("messy_statement.csv")
    rows = {r.row_number: r for r in result.rows}
    errors = {e.row_number: e for e in result.errors}
    assert result.skipped == [3]
    assert rows[6].amount == Decimal("-45.00")  # "(45.00)"
    assert rows[7].amount == Decimal("500")  # "Rs 500"
    assert rows[8].amount == Decimal("-12.99")  # "-$12.99"
    assert rows[14].amount == Decimal("185000.00")  # "185,000.00"
    assert "expected 4 columns, got 5" in errors[12].reason
    assert "date" in errors[5].reason and "date" in errors[15].reason
    assert errors[4].raw_line == "2026-09-04,DIGITALOCEAN.COM NEW YORK NY,,USD"
    # duplicates are not detected at this stage
    assert 10 in rows and 11 in rows


def test_raw_description_is_untouched() -> None:
    rows = {r.row_number: r for r in parse_sample("messy_statement.csv").rows}
    assert rows[1].raw_description == "  github inc   san francisco ca "
    assert rows[9].raw_description == "UBER   *TRIP    HELP.UBER.COM"
    assert rows[13].raw_description == "  XYZ TRADERS 4471 RAWALPINDI  "


def test_unknown_header_lists_supported_formats() -> None:
    with pytest.raises(UnsupportedFormatError) as exc:
        parse(b"When,What,How much\n2026-09-01,X,-1\n")
    message = str(exc.value)
    assert "bank_a_card" in message and "bank_b_checking" in message
    assert "Date,Description,Amount,Currency" in message


@pytest.mark.parametrize("content", [b"", b"\n"])
def test_empty_or_headerless_file(content: bytes) -> None:
    with pytest.raises(IngestError):
        parse(content)


def test_invalid_utf8_rejected() -> None:
    with pytest.raises(IngestError, match="UTF-8"):
        parse(b"Date,Description,Amount,Currency\n2026-09-01,\xff\xfe,-1,USD\n")


HEADER = "Date,Description,Amount,Currency\n"


def test_bom_and_crlf_handled() -> None:
    data = ("﻿" + HEADER.replace("\n", "\r\n") + "2026-09-01,GITHUB,-4.00,USD\r\n").encode()
    result = parse(data)
    assert result.profile_name == "bank_a_card"
    assert [r.row_number for r in result.rows] == [1]


def test_header_may_be_reordered() -> None:
    result = parse(b"Currency,Amount,Description,Date\nUSD,-4.00,GITHUB,2026-09-01\n")
    assert result.rows[0].amount == Decimal("-4.00")
    assert result.rows[0].date == date(2026, 9, 1)


def test_quoted_description_with_comma() -> None:
    result = parse((HEADER + '2026-09-01,"ACME, INC",-4.00,USD\n').encode())
    assert result.rows[0].raw_description == "ACME, INC"


@pytest.mark.parametrize(
    "line",
    [
        "2026-9-1,GITHUB,-4.00,USD",  # not zero-padded
        "01/09/2026,GITHUB,-4.00,USD",  # wrong format for this file
        "2026-02-30,GITHUB,-4.00,USD",  # impossible date
        ",GITHUB,-4.00,USD",  # missing date
        "2026-09-01,GITHUB,-4.00,",  # missing currency
        "2026-09-01,   ,-4.00,USD",  # empty description
        "2026-09-01,GITHUB,abc,USD",  # non-numeric amount
        '2026-09-01,"GITHUB,-4.00,USD',  # unbalanced quote
        "2026-09-01,GITHUB,-4.00",  # too few columns
    ],
)
def test_bad_bank_a_lines_become_errors(line: str) -> None:
    result = parse((HEADER + line + "\n").encode())
    assert result.rows == [] and result.skipped == []
    assert [e.row_number for e in result.errors] == [1]
    assert result.errors[0].raw_line == line


B_HEADER = "Txn Date,Details,Debit,Credit,Balance\n"


@pytest.mark.parametrize(
    ("line", "fragment"),
    [
        ("01/09/2026,X,,,100.00", "neither"),
        ("01/09/2026,X,5.00,5.00,100.00", "both"),
        ("01/09/2026,X,-5.00,,100.00", "negative"),
        ("01/09/2026,X,,(5.00),100.00", "negative"),
        ("2026-09-01,X,5.00,,100.00", "date"),
        ("01/09/2026,X,5.00,,100.00,extra", "expected 5 columns, got 6"),
    ],
)
def test_bad_bank_b_lines_become_errors(line: str, fragment: str) -> None:
    result = parse((B_HEADER + line + "\n").encode())
    assert result.rows == []
    assert fragment in result.errors[0].reason


def test_whitespace_only_line_is_skipped_and_counted() -> None:
    result = parse((HEADER + "\n   \n2026-09-01,GITHUB,-4.00,USD\n").encode())
    assert result.skipped == [1, 2]
    assert [r.row_number for r in result.rows] == [3]


def test_amount_with_more_than_two_decimals_is_an_error_not_a_rounding() -> None:
    result = parse((HEADER + "2026-09-01,GITHUB,-4.005,USD\n").encode())
    assert result.rows == []
    assert "decimal places" in result.errors[0].reason
