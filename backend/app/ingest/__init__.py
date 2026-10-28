"""Statement ingestion: bytes in, ParseResult out."""

from app.core.errors import ParseError
from app.domain.enums import SourceFormat
from app.domain.models import ParseResult
from app.ingest.csv_reader import parse_csv
from app.ingest.detect import decode_text, detect_format
from app.ingest.ofx_reader import parse_ofx

DEFAULT_MAX_ROWS = 20_000


def parse_statement(
    data: bytes, filename: str, *, max_rows: int = DEFAULT_MAX_ROWS
) -> tuple[SourceFormat, ParseResult]:
    """Detect, decode and parse. Raises AppError subclasses (415/422)."""
    fmt, detect_warnings = detect_format(data, filename)
    text, decode_warnings = decode_text(data)
    result = (
        parse_ofx(text, max_rows=max_rows)
        if fmt is SourceFormat.OFX
        else parse_csv(text, max_rows=max_rows)
    )
    if not result.rows:
        raise ParseError("The file contains no transactions", code="NO_TRANSACTIONS")
    merged = ParseResult(
        rows=result.rows,
        warnings=(*detect_warnings, *decode_warnings, *result.warnings),
        date_format=result.date_format,
        decimal_comma=result.decimal_comma,
        account_type_hint=result.account_type_hint,
    )
    return fmt, merged
