"""CSV, TSV and plain-text delimited statements."""

from __future__ import annotations

import csv
import io
import statistics

from app.domain.models import ParsedStatement, SourceFormat
from app.errors import FileProblem
from app.parsing.tabular import grid_to_statement

_DELIMITERS = (",", ";", "\t", "|")


def decode_text(data: bytes) -> str:
    """Decode bytes from the encodings banks actually use. Never raises."""
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16", errors="replace")
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("cp1252", errors="replace")


def sniff_delimiter(lines: list[str]) -> str:
    sample = [ln for ln in lines if ln.strip() and not ln.lower().startswith("sep=")][:25]
    best, best_score = ",", 0.0
    for delimiter in _DELIMITERS:
        counts = [ln.count(delimiter) for ln in sample]
        if not counts or max(counts) == 0:
            continue
        typical = statistics.median(counts)
        consistent = sum(1 for c in counts if c == typical) / len(counts)
        score = typical * consistent
        if score > best_score:
            best, best_score = delimiter, score
    return best


def read_csv(data: bytes, *, max_rows: int) -> ParsedStatement:
    text = decode_text(data).replace("\x00", "")
    delimiter = sniff_delimiter(text.splitlines())
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    grid: list[list[str]] = []
    line_numbers: list[int] = []
    try:
        previous = 0
        for row in reader:
            start = previous + 1
            previous = reader.line_num
            if row and not (len(row) == 1 and row[0].lower().startswith("sep=")):
                grid.append(row)
                line_numbers.append(start)
            if len(grid) > max_rows + 60:
                break
    except csv.Error as exc:
        raise FileProblem(f"The file could not be read as delimited text: {exc}") from exc
    return grid_to_statement(grid, SourceFormat.CSV, max_rows=max_rows, line_numbers=line_numbers)
