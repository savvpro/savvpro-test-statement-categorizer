import pytest

from app.core.errors import ParseError, UnsupportedFileType
from app.domain.enums import SourceFormat
from app.ingest.detect import decode_text, detect_format
from tests.factories import OFX_V1, bank_csv


def test_csv_detected() -> None:
    fmt, warnings = detect_format(bank_csv().encode(), "a.csv")
    assert fmt is SourceFormat.CSV
    assert warnings == []


@pytest.mark.parametrize("name", ["a.ofx", "a.QFX"])
def test_ofx_detected(name: str) -> None:
    assert detect_format(OFX_V1.encode(), name)[0] is SourceFormat.OFX


def test_P21_csv_extension_with_ofx_content_warns() -> None:
    fmt, warnings = detect_format(OFX_V1.encode(), "statement.csv")
    assert fmt is SourceFormat.OFX
    assert [w.code for w in warnings] == ["EXTENSION_MISMATCH"]


@pytest.mark.parametrize("name", ["a.exe", "a.pdf", "a", "a.xlsx"])
def test_extension_allowlist(name: str) -> None:
    with pytest.raises(UnsupportedFileType):
        detect_format(b"Date,Description,Amount\n", name)


@pytest.mark.parametrize(
    "magic", [b"MZ\x90\x00", b"%PDF-1.7 ", b"PK\x03\x04", b"\x89PNG\r\n", b"\x7fELF"]
)
def test_S02_S03_binary_magic_rejected(magic: bytes) -> None:
    with pytest.raises(UnsupportedFileType):
        detect_format(magic + b"Date,Description,Amount\n", "a.csv")


def test_nul_bytes_rejected() -> None:
    with pytest.raises(UnsupportedFileType):
        detect_format(b"Date,Desc\x00ription\n", "a.csv")


def test_empty_file_is_422() -> None:
    with pytest.raises(ParseError):
        detect_format(b"   \n", "a.csv")


def test_P01_bom_is_stripped_without_warning() -> None:
    text, warnings = decode_text(b"\xef\xbb\xbfDate,Description\r\n1,2\r\n")
    assert text.startswith("Date")
    assert "\r" not in text
    assert warnings == []


def test_P02_cp1252_decodes_with_warning() -> None:
    text, warnings = decode_text("Café ’s".encode("cp1252"))
    assert "Café" in text
    assert [w.code for w in warnings] == ["ENCODING_FALLBACK"]


def test_latin1_last_resort() -> None:
    text, warnings = decode_text(b"abc \x81 def")
    assert text.startswith("abc")
    assert warnings[0].code == "ENCODING_FALLBACK"


def test_P22_crlf_and_cr_normalised() -> None:
    text, _ = decode_text(b"a\r\nb\rc\n")
    assert text == "a\nb\nc\n"
