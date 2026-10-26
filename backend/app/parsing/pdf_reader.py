"""Text-based PDF statements.

Three strategies are tried in order:

1. Word positions. Characters are filtered by orientation (a diagonal or sideways security
   watermark never reaches the text), grouped into lines by baseline and words by gap, a
   header line is recognised with the same vocabulary the CSV reader uses, and every word
   is assigned to a column by its x position. Rows are the lines that carry a date, with
   the lines around them (wrapped descriptions) merged in.
2. Ruled tables as pdfplumber sees them.
3. Plain text lines that start with a date and end with an amount, for PDFs whose layout
   has no usable column positions.

Scanned PDFs have no text layer; those are reported clearly because OCR is out of scope.
"""

from __future__ import annotations

import contextlib
import io
import math
import re
import statistics
from collections import Counter
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

import pdfplumber
from pdfminer.layout import LTChar, LTContainer

from app.domain.models import ParsedStatement, RawRow, RejectedRow, SourceFormat
from app.errors import FileProblem
from app.parsing.amounts import CURRENCY_CODES, parse_amount
from app.parsing.dates import (
    DMY,
    MDY,
    fix_year_rollover,
    guess_year,
    has_year,
    infer_date_order,
    parse_date,
    split_date_prefix,
)
from app.parsing.tabular import (
    _OPENING_LINE,
    _SUMMARY_LINE,
    DATE,
    MONEY_ROLES,
    find_columns,
    grid_to_statement,
    join_description,
    scan_header_tokens,
    select_columns,
)

# -- page layout -------------------------------------------------------------------------

_BASELINE_TOLERANCE = 0.6  # points; text on one line shares a baseline to well within this
_WORD_GAP = 0.17  # a gap wider than this many em starts a new word
_ORIENTATION_TOLERANCE = 0.08


@dataclass
class _Word:
    text: str
    x0: float
    x1: float
    size: float


@dataclass
class _Line:
    number: int  # 1-based position in the document, used as the row's "line"
    base: float  # baseline measured down from the top of the page
    words: list[_Word]
    size: float

    @property
    def text(self) -> str:
        return " ".join(w.text for w in self.words)


def _direction(char: dict) -> tuple[float, float]:
    matrix = char.get("matrix")
    if not matrix or (matrix[1] == 0 and matrix[0] > 0):
        return 1.0, 0.0
    scale = math.hypot(matrix[0], matrix[1]) or 1.0
    return matrix[0] / scale, matrix[1] / scale


def _dominant_direction(chars: list[dict]) -> tuple[float, float]:
    counts: Counter[tuple[float, float]] = Counter()
    for char in chars:
        ux, uy = _direction(char)
        counts[(round(ux, 1), round(uy, 1))] += 1
    return counts.most_common(1)[0][0] if counts else (1.0, 0.0)


def _keeps(char: dict, dominant: tuple[float, float]) -> bool:
    """Keep text that runs the same way as the bulk of the page.

    Watermarks are drawn sideways or at an angle; pdfminer calls a 30 degree watermark
    "upright", so the check looks at the direction of the baseline instead.
    """
    if not char.get("upright", True):
        return False
    ux, uy = _direction(char)
    return (
        abs(ux - dominant[0]) <= _ORIENTATION_TOLERANCE
        and abs(uy - dominant[1]) <= _ORIENTATION_TOLERANCE
    )


def _layout_chars(page: pdfplumber.page.Page) -> list[dict]:
    """Characters of a page straight from the pdfminer layout.

    pdfplumber's own `page.chars` resolves dozens of attributes per character, which costs
    several times more than reading the few fields needed here.
    """
    chars: list[dict] = []
    pending: list[LTContainer] = [page.layout]
    while pending:
        for obj in pending.pop():
            if isinstance(obj, LTChar):
                text = obj.get_text()
                if text and text != "\x00":
                    chars.append(
                        {
                            "text": text,
                            "x0": obj.x0,
                            "x1": obj.x1,
                            "size": obj.size,
                            "matrix": obj.matrix,
                            "upright": obj.upright,
                            "bottom": obj.y0,
                        }
                    )
            elif isinstance(obj, LTContainer):
                pending.append(obj)
    return chars


def _page_chars(page: pdfplumber.page.Page) -> list[dict]:
    chars = _layout_chars(page)
    dominant = _dominant_direction(chars)
    return [c for c in chars if _keeps(c, dominant)]


def _page_lines(chars: list[dict], first_number: int) -> list[_Line]:
    keyed = sorted(
        ((-(c["matrix"][5]) if c.get("matrix") else c["bottom"]), c["x0"], i, c)
        for i, c in enumerate(chars)
    )
    clusters: list[tuple[float, list[dict]]] = []
    for base, _x, _i, char in keyed:
        if clusters and base - clusters[-1][0] <= _BASELINE_TOLERANCE:
            clusters[-1][1].append(char)
        else:
            clusters.append((base, [char]))

    lines: list[_Line] = []
    for base, members in clusters:
        words = _words(sorted(members, key=lambda c: c["x0"]))
        if words:
            lines.append(_Line(0, base, words, statistics.median(w.size for w in words)))
    for offset, line in enumerate(lines):
        line.number = first_number + offset
    return lines


