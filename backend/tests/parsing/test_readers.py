import datetime as dt
import random
import zipfile
from decimal import Decimal
from io import BytesIO

import pytest

from app.brain.models import AccountType
from app.parsing import (
    MAX_ROWS,
    EmptyFileError,
    HeaderNotFoundError,
    TooManyRowsError,
    UnsupportedFileError,
    parse_statement,
)
from tests.parsing.helpers import JAN_5, csv_bytes, xlsx_bytes

CHECKING = AccountType.checking


def parse(content: bytes, filename: str = "test.csv"):  # type: ignore[no-untyped-def]
    return parse_statement(content, filename, CHECKING)


@pytest.mark.parametrize("delimiter", [",", ";", "\t", "|"])
def test_delimiter_sniffed(delimiter: str) -> None:
    lines = ["Date", "Description", "Amount"], ["01/05/2026", "FAKE VENDOR", "-10.00"]
    result = parse(csv_bytes(*(delimiter.join(cells) for cells in lines)))

    assert result.detected.delimiter == delimiter
    assert result.rows[0].amount == Decimal("-10.00")


def test_quoted_thousands_do_not_confuse_sniffer() -> None:
    result = parse(csv_bytes("Date,Description,Amount", '01/05/2026,"FAKE, INC","1,234.56"'))

    assert result.detected.delimiter == ","
    assert result.rows[0].description == "FAKE, INC"
    assert result.rows[0].amount == Decimal("1234.56")


def test_utf8_bom() -> None:
    content = b"\xef\xbb\xbf" + csv_bytes(
        "Date;Description;Amount", "01/05/2026;CAF\u00c9 FAKE;-4.50"
    )
    result = parse(content)

    assert result.detected.encoding == "utf-8-sig"
    assert result.detected.column_map["date"] == "Date"  # BOM not glued onto the header
    assert result.rows[0].description == "CAF\u00c9 FAKE"


def test_cp1252_fallback() -> None:
    content = csv_bytes(
        "Date,Description,Amount", "01/05/2026,CAF\u00c9 FAKE,-4.50", encoding="cp1252"
    )
    result = parse(content)

    assert result.detected.encoding == "cp1252"
    assert result.rows[0].description == "CAF\u00c9 FAKE"


def test_xlsx_cells_converted() -> None:
    content = xlsx_bytes(
        [
            ["Transaction Date", "Post Date", "Description", "Amount"],
            [dt.datetime(2026, 1, 5), dt.datetime(2026, 1, 6), "FAKE VENDOR", -59.99],
            [dt.date(2026, 1, 7), None, "FAKE CLIENT", 1200],
            ["01/08/2026", None, "TEXT CELLS", "-1.10"],
        ]
    )
    result = parse_statement(content, "card.xlsx", AccountType.credit_card, charges_positive=False)

    assert result.detected.file_type == "xlsx"
    assert result.detected.encoding is None and result.detected.delimiter is None
    assert result.detected.column_map["date"] == "Transaction Date"
    assert [r.date for r in result.rows] == [JAN_5, dt.date(2026, 1, 7), dt.date(2026, 1, 8)]
    assert [r.amount for r in result.rows] == [Decimal("-59.99"), Decimal("1200"), Decimal("-1.10")]
    assert result.rows[0].raw["Post Date"] == "2026-01-06"


def test_xlsx_detected_by_magic_not_extension() -> None:
    content = xlsx_bytes([["Date", "Description", "Amount"], ["2026-01-05", "FAKE", -1.0]])

    assert parse(content, "statement.csv").detected.file_type == "xlsx"


def test_random_binary_rejected() -> None:
    content = random.Random(0).randbytes(4096)

    with pytest.raises(UnsupportedFileError):
        parse(content, "statement.csv")


def test_legacy_xls_rejected() -> None:
    with pytest.raises(UnsupportedFileError, match="legacy"):
        parse(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 100, "old.xls")


def test_zip_that_is_not_a_workbook_rejected() -> None:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("hello.txt", "not a workbook")

    with pytest.raises(UnsupportedFileError, match="xlsx"):
        parse(buffer.getvalue(), "fake.xlsx")


@pytest.mark.parametrize("content", [b"", b"   \n\n  ", b"\xef\xbb\xbf"])
def test_empty_file(content: bytes) -> None:
    with pytest.raises(EmptyFileError):
        parse(content)


def test_header_only_is_empty() -> None:
    with pytest.raises(EmptyFileError, match="no transactions"):
        parse(csv_bytes("Date,Description,Amount", "", ",TOTAL,0.00"))


def test_no_header() -> None:
    with pytest.raises(HeaderNotFoundError):
        parse(csv_bytes("hello,world", "1,2"))


def test_too_many_rows() -> None:
    rows = [f"01/05/2026,FAKE {i},-1.00" for i in range(MAX_ROWS + 1)]

    with pytest.raises(TooManyRowsError, match="10,000"):
        parse(csv_bytes("Date,Description,Amount", *rows))


def test_exactly_max_rows_is_fine() -> None:
    rows = [f"01/05/2026,FAKE {i},-1.00" for i in range(MAX_ROWS)]

    assert len(parse(csv_bytes("Date,Description,Amount", *rows)).rows) == MAX_ROWS
