"""Rebuild table rows from positioned words.

Text PDFs (pdfplumber) and scanned pages (tesseract) both give us words with
x/y positions. Both go through the same code here, so OCR output gets the same
checks as real text.

Supported layout: one header line with Date, Description and either
Debit/Credit or Amount, plus an optional Balance. Number columns must be
right-aligned under their header, which is how bank statements print them.
"""

import re
from dataclasses import dataclass
from statistics import median

from .columns import canonical_column
from .rows import RawRow

NUMERIC_ROLES = ("debit", "credit", "amount", "balance")
ALIGN_TOLERANCE = 0.035  # share of page width
CONTINUATION_GAP = 0.025  # share of page height between a row and its wrapped second line
_DIGITISH = re.compile(r"\d")
_DATE_LIKE = re.compile(
    r"^\d{1,2}[\s/\-.](\d{1,2}|[A-Za-z]{3,9})[\s/\-.]\d{2,4}$"  # 05/03/2026, 05 Mar 2026, 05-Mar-26
    r"|^\d{4}-\d{1,2}-\d{1,2}$"  # 2026-03-05
    r"|^[A-Za-z]{3,9} \d{1,2},? \d{4}$"  # Mar 5, 2026
)


@dataclass
class Word:
    text: str
    x0: float  # all positions are a share of the page size, 0..1
    x1: float
    top: float
    bottom: float
    conf: float | None = None

    @property
    def middle(self) -> float:
        return (self.top + self.bottom) / 2


@dataclass
class Column:
    role: str
    x0: float
    x1: float


def group_lines(words: list[Word]) -> list[list[Word]]:
    if not words:
        return []
    height = median(w.bottom - w.top for w in words) or 0.01
    lines: list[list[Word]] = []
    for word in sorted(words, key=lambda w: (w.middle, w.x0)):
        if lines and abs(word.middle - lines[-1][0].middle) <= height * 0.5:
            lines[-1].append(word)
        else:
            lines.append([word])
    return [sorted(line, key=lambda w: w.x0) for line in lines]


def find_header(line: list[Word]) -> list[Column] | None:
    columns: dict[str, Column] = {}
    i = 0
    while i < len(line):
        if i + 1 < len(line):
            role, _ = canonical_column(f"{line[i].text} {line[i + 1].text}")
            if role:
                columns.setdefault(role, Column(role, line[i].x0, line[i + 1].x1))
                i += 2
                continue
        role, _ = canonical_column(line[i].text)
        if role:
            columns.setdefault(role, Column(role, line[i].x0, line[i].x1))
        i += 1
    has_amount = "amount" in columns or "debit" in columns or "credit" in columns
    if "date" in columns and "description" in columns and has_amount:
        return sorted(columns.values(), key=lambda c: c.x0)
    return None


def _numeric_column(word: Word, columns: list[Column]) -> Column | None:
    best, best_gap = None, ALIGN_TOLERANCE
    for column in columns:
        if column.role not in NUMERIC_ROLES:
            continue
        gap = abs(word.x1 - column.x1)
        if gap <= best_gap and _DIGITISH.search(word.text):
            best, best_gap = column, gap
    return best


def rows_from_pages(pages: list[list[Word]]) -> tuple[list[RawRow], bool]:
    """Returns the raw rows and whether the layout has a balance column."""
    rows: list[RawRow] = []
    columns: list[Column] | None = None
    has_balance = False

    for page_number, words in enumerate(pages, start=1):
        lines = group_lines(words)
        start = 0
        for index, line in enumerate(lines):
            header = find_header(line)
            if header:
                columns, start = header, index + 1
                has_balance = has_balance or any(c.role == "balance" for c in header)
                break
        if columns is None:
            continue  # nothing recognisable yet (cover page, letter)

        description_x0 = next(c.x0 for c in columns if c.role == "description")
        current: RawRow | None = None
        current_bottom = 0.0
        confidences: list[float] = []

        for line_number, line in enumerate(lines[start:], start=start + 1):
            if find_header(line):
                continue  # repeated header
            date_words, desc_words, numbers = [], [], {}
            for word in line:
                column = _numeric_column(word, columns)
                if column and word.x0 > description_x0:
                    numbers.setdefault(column.role, []).append(word)
                elif word.x1 <= description_x0 + 0.002:
                    date_words.append(word)
                else:
                    desc_words.append(word)

            top = min(w.top for w in line)

            date_text = _join(date_words)
            if numbers or (date_words and _DATE_LIKE.match(date_text)):
                if current is not None:
                    _finish(current, confidences)
                current = RawRow(
                    source_row=f"page {page_number}, line {line_number}",
                    date_text=date_text,
                    description=_join(desc_words),
                    amount_text=_join(numbers.get("amount", [])),
                    debit_text=_join(numbers.get("debit", [])),
                    credit_text=_join(numbers.get("credit", [])),
                    balance_text=_join(numbers.get("balance", [])),
                )
                confidences = [
                    w.conf for w in date_words + [w for ws in numbers.values() for w in ws] if w.conf is not None
                ]
                rows.append(current)
                current_bottom = max(w.bottom for w in line)
            elif desc_words and current is not None and top - current_bottom <= CONTINUATION_GAP:
                current.description = f"{current.description} {_join(desc_words)}".strip()
                current_bottom = max(w.bottom for w in line)
            else:
                current_bottom = -1.0  # a gap or footer ends the wrapped-line run
        if current is not None:
            _finish(current, confidences)
    return rows, has_balance


def _join(words: list[Word]) -> str:
    return " ".join(w.text for w in words)


def _finish(row: RawRow, confidences: list[float]) -> None:
    if confidences:
        row.ocr_confidence = min(confidences)
