import csv
import io
from datetime import date

import pytest

from app.core.security import csv_escape, safe_download_stem, sanitize_filename
from app.db.models import TransactionRow
from app.services.export import COLUMNS, export_csv

OWASP = [
    "=cmd|' /C calc'!A0",
    "+1+1",
    "-2+3",
    "@SUM(1+1)",
    "\t=1+1",
    "\r=1+1",
    '=HYPERLINK("http://evil","x")',
    "  =1+1",
    "%0A=1+1",
]


@pytest.mark.parametrize("payload", OWASP[:-1])
def test_S08_dangerous_prefixes_are_neutralised(payload: str) -> None:
    assert csv_escape(payload).startswith("'")


def test_safe_values_untouched() -> None:
    assert csv_escape("HOME DEPOT") == "HOME DEPOT"
    assert csv_escape("") == ""


def _row(description: str, reasons: list[str] | None = None) -> TransactionRow:
    return TransactionRow(
        id="1",
        statement_id="s",
        row_index=1,
        posted_date=date(2026, 1, 5),
        amount_cents=-4500,
        direction="outflow",
        description=description,
        merchant_key="X",
        fingerprint="f",
        category="REPAIRS",
        status="auto",
        confidence=0.9,
        reasons=reasons or ["ok"],
        flags=["RECURRING"],
    )


def test_S08_export_escapes_every_text_cell_and_keeps_amount_numeric() -> None:
    rows = [_row(p, [p]) for p in OWASP]
    parsed = list(csv.reader(io.StringIO(export_csv(rows), newline="")))
    assert tuple(parsed[0]) == COLUMNS
    for out in parsed[1:]:
        assert out[2] == "-45.00"
        assert out[3] == "REPAIRS"
        assert out[4] == "Repairs"
        assert out[5] == "14"
        for cell in (out[1], out[9]):
            assert cell[:1] not in {"=", "+", "-", "@", "\t", "\r"}


def test_export_quotes_commas_and_newlines_via_csv_writer() -> None:
    text = export_csv([_row('a, "b"\nc')])
    assert list(csv.reader(io.StringIO(text, newline="")))[1][1] == 'a, "b"\nc'


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("../../etc/passwd.csv", "passwd.csv"),
        ("..\\..\\win\\x.csv", "x.csv"),
        ("a\x00b\x1f.csv", "ab.csv"),
        ("", "upload"),
        ("..", "upload"),
        (None, "upload"),
    ],
)
def test_S07_filename_sanitised(raw: str | None, expected: str) -> None:
    assert sanitize_filename(raw) == expected


def test_filename_capped_at_255() -> None:
    assert len(sanitize_filename("a" * 400 + ".csv")) == 255


def test_download_stem_is_header_safe() -> None:
    assert safe_download_stem('we"ird name\r\n.csv') == "we-ird-name"
    assert safe_download_stem("...csv") == "statement"
