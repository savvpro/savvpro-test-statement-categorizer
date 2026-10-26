from dataclasses import dataclass

from app.brain.models import ParsedRow


@dataclass(frozen=True, slots=True)
class RowError:
    """A data row that could not be turned into a transaction. Never silently dropped."""

    line_no: int
    reason: str
    raw: dict[str, str]


@dataclass(frozen=True, slots=True)
class DetectedFormat:
    file_type: str  # "csv" | "xlsx"
    encoding: str | None  # None for xlsx
    delimiter: str | None  # None for xlsx
    header_line: int  # 1-based line (csv) or row (xlsx) of the header
    column_map: dict[str, str]  # logical field -> header text as it appears in the file
    date_order: str  # see dates.DateOrder
    sign_convention: str  # see signs.SignConvention
    sign_reason: str


@dataclass(frozen=True, slots=True)
class ParseResult:
    rows: list[ParsedRow]
    errors: list[RowError]
    warnings: list[str]
    detected: DetectedFormat
