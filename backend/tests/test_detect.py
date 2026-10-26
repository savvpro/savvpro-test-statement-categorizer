import pytest

from app.domain.models import SourceFormat
from app.errors import FileProblem
from app.parsing.detect import detect_format
from tests.factories import (
    CARD_ROWS,
    OFX_SAMPLE,
    csv_bytes,
    pdf_text_bytes,
    xlsx_bytes,
)


def test_honest_extensions_give_no_warning():
    assert detect_format("a.csv", csv_bytes(CARD_ROWS)) == (SourceFormat.CSV, [])
    assert detect_format("a.ofx", OFX_SAMPLE)[0] is SourceFormat.OFX
    assert detect_format("a.qfx", OFX_SAMPLE)[0] is SourceFormat.OFX
    assert detect_format("a.xlsx", xlsx_bytes({"S": [["Date"]]}))[0] is SourceFormat.XLSX
    assert detect_format("a.pdf", pdf_text_bytes(["hello"]))[0] is SourceFormat.PDF


@pytest.mark.parametrize(
    ("name", "data", "expected"),
    [
        ("statement.csv", pdf_text_bytes(["03/01/2026 ADOBE 54.99"]), SourceFormat.PDF),
        ("statement.pdf", csv_bytes(CARD_ROWS), SourceFormat.CSV),
        ("statement.txt", OFX_SAMPLE, SourceFormat.OFX),
        ("statement.csv", xlsx_bytes({"S": [["Date"]]}), SourceFormat.XLSX),
    ],
)
def test_content_beats_extension_with_a_warning(name, data, expected):
    fmt, warnings = detect_format(name, data)
    assert fmt is expected
    assert len(warnings) == 1 and "looks like" in warnings[0]


def test_extension_is_case_insensitive_and_path_safe():
    assert (
        detect_format("C:\\Users\\me\\STATEMENT.CSV", csv_bytes(CARD_ROWS))[0] is SourceFormat.CSV
    )


@pytest.mark.parametrize("data", [b"", b"   \n  ", b"\n\n"])
def test_empty_files(data):
    with pytest.raises(FileProblem) as info:
        detect_format("a.csv", data)
    assert info.value.code == "empty_file"


@pytest.mark.parametrize(
    "name", ["malware.exe", "notes.docx", "archive.zip", "noextension", "a.csv.exe"]
)
def test_unsupported_extensions(name):
    with pytest.raises(FileProblem) as info:
        detect_format(name, b"hello,world")
    assert info.value.code == "unsupported_format"
    assert info.value.status_code == 415


def test_legacy_xls_is_explained():
    with pytest.raises(FileProblem) as info:
        detect_format("old.csv", b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"0" * 50)
    assert info.value.code == "unsupported_format"
    assert ".xlsx" in info.value.message


def test_non_excel_zip_is_rejected():
    import io
    import zipfile

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("word/document.xml", "<x/>")
    with pytest.raises(FileProblem) as info:
        detect_format("a.xlsx", buffer.getvalue())
    assert info.value.code == "unsupported_format"


def test_binary_garbage_is_rejected():
    with pytest.raises(FileProblem) as info:
        detect_format("a.csv", b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"\x00" * 100)
    assert info.value.code == "unsupported_format"
