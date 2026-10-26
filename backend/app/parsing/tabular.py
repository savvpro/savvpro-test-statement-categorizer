"""Turn a grid of cells (from CSV, Excel or a PDF table) into raw transaction rows.

The grid is just a list of rows of strings; everything format-specific happens before
this point, everything about statement semantics (which column is what, how dates and
amounts are written) happens here.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.domain.models import ParsedStatement, RawRow, RejectedRow, SourceFormat
from app.errors import FileProblem
from app.parsing.amounts import CURRENCY_CODES, ParsedAmount, detect_currency, parse_amount
from app.parsing.dates import (
    DMY,
    fix_year_rollover,
    has_year,
    infer_date_order,
    parse_date,
)

Grid = Sequence[Sequence[str]]

# -- header vocabulary --------------------------------------------------------------------
# Labels are compared after normalisation (see `normalize_label`): lowercase, accents and
# symbols removed, text inside brackets dropped. Aliases below are written in that form.
# Each tuple is one preference tier; earlier tiers win when a file has several candidates.

_DATE_TIERS: tuple[tuple[str, ...], ...] = (
    (
        "date", "transaction date", "trans date", "txn date", "tran date", "purchase date",
        "date of transaction", "date of purchase", "datum", "fecha", "fecha operacion",
        "fecha de operacion", "fecha transaccion", "fecha de transaccion", "date operation",
        "date de l operation", "date d operation", "transactiedatum", "datum transactie",
        "date time", "datetime", "transaction date time",
    ),
    (
        "booking date", "book date", "buchungstag", "buchungsdatum", "boekdatum",
        "boekingsdatum", "fecha contable", "date comptable", "date de comptabilisation",
        "accounting date",
    ),
    (
        "posting date", "post date", "posted date", "posted", "date posted", "processing date",
        "clearing date", "fecha de registro",
    ),
    (
        "value date", "valuta", "valutadatum", "wertstellung", "fecha valor", "date de valeur",
        "interest date", "rentedatum", "settlement date", "date de reglement", "effective date",
    ),
)  # fmt: skip

_MERCHANT = (
    "merchant", "merchant name", "payee", "payee name", "counterparty", "supplier",
    "supplier name", "vendor", "beneficiary", "beneficiary name", "empfaenger", "empfanger",
    "tegenpartij", "begunstigde", "naam", "nom", "beneficiaire", "tiers", "comercio",
    "beneficiario", "other party",
)  # fmt: skip
_DETAIL = (
    "description", "transaction description", "details", "transaction details", "narrative",
    "narration", "particulars", "memo", "libelle", "descripcion", "concepto", "omschrijving",
    "beschreibung", "buchungstext", "verwendungszweck", "remarks", "transaction remarks",
    "description of transaction", "merchant name or transaction description",
    "merchant or description", "mededelingen", "naam omschrijving", "transaction narrative",
    "detail", "text", "libelle de l operation", "libelle operation", "descripcion operacion",
)  # fmt: skip
_WEAK_DESCRIPTION = (
    "name", "reference", "ref", "payment reference", "transaction", "note", "notes", "comment",
)  # fmt: skip

_AMOUNT = (
    "amount", "amt", "transaction amount", "gross amount", "net amount", "total amount",
    "transaction value", "value", "betrag", "importe", "montant", "bedrag", "amount in", "sum",
    "monto", "umsatz", "valor",
)  # fmt: skip
_DEBIT = (
    "debit", "debits", "debit amount", "withdrawal", "withdrawals", "withdrawn", "money out",
    "paid out", "payments out", "payment out", "charge", "outgoing", "expense", "expenses", "dr",
    "soll", "debe", "cargo", "cargos", "retrait", "retraits", "cheques et debits", "af",
    "sortie", "sorties", "debito", "ausgaben", "uitgaven", "amount debited", "debited", "spent",
    "debet",
)  # fmt: skip
_CREDIT = (
    "credit", "credits", "credit amount", "deposit", "deposits", "money in", "paid in",
    "payments in", "payment in", "cr", "incoming", "income", "haben", "haber", "abono",
    "abonos", "ingreso", "ingresos", "depots et credits", "depot", "depots", "bij", "received",
    "amount credited", "credited", "entrada", "entradas", "einnahmen", "inkomsten", "credito",
)  # fmt: skip
_BALANCE = (
    "balance", "running balance", "closing balance", "available balance", "solde", "saldo",
    "saldo disponible", "kontostand", "account balance", "ledger balance", "balance after",
    "balance after transaction", "saldo na mutatie", "solde apres operation", "running bal",
    "bal", "balance amount",
)  # fmt: skip
_CURRENCY = (
    "currency", "ccy", "cur", "waehrung", "wahrung", "moneda", "devise", "munteenheid",
)  # fmt: skip
_DIRECTION = (
    "af bij", "debit credit", "dr cr", "cr dr", "d c", "c d", "debit credit indicator",
    "credit debit indicator", "cr dr indicator", "dc", "dc indicator", "sens", "soll haben",
    "s h",
)  # fmt: skip

DATE = "date"
MERCHANT = "merchant"
DETAIL = "detail"
WEAK = "weak"
AMOUNT = "amount"
DEBIT = "debit"
CREDIT = "credit"
BALANCE = "balance"
CURRENCY = "currency"
DIRECTION = "direction"
MONEY_ROLES = (AMOUNT, DEBIT, CREDIT, BALANCE)

_ALIASES: dict[str, tuple[str, int]] = {}


def _register(role: str, names: Sequence[str], rank: int = 0) -> None:
    for name in names:
        _ALIASES.setdefault(name, (role, rank))


for _rank, _names in enumerate(_DATE_TIERS):
    _register(DATE, _names, _rank)
_register(MERCHANT, _MERCHANT)
_register(DETAIL, _DETAIL)
_register(WEAK, _WEAK_DESCRIPTION)
_register(AMOUNT, _AMOUNT)
_register(DEBIT, _DEBIT)
_register(CREDIT, _CREDIT)
_register(BALANCE, _BALANCE)
_register(CURRENCY, _CURRENCY)
_register(DIRECTION, _DIRECTION)
_MAX_ALIAS_WORDS = max(len(name.split()) for name in _ALIASES)

_OUT_WORDS = frozenset(
    {"af", "debit", "dr", "d", "db", "debet", "soll", "s", "out", "withdrawal", "debe", "sortie"}
)
_IN_WORDS = frozenset(
    {"bij", "credit", "cr", "c", "cred", "haben", "h", "in", "deposit", "haber", "entree"}
)

_SUMMARY_LINE = re.compile(
    r"""^(
        (sub|grand\s+)?totals?(\s*:|\s*$|\s+(debits?|credits?|withdrawals?|deposits?|charges|
            payments|purchases|fees|interest|amount|no\b|number|for\b|this|new|previous|
            des\b|de\b|[-$€£(\d]))
      | totaal | opening\s+balance | closing\s+balance | balance\s+(brought|carried|forward|b/f|c/f)
      | brought\s+forward | carried\s+forward | previous\s+balance | new\s+balance
      | statement\s+(period|balance|date) | ending\s+balance | beginning\s+balance
      | solde\s+(d.ouverture|de\s+fermeture|initial|final|precedent|reporte|ancien|nouveau)
      | saldo\s+(inicial|final|anterior|previo) | page\s+\d+ | account\s+summary
    )""",
    re.I | re.X,
)
_OPENING_LINE = re.compile(
    r"""^(opening\s+balance|beginning\s+balance|previous\s+balance|balance\s+(brought\s+)?forward
        |balance\s+b/f|brought\s+forward|solde\s+(d.ouverture|initial|precedent|reporte|ancien)
        |saldo\s+(inicial|anterior|previo))""",
    re.I | re.X,
)

# Dollar-like currencies are left out: "$" alone cannot say which dollar a file uses, and
# month/day/year is the safer reading of those.
_DAY_FIRST_CURRENCIES = frozenset(CURRENCY_CODES) - {
    "USD", "CAD", "JPY", "CNY", "KRW", "PHP",
}  # fmt: skip


@dataclass(frozen=True)
class ColumnMap:
    date: int
    description: int
    amount: int | None
    debit: int | None
    credit: int | None
    currency: int | None
    header_index: int
    # Added for bank-style layouts. Everything below has a default so older call sites work.
    extra_description: tuple[int, ...] = ()
    balance: int | None = None
    direction: int | None = None
    header_currency: str | None = None


@dataclass(frozen=True)
class HeaderHit:
    """A header phrase recognised on a line of words (used for PDF headers)."""

    role: str
    rank: int
    first: int  # index of the first token covered, including attached symbols
    last: int  # index of the last token covered, including attached "(-)" style marks
    currency: str | None


def _clean(cell: object) -> str:
    return re.sub(r"\s+", " ", str(cell if cell is not None else "")).strip()


_BRACKETED = re.compile(r"[(\[{][^)\]}]*(?:[)\]}]|$)")


def normalize_label(text: object) -> str:
    """Reduce a header label to lowercase ASCII words for alias matching.

    "Gross Amount (£)" -> "gross amount", "$ Amount" -> "amount", "Libellé" -> "libelle".
    """
    raw = str(text if text is not None else "")
    stripped = _BRACKETED.sub(" ", raw)
    if not stripped.strip():
        stripped = raw  # a label that is only a bracket, e.g. "(Amount)"
    decomposed = unicodedata.normalize("NFKD", stripped)
    ascii_only = decomposed.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", " ", ascii_only).strip()


def classify_label(label: object) -> tuple[str, int, str | None] | None:
    """Role, preference rank and currency (if the label names one) for a header label."""
    norm = normalize_label(label)
    if not norm:
        return None
    hit = _ALIASES.get(norm)
    currency = None
    if hit is None:
        # "Amount EUR" or "Bedrag eur": a trailing currency code is not part of the name.
        words = norm.split()
        if len(words) > 1 and words[-1].upper() in CURRENCY_CODES:
            hit = _ALIASES.get(" ".join(words[:-1]))
            currency = words[-1].upper()
    if hit is None:
        return None
    role, rank = hit
    if role in MONEY_ROLES and currency is None:
        currency = detect_currency(str(label))
    return role, rank, currency


def scan_header_tokens(tokens: Sequence[str]) -> tuple[list[HeaderHit], int, int]:
    """Find header phrases in the words of one visual line.

    Returns the hits (left to right), the number of word tokens they cover and the number of
    word tokens that were considered at all. Bracketed marks like "(-)" and bare symbols are
    not counted as words; they are folded into the neighbouring hit.
    """
    word_at: dict[int, str] = {}
    bracketed: set[int] = set()
    in_bracket = False
    for index, token in enumerate(tokens):
        closes = any(ch in token for ch in ")]}")
        if in_bracket or token[:1] in ("(", "[", "{"):
            bracketed.add(index)
            in_bracket = not closes
        else:
            norm = normalize_label(token)
            if norm:
                word_at[index] = norm
    words = sorted(word_at.items())

    hits: list[HeaderHit] = []
    covered = 0
    previous_end = -1
    i = 0
    while i < len(words):
        for length in range(min(_MAX_ALIAS_WORDS, len(words) - i), 0, -1):
            phrase = " ".join(w for _, w in words[i : i + length])
            found = _ALIASES.get(phrase)
            if found is None:
                continue
            if found[0] == DIRECTION and length > 1:
                continue  # side by side "Debit Credit" headings are two columns, not one flag
            start, end = words[i][0], words[i + length - 1][0]
            while end + 1 < len(tokens) and end + 1 in bracketed:
                end += 1
            while (
                start - 1 > previous_end and start - 1 not in word_at and start - 1 not in bracketed
            ):
                start -= 1
            role, rank = found
            currency = detect_currency(" ".join(tokens[start : end + 1]))
            hits.append(
                HeaderHit(role, rank, start, end, currency if role in MONEY_ROLES else None)
            )
            previous_end = end
            covered += length
            i += length
            break
        else:
            i += 1
    if hits:
        # A bare symbol after the last word ("Amount $") belongs to that heading.
        last = hits[-1]
        end = last.last
        while end + 1 < len(tokens) and end + 1 not in word_at:
            end += 1
        if end != last.last:
            currency = detect_currency(" ".join(tokens[last.first : end + 1]))
            hits[-1] = HeaderHit(
                last.role, last.rank, last.first, end,
                (currency or last.currency) if last.role in MONEY_ROLES else None,
            )  # fmt: skip
    return hits, covered, len(words)


def _best(candidates: list[tuple[int, int]]) -> int | None:
    """Column with the best (lowest) rank, leftmost on a tie."""
    return min(candidates, key=lambda c: (c[1], c[0]))[0] if candidates else None


def select_columns(
    labels: Sequence[tuple[int, str, int, str | None]], header_index: int
) -> ColumnMap | None:
    """Pick one column per role from classified header cells: (column, role, rank, currency)."""
    by_role: dict[str, list[tuple[int, int]]] = {}
    currencies: list[str] = []
    for col, role, rank, currency in labels:
        by_role.setdefault(role, []).append((col, rank))
        if currency:
            currencies.append(currency)
    date_col = _best(by_role.get(DATE, []))
    merchant = _best(by_role.get(MERCHANT, []))
    detail = _best(by_role.get(DETAIL, []))
    weak = _best(by_role.get(WEAK, []))
    ordered = [c for c in (merchant, detail) if c is not None]
    if not ordered and weak is not None:
        ordered = [weak]
    amount = _best(by_role.get(AMOUNT, []))
    debit = _best(by_role.get(DEBIT, []))
    credit = _best(by_role.get(CREDIT, []))
    if date_col is None or not ordered or (amount is None and debit is None and credit is None):
        return None
    return ColumnMap(
        date=date_col,
        description=ordered[0],
        amount=amount,
        debit=debit,
        credit=credit,
        currency=_best(by_role.get(CURRENCY, [])),
        header_index=header_index,
        extra_description=tuple(ordered[1:]),
        balance=_best(by_role.get(BALANCE, [])),
        direction=_best(by_role.get(DIRECTION, [])),
        header_currency=currencies[0] if currencies else None,
    )


def find_columns(grid: Grid, max_scan: int = 40) -> ColumnMap | None:
    """Locate the header row within the first rows and map its columns to roles."""
    for index, row in enumerate(grid[:max_scan]):
        labels: list[tuple[int, str, int, str | None]] = []
        for col, cell in enumerate(row):
            found = classify_label(cell)
            if found is not None:
                labels.append((col, *found))
        columns = select_columns(labels, index)
        if columns is not None:
            return columns
    return None


def _cell(row: Sequence[str], index: int | None) -> str:
    if index is None or index >= len(row):
        return ""
    return _clean(row[index])


def join_description(texts: Sequence[str]) -> str:
    """Join description parts, leaving out one that only repeats another."""
    parts: list[str] = []
    for text in texts:
        if not text:
            continue
        lowered = text.lower()
        if any(lowered in p.lower() for p in parts):
            continue
        parts = [p for p in parts if p.lower() not in lowered]
        parts.append(text)
    return " ".join(parts)


def _description(row: Sequence[str], columns: ColumnMap) -> str:
    return join_description(
        [_cell(row, index) for index in (columns.description, *columns.extra_description)]
    )


@dataclass
class _Entry:
    line: int
    date: date
    yearless: bool
    description: str
    debit: Decimal | None
    credit: Decimal | None
    amount: Decimal | None
    currency: str | None
    balance: Decimal | None
    opening: Decimal | None  # balance printed on a "brought forward" line just before this row

    @property
    def magnitude(self) -> Decimal:
        for value in (self.debit, self.credit, self.amount):
            if value is not None:
                return abs(value)
        return Decimal(0)


def grid_to_statement(
    grid: Grid,
    source_format: SourceFormat,
    *,
    max_rows: int,
    default_year: int | None = None,
    line_numbers: Sequence[int] | None = None,
) -> ParsedStatement:
    columns = find_columns(grid)
    if columns is None:
        raise FileProblem(
            "Could not find a header row with date, description and amount columns. "
            "Check that the file is a transaction export and not a summary page.",
            code="missing_columns",
        )

    body = [(i, list(r)) for i, r in enumerate(grid) if i > columns.header_index]
    body = [(i, r) for i, r in body if any(_clean(c) for c in r)]
    if len(body) > max_rows:
        raise FileProblem(
            f"The file has more than {max_rows} rows. Split it by month and upload again.",
            code="too_many_rows",
            status_code=413,
        )

    hint = _currency_hint(body, columns)
    parsed = ParsedStatement(source_format=source_format, currency_hint=hint)
    order = infer_date_order(_cell(r, columns.date) for _, r in body)
    date_order = order.order
    day_first_by_locale = order.ambiguous and hint in _DAY_FIRST_CURRENCIES
    if day_first_by_locale:
        date_order = DMY
    if order.ambiguous and any(
        re.match(r"^\d{1,2}[-/.]\d{1,2}(?:[-/.]\d{2,4})?(?!\d)", _cell(r, columns.date))
        for _, r in body
    ):
        if day_first_by_locale:
            parsed.warnings.append(
                f"Dates like 03/04/2026 can be read two ways; assumed day/month/year because "
                f"the amounts are in {hint}. Check the first rows if that is wrong."
            )
        else:
            parsed.warnings.append(
                "Dates like 03/04/2026 can be read two ways; assumed month/day/year. "
                "Check the first rows if your bank uses day/month/year."
            )

    entries: list[_Entry] = []
    pending_opening: Decimal | None = None
    for index, row in body:
        line = line_numbers[index] if line_numbers else index + 1
        raw_text = ", ".join(_clean(c) for c in row if _clean(c))
        description = _description(row, columns)
        date_text = _cell(row, columns.date)

        if _SUMMARY_LINE.match(description) or _SUMMARY_LINE.match(date_text):
            if _OPENING_LINE.match(description):
                value = _opening_value(row, columns)
                if value is not None:
                    pending_opening = value
            parsed.rejected.append(
                RejectedRow(line, raw_text, "Summary or balance line, not a transaction")
            )
            continue

        if not date_text and description and not _has_money(row, columns) and entries:
            previous = entries[-1]
            if description.lower() not in previous.description.lower():
                previous.description = f"{previous.description} {description}"
            continue

        row_date = parse_date(date_text, date_order, default_year)
        if row_date is None:
            parsed.rejected.append(RejectedRow(line, raw_text, f"Unreadable date {date_text!r}"))
            continue
        if not description:
            parsed.rejected.append(RejectedRow(line, raw_text, "Missing description"))
            continue

        built = _read_money(row, columns)
        if isinstance(built, str):
            parsed.rejected.append(RejectedRow(line, raw_text, built))
            continue
        currency = _cell(row, columns.currency).upper() or None
        if currency and not re.fullmatch(r"[A-Z]{3}", currency):
            currency = None
        balance = None
        if columns.balance is not None:
            balance = _parse_balance(_cell(row, columns.balance))
        entries.append(
            _Entry(
                line, row_date, not has_year(date_text), description, built[0], built[1],
                built[2], currency, balance, pending_opening,
            )
        )  # fmt: skip
        pending_opening = None

    _resolve_years(entries, default_year)
    if default_year is not None and any(e.yearless for e in entries):
        parsed.warnings.append(
            f"Some dates had no year; {default_year} was assumed from the statement text."
        )
    _emit_rows(entries, columns, parsed)
    return parsed


def _has_money(row: Sequence[str], columns: ColumnMap) -> bool:
    return any(
        _cell(row, c) for c in (columns.amount, columns.debit, columns.credit) if c is not None
    )


def _resolve_years(entries: list[_Entry], default_year: int | None) -> None:
    if default_year is None or not entries:
        return
    fixed = fix_year_rollover(
        [e.date for e in entries], [e.yearless for e in entries], default_year
    )
    for entry, when in zip(entries, fixed, strict=True):
        if when is not None:
            entry.date = when


def _opening_value(row: Sequence[str], columns: ColumnMap) -> Decimal | None:
    for index in (columns.balance, columns.amount):
        if index is None:
            continue
        value = _parse_balance(_cell(row, index))
        if value is not None:
            return value
    return None


def _parse_balance(text: str) -> Decimal | None:
    parsed = parse_amount(text) if text else None
    if parsed is None:
        return None
    # A balance followed by DR is overdrawn; CR is the normal positive balance.
    return -abs(parsed.value) if parsed.suffix == "DR" else parsed.value


def _currency_hint(body: list[tuple[int, list[str]]], columns: ColumnMap) -> str | None:
    if columns.currency is not None:
        codes = Counter(
            c.upper()
            for _, r in body
            if (c := _cell(r, columns.currency)) and re.fullmatch(r"[A-Za-z]{3}", c)
        )
        if codes and codes.most_common(1)[0][1] >= 0.5 * sum(codes.values()):
            return codes.most_common(1)[0][0]
    if columns.header_currency:
        return columns.header_currency
    votes: Counter[str] = Counter()
    total = 0
    for _, r in body:
        for index in (columns.amount, columns.debit, columns.credit):
            text = _cell(r, index)
            if not text:
                continue
            total += 1
            found = detect_currency(text)
            if found:
                votes[found] += 1
    if votes and votes.most_common(1)[0][1] >= 0.6 * total:
        return votes.most_common(1)[0][0]
    return None


def _direction_of(cell: str) -> str | None:
    word = re.sub(r"[^a-z]", "", normalize_label(cell))
    if word in _OUT_WORDS:
        return "out"
    if word in _IN_WORDS:
        return "in"
    return None


def _read_money(
    row: Sequence[str], columns: ColumnMap
) -> tuple[Decimal | None, Decimal | None, Decimal | None] | str:
    """(debit, credit, signed amount) for a row, or the reason it cannot be read."""
    debit_cell = _cell(row, columns.debit)
    credit_cell = _cell(row, columns.credit)
    if columns.debit is not None or columns.credit is not None:
        debit = parse_amount(debit_cell) if debit_cell else None
        credit = parse_amount(credit_cell) if credit_cell else None
        if debit_cell and debit is None:
            return f"Unreadable debit amount {debit_cell!r}"
        if credit_cell and credit is None:
            return f"Unreadable credit amount {credit_cell!r}"
        if debit is None and credit is None and columns.amount is None:
            return "No amount on this line"
        if debit is not None or credit is not None:
            out = abs(debit.value) if debit else None
            into = abs(credit.value) if credit else None
            if out and into:
                return "Both debit and credit are filled in"
            if (out is None or out == 0) and (into is None or into == 0):
                return "Zero amount"
            return out or None, into or None, None

    amount_cell = _cell(row, columns.amount)
    if not amount_cell:
        return "No amount on this line"
    amount = parse_amount(amount_cell)
    if amount is None:
        return f"Unreadable amount {amount_cell!r}"
    if amount.value == 0:
        return "Zero amount"
    return _from_single_amount(amount, _direction_of(_cell(row, columns.direction)))


def _from_single_amount(
    amount: ParsedAmount, direction: str | None
) -> tuple[Decimal | None, Decimal | None, Decimal | None]:
    magnitude = abs(amount.value)
    if amount.suffix == "DR" or (amount.suffix is None and direction == "out"):
        return magnitude, None, None
    if amount.suffix == "CR" or (amount.suffix is None and direction == "in"):
        return None, magnitude, None
    return None, None, amount.value


def _delta(entries: list[_Entry], i: int) -> Decimal | None:
    current, previous = entries[i].balance, entries[i - 1].balance
    return None if current is None or previous is None else current - previous


def _balance_directions(entries: list[_Entry]) -> list[str | None] | None:
    """Per row "in"/"out" read from a running balance, or None when it does not chain.

    The balances must really follow from the amounts (so a stray second number is never
    mistaken for a balance). Both file orders are tried: oldest first and newest first.
    """
    known = [i for i, e in enumerate(entries) if e.balance is not None]
    if len(known) < 2:
        return None
    oldest_first = [
        _delta(entries, i) if _both(entries, i - 1, i) else None for i in range(1, len(entries))
    ]
    matches_asc = sum(
        1
        for i, delta in enumerate(oldest_first, start=1)
        if delta is not None and abs(delta) == entries[i].magnitude
    )
    matches_desc = sum(
        1
        for i, delta in enumerate(oldest_first, start=1)
        if delta is not None and abs(delta) == entries[i - 1].magnitude
    )
    testable = sum(1 for d in oldest_first if d is not None)
    best = max(matches_asc, matches_desc)
    if testable == 0 or best < max(1 if testable <= 2 else 2, 0.7 * testable):
        return None

    result: list[str | None] = [None] * len(entries)
    if matches_asc >= matches_desc:
        for i, entry in enumerate(entries):
            before = entries[i - 1].balance if i else entry.opening
            if entry.balance is None or before is None:
                continue
            result[i] = _delta_direction(entry.balance - before, entry.magnitude)
    else:
        for i, entry in enumerate(entries[:-1]):
            after = entries[i + 1].balance
            if entry.balance is None or after is None:
                continue
            result[i] = _delta_direction(entry.balance - after, entry.magnitude)
    return result


def _both(entries: list[_Entry], a: int, b: int) -> bool:
    return entries[a].balance is not None and entries[b].balance is not None


def _delta_direction(delta: Decimal, magnitude: Decimal) -> str | None:
    if magnitude == 0 or abs(delta) != magnitude:
        return None
    return "in" if delta > 0 else "out"


def _emit_rows(entries: list[_Entry], columns: ColumnMap, parsed: ParsedStatement) -> None:
    chain = _balance_directions(entries) if columns.balance is not None else None
    if columns.balance is not None and chain is None and any(e.amount is not None for e in entries):
        parsed.warnings.append(
            "Could not verify a running balance column; amounts were kept as printed."
        )
    for index, entry in enumerate(entries):
        direction = chain[index] if chain else None
        magnitude = entry.magnitude
        if direction is None and entry.amount is not None:
            row = RawRow(
                entry.line, entry.date, entry.description, amount=entry.amount,
                currency=entry.currency,
            )  # fmt: skip
        else:
            if direction is None:
                direction = "out" if entry.debit is not None else "in"
            row = RawRow(
                entry.line,
                entry.date,
                entry.description,
                debit=magnitude if direction == "out" else None,
                credit=magnitude if direction == "in" else None,
                currency=entry.currency,
            )
        parsed.rows.append(row)
