"""ParseResult -> Transaction[]: signs, directions, cleaned text, merchant keys, fingerprints."""

import hashlib
import re
import unicodedata
from collections import Counter
from datetime import date
from decimal import Decimal

from app.domain.enums import AccountType, Direction
from app.domain.models import ParseResult, ParseWarning, RawTransaction, Transaction
from app.ingest import amounts, dates
from app.normalize.merchant import clean_description

MAX_DESCRIPTION = 512
_CARD_PAYMENT_RE = re.compile(
    r"\b(PAYMENT|PMT|AUTOPAY|AUTO PAY|THANK YOU|ONLINE PYMT)\b", re.IGNORECASE
)
_PENDING_RE = re.compile(r"\bPENDING\b", re.IGNORECASE)
_SPACE_RE = re.compile(r"\s+")
_CHARGE_FRACTION = 0.6


def _tidy(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = "".join(c for c in text if c.isprintable() or c in " \t")
    return _SPACE_RE.sub(" ", text).strip()


def make_fingerprint(
    account_type: AccountType, posted: date, amount_cents: int, merchant_key: str, occurrence: int
) -> str:
    raw = f"{account_type.value}|{posted.isoformat()}|{amount_cents}|{merchant_key}|{occurrence}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _row_amount(row: RawTransaction, decimal_comma: bool) -> Decimal:
    if row.amount_raw is not None:
        value = amounts.parse_amount(row.amount_raw, decimal_comma=decimal_comma)
        kind = (row.type_raw or "").strip().upper()
        if value > 0 and kind in {"DR", "DEBIT"}:
            return -value
        return value
    debit = (
        amounts.parse_amount(row.debit_raw, decimal_comma=decimal_comma) if row.debit_raw else None
    )
    credit = (
        amounts.parse_amount(row.credit_raw, decimal_comma=decimal_comma)
        if row.credit_raw
        else None
    )
    if debit is None and credit is None:
        raise amounts.AmountError("EMPTY_AMOUNT", "no amount")
    return (credit or Decimal(0)) - abs(debit or Decimal(0))


def _detect_card_inversion(
    parsed: list[tuple[RawTransaction, Decimal]],
) -> tuple[bool, ParseWarning | None]:
    """Decide whether a single-amount credit-card CSV lists charges as positive."""
    payments = [v for r, v in parsed if _CARD_PAYMENT_RE.search(r.description_raw) and v != 0]
    others = [v for r, v in parsed if not _CARD_PAYMENT_RE.search(r.description_raw) and v != 0]
    if not others:
        return False, None
    pos = sum(1 for v in others if v > 0) / len(others)
    pay_negative = bool(payments) and sum(1 for v in payments if v < 0) / len(payments) > 0.5
    if pos >= _CHARGE_FRACTION and pay_negative:
        return True, None
    if (1 - pos) >= _CHARGE_FRACTION and not pay_negative:
        return False, None
    return True, _assumed()


def _assumed() -> ParseWarning:
    return ParseWarning(
        "CARD_SIGN_ASSUMED",
        "Could not confirm the card sign convention; assuming charges are positive",
    )


def normalize(
    result: ParseResult, account_type: AccountType
) -> tuple[list[Transaction], list[ParseWarning]]:
    """Total over parsed rows: a row that still fails is dropped with a warning."""
    warnings: list[ParseWarning] = []
    fmt = result.date_format or "ofx"
    parsed: list[tuple[RawTransaction, date, Decimal]] = []
    for row in result.rows:
        try:
            posted = dates.parse_date(row.date_raw, fmt)
            value = _row_amount(row, result.decimal_comma)
        except (dates.DateError, amounts.AmountError) as exc:
            warnings.append(ParseWarning("ROW_SKIPPED", str(exc), row.row_index))
            continue
        parsed.append((row, posted, value))

    if result.account_type_hint and result.account_type_hint is not account_type:
        warnings.append(
            ParseWarning(
                "ACCOUNT_TYPE_MISMATCH",
                f"File looks like a {result.account_type_hint.value} account; "
                f"using your choice of {account_type.value}",
            )
        )

    invert = False
    single_column = all(r.amount_raw is not None for r, _, _ in parsed)
    if account_type is AccountType.CREDIT_CARD and fmt != "ofx" and single_column and parsed:
        invert, warn = _detect_card_inversion([(r, v) for r, _, v in parsed])
        if warn:
            warnings.append(warn)

    seen: Counter[tuple[date, int, str]] = Counter()
    out: list[Transaction] = []
    for row, posted, value in parsed:
        cents = amounts.to_cents(-value if invert else value)
        if amounts.has_extra_precision(value) and fmt == "ofx":
            warnings.append(
                ParseWarning("EXTRA_PRECISION", "Amount rounded to cents", row.row_index)
            )
        description = _tidy(row.description_raw)
        if len(description) > MAX_DESCRIPTION:
            description = description[:MAX_DESCRIPTION]
            warnings.append(
                ParseWarning(
                    "DESCRIPTION_TRUNCATED",
                    f"Description truncated to {MAX_DESCRIPTION} characters",
                    row.row_index,
                )
            )
        memo = _tidy(row.memo_raw)[:MAX_DESCRIPTION] if row.memo_raw else None
        key, channel, counterparty = clean_description(description)
        slot = (posted, cents, key)
        occurrence = seen[slot]
        seen[slot] += 1
        pending = bool(_PENDING_RE.search(row.status_raw or "") or _PENDING_RE.search(description))
        out.append(
            Transaction(
                row_index=row.row_index,
                posted_date=posted,
                amount_cents=cents,
                direction=Direction.INFLOW if cents > 0 else Direction.OUTFLOW,
                description=description,
                memo=memo or None,
                merchant_key=key,
                channel=channel,
                counterparty=counterparty,
                account_type=account_type,
                fitid=row.fitid,
                fingerprint=make_fingerprint(account_type, posted, cents, key, occurrence),
                is_pending=pending,
            )
        )
    return out, warnings