def _words(chars: list[dict]) -> list[_Word]:
    words: list[_Word] = []
    current: list[dict] = []

    def flush() -> None:
        if current:
            words.append(
                _Word(
                    "".join(c["text"] for c in current),
                    current[0]["x0"],
                    max(c["x1"] for c in current),
                    max(c.get("size", 0.0) for c in current),
                )
            )
            current.clear()

    for char in chars:
        if char["text"].isspace():
            flush()
            continue
        if current and char["x0"] - current[-1]["x1"] > _WORD_GAP * max(char.get("size", 8.0), 4):
            flush()
        current.append(char)
    flush()
    return words


# -- tokens: words with split numbers put back together -------------------------------------

_MONEY_SYMBOLS = "$€£¥₹"
_CODES = "|".join(CURRENCY_CODES)
_SYMBOL_ONLY = re.compile(rf"^(?:[{_MONEY_SYMBOLS}]|{_CODES})$")
_MONEY_CLEAN = re.compile(rf"[{_MONEY_SYMBOLS}]|\b(?:{_CODES})\b|\b(?:CR|DR)\b\.?|[()+\-]", re.I)
_MONEY_SHAPE = re.compile(r"^(?:\d{1,3}(?:[ ,.']\d{3})+|\d+)[.,]\d{2}$")
_LEADING_SYMBOL = re.compile(rf"^(?:[{_MONEY_SYMBOLS}]|{_CODES})\s*")
_SMALL_INT = re.compile(r"^\d{1,3}$")
_NUMBER_TAIL = re.compile(r"^\d{3}(?:[ ,.']\d{3})*[.,]\d{2}\)?-?$")
_MARKER = re.compile(r"^(?:CR|DR)\.?$", re.I)


def _is_money(text: str) -> bool:
    cleaned = _MONEY_CLEAN.sub("", text).replace("−", "").strip()
    return bool(_MONEY_SHAPE.match(cleaned))


@dataclass
class _Token:
    text: str
    x0: float
    x1: float
    size: float

    @property
    def center(self) -> float:
        return (self.x0 + self.x1) / 2


def _near(token: _Token, nxt: _Word) -> bool:
    return nxt.x0 - token.x1 <= 0.9 * max(token.size, 6)


def _merge(a: _Token, b: _Word) -> _Token:
    return _Token(f"{a.text} {b.text}", a.x0, max(a.x1, b.x1), max(a.size, b.size))


def _tokens(words: list[_Word]) -> list[_Token]:
    """Words of a line with "10 598,70", "$ 12.50" and "12.50 CR" each as one token."""
    out: list[_Token] = []
    i = 0
    while i < len(words):
        word = words[i]
        token = _Token(word.text, word.x0, word.x1, word.size)
        i += 1
        while i < len(words) and _near(token, words[i]):
            nxt = words[i]
            core = _LEADING_SYMBOL.sub("", token.text)
            if not core:
                joinable = _is_money(nxt.text) or bool(_SMALL_INT.match(nxt.text))
            elif _SMALL_INT.match(core):
                joinable = bool(_NUMBER_TAIL.match(nxt.text))
            elif _is_money(token.text):
                joinable = bool(_SYMBOL_ONLY.match(nxt.text) or _MARKER.match(nxt.text))
            else:
                joinable = False
            if not joinable:
                break
            token = _merge(token, nxt)
            i += 1
        out.append(token)
    return out


# -- table geometry from a header line --------------------------------------------------------


@dataclass
class _Column:
    role: str | None  # canonical role, or None when the column's text is not used
    x0: float
    x1: float
    numeric: bool
    description_rank: int | None = None


@dataclass
class _Geometry:
    columns: list[_Column]
    embedded_date: bool
    currency: str | None  # symbol or code printed in the amount headers

    @property
    def numeric(self) -> list[int]:
        return [i for i, c in enumerate(self.columns) if c.numeric]

    @property
    def text(self) -> list[int]:
        return [i for i, c in enumerate(self.columns) if not c.numeric]

    def with_role(self, role: str) -> int | None:
        return next((i for i, c in enumerate(self.columns) if c.role == role), None)

    @property
    def descriptions(self) -> list[int]:
        ranked = [
            (c.description_rank, i)
            for i, c in enumerate(self.columns)
            if c.description_rank is not None
        ]
        return [i for _, i in sorted(ranked)]

    @property
    def roles(self) -> set[str]:
        return {c.role for c in self.columns if c.role}


