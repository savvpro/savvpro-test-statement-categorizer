from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.core.domain import AccountType


class ParsedRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    row_number: int
    date: date
    raw_description: str
    amount: Decimal  # negative = money out
    currency: str
    account_type: AccountType


class ParseError(BaseModel):
    model_config = ConfigDict(frozen=True)

    row_number: int
    raw_line: str
    reason: str


class ParseResult(BaseModel):
    profile_name: str
    rows: list[ParsedRow]
    errors: list[ParseError]
    skipped: list[int]
