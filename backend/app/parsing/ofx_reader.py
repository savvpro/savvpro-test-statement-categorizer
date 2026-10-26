"""OFX and QFX bank exports (SGML v1 and XML v2 both work)."""

from __future__ import annotations

import re
from datetime import date

from app.domain.models import Convention, ParsedStatement, RawRow, RejectedRow, SourceFormat
from app.errors import FileProblem
from app.parsing.amounts import parse_amount
from app.parsing.csv_reader import decode_text

_BLOCK = re.compile(
    r"<STMTTRN>(.*?)(?=</STMTTRN>|<STMTTRN>|</BANKTRANLIST>|</CCSTMTRS>|</STMTRS>|\Z)",
    re.S | re.I,
)
_CURDEF = re.compile(r"<CURDEF>\s*([A-Za-z]{3})", re.I)


def _tag(block: str, name: str) -> str:
    match = re.search(rf"<{name}>\s*([^<\r\n]*)", block, re.I)
    return match.group(1).strip() if match else ""


def read_ofx(data: bytes, *, max_rows: int) -> ParsedStatement:
    text = decode_text(data)
    blocks = _BLOCK.findall(text)
    if not blocks:
        raise FileProblem(
            "No transactions were found in this OFX file.", code="no_transactions_found"
        )
    if len(blocks) > max_rows:
        raise FileProblem(
            f"The file has more than {max_rows} transactions. Export a shorter date range.",
            code="too_many_rows",
            status_code=413,
        )

    currency = _CURDEF.search(text)
    parsed = ParsedStatement(
        source_format=SourceFormat.OFX,
        convention_hint=Convention.NEGATIVE_IS_SPENDING,
        currency_hint=currency.group(1).upper() if currency else None,
    )
    seen_ids: set[str] = set()
    repeated = 0

    for number, block in enumerate(blocks, start=1):
        raw = " ".join(block.split())[:200]
        posted = re.match(r"(\d{4})(\d{2})(\d{2})", _tag(block, "DTPOSTED"))
        amount = parse_amount(_tag(block, "TRNAMT"))
        if not posted:
            parsed.rejected.append(RejectedRow(number, raw, "Missing or unreadable posting date"))
            continue
        if amount is None or amount.value == 0:
            parsed.rejected.append(RejectedRow(number, raw, "Missing, zero or unreadable amount"))
            continue
        try:
            when = date(int(posted.group(1)), int(posted.group(2)), int(posted.group(3)))
        except ValueError:
            parsed.rejected.append(RejectedRow(number, raw, "Impossible posting date"))
            continue

        fitid = _tag(block, "FITID")
        if fitid:
            if fitid in seen_ids:
                repeated += 1
                continue
            seen_ids.add(fitid)

        name, memo = _tag(block, "NAME"), _tag(block, "MEMO")
        description = name if not memo or memo.lower() in name.lower() else f"{name} {memo}".strip()
        description = description or memo or _tag(block, "TRNTYPE")
        if not description:
            parsed.rejected.append(RejectedRow(number, raw, "Missing description"))
            continue
        parsed.rows.append(
            RawRow(number, when, description, amount=amount.value, external_id=fitid or None)
        )

    if repeated:
        parsed.warnings.append(f"{repeated} repeated transaction id(s) in the file were ignored.")
    return parsed
