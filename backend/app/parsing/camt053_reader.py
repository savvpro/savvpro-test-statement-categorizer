"""ISO 20022 bank-to-customer statements (camt.053, and camt.052/054 reports)."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from xml.etree.ElementTree import Element

from app.domain.models import ParsedStatement, RawRow, RejectedRow, SourceFormat
from app.errors import FileProblem
from app.parsing.csv_reader import decode_text

_CONTAINERS = {"Stmt", "Rpt", "Ntfctn"}
_FORBIDDEN = re.compile(r"<!\s*(?:DOCTYPE|ENTITY)", re.I)
_AMOUNT = re.compile(r"^\d{1,18}(?:\.\d{1,6})?$")
_CENT = Decimal("0.01")
# Entries that are not (yet) money movements on the account.
_SKIPPED_STATUS = {"INFO", "FUTR"}


def _local(tag: object) -> str:
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


def _children(elem: Element, name: str) -> list[Element]:
    return [c for c in elem if _local(c.tag) == name]


def _child(elem: Element | None, *path: str) -> Element | None:
    for name in path:
        if elem is None:
            return None
        found = _children(elem, name)
        elem = found[0] if found else None
    return elem


def _text(elem: Element | None) -> str:
    return " ".join("".join(elem.itertext()).split()) if elem is not None else ""


def _first_descendant(elem: Element | None, name: str) -> str:
    if elem is None:
        return ""
    for node in elem.iter():
        if _local(node.tag) == name and _text(node):
            return _text(node)
    return ""


def _clean(value: str) -> str:
    return " ".join(value.split())


def _guard_document(data: bytes) -> None:
    # Entity declarations are how XML bombs and external-entity reads are built, and no
    # statement needs them, so the document is refused before the parser sees it.
    probes = (data.replace(b"\x00", b"").decode("latin-1"), decode_text(data))
    if any(_FORBIDDEN.search(p) for p in probes):
        raise FileProblem(
            "This XML file declares a DOCTYPE or entities, which statements never need. "
            "It was not opened.",
            code="file_corrupt",
        )


def _amount(elem: Element | None) -> tuple[Decimal, Decimal, str | None] | None:
    """Return (exact, rounded, currency) for an Amt element, or None when unusable."""
    if elem is None:
        return None
    raw = (elem.text or "").strip()
    if not _AMOUNT.match(raw):
        return None
    exact = Decimal(raw)
    currency = (elem.get("Ccy") or "").strip().upper()
    return exact, exact.quantize(_CENT, rounding=ROUND_HALF_UP), currency or None


def _day(parent: Element | None) -> date | None:
    for name in ("Dt", "DtTm"):
        value = _text(_child(parent, name))[:10]
        if value:
            try:
                return date.fromisoformat(value)
            except ValueError:
                return None
    return None


def _status(entry: Element) -> str:
    node = _child(entry, "Sts")
    if node is None:
        return "BOOK"
    value = _text(_child(node, "Cd")) or _text(_child(node, "Prtry")) or _text(node)
    return value.upper() or "BOOK"


def _tx_details(entry: Element) -> list[Element]:
    out: list[Element] = []
    for details in _children(entry, "NtryDtls"):
        out.extend(_children(details, "TxDtls"))
    return out


def _code_text(entry: Element) -> str:
    code = _child(entry, "BkTxCd")
    if code is None:
        return ""
    prtry = _text(_child(code, "Prtry", "Cd"))
    if prtry:
        return prtry
    domain = _child(code, "Domn")
    parts = [
        _text(_child(domain, "Cd")),
        _text(_child(domain, "Fmly", "Cd")),
        _text(_child(domain, "Fmly", "SubFmlyCd")),
    ]
    return "/".join(p for p in parts if p)


def _describe(entry: Element, scopes: list[Element], debit: bool) -> str:
    """Pick the most human description, scanning the transaction scopes before the entry."""
    pieces: list[str] = []
    for scope in scopes:
        for rmt in _children(scope, "RmtInf"):
            pieces.extend(_clean(_text(u)) for u in _children(rmt, "Ustrd"))
    if joined := _clean(" ".join(p for p in pieces if p)):
        return joined

    for scope in scopes:
        if text := _clean(_text(_child(scope, "AddtlTxInf"))):
            return text

    party = "Cdtr" if debit else "Dbtr"
    for scope in scopes:
        name = _first_descendant(_child(scope, "RltdPties", party), "Nm")
        if name:
            return _clean(name)

    if text := _clean(_text(_child(entry, "AddtlNtryInf"))):
        return text
    for details in _children(entry, "NtryDtls"):
        if text := _clean(_text(_child(details, "Btch", "PmtInfId"))):
            return text
    return _code_text(entry)


def _split_batch(
    entry: Element, total: Decimal, currency: str | None
) -> list[tuple[Element, Decimal]] | None:
    """TxDtls blocks with their amounts, when they each carry one and add up to the entry."""
    details = _tx_details(entry)
    if len(details) < 2:
        return None
    parts: list[tuple[Element, Decimal]] = []
    running = Decimal(0)
    for tx in details:
        parsed = _amount(_child(tx, "Amt"))
        if parsed is None or parsed[0] <= 0 or parsed[1] <= 0:
            return None
        if parsed[2] and currency and parsed[2] != currency:
            return None
        running += parsed[0]
        parts.append((tx, parsed[1]))
    return parts if running == total else None


def _excerpt(entry: Element) -> str:
    return " ".join("".join(entry.itertext()).split())[:200]


def _statements(root: Element) -> list[Element]:
    return [node for node in root.iter() if _local(node.tag) in _CONTAINERS]


def _ccy(amt: Element | None) -> str | None:
    value = (amt.get("Ccy") if amt is not None else None) or ""
    return value.strip().upper() or None


def _statement_currency(container: Element, entries: list[Element]) -> str | None:
    for path in (("Acct", "Ccy"), ("Acct", "Id", "Othr", "Ccy")):
        value = _text(_child(container, *path)).upper()
        if value:
            return value
    for bal in _children(container, "Bal"):
        code = _text(_child(bal, "Tp", "CdOrPrtry", "Cd"))
        if code == "OPBD" and (currency := _ccy(_child(bal, "Amt"))):
            return currency
    for entry in entries:
        if currency := _ccy(_child(entry, "Amt")):
            return currency
    return None


def _too_many(max_rows: int) -> FileProblem:
    return FileProblem(
        f"The file has more than {max_rows} transactions. Export a shorter date range.",
        code="too_many_rows",
        status_code=413,
    )


def read_camt053(data: bytes, *, max_rows: int) -> ParsedStatement:
    try:
        return _read(data, max_rows)
    except FileProblem:
        raise
    except Exception as exc:
        raise FileProblem("This file could not be read as an ISO 20022 statement.") from exc


def _read(data: bytes, max_rows: int) -> ParsedStatement:
    _guard_document(data)
    try:
        root = ET.fromstring(data)
    except Exception as exc:
        raise FileProblem("This file is not well-formed XML.", code="file_corrupt") from exc

    containers = _statements(root)
    if not containers:
        raise FileProblem(
            "No statement was found in this XML file. Expected an ISO 20022 camt.053 document.",
            code="file_corrupt",
        )

    parsed = ParsedStatement(source_format=SourceFormat.CAMT053)
    ordinal = 0
    pending = 0
    skipped = 0

    for container in containers:
        entries = _children(container, "Ntry")
        if parsed.currency_hint is None:
            parsed.currency_hint = _statement_currency(container, entries)
        for entry in entries:
            ordinal += 1
            status = _status(entry)
            if status in _SKIPPED_STATUS:
                skipped += 1
                continue
            if status == "PDNG":
                pending += 1

            rows = _entry_rows(entry, ordinal)
            if isinstance(rows, RejectedRow):
                parsed.rejected.append(rows)
            else:
                parsed.rows.extend(rows)
            if len(parsed.rows) + len(parsed.rejected) > max_rows:
                raise _too_many(max_rows)

    if not parsed.rows and not parsed.rejected:
        raise FileProblem(
            "No transactions were found in this statement.", code="no_transactions_found"
        )
    if pending:
        parsed.warnings.append(f"{pending} pending entries included")
    if skipped:
        parsed.warnings.append(f"{skipped} informational entries were skipped")
    return parsed


def _entry_rows(entry: Element, ordinal: int) -> list[RawRow] | RejectedRow:
    def reject(reason: str) -> RejectedRow:
        return RejectedRow(ordinal, _excerpt(entry), reason)

    amount = _amount(_child(entry, "Amt"))
    if amount is None:
        return reject("Missing or unreadable amount")
    exact, value, currency = amount
    if value <= 0:
        return reject("Zero amount")

    indicator = _text(_child(entry, "CdtDbtInd")).upper()
    if indicator not in {"CRDT", "DBIT"}:
        return reject("Missing credit/debit indicator")
    reversal = _text(_child(entry, "RvslInd")).lower() in {"true", "1"}
    stated_debit = indicator == "DBIT"
    is_debit = stated_debit != reversal

    booked = _day(_child(entry, "BookgDt")) or _day(_child(entry, "ValDt"))
    if booked is None:
        return reject("Missing or unreadable booking date")

    external_id = _clean(_text(_child(entry, "AcctSvcrRef")) or _text(_child(entry, "NtryRef")))
    prefix = "Reversal: " if reversal else ""
    batch = _split_batch(entry, exact, currency)

    def build(amt: Decimal, description: str, ref: str) -> RawRow:
        return RawRow(
            line=ordinal,
            date=booked,
            description=prefix + (description or "Bank transaction"),
            debit=amt if is_debit else None,
            credit=None if is_debit else amt,
            currency=currency,
            external_id=ref or None,
        )

    if batch is not None:
        rows = []
        for tx, part in batch:
            tx_ref = _clean(_text(_child(tx, "Refs", "AcctSvcrRef"))) or external_id
            rows.append(build(part, _describe(entry, [tx], stated_debit), tx_ref))
        return rows

    return [build(value, _describe(entry, _tx_details(entry), stated_debit), external_id)]
