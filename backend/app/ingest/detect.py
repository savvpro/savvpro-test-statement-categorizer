"""Format detection and text decoding (03-ingestion sections 1 and 2)."""

import re
import unicodedata
from pathlib import PurePath

from app.core.errors import ParseError, UnsupportedFileType
from app.domain.enums import SourceFormat
from app.domain.models import ParseWarning

ALLOWED_EXTENSIONS: dict[str, SourceFormat] = {
    ".csv": SourceFormat.CSV,
    ".txt": SourceFormat.CSV,
    ".ofx": SourceFormat.OFX,
    ".qfx": SourceFormat.OFX,
}
BINARY_MAGIC: tuple[bytes, ...] = (
    b"PK",
    b"%PDF",
    b"MZ",
    b"\x89PNG",
    b"\x7fELF",
    b"GIF8",
    b"\xff\xd8\xff",
    b"\x1f\x8b",
)
_SNIFF_BYTES = 4096
_OFX_TAG_RE = re.compile(rb"<OFX[\s>]", re.IGNORECASE)


def detect_format(data: bytes, filename: str) -> tuple[SourceFormat, list[ParseWarning]]:
    if not data.strip():
        raise ParseError("The file is empty", code="EMPTY_FILE")
    ext = PurePath(filename.replace("\\", "/")).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise UnsupportedFileType(
            f"Unsupported file extension {ext or '(none)'}; use .csv, .txt, .ofx or .qfx"
        )
    head = data[:_SNIFF_BYTES]
    if b"\x00" in head or data.startswith(BINARY_MAGIC):
        raise UnsupportedFileType("File content looks binary, not a text statement")
    stripped = head.lstrip(b"\xef\xbb\xbf \t\r\n")
    is_ofx = stripped.upper().startswith(b"OFXHEADER:") or bool(_OFX_TAG_RE.search(head))
    if not is_ofx and stripped[:5].lower() == b"<?xml" and b"<OFX" in data[:65536].upper():
        is_ofx = True
    if not is_ofx and stripped[:5].lower() == b"<?ofx":
        is_ofx = True
    fmt = SourceFormat.OFX if is_ofx else SourceFormat.CSV
    warnings: list[ParseWarning] = []
    if fmt is not ALLOWED_EXTENSIONS[ext]:
        warnings.append(
            ParseWarning(
                "EXTENSION_MISMATCH",
                f"File extension {ext} does not match its {fmt.value.upper()} content; "
                "parsed by content",
            )
        )
    return fmt, warnings


def decode_text(data: bytes) -> tuple[str, list[ParseWarning]]:
    """utf-8-sig -> cp1252 -> latin-1; normalise newlines and NFKC."""
    if b"\x00" in data:
        raise UnsupportedFileType("File content looks binary, not a text statement")
    warnings: list[ParseWarning] = []
    text: str | None = None
    for enc in ("utf-8-sig", "cp1252"):
        try:
            text = data.decode(enc)
        except UnicodeDecodeError:
            continue
        if enc != "utf-8-sig":
            warnings.append(
                ParseWarning("ENCODING_FALLBACK", f"File is not UTF-8; decoded as {enc}")
            )
        break
    if text is None:
        text = data.decode("latin-1")
        warnings.append(
            ParseWarning("ENCODING_FALLBACK", "File encoding unknown; decoded as latin-1")
        )
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return unicodedata.normalize("NFKC", text), warnings