def _geometry(line: _Line) -> _Geometry | None:
    tokens = [w.text for w in line.words]
    hits, covered, total = scan_header_tokens(tokens)
    if len(hits) < 3 or total == 0 or covered / total < 0.6:
        return None
    roles = {h.role for h in hits}
    if not roles & set(MONEY_ROLES):
        return None
    labels = [(i, h.role, h.rank, h.currency) for i, h in enumerate(hits)]
    chosen = select_columns(labels, 0)
    embedded = False
    if chosen is None:
        if DATE in roles:
            return None
        chosen = select_columns([*labels, (-1, DATE, 0, None)], 0)
        embedded = True
        if chosen is None:
            return None

    role_of: dict[int, str] = {}
    for role, index in (
        ("amount", chosen.amount),
        ("debit", chosen.debit),
        ("credit", chosen.credit),
        ("balance", chosen.balance),
        ("currency", chosen.currency),
        ("direction", chosen.direction),
    ):
        if index is not None:
            role_of[index] = role
    if not embedded:
        role_of[chosen.date] = "date"
    description_order = [chosen.description, *chosen.extra_description]
    for index in description_order:
        role_of[index] = "description"

    columns: list[_Column] = []
    covered_words: set[int] = set()
    for hit_index, hit in enumerate(hits):
        covered_words.update(range(hit.first, hit.last + 1))
        rank = description_order.index(hit_index) if hit_index in description_order else None
        columns.append(
            _Column(
                role_of.get(hit_index),
                line.words[hit.first].x0,
                line.words[hit.last].x1,
                hit.role in MONEY_ROLES,
                rank,
            )
        )
    # Header words nobody recognised still mark where another column starts.
    run: list[int] = []
    for index in range(len(line.words) + 1):
        if index < len(line.words) and index not in covered_words:
            run.append(index)
            continue
        if run:
            columns.append(_Column(None, line.words[run[0]].x0, line.words[run[-1]].x1, False))
            run = []
    columns.sort(key=lambda c: c.x0)
    currency = next((h.currency for h in hits if h.currency), None)
    return _Geometry(columns, embedded, currency)


# -- one visual line mapped onto the columns ----------------------------------------------------

_NUMERIC_REACH = 60.0  # how far (points) a money word may sit from a numeric header
_COLUMN_SLACK = 6.0
_PAGE_FOOTER = re.compile(
    r"\bpage\s+\d+\s*(?:of|de|sur|/)\s*\d+\b|(?:^|\s)\d+\s*(?:/|of|de|sur)\s*\d+\s*$", re.I
)
_CARRIED_FORWARD = re.compile(r"carried\s+forward|brought\s+forward|c/f|b/f", re.I)
_HEADING = re.compile(r"account|currency|ccy|devise|compte", re.I)
_CODE_WORD = re.compile(rf"\b({_CODES})\b")


@dataclass
class _Cells:
    text: dict[int, list[str]] = field(default_factory=dict)
    money: dict[int, list[str]] = field(default_factory=dict)
    marks: dict[int, str] = field(default_factory=dict)
    stray_money: bool = False


def _assign(tokens: list[_Token], geo: _Geometry) -> _Cells:
    cells = _Cells()
    numeric, text = geo.numeric, geo.text
    for token in tokens:
        if numeric and _is_money(token.text):
            distance, column = min((_distance(token, geo.columns[i]), i) for i in numeric)
            if distance <= _NUMERIC_REACH:
                cells.money.setdefault(column, []).append(token.text)
                continue
            cells.stray_money = True
        elif numeric and _MARKER.match(token.text):
            mark_column = next(
                (
                    i
                    for i in numeric
                    if geo.columns[i].x0 - 12 <= token.x0 and token.x1 <= geo.columns[i].x1 + 6
                ),
                None,
            )
            if mark_column is not None:
                cells.marks[mark_column] = token.text.upper().rstrip(".")
                continue
        text_column = _text_column(token, geo, text)
        if text_column is not None:
            cells.text.setdefault(text_column, []).append(token.text)
    return cells


def _distance(token: _Token, column: _Column) -> float:
    return min(
        abs(token.x1 - column.x1),
        abs(token.x0 - column.x0),
        abs(token.center - (column.x0 + column.x1) / 2),
    )


def _text_column(token: _Token, geo: _Geometry, text: list[int]) -> int | None:
    if not text:
        return None
    chosen = text[0]
    for index in text:
        if geo.columns[index].x0 - _COLUMN_SLACK <= token.x0:
            chosen = index
    return chosen


def _parses_as_date(text: str) -> bool:
    return bool(text) and (parse_date(text, MDY, 2000) or parse_date(text, DMY, 2000)) is not None


@dataclass
class _Info:
    line: _Line
    cells: _Cells
    kind: str  # "row", "text", "skip" or "opening"
    date_text: str = ""
    has_description: bool = False
    small: bool = False


