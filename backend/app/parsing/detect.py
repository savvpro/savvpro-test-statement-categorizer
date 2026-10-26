"""Work out what an uploaded file really is, whatever its name says."""

from __future__ import annotations

import io
import re
import zipfile
from pathlib import PurePath

from app.config import ACCEPTED_EXTENSIONS
from app.domain.models import SourceFormat
from app.errors import FileProblem

_EXPECTED_EXTENSIONS: dict[SourceFormat, tuple[str, ...]] = {
    SourceFormat.CSV: (".csv", ".tsv", ".txt"),
    SourceFormat.XLSX: (".xlsx",),
    SourceFormat.OFX: (".ofx", ".qfx"),
    SourceFormat.PDF: (".pdf",),
    SourceFormat.CAMT053: (".xml",),
    SourceFormat.MT940: (".sta", ".mt940", ".940", ".swi", ".dat", ".txt"),
}

_CAMT = re.compile(rb"camt\.05[234]|<bktocstmrstmt|<bktocstmrdbtcdtntfctn|<bktocstmracctrpt", re.I)
_MT940_TAGS = re.compile(rb"^:(?:20|25|28C?|60[FM]|61):", re.M)

_OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"


def extension_of(filename: str) -> str:
    return PurePath(filename.replace("\\", "/")).suffix.lower()


def detect_format(filename: str, data: bytes) -> tuple[SourceFormat, list[str]]:
    """Return the real format and any warnings about a misleading file name."""
    if not data or not data.strip():
        raise FileProblem("The file is empty.", code="empty_file")

    ext = extension_of(filename)
    if ext not in ACCEPTED_EXTENSIONS:
        shown = ext or "no extension"
        raise FileProblem(
            f"Files with {shown} are not supported. "
            f"Upload one of: {', '.join(ACCEPTED_EXTENSIONS)}.",
            code="unsupported_format",
            status_code=415,
        )

    detected = _sniff(data)
    warnings: list[str] = []
    if ext not in _EXPECTED_EXTENSIONS[detected]:
        warnings.append(
            f"The file name ends in {ext} but the content looks like {detected.value.upper()}; "
            f"it was read as {detected.value.upper()}."
        )
    return detected, warnings


def _sniff(data: bytes) -> SourceFormat:
    if b"%PDF-" in data[:1024]:
        return SourceFormat.PDF
    if data.startswith(_OLE_MAGIC):
        raise FileProblem(
            "This looks like a legacy .xls file or a password-protected workbook. "
            "Save it as .xlsx or .csv and upload again.",
            code="unsupported_format",
            status_code=415,
        )
    if data.startswith(b"PK\x03\x04"):
        if _is_xlsx(data):
            return SourceFormat.XLSX
        raise FileProblem(
            "This is a zip-based file but not an Excel workbook.",
            code="unsupported_format",
            status_code=415,
        )
    head = data[:4096]
    if b"\x00" in head and not head.startswith((b"\xff\xfe", b"\xfe\xff")):
        raise FileProblem(
            "This file contains binary data and is not a text statement.",
            code="unsupported_format",
            status_code=415,
        )
    lowered = head.lower()
    if lowered.lstrip().startswith(b"ofxheader") or b"<ofx>" in lowered:
        return SourceFormat.OFX
    stripped = lowered.lstrip(b"\xef\xbb\xbf \t\r\n")
    if stripped.startswith((b"<?xml", b"<document")):
        if _CAMT.search(data[:8192]):
            return SourceFormat.CAMT053
        raise FileProblem(
            "This is an XML file but not an ISO 20022 account statement (camt.053).",
            code="unsupported_format",
            status_code=415,
        )
    if len(_MT940_TAGS.findall(data[:8192])) >= 2 or (
        b"{4:" in data[:512]
        and len(_MT940_TAGS.findall(data[:8192].replace(b"{4:", b"{4:\n"))) >= 2
    ):
        return SourceFormat.MT940
    return SourceFormat.CSV


def _is_xlsx(data: bytes) -> bool:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            return any(name.startswith("xl/") for name in archive.namelist())
    except zipfile.BadZipFile:
        return False
