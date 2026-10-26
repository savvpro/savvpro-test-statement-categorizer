"""File-level parse failures. Row-level problems are reported as `RowError`, not raised."""

MAX_ROWS = 10_000


class ParseError(ValueError):
    """Base class: the file as a whole cannot be parsed."""


class UnsupportedFileError(ParseError):
    pass


class EmptyFileError(ParseError):
    pass


class HeaderNotFoundError(ParseError):
    def __init__(self, scanned: int, expected: dict[str, list[str]]) -> None:
        def names(field: str) -> str:
            return ", ".join(f'"{name}"' for name in expected[field])

        super().__init__(
            f"no header row found in the first {scanned} rows. Expected a date column "
            f"({names('date')}), a description column ({names('description')}) and either "
            f"an amount column ({names('amount')}) or debit ({names('debit')}) and "
            f"credit ({names('credit')}) columns."
        )


class TooManyRowsError(ParseError):
    def __init__(self, limit: int = MAX_ROWS) -> None:
        super().__init__(f"statement has more than {limit:,} rows; split it into smaller files")
        self.limit = limit