def _inspect(line: _Line, geo: _Geometry, body_size: float) -> _Info:
    cells = _assign(_tokens(line.words), geo)
    text = line.text
    date_col = geo.with_role("date")
    descriptions = geo.descriptions
    has_description = any(cells.text.get(c) for c in descriptions)
    small = line.size < 0.8 * body_size
    info = _Info(line, cells, "text", has_description=has_description, small=small)

    if _OPENING_LINE.match(text):
        info.kind = "opening"
        return info
    if _PAGE_FOOTER.search(text) or _SUMMARY_LINE.match(text):
        info.kind = "skip"
        return info

    if geo.embedded_date:
        first = descriptions[0] if descriptions else None
        words = " ".join(cells.text.get(first, [])) if first is not None else ""
        split = split_date_prefix(words)
        if split is not None:
            info.kind, info.date_text = "row", split[0]
    else:
        words = " ".join(cells.text.get(date_col, [])) if date_col is not None else ""
        if _parses_as_date(words):
            info.kind, info.date_text = "row", words
        elif words:
            info.kind = "skip"  # text in the date column that is not a date: a note or footer
    if info.kind == "text" and cells.stray_money:
        info.kind = "skip"
    return info


# -- rows ----------------------------------------------------------------------------------


@dataclass
class _Block:
    infos: list[_Info]


