import datetime as dt
import io

from openpyxl import Workbook

from app.brain.models import AccountType
from app.parsing import ParseResult, parse_statement


def csv_bytes(*lines: str, encoding: str = "utf-8") -> bytes:
    return ("\n".join(lines) + "\n").encode(encoding)


def parse_lines(
    *lines: str,
    account_type: AccountType = AccountType.checking,
    charges_positive: bool | None = None,
) -> ParseResult:
    return parse_statement(csv_bytes(*lines), "test.csv", account_type, charges_positive)


def xlsx_bytes(rows: list[list[object]]) -> bytes:
    workbook = Workbook()
    for row in rows:
        workbook.active.append(row)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


JAN_5 = dt.date(2026, 1, 5)
