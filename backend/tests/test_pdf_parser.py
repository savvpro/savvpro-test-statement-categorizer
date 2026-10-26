import pytest

from app.parsing import UnsupportedFile, clean_rows
from app.parsing.layout import Word, rows_from_pages
from app.parsing.ocr import ocr_available
from app.parsing.pdf_parser import parse_pdf
from app.parsing.rows import ParsedFile

from .conftest import SAMPLES


def test_text_pdf_sample():
    parsed = parse_pdf((SAMPLES / "pkr_statement_april.pdf").read_bytes())
    result = clean_rows(parsed)
    assert parsed.source_kind == "pdf"
    assert result.currency == "PKR"  # read from "Currency: PKR" in the page header
    assert len(result.rows) == 18 and result.errors == []
    descriptions = [r.description for r in result.rows]
    assert "HETZNER ONLINE GMBH SERVER RENTAL" in descriptions  # wrapped over two lines
    assert all(not r.flags for r in result.rows)  # every running balance checks out
    assert result.rows[-1].source_row.startswith("page 2")  # second page, repeated header


@pytest.mark.skipif(not ocr_available(), reason="Tesseract is not installed")
def test_scanned_pdf_sample_is_read_with_ocr():
    parsed = parse_pdf((SAMPLES / "pkr_statement_may_scanned.pdf").read_bytes())
    result = clean_rows(parsed)
    assert parsed.source_kind == "ocr"
    assert len(result.rows) == 10
    assert any("OCR" in note for note in result.warnings)


def test_damaged_pdf_gives_a_clear_error():
    with pytest.raises(UnsupportedFile, match="couldn't be opened"):
        parse_pdf(b"%PDF-1.4 this is not really a pdf")


# --- the same layout code, fed with word positions like tesseract returns ------

def line(y, *cells, conf=95.0):
    """cells are (text, x0, x1) in page-width units."""
    return [Word(text, x0, x1, y, y + 0.012, conf) for text, x0, x1 in cells]


HEADER = line(0.10, ("Date", 0.07, 0.12), ("Description", 0.19, 0.30), ("Debit", 0.61, 0.66),
              ("Credit", 0.73, 0.79), ("Balance", 0.87, 0.93))


OPENING = line(0.14, ("15/03/2026", 0.07, 0.16), ("Opening", 0.19, 0.25), ("Balance", 0.26, 0.32),
               ("1,000.00", 0.86, 0.93))


def ocr_page(*rows):
    return [w for row in (HEADER, *rows) for w in row]


def test_low_ocr_confidence_holds_the_row_for_review():
    page = ocr_page(
        OPENING,
        line(0.17, ("16/03/2026", 0.07, 0.16), ("GITHUB.COM", 0.19, 0.30), ("120.00", 0.61, 0.66),
             ("880.00", 0.88, 0.93), conf=52.0),
    )
    rows, has_balance = rows_from_pages([page])
    result = clean_rows(ParsedFile(rows, "ocr", has_balance, "PKR"))
    assert "wasn't sure" in result.rows[0].flags[0]


def test_ocr_misread_amount_is_caught_by_the_running_balance():
    page = ocr_page(
        OPENING,
        line(0.17, ("16/03/2026", 0.07, 0.16), ("GITHUB.COM", 0.19, 0.30), ("170.00", 0.61, 0.66),
             ("880.00", 0.88, 0.93)),
    )
    rows, has_balance = rows_from_pages([page])
    result = clean_rows(ParsedFile(rows, "ocr", has_balance, "PKR"))
    assert "running balance doesn't add up" in result.rows[0].flags[0]


def test_scan_without_balance_column_flags_every_row():
    header = line(0.10, ("Date", 0.07, 0.12), ("Description", 0.19, 0.30), ("Amount", 0.80, 0.86))
    row = line(0.14, ("16/03/2026", 0.07, 0.16), ("GITHUB.COM", 0.19, 0.30), ("-120.00", 0.79, 0.86))
    rows, has_balance = rows_from_pages([header + row])
    result = clean_rows(ParsedFile(rows, "ocr", has_balance, "PKR"))
    assert not has_balance
    assert "no balance column" in result.rows[0].flags[0]


def test_numbers_inside_the_description_stay_in_the_description():
    page = ocr_page(line(0.14, ("16/03/2026", 0.07, 0.16), ("JOES", 0.19, 0.23), ("CAFE", 0.24, 0.28),
                         ("9921", 0.29, 0.32), ("800.00", 0.61, 0.66)))
    rows, _ = rows_from_pages([page])
    assert rows[0].description == "JOES CAFE 9921"
    assert rows[0].debit_text == "800.00"