def _blocks(infos: list[_Info]) -> list[_Block]:
    """Group the lines of a table into visual blocks, one per row where the layout allows."""
    mains = [i for i in infos if i.kind != "skip" and i.has_description and not i.small]
    if not mains:
        return []
    sizes = [m.line.size for m in mains]
    body = statistics.median(sizes)
    diffs = sorted(
        b.line.base - a.line.base
        for a, b in zip(mains, mains[1:], strict=False)
        if b.line.base - a.line.base >= 0.5 * body
    )
    pitch = diffs[len(diffs) // 4] if diffs else 1.2 * body
    limit = pitch * 1.35 + 0.2

    index_of = {id(m): k for k, m in enumerate(mains)}
    block_of: dict[int, int] = {}
    block = 0
    previous: _Info | None = None
    pending_break = False
    for info in infos:
        if info.kind == "skip":
            pending_break = True
            continue
        if id(info) not in index_of:
            continue
        if previous is not None and (pending_break or info.line.base - previous.line.base > limit):
            block += 1
        block_of[index_of[id(info)]] = block
        previous, pending_break = info, False

    blocks: dict[int, list[_Info]] = {}
    for info in infos:
        if info.kind == "skip":
            continue
        if id(info) in index_of:
            key = block_of[index_of[id(info)]]
        else:
            nearest = min(range(len(mains)), key=lambda k: abs(mains[k].line.base - info.line.base))
            key = block_of[nearest]
        blocks.setdefault(key, []).append(info)
    return [_Block(sorted(v, key=lambda i: i.line.base)) for _, v in sorted(blocks.items())]


@dataclass
class _Row:
    line: int
    cells: dict[str, str]
    base: float = 0.0


_PAYMENT_ROLES = ("debit", "credit", "amount")


def _has_payment(info: _Info, geo: _Geometry) -> bool:
    """True when the line carries a non-zero amount in a debit, credit or amount column."""
    return any(
        re.search(r"[1-9]", token)
        for index, column in enumerate(geo.columns)
        if column.role in _PAYMENT_ROLES
        for token in info.cells.money.get(index, [])
    )


def _group_rows(block: _Block, geo: _Geometry, stats: _Stats, *, headerless: bool) -> list[_Row]:
    infos = block.infos
    anchors = [k for k, info in enumerate(infos) if info.kind == "row"]
    rows: list[_Row] = []
    for n, start in enumerate(anchors):
        begin = 0 if n == 0 else start
        end = anchors[n + 1] if n + 1 < len(anchors) else len(infos)
        group = infos[begin:end]
        anchor = infos[start]
        # A second line with its own amount is another transaction that repeats the date
        # by leaving it blank, not a continuation of the first one.
        money_at = [k for k, info in enumerate(group) if _has_payment(info, geo)]
        bounds = [0, *money_at[1:], len(group)]
        for k in range(len(bounds) - 1):
            lines = group[bounds[k] : bounds[k + 1]]
            main = anchor if k == 0 else lines[0]
            row = _build_row(anchor.date_text, main, lines, geo, stats)
            if headerless and not any(row.cells.get(r) for r in _PAYMENT_ROLES):
                continue
            rows.append(row)
            stats.anchors += 1
    return rows


def _build_row(
    date_text: str, main: _Info, group: list[_Info], geo: _Geometry, stats: _Stats
) -> _Row:
    cells: dict[str, str] = {"date": date_text}
    descriptions = geo.descriptions

    # Lines that carry their own amounts: a zero amount marks a memo line that is not part
    # of the description, a non-zero one is only used when the main line has no amount.
    main_has_money = _has_payment(main, geo)
    usable: list[_Info] = []
    borrowed: _Info | None = None
    for info in group:
        if info is main or not any(info.cells.money.get(c) for c in geo.numeric):
            usable.append(info)
        elif not _has_payment(info, geo):
            continue
        elif not main_has_money and borrowed is None:
            borrowed = info
            usable.append(info)

    if geo.embedded_date:
        parts = []
        for info in usable:
            words = " ".join(info.cells.text.get(descriptions[0], [])) if descriptions else ""
            if info.kind == "row":
                split = split_date_prefix(words)
                words = split[1] if split else words
            if words:
                parts.append(words)
        cells["description"] = " ".join(parts)
    else:
        cells["description"] = join_description(
            [" ".join(w for i in usable for w in i.cells.text.get(c, [])) for c in descriptions]
        )

    sources = [main] if borrowed is None else [main, borrowed]
    for column, spec in enumerate(geo.columns):
        role = spec.role
        if role in ("debit", "credit", "amount", "balance"):
            for source in sources:
                tokens = source.cells.money.get(column)
                if not tokens:
                    continue
                if len(tokens) > 1:
                    stats.conflicts += 1
                mark = next((i.cells.marks[column] for i in usable if column in i.cells.marks), "")
                text = tokens[0]
                has_marker = re.search(r"CR|DR", text, re.I)
                cells[role] = f"{text} {mark}" if mark and not has_marker else text
                break
        elif role in ("currency", "direction"):
            cells[role] = " ".join(w for i in usable for w in i.cells.text.get(column, []))
    return _Row(main.line.number, cells, main.line.base)


@dataclass
class _Stats:
    anchors: int = 0
    conflicts: int = 0


@dataclass
class _Table:
    geometry: _Geometry
    events: list[tuple[float, _Row]]  # (baseline, row) in page order
    currency: str | None = None


_GRID_LABELS = {
    "date": "Date",
    "description": "Description",
    "debit": "Debit",
    "credit": "Credit",
    "amount": "Amount",
    "balance": "Balance",
    "currency": "Currency",
    "direction": "DR/CR",
}


def _read_segment(
    lines: list[_Line],
    geo: _Geometry,
    heading: list[_Line],
    stats: _Stats,
    *,
    headerless: bool,
) -> tuple[list[tuple[float, _Row]], str | None, bool]:
    """Rows of one table segment, the table's explicit currency code and whether it ended."""
    if not lines:
        return [], None, False
    body = statistics.median(ln.size for ln in lines)
    infos = [_inspect(line, geo, body) for line in lines]
    first_anchor = next((k for k, i in enumerate(infos) if i.kind == "row"), len(infos))
    # Between the header and the first row, lines with no Latin text or digits are the
    # header's translation or a second header line ("($)").
    for info in infos[:first_anchor]:
        latin = any(ch.isalnum() and ord(ch) < 0x250 for ch in info.line.text)
        if info.kind == "text" and not latin:
            info.kind = "skip"

    events: list[tuple[float, _Row]] = []
    currency = None
    for info in infos:
        if info.kind == "opening":
            row = _opening_row(info, geo)
            if row is not None:
                events.append((info.line.base, row))
                currency = currency or _explicit_code(info.line.text)
    for block in _blocks(infos):
        for row in _group_rows(block, geo, stats, headerless=headerless):
            events.append((row.base, row))
    events.sort(key=lambda e: e[0])
    # A "balance carried forward" line closes a page, not the table.
    ended = any(
        i.kind == "skip"
        and _SUMMARY_LINE.match(i.line.text)
        and not _CARRIED_FORWARD.search(i.line.text)
        for i in infos[first_anchor:]
    )
    if currency is None:
        for line in reversed(heading):
            if _HEADING.search(line.text) and (code := _explicit_code(line.text)):
                currency = code
                break
    return events, currency, ended


def _explicit_code(text: str) -> str | None:
    match = _CODE_WORD.search(text)
    return match.group(1) if match else None


def _opening_row(info: _Info, geo: _Geometry) -> _Row | None:
    balance_col = geo.with_role("balance")
    if balance_col is None:
        balance_col = geo.with_role("amount")
    if balance_col is None:
        return None
    tokens = info.cells.money.get(balance_col)
    if not tokens:
        return None
    words = [w for c in geo.text for w in info.cells.text.get(c, [])]
    return _Row(
        info.line.number, {"description": " ".join(words), "balance": tokens[0]}, info.line.base
    )


def _word_route(pages: list[list[_Line]]) -> tuple[list[_Table], _Stats]:
    tables: list[_Table] = []
    stats = _Stats()
    active: _Geometry | None = None
    table_for_active: _Table | None = None
    for lines in pages:
        headers = [(i, g) for i, ln in enumerate(lines) if (g := _geometry(ln)) is not None]
        segments: list[tuple[_Geometry, list[_Line], list[_Line], bool]] = []
        if active is not None:
            stop = headers[0][0] if headers else len(lines)
            segments.append((active, lines[:stop], [], True))
        for n, (i, geo) in enumerate(headers):
            end = headers[n + 1][0] if n + 1 < len(headers) else len(lines)
            segments.append((geo, lines[i + 1 : end], lines[max(0, i - 3) : i], False))
        for geo, body, heading, headerless in segments:
            events, currency, ended = _read_segment(
                body, geo, heading, stats, headerless=headerless
            )
            if headerless and table_for_active is not None:
                table = table_for_active
            else:
                table = _Table(geo, [])
                tables.append(table)
                table_for_active = table
            table.events.extend(events)
            table.currency = table.currency or currency
            active = None if ended else geo
    return tables, stats


def _grid_from_tables(tables: list[_Table]) -> tuple[list[list[str]], list[int]]:
    present: set[str] = set()
    for table in tables:
        present |= table.geometry.roles
        if table.geometry.embedded_date:
            present.add("date")
        present.add("description")
    if any(t.currency for t in tables):
        present.add("currency")
    roles = [r for r in _GRID_LABELS if r in present]
    labels = [_GRID_LABELS[r] for r in roles]
    header_currency = next((t.geometry.currency for t in tables if t.geometry.currency), None)
    money = next((i for i, r in enumerate(roles) if r in ("amount", "debit", "credit")), None)
    if header_currency and money is not None:
        labels[money] = f"{labels[money]} ({header_currency})"
    grid = [labels]
    line_numbers = [0]
    for table in tables:
        for _, row in table.events:
            cells = dict(row.cells)
            if table.currency:
                cells.setdefault("currency", table.currency)
            grid.append([cells.get(r, "") for r in roles])
            line_numbers.append(row.line)
    return grid, line_numbers


# -- entry point -------------------------------------------------------------------------------

_DOC_CODE = re.compile(
    rf"\b({_CODES})\s?(?=[\d(\-])|(?<=\d)\s?({_CODES})\b|[Cc]urrency\W{{0,3}}({_CODES})\b"
)


def _document_currency(text: str) -> str | None:
    counts: Counter[str] = Counter()
    for match in _DOC_CODE.finditer(text):
        counts[next(g for g in match.groups() if g)] += 1
    return counts.most_common(1)[0][0] if counts else None


_DOLLAR_COUNTRIES = (
    ("CAD", re.compile(r"\bcanad(?:a|ian)\b", re.I)),
    ("AUD", re.compile(r"\baustrali(?:a|an)\b", re.I)),
    ("NZD", re.compile(r"\bnew zealand\b", re.I)),
    ("SGD", re.compile(r"\bsingapore\b", re.I)),
    ("HKD", re.compile(r"\bhong kong\b", re.I)),
)
_US_MENTION = re.compile(r"\bUSD\b|US\$|U\.S\.|United States", re.I)


def _refine_dollar(hint: str | None, text: str) -> str | None:
    """A bare "$" reads as US dollars unless the document is clearly from another country."""
    if hint != "USD" or _US_MENTION.search(text):
        return hint
    for code, pattern in _DOLLAR_COUNTRIES:
        if pattern.search(text):
            return code
    return hint


def read_pdf(data: bytes, *, max_rows: int, max_pages: int) -> ParsedStatement:
    pdf = _open(data)
    try:
        try:
            pages = len(pdf.pages)
            if pages > max_pages:
                raise FileProblem(
                    f"The PDF has {pages} pages; the limit is {max_pages}. "
                    "Upload a shorter period.",
                    code="pdf_too_many_pages",
                    status_code=413,
                )
            return _read_open_pdf(pdf, max_rows=max_rows)
        except FileProblem:
            raise
        except Exception as exc:  # pdfminer raises many kinds of errors
            raise FileProblem("The PDF could not be read and may be damaged.") from exc
    finally:
        with contextlib.suppress(Exception):
            pdf.close()


def _read_open_pdf(pdf: pdfplumber.pdf.PDF, *, max_rows: int) -> ParsedStatement:
    pages: list[list[_Line]] = []
    number = 1
    for page in pdf.pages:
        try:
            chars = _page_chars(page)
        except Exception:
            chars = []
        lines = _page_lines(chars, number) if chars else []
        number += len(lines)
        pages.append(lines)

    full_text = "\n".join(line.text for lines in pages for line in lines)
    if len(full_text.strip()) < 20:
        raise FileProblem(
            "This PDF has no readable text, so it is probably a scan or photo. "
            "Export a CSV or Excel file from your bank instead.",
            code="pdf_no_text",
        )
    year = guess_year(full_text)
    doc_currency = _document_currency(full_text)

    parsed = _try_word_route(pages, year, max_rows)
    if parsed is None:
        parsed = _try_ruled_route(pdf, year, max_rows)
    if parsed is None:
        page_texts = ["\n".join(line.text for line in lines) for lines in pages]
        parsed = _parse_text_lines("\n".join(page_texts), max_rows=max_rows, year=year)
    parsed.currency_hint = _refine_dollar(parsed.currency_hint or doc_currency, full_text)
    return parsed


def _try_word_route(
    pages: list[list[_Line]], year: int | None, max_rows: int
) -> ParsedStatement | None:
    tables, stats = _word_route(pages)
    if not tables or stats.anchors == 0:
        return None
    grid, line_numbers = _grid_from_tables(tables)
    if len(grid) < 2:
        return None
    try:
        parsed = grid_to_statement(
            grid, SourceFormat.PDF, max_rows=max_rows, default_year=year, line_numbers=line_numbers
        )
    except FileProblem as exc:
        if exc.code == "too_many_rows":
            raise
        return None
    real_rejects = [r for r in parsed.rejected if not r.reason.startswith("Summary")]
    if not parsed.rows or len(real_rejects) > 0.5 * stats.anchors:
        return None
    if stats.conflicts > 0.2 * stats.anchors:
        return None
    return parsed


def _open(data: bytes) -> pdfplumber.pdf.PDF:
    try:
        return pdfplumber.open(io.BytesIO(data))
    except Exception as exc:
        text = f"{type(exc).__name__} {exc} {exc.__cause__!r} {exc.args!r}".lower()
        if "password" in text or "encrypt" in text:
            raise FileProblem(
                "This PDF is password protected. Remove the password and upload it again.",
                code="pdf_encrypted",
            ) from exc
        raise FileProblem("The PDF is damaged and could not be opened.") from exc


# -- strategy 2: ruled tables -----------------------------------------------------------------


def _try_ruled_route(
    pdf: pdfplumber.pdf.PDF, year: int | None, max_rows: int
) -> ParsedStatement | None:
    grid = _table_grid(pdf)
    if not grid or find_columns(grid) is None:
        return None
    try:
        parsed = grid_to_statement(grid, SourceFormat.PDF, max_rows=max_rows, default_year=year)
    except FileProblem as exc:
        if exc.code == "too_many_rows":
            raise
        return None
    return parsed if parsed.rows else None


def _table_grid(pdf: pdfplumber.pdf.PDF) -> list[list[str]]:
    grid: list[list[str]] = []
    header: list[str] | None = None
    for page in pdf.pages:
        try:
            chars = [c for c in page.chars if c.get("text")]
            dominant = _dominant_direction(chars)

            def keep(obj: dict[str, Any], direction: Any = dominant) -> bool:
                return obj.get("object_type") != "char" or _keeps(obj, direction)

            tables = page.filter(keep).extract_tables()
        except Exception:
            continue
        for table in tables:
            for row in table:
                cells = [re.sub(r"\s+", " ", c or "").strip() for c in row]
                if not any(cells):
                    continue
                if header is None and find_columns([cells]) is not None:
                    header = cells
                elif header is not None and cells == header:
                    continue  # repeated header on a later page
                grid.append(cells)
    return grid


# -- strategy 3: plain text lines ---------------------------------------------------------------

_DATE_PATTERNS = (
    r"\d{4}-\d{2}-\d{2}",
    r"\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}",
    r"\d{1,2}[ -](?:[A-Za-z]{3,12})\.?(?:,?[ -]\d{2,4})?",
    r"(?:[A-Za-z]{3,12})\.? \d{1,2}(?:st|nd|rd|th)?(?:,? \d{4})?",
    r"\d{1,2}/\d{1,2}",
)
_DATE_RE = "(?:" + "|".join(_DATE_PATTERNS) + ")"
_MONEY = r"[-+(]?[$€£]?\s?\d[\d,]*\.\d{2}\)?-?(?:\s?(?:CR|DR))?"
_LINE = re.compile(rf"^\s*(?P<date>{_DATE_RE})\s+(?:(?P<post>{_DATE_RE})\s+)?(?P<rest>.+)$")
_TRAILING_MONEY = re.compile(rf"(?:\s+(?P<m>{_MONEY}))+\s*$")
_MONEY_TOKEN = re.compile(_MONEY)


@dataclass
class _TextLine:
    number: int
    raw: str
    date_text: str
    description: str
    amounts: list[str]


def _split_line(number: int, text: str) -> _TextLine | None:
    match = _LINE.match(text)
    if not match:
        return None
    rest = match.group("rest").strip()
    amounts: list[str] = []
    tail = _TRAILING_MONEY.search(rest)
    if tail:
        amounts = _MONEY_TOKEN.findall(rest[tail.start() :])
        rest = rest[: tail.start()].strip()
    return _TextLine(number, text.strip(), match.group("date"), rest, amounts)


def _parse_text_lines(text: str, *, max_rows: int, year: int | None) -> ParsedStatement:
    parsed = ParsedStatement(source_format=SourceFormat.PDF)
    lines: list[_TextLine] = []
    previous: _TextLine | None = None

    for number, raw in enumerate(text.splitlines(), start=1):
        if not raw.strip():
            continue
        line = _split_line(number, raw)
        if line is None:
            # Wrapped description: only attach short, number-free text right under a row.
            if (
                previous is not None
                and previous.number == number - 1
                and len(raw.strip()) < 50
                and not _MONEY_TOKEN.search(raw)
                and not _SUMMARY_LINE.match(raw.strip())
                and not re.search(r"page \d+|statement|balance|total", raw, re.I)
            ):
                previous.description = f"{previous.description} {raw.strip()}".strip()
            continue
        if _SUMMARY_LINE.match(line.description):
            parsed.rejected.append(RejectedRow(number, line.raw, "Summary or balance line"))
            previous = None
            continue
        if not line.amounts or not line.description:
            parsed.rejected.append(RejectedRow(number, line.raw, "No description or amount found"))
            previous = None
            continue
        lines.append(line)
        previous = line

    if not lines:
        raise FileProblem(
            "No transaction lines were found in this PDF. If it is a summary or a scan, "
            "export a CSV from your bank instead.",
            code="no_transactions_found",
        )
    if len(lines) > max_rows:
        raise FileProblem(
            f"The PDF has more than {max_rows} transactions.",
            code="too_many_rows",
            status_code=413,
        )

    order = infer_date_order(ln.date_text for ln in lines)
    dates = [parse_date(ln.date_text, order.order, year) for ln in lines]
    yearless = [not has_year(ln.date_text) for ln in lines]
    dates = fix_year_rollover(dates, yearless, year)

    directions = _directions_from_balance(lines)
    if directions is None and any(len(ln.amounts) > 1 for ln in lines):
        parsed.warnings.append(
            "Could not verify a running balance column; the first amount on each line was used."
        )

    for index, (line, when) in enumerate(zip(lines, dates, strict=True)):
        amount = parse_amount(line.amounts[0])
        if when is None:
            parsed.rejected.append(
                RejectedRow(line.number, line.raw, f"Unreadable date {line.date_text!r}")
            )
            continue
        if amount is None or amount.value == 0:
            parsed.rejected.append(RejectedRow(line.number, line.raw, "Unreadable or zero amount"))
            continue
        value = abs(amount.value)
        direction = directions[index] if directions else None
        if direction == "out":
            parsed.rows.append(RawRow(line.number, when, line.description, debit=value))
        elif direction == "in":
            parsed.rows.append(RawRow(line.number, when, line.description, credit=value))
        elif amount.suffix == "DR":
            parsed.rows.append(RawRow(line.number, when, line.description, debit=value))
        elif amount.suffix == "CR":
            parsed.rows.append(RawRow(line.number, when, line.description, credit=value))
        else:
            parsed.rows.append(RawRow(line.number, when, line.description, amount=amount.value))

    if year is not None and any(yearless):
        parsed.warnings.append(
            f"Some dates had no year; {year} was assumed from the statement text."
        )
    return parsed


def _directions_from_balance(lines: list[_TextLine]) -> list[str | None] | None:
    """Use a running balance to decide whether each line moved money in or out.

    Returns None unless every line has an amount and a balance and the balances really
    chain together (so a stray second number is never mistaken for a balance).
    """
    if len(lines) < 3 or any(len(ln.amounts) != 2 for ln in lines):
        return None
    parsed = [(parse_amount(ln.amounts[0]), parse_amount(ln.amounts[1])) for ln in lines]
    if any(a is None or b is None for a, b in parsed):
        return None
    amounts = [abs(a.value) for a, _ in parsed if a]
    balances = [b.value for _, b in parsed if b]

    ascending = sum(
        1 for i in range(1, len(lines)) if abs(balances[i] - balances[i - 1]) == amounts[i]
    )
    descending = sum(
        1 for i in range(1, len(lines)) if abs(balances[i - 1] - balances[i]) == amounts[i - 1]
    )
    best = max(ascending, descending)
    if best < 0.8 * (len(lines) - 1):
        return None

    result: list[str | None] = [None] * len(lines)
    if ascending >= descending:
        for i in range(1, len(lines)):
            result[i] = _sign_to_direction(balances[i] - balances[i - 1], amounts[i])
        # The first line has no earlier balance; its direction is inferred from the second.
        result[0] = None
    else:
        for i in range(len(lines) - 1):
            result[i] = _sign_to_direction(balances[i] - balances[i + 1], amounts[i])
        result[-1] = None
    return result


def _sign_to_direction(delta: Decimal, amount: Decimal) -> str | None:
    if abs(delta) != amount:
        return None
    return "in" if delta > 0 else "out"
