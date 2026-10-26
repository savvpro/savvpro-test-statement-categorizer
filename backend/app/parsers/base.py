"""
Base parser interface.

All parsers return a list of RawRow objects.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import IO


@dataclass
class RawRow:
    """A single parsed row before normalization."""
    row_index: int
    posted_date: date
    raw_description: str
    amount_cents: int
    currency: str = "USD"


class BaseParser(ABC):
    """Interface that all parsers must implement."""

    @abstractmethod
    def parse(self, file: IO[bytes], account_type: str = "credit_card") -> list[RawRow]:
        """
        Parse a file and return a list of RawRow objects.

        Raises:
            ParseError: if the file cannot be parsed.
        """
        ...

    @abstractmethod
    def can_handle(self, filename: str, content_type: str | None = None) -> bool:
        """Return True if this parser can handle the given file."""
        ...


class ParseError(Exception):
    """Raised when a file cannot be parsed."""

    def __init__(self, message: str, available_columns: list[str] | None = None):
        super().__init__(message)
        self.available_columns = available_columns
