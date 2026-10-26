"""Statement parsing: bytes in, canonical `ParsedRow`s out. Pure: no DB or web imports."""

from app.parsing.errors import (
    MAX_ROWS,
    EmptyFileError,
    HeaderNotFoundError,
    ParseError,
    TooManyRowsError,
    UnsupportedFileError,
)
from app.parsing.parser import parse_statement
from app.parsing.result import DetectedFormat, ParseResult, RowError

__all__ = [
    "MAX_ROWS",
    "DetectedFormat",
    "EmptyFileError",
    "HeaderNotFoundError",
    "ParseError",
    "ParseResult",
    "RowError",
    "TooManyRowsError",
    "UnsupportedFileError",
    "parse_statement",
]
