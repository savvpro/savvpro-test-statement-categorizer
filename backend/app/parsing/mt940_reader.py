"""SWIFT MT940 customer statement messages (bare tag files and block-wrapped ones)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from app.domain.models import ParsedStatement, RawRow, RejectedRow, SourceFormat
from app.errors import FileProblem
from app.parsing.csv_reader import decode_text

_FIELD = re.compile(r"^:(\d{2}[A-Z]?):(.*)$")
_BALANCE = re.compile(r"^[CD]\d{6}([A-Z]{3})\d")
_LINE61 = re.compile(
    r"^(?P<value>\d{6})(?P<entry>\d{4})?(?P<mark>RC|RD|C|D)(?P<fund>[A-Za-z])?"
    r"(?P<amount>\d+(?:,\d*)?)(?P<type>[NFS][A-Z0-9]{3})(?P<rest>.*)$"
)
_GERMAN = re.compile(r"^\s*(?:\d{3,4})?\?\d{2}")
_GERMAN_SPLIT = re.compile(r"\?(\d{2})")
_SLASH_STYLE = re.compile(r"^\s*/[A-Z]{3,5}/")
_SLASH_KEY = re.compile(r"(?:^|/)([A-Z]{3,5})/")
_CENT = Decimal("0.01")
_WRAP_WIDTH = 64  # SWIFT breaks lines at 65 characters
_SUBFIELD_WIDTH = 27  # German structured subfields are 27 characters wide
_MAX_ENTRY_GAP_DAYS = 92


@dataclass
class _Field:
    tag: str
    lines: list[str]


@dataclass
class _Group:
    fields: list[_Field] = field(default_factory=list)
    currency: str | None = None
    has_balance: bool = False

    def seal(self) -> None:
        for wanted in ("60", "62", "64", "65"):
            for item in self.fields:
                if item.tag.startswith(wanted):
                    match = _BALANCE.match(item.lines[0] if item.lines else "")
                    if match:
                        self.currency = match.group(1)
                        return


def _fields(text: str) -> list[_Field]:
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
    text = text.replace("{4:", "\n")
    out: list[_Field] = []
    current: _Field | None = None
    for line in text.split("\n"):
        match = _FIELD.match(line)
        if match:
            current = _Field(match.group(1), [match.group(2)])
            out.append(current)
        elif line.startswith("-}") or line.strip() == "-" or line.startswith("{"):
            current = None
        elif current is not None:
            current.lines.append(line)
    return out


def _groups(fields: list[_Field]) -> list[_Group]:
    groups: list[_Group] = []
    current: _Group | None = None
    for item in fields:
        starts = item.tag == "20" or (
            item.tag == "60F" and current is not None and current.has_balance
        )
        if current is None or starts:
            current = _Group()
            groups.append(current)
        current.fields.append(item)
        if item.tag in {"60F", "62F"}:
            current.has_balance = True
    for group in groups:
        group.seal()
    return groups


def _join(lines: list[str], width: int = _WRAP_WIDTH) -> str:
    """Re-join hard-wrapped lines: a full-width line was cut mid-text, so no space is added."""
    out = ""
    previous = ""
    for index, line in enumerate(lines):
        if index:
            out += "" if len(previous) >= width else " "
        out += line
        previous = line
    return " ".join(out.split())


def _structured_german(text: str) -> str:
    pieces = _GERMAN_SPLIT.split(text)
    subfields: dict[int, str] = {}
    # pieces = [prefix, code, value, code, value, ...]
    for code, value in zip(pieces[1::2], pieces[2::2], strict=False):
        subfields.setdefault(int(code), value)

    def stitch(codes: list[int]) -> str:
        out = ""
        previous = ""
        for code in codes:
            part = subfields.get(code)
            if part is None:
                continue
            if out:
                out += "" if len(previous) >= _SUBFIELD_WIDTH else " "
            out += part
            previous = part
        return " ".join(out.split())

    purpose = stitch([*range(20, 30), *range(60, 64)])
    name = stitch([32, 33])
    posting = stitch([0])
    return " ".join(p for p in (name, purpose) if p) or posting


def _structured_slash(text: str) -> str:
    matches = list(_SLASH_KEY.finditer(text))
    values: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        values.setdefault(match.group(1), text[match.end() : end])

    def tidy(value: str) -> str:
        return " ".join(value.replace("/", " ").split())

    name = next((tidy(values[k]) for k in ("NAME", "ORDP", "BENM") if k in values), "")
    remittance = tidy(values.get("REMI", ""))
    if name or remittance:
        return " ".join(p for p in (name, remittance) if p)
    skip = {"TRCD", "EREF", "MARF", "CSID", "PREF", "ISDT", "CHGS", "EXCH"}
    return " ".join(tidy(v) for k, v in values.items() if k not in skip and tidy(v))


def _information(lines: list[str]) -> str:
    text = _join(lines)
    if _GERMAN.match(text):
        return _structured_german(text) or text
    if _SLASH_STYLE.match(text):
        return _structured_slash(text) or text
    return text


def _year(two_digits: int) -> int:
    return 2000 + two_digits if two_digits < 70 else 1900 + two_digits


def _safe_date(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _booking_date(value: date, mmdd: str | None) -> date:
    """The entry date carries no year, so take the nearest one to the value date."""
    if not mmdd:
        return value
    month, day = int(mmdd[:2]), int(mmdd[2:])
    candidates = [
        d
        for year in (value.year - 1, value.year, value.year + 1)
        if (d := _safe_date(year, month, day)) is not None
    ]
    if not candidates:
        return value
    best = min(candidates, key=lambda d: abs((d - value).days))
    return best if abs((best - value).days) <= _MAX_ENTRY_GAP_DAYS else value


def _amount(text: str) -> Decimal | None:
    whole, _, frac = text.partition(",")
    if not whole:
        return None
    try:
        return Decimal(f"{whole}.{frac or '0'}").quantize(_CENT, rounding=ROUND_HALF_UP)
    except ArithmeticError:
        return None


@dataclass
class _Entry:
    ordinal: int
    statement_line: list[str]
    information: list[str] = field(default_factory=list)


def _too_many(max_rows: int) -> FileProblem:
    return FileProblem(
        f"The file has more than {max_rows} transactions. Export a shorter date range.",
        code="too_many_rows",
        status_code=413,
    )


def read_mt940(data: bytes, *, max_rows: int) -> ParsedStatement:
    try:
        return _read(data, max_rows)
    except FileProblem:
        raise
    except Exception as exc:
        raise FileProblem("This file could not be read as an MT940 statement.") from exc


def _read(data: bytes, max_rows: int) -> ParsedStatement:
    fields = _fields(decode_text(data))
    if not fields:
        raise FileProblem(
            "No MT940 fields were found in this file. Expected tags such as :20: and :61:.",
            code="file_corrupt",
        )

    parsed = ParsedStatement(source_format=SourceFormat.MT940)
    ordinal = 0

    for group in _groups(fields):
        if parsed.currency_hint is None:
            parsed.currency_hint = group.currency
        entry: _Entry | None = None
        entries: list[_Entry] = []
        for item in group.fields:
            if item.tag == "61":
                ordinal += 1
                entry = _Entry(ordinal, item.lines)
                entries.append(entry)
                if len(entries) + len(parsed.rows) + len(parsed.rejected) > max_rows:
                    raise _too_many(max_rows)
            elif item.tag == "86" and entry is not None:
                entry.information.extend(item.lines)
            elif item.tag.startswith("6") and item.tag != "61":
                entry = None  # a balance closes the run of entries
        for built in entries:
            result = _build(built, group.currency)
            if isinstance(result, RejectedRow):
                parsed.rejected.append(result)
            else:
                parsed.rows.append(result)
        if len(parsed.rows) + len(parsed.rejected) > max_rows:
            raise _too_many(max_rows)

    if not parsed.rows and not parsed.rejected:
        raise FileProblem(
            "No transactions were found in this statement.", code="no_transactions_found"
        )
    return parsed


def _build(entry: _Entry, currency: str | None) -> RawRow | RejectedRow:
    raw = " ".join(" ".join(entry.statement_line + entry.information).split())[:200]

    def reject(reason: str) -> RejectedRow:
        return RejectedRow(entry.ordinal, raw, reason)

    first = entry.statement_line[0].strip() if entry.statement_line else ""
    match = _LINE61.match(first)
    if not match:
        return reject("Unreadable :61: statement line")

    value_date = _safe_date(
        _year(int(match["value"][:2])), int(match["value"][2:4]), int(match["value"][4:])
    )
    if value_date is None:
        return reject("Impossible value date")
    amount = _amount(match["amount"])
    if amount is None:
        return reject("Unreadable amount")
    if amount <= 0:
        return reject("Zero amount")

    mark = match["mark"]
    is_debit = mark in {"D", "RC"}  # a reversal of a credit takes the money back out

    reference, _, bank_ref = match["rest"].partition("//")
    reference = reference.strip()
    bank_ref = bank_ref.strip()
    if reference.upper() == "NONREF":
        reference = ""
    supplementary = " ".join(" ".join(entry.statement_line[1:]).split())

    description = _information(entry.information)
    if not description:
        description = " ".join(p for p in (reference, supplementary) if p) or match["type"]
    if mark.startswith("R"):
        description = f"Reversal: {description}"

    return RawRow(
        line=entry.ordinal,
        date=_booking_date(value_date, match["entry"]),
        description=description,
        debit=amount if is_debit else None,
        credit=None if is_debit else amount,
        currency=currency,
        external_id=bank_ref or None,
    )
