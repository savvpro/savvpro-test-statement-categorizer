"""Find the header row and map its columns to logical fields."""

import re
from dataclasses import dataclass

from app.parsing.errors import HeaderNotFoundError
from app.parsing.readers import SourceRow

HEADER_SCAN_ROWS = 30

# Order matters: earlier synonyms win when two columns map to the same field
# (e.g. "Transaction Date" beats "Post Date").
SYNONYMS: dict[str, list[str]] = {
    "date": ["transaction date", "trans date", "date", "posted date", "post date", "posting date"],
    "description": [
        "description",
        "transaction description",
        "details",
        "merchant",
        "payee",
        "name",
    ],
    "amount": ["amount", "transaction amount"],
    "debit": ["debit", "debits", "withdrawal", "withdrawals", "money out", "charges"],
    "credit": ["credit", "credits", "deposit", "deposits", "money in", "payments"],
    "status": ["status"],
    "type": ["type", "dr cr"],
}

_LOOKUP = {
    synonym: (field, priority)
    for field, synonyms in SYNONYMS.items()
    for priority, synonym in enumerate(synonyms)
}


def normalize_header(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


@dataclass(frozen=True, slots=True)
class ColumnMap:
    position: int  # index of the header row within the table
    line_no: int
    keys: list[str]  # unique raw-dict key per column
    fields: dict[str, int]  # logical field -> column index

    @property
    def split_amounts(self) -> bool:
        return "debit" in self.fields and "credit" in self.fields

    def cell(self, cells: list[str], field: str) -> str:
        index = self.fields.get(field)
        return cells[index] if index is not None and index < len(cells) else ""

    def raw(self, cells: list[str]) -> dict[str, str]:
        raw = {key: (cells[i] if i < len(cells) else "") for i, key in enumerate(self.keys)}
        for i in range(len(self.keys), len(cells)):
            if cells[i]:
                raw[f"column_{i + 1}"] = cells[i]
        return raw

    def describe(self) -> dict[str, str]:
        return {field: self.keys[index] for field, index in self.fields.items()}


def map_columns(cells: list[str]) -> dict[str, int]:
    best: dict[str, tuple[int, int]] = {}  # field -> (priority, column)
    for column, cell in enumerate(cells):
        match = _LOOKUP.get(normalize_header(cell))
        if match is None:
            continue
        field, priority = match
        if field not in best or priority < best[field][0]:
            best[field] = (priority, column)
    return {field: column for field, (_, column) in best.items()}


def _usable(fields: dict[str, int]) -> bool:
    has_amount = "amount" in fields or ("debit" in fields and "credit" in fields)
    return "date" in fields and "description" in fields and has_amount


def detect_header(rows: list[SourceRow]) -> ColumnMap:
    best: tuple[int, int, dict[str, int]] | None = None  # (score, position, fields)
    for position, row in enumerate(rows[:HEADER_SCAN_ROWS]):
        fields = map_columns(row.cells)
        if _usable(fields) and (best is None or len(fields) > best[0]):
            best = (len(fields), position, fields)

    if best is None:
        raise HeaderNotFoundError(min(len(rows), HEADER_SCAN_ROWS), SYNONYMS)

    _, position, fields = best
    header = rows[position]
    return ColumnMap(position, header.line_no, _unique_keys(header.cells), fields)


def _unique_keys(cells: list[str]) -> list[str]:
    keys: list[str] = []
    seen: dict[str, int] = {}
    for index, cell in enumerate(cells):
        key = cell or f"column_{index + 1}"
        if key in seen:
            seen[key] += 1
            key = f"{key}_{seen[key]}"
        else:
            seen[key] = 1
        keys.append(key)
    return keys
