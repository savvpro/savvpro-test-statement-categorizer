"""Unit tests for CSV reader with messy bank formats."""
from __future__ import annotations

import pytest

from app.ingest.csv_reader import parse_csv


def _csv(text: str, delimiter: str = ",") -> bytes:
    return text.encode("utf-8")


def test_basic_csv() -> None:
    data = _csv(
        "Date,Description,Amount\n"
        "01/15/2026,ADOBE CREATIVE CLOUD,-54.99\n"
        "01/16/2026,STARBUCKS,-8.50\n"
    )
    result = parse_csv(data, "utf-8", ",")
    assert len(result.rows) == 2
    assert result.rows[0]["amount_cents"] == -5499
    assert result.rows[0]["description_raw"] == "ADOBE CREATIVE CLOUD"
    assert result.rows[1]["amount_cents"] == -850


def test_debit_credit_columns() -> None:
    data = _csv(
        "Date,Payee,Debit,Credit\n"
        "01/15/2026,STRIPE TRANSFER,,320.00\n"
        "01/16/2026,ADOBE,-54.99,\n"
    )
    result = parse_csv(data, "utf-8", ",")
    assert len(result.rows) == 2
    assert result.rows[0]["amount_cents"] == 32000   # income (credit)
    assert result.rows[1]["amount_cents"] == -5499   # expense (debit)


def test_preamble_rows_skipped() -> None:
    """Bank preamble lines before header should be ignored."""
    data = _csv(
        "Northwind Bank Statement Export\n"
        "Account: Business Checking ****4892\n"
        "Period: Jan 2026\n"
        "\n"
        "Date,Description,Amount\n"
        "01/15/2026,FIGMA,-15.00\n"
    )
    result = parse_csv(data, "utf-8", ",")
    assert len(result.rows) == 1
    assert result.rows[0]["description_raw"] == "FIGMA"


def test_blank_rows_skipped() -> None:
    data = _csv(
        "Date,Description,Amount\n"
        "01/15/2026,FIGMA,-15.00\n"
        ",,\n"
        "01/16/2026,GITHUB,-4.00\n"
    )
    result = parse_csv(data, "utf-8", ",")
    assert len(result.rows) == 2
    assert len(result.skipped) == 1
    assert "Blank" in result.skipped[0].reason


def test_malformed_date_skipped() -> None:
    data = _csv(
        "Date,Description,Amount\n"
        "BAD-DATE,FIGMA,-15.00\n"
        "01/16/2026,GITHUB,-4.00\n"
    )
    result = parse_csv(data, "utf-8", ",")
    assert len(result.rows) == 1
    assert len(result.skipped) == 1
    assert "date" in result.skipped[0].reason.lower()


def test_balance_row_skipped() -> None:
    data = _csv(
        "Date,Description,Amount\n"
        "01/15/2026,FIGMA,-15.00\n"
        "01/31/2026,Closing Balance,10000.00\n"
    )
    result = parse_csv(data, "utf-8", ",")
    assert len(result.rows) == 1
    assert len(result.skipped) == 1


def test_parentheses_amount() -> None:
    data = _csv(
        "Date,Description,Amount\n"
        "01/15/2026,SOME CHARGE,(54.99)\n"
    )
    result = parse_csv(data, "utf-8", ",")
    assert result.rows[0]["amount_cents"] == -5499


def test_tab_delimiter() -> None:
    data = b"Date\tDescription\tAmount\n01/15/2026\tFIGMA\t-15.00\n"
    result = parse_csv(data, "utf-8", "\t")
    assert len(result.rows) == 1


def test_dollar_sign_amount() -> None:
    """$ prefix should be stripped; sign stays as-is (-$15.00 → -1500)."""
    data = _csv(
        "Date,Description,Amount\n"
        "01/15/2026,FIGMA,-$15.00\n"
    )
    result = parse_csv(data, "utf-8", ",")
    assert result.rows[0]["amount_cents"] == -1500


def test_sign_inversion_detected() -> None:
    """Credit card exports where ALL purchases appear positive are auto-flipped.

    Requires 5+ rows to trigger auto-detection.
    """
    rows = "\n".join(
        f"01/{i:02d}/2026,PURCHASE {i},{float(i) * 10:.2f}" for i in range(1, 8)
    )
    data = _csv(f"Date,Description,Amount\n{rows}\n")
    result = parse_csv(data, "utf-8", ",")
    # All rows were positive → inverted → should all be negative now
    for r in result.rows:
        assert r["amount_cents"] < 0, f"Expected negative, got {r['amount_cents']}"


def test_forced_inversion() -> None:
    data = _csv(
        "Date,Description,Amount\n"
        "01/15/2026,ADOBE,54.99\n"
    )
    result = parse_csv(data, "utf-8", ",", invert_sign=True)
    assert result.rows[0]["amount_cents"] == -5499


@pytest.mark.parametrize(
    "name",
    ["northwind_bank_checking.csv", "contoso_card.csv", "fabrikam_cu_debit_credit.csv"],
)
def test_sample_files_parse(name: str) -> None:
    from pathlib import Path

    path = Path(__file__).resolve().parents[4] / "sample_data" / name
    result = parse_csv(path.read_bytes(), "utf-8", ",")
    assert len(result.rows) == 30
    assert result.skipped == []
