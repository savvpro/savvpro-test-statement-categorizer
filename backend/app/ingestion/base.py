"""Statement reader abstraction.

New formats (OFX, QIF, PDF) plug in by implementing `StatementReader` and
registering with the `ReaderRegistry`; nothing downstream changes.
"""
from typing import List, Protocol

from ..domain.errors import UnsupportedFormatError
from ..domain.models import ParsedStatement


class StatementReader(Protocol):
    extensions: tuple

    def read(self, content: bytes) -> ParsedStatement:
        ...


class ReaderRegistry:
    def __init__(self, readers: List[StatementReader]):
        self._readers = list(readers)

    def for_filename(self, filename: str) -> StatementReader:
        name = (filename or "").lower()
        for reader in self._readers:
            if name.endswith(reader.extensions):
                return reader
        supported = ", ".join(ext for r in self._readers for ext in r.extensions)
        raise UnsupportedFormatError(f"Unsupported file type. Supported: {supported}")
