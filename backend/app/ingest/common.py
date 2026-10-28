"""Shared ingest helpers: row errors and the partial-failure policy."""

from collections.abc import Sequence
from dataclasses import dataclass

from app.core.errors import ParseError

FAILURE_RATE_LIMIT = 0.05
MIN_TOLERATED_ERRORS = 2
MAX_REPORTED_ERRORS = 20


@dataclass(frozen=True, slots=True)
class RowError:
    row_index: int
    code: str
    message: str


def enforce_failure_policy(errors: Sequence[RowError], good_rows: int) -> None:
    """More than max(2, 5%) failed rows -> refuse the whole file and list the first 20 errors."""
    total = len(errors) + good_rows
    if errors and (
        good_rows == 0 or len(errors) > max(MIN_TOLERATED_ERRORS, FAILURE_RATE_LIMIT * total)
    ):
        shown = [
            {"row_index": e.row_index, "code": e.code, "message": e.message}
            for e in errors[:MAX_REPORTED_ERRORS]
        ]
        raise ParseError(
            f"{len(errors)} of {total} rows could not be parsed; refusing a partial import",
            code="TOO_MANY_BAD_ROWS",
            errors=shown,
        )
