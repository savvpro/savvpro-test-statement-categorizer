"""File type detection and encoding sniffing."""
from __future__ import annotations

import chardet

MAX_BYTES = 5 * 1024 * 1024  # 5 MB


class SniffResult:
    def __init__(
        self,
        fmt: str,  # "csv" | "ofx" | "qfx" | "unknown"
        encoding: str,
        delimiter: str | None = None,
    ):
        self.fmt = fmt
        self.encoding = encoding
        self.delimiter = delimiter


def sniff(data: bytes, filename: str = "") -> SniffResult:
    """Detect file format and encoding from raw bytes."""
    if len(data) > MAX_BYTES:
        raise ValueError(f"File exceeds 5 MB limit ({len(data):,} bytes)")

    # Detect encoding
    det = chardet.detect(data[:32_768])
    encoding = (det.get("encoding") or "utf-8").replace("UTF-8-SIG", "utf-8-sig")

    # Try to decode a sample
    sample = _decode_sample(data, encoding)

    # OFX/QFX detection
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext in {"ofx", "qfx"} or sample.strip().startswith(("OFXHEADER", "<OFX")):
        return SniffResult("ofx", encoding)

    # CSV: sniff delimiter
    delimiter = _sniff_delimiter(sample)
    return SniffResult("csv", encoding, delimiter)


def _decode_sample(data: bytes, encoding: str, n: int = 4096) -> str:
    try:
        return data[:n].decode(encoding, errors="replace")
    except (LookupError, UnicodeDecodeError):
        return data[:n].decode("utf-8", errors="replace")


def _sniff_delimiter(sample: str) -> str:
    # Count potential delimiters in first few non-empty lines
    lines = [ln for ln in sample.splitlines() if ln.strip()][:10]
    counts: dict[str, int] = {",": 0, ";": 0, "\t": 0}
    for ln in lines:
        for delim in counts:
            counts[delim] += ln.count(delim)
    return max(counts, key=lambda d: counts[d])
