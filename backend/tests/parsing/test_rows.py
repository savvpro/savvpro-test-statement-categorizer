from decimal import Decimal

import pytest

from tests.parsing.helpers import JAN_5, parse_lines

HEADER = "Date,Description,Amount"


@pytest.mark.parametrize(
    "footer",
    [
        ",TOTAL,-30.00",
        "Total,,-30.00",
        "TOTALS:,,",
        ",Closing Balance,970.00",
        "01/31/2026,ENDING BALANCE,970.00",
        ",Balance Forward,1000.00",
        "01/01/2026,OPENING BALANCE,1000.00",
    ],
)
def test_summary_rows_skipped_with_warning(footer: str) -> None:
    result = parse_lines(HEADER, "01/05/2026,FAKE VENDOR,-30.00", footer)

    assert len(result.rows) == 1
    assert result.errors == []
    assert len(result.warnings) == 1
    assert result.warnings[0].startswith("line 3: skipped summary row")


def test_dated_merchant_named_total_is_kept() -> None:
    result = parse_lines(HEADER, "01/05/2026,TOTAL WINE & MORE 123,-42.00")

    assert [r.description for r in result.rows] == ["TOTAL WINE & MORE 123"]
    assert result.warnings == []


def test_blank_rows_skipped_silently() -> None:
    result = parse_lines(HEADER, "", "01/05/2026,FAKE VENDOR,-1.00", ",,", "   ", "")

    assert len(result.rows) == 1
    assert result.errors == [] and result.warnings == []


def test_bad_rows_become_errors_with_line_numbers() -> None:
    result = parse_lines(
        HEADER,
        "01/05/2026,GOOD ONE,-1.00",
        "31/02/2026x,BAD DATE,-1.00",
        "01/06/2026,BAD AMOUNT,12.3.4",
        "01/07/2026,NO AMOUNT,",
        "01/08/2026,,-1.00",
        "01/09/2026,GOOD TWO,-2.00",
    )

    assert [r.description for r in result.rows] == ["GOOD ONE", "GOOD TWO"]
    assert [(e.line_no, e.reason) for e in result.errors] == [
        (3, "unrecognized date '31/02/2026x'"),
        (4, "invalid amount '12.3.4'"),
        (5, "missing amount"),
        (6, "missing description"),
    ]
    assert result.errors[1].raw == {
        "Date": "01/06/2026",
        "Description": "BAD AMOUNT",
        "Amount": "12.3.4",
    }


def test_row_index_is_sequential_over_parsed_rows() -> None:
    result = parse_lines(HEADER, "01/05/2026,A,-1", "bad,B,-1", "01/06/2026,C,-1")

    assert [r.row_index for r in result.rows] == [0, 1]


def test_pending_from_status_column() -> None:
    result = parse_lines(
        "Date,Description,Amount,Status",
        "01/05/2026,FAKE VENDOR,-1.00,Pending",
        "01/06/2026,FAKE VENDOR,-1.00,Posted",
    )

    assert [r.is_pending for r in result.rows] == [True, False]


def test_pending_from_description_prefix() -> None:
    result = parse_lines(
        HEADER, "01/05/2026,PENDING - UBER *TRIP,-12.00", "01/06/2026,PENDINGTON CO,-1"
    )

    assert result.rows[0].is_pending
    assert result.rows[0].description == "UBER *TRIP"
    assert result.rows[0].raw["Description"] == "PENDING - UBER *TRIP"
    assert not result.rows[1].is_pending


def test_whitespace_stripped() -> None:
    result = parse_lines(" Date , Description , Amount ", "  01/05/2026 ,  FAKE VENDOR  , -1.00 ")

    row = result.rows[0]
    assert (row.date, row.description, row.amount) == (JAN_5, "FAKE VENDOR", Decimal("-1.00"))
    assert row.raw["Description"] == "FAKE VENDOR"


def test_day_first_column() -> None:
    result = parse_lines(HEADER, "05/01/2026,A,-1", "25/01/2026,B,-1")

    assert result.detected.date_order == "day_first"
    assert result.rows[0].date == JAN_5


def test_extra_cells_beyond_header_kept() -> None:
    result = parse_lines(HEADER, "01/05/2026,FAKE,-1.00,surprise")

    assert result.rows[0].raw["column_4"] == "surprise"
