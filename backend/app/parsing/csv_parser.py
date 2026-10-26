import csv
import io

from .columns import canonical_column
from .rows import ParsedFile, RawRow
from .values import NeedsUserChoice, UnsupportedFile, currency_hint

HEADER_SEARCH_LINES = 15  # bank exports often start with account details before the header


def _decode(data: bytes) -> str:
    if b"\x00" in data[:4096]:
        raise UnsupportedFile("This doesn't look like a text CSV file.")
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise UnsupportedFile("The CSV file's text encoding couldn't be read. Save it as UTF-8 and try again.")


def _dialect(text: str):
    try:
        return csv.Sniffer().sniff(text[:4096], delimiters=",;\t|")
    except csv.Error:
        return csv.excel


def parse_csv(data: bytes) -> ParsedFile:
    text = _decode(data)
    lines = list(csv.reader(io.StringIO(text), _dialect(text)))
    if not lines:
        raise UnsupportedFile("The CSV file is empty.")

    header_index, roles, header_currency = None, {}, None
    for index, cells in enumerate(lines[:HEADER_SEARCH_LINES]):
        found, found_currency = {}, None
        for col, cell in enumerate(cells):
            role, currency = canonical_column(cell)
            if role and role not in found:
                found[role] = col
            found_currency = found_currency or currency
        if "date" in found and "description" in found:
            header_index, roles, header_currency = index, found, found_currency
            break

    if header_index is None:
        raise UnsupportedFile(
            "Couldn't find the header row. The file needs a date column and a description column "
            "(for example 'Date' and 'Description'). The README lists every column name the app accepts."
        )
    if "amount" not in roles and not ({"debit", "credit"} & roles.keys()):
        raise UnsupportedFile(
            "Couldn't find an amount. The file needs either an 'Amount' column or 'Debit' and 'Credit' columns."
        )
    if "amount" in roles and ({"debit", "credit"} & roles.keys()):
        raise NeedsUserChoice(
            "The file has both an 'Amount' column and 'Debit'/'Credit' columns, so it isn't clear which one to trust."
        )

    def cell(cells: list[str], role: str) -> str:
        col = roles.get(role)
        return cells[col].strip() if col is not None and col < len(cells) else ""

    rows = []
    for offset, cells in enumerate(lines[header_index + 1:], start=header_index + 2):
        rows.append(RawRow(
            source_row=f"row {offset}",
            date_text=cell(cells, "date"),
            description=cell(cells, "description"),
            amount_text=cell(cells, "amount"),
            debit_text=cell(cells, "debit"),
            credit_text=cell(cells, "credit"),
            balance_text=cell(cells, "balance"),
            type_text=cell(cells, "type"),
            currency_text=cell(cells, "currency"),
        ))

    preamble = " ".join(" ".join(c) for c in lines[:header_index])
    hint = header_currency or currency_hint(preamble)
    if hint is None:
        amounts = " ".join(r.amount_text + " " + r.debit_text + " " + r.credit_text for r in rows[:50])
        hint = currency_hint(amounts)

    return ParsedFile(rows=rows, source_kind="csv", has_balance="balance" in roles, currency_hint=hint)
