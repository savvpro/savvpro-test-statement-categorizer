"""Test factories: raw rows, transactions, fake brain and statement text builders."""

from collections.abc import Sequence
from datetime import date

from app.brain.context import BrainContext
from app.domain.enums import (
    AccountType,
    Category,
    Direction,
    Flag,
    Status,
)
from app.domain.models import Decision, RawTransaction, Transaction
from app.normalize.merchant import clean_description
from app.normalize.normalizer import make_fingerprint

CSV_HEADER = "Date,Description,Amount"


def make_raw(**kw: object) -> RawTransaction:
    base: dict[str, object] = {
        "row_index": 1,
        "date_raw": "01/05/2026",
        "description_raw": "TEST",
        "amount_raw": "-10.00",
    }
    base.update(kw)
    return RawTransaction(**base)  # type: ignore[arg-type]


def make_txn(**kw: object) -> Transaction:
    desc = str(kw.pop("description", "HOME DEPOT #4410 TACOMA WA"))
    cents = int(kw.pop("amount_cents", -12_345))  # type: ignore[call-overload]
    posted = kw.pop("posted_date", date(2026, 1, 5))
    assert isinstance(posted, date)
    key, channel, cp = clean_description(desc)
    base: dict[str, object] = {
        "row_index": 1,
        "posted_date": posted,
        "amount_cents": cents,
        "direction": Direction.INFLOW if cents > 0 else Direction.OUTFLOW,
        "description": desc,
        "memo": None,
        "merchant_key": key,
        "channel": channel,
        "counterparty": cp,
        "account_type": AccountType.CHECKING,
        "fitid": None,
        "fingerprint": make_fingerprint(AccountType.CHECKING, posted, cents, key, 0),
        "is_pending": False,
    }
    base.update(kw)
    return Transaction(**base)  # type: ignore[arg-type]


def fake_categorize(txns: Sequence[Transaction], ctx: BrainContext) -> list[Decision]:
    """Deterministic stand-in for the brain, enough to exercise persistence and review."""
    out: list[Decision] = []
    seen_fitid: dict[str, int] = {}
    for t in txns:
        flags: set[Flag] = set()
        if t.fingerprint in ctx.prior_fingerprints:
            flags.add(Flag.DUPLICATE_PRIOR_UPLOAD)
            out.append(
                Decision(None, Status.DUPLICATE, 0.0, ("seen before",), (), frozenset(flags))
            )
            continue
        if t.fitid and t.fitid in seen_fitid:
            out.append(
                Decision(
                    None,
                    Status.DUPLICATE,
                    0.0,
                    ("same FITID",),
                    (),
                    frozenset({Flag.DUPLICATE_FITID}),
                    duplicate_of_row=seen_fitid[t.fitid],
                )
            )
            continue
        if t.fitid:
            seen_fitid[t.fitid] = t.row_index
        if t.merchant_key in ctx.memory:
            out.append(
                Decision(
                    ctx.memory[t.merchant_key],
                    Status.AUTO,
                    0.99,
                    ("memory",),
                    ("mem",),
                    frozenset(),
                )
            )
        elif "RENT" in t.description.upper() and t.amount_cents > 0:
            out.append(Decision(Category.RENT, Status.AUTO, 0.95, ("rent",), ("r1",), frozenset()))
        elif "HOME DEPOT" in t.merchant_key:
            out.append(
                Decision(
                    Category.REPAIRS,
                    Status.AUTO,
                    0.9,
                    ("hd",),
                    ("r2",),
                    frozenset(),
                    is_refund=t.amount_cents > 0,
                )
            )
        else:
            out.append(
                Decision(
                    None,
                    Status.NEEDS_REVIEW,
                    0.3,
                    ("unknown",),
                    (),
                    frozenset({Flag.UNKNOWN_MERCHANT}),
                    suggestion=Category.OTHER_EXPENSE if t.amount_cents < 0 else None,
                )
            )
    return out


def csv_text(rows: Sequence[tuple[str, str, str]], header: str = CSV_HEADER) -> str:
    return "\n".join([header, *[f"{d},{desc},{a}" for d, desc, a in rows]]) + "\n"


def bank_csv(extra: Sequence[tuple[str, str, str]] = ()) -> str:
    return csv_text(
        [
            ("01/02/2026", "ACH CREDIT TENANT RENT UNIT 4", "1800.00"),
            ("01/05/2026", "POS DEBIT HOME DEPOT #4410 TACOMA WA", "-123.45"),
            ("01/09/2026", "SQ *JOES CAFE 9921 SEATTLE WA", "-18.50"),
            ("01/20/2026", "POS DEBIT HOME DEPOT #4410 TACOMA WA", "45.00"),
            *extra,
        ]
    )


OFX_V1 = """OFXHEADER:100
DATA:OFXSGML
VERSION:102
SECURITY:NONE
ENCODING:USASCII
CHARSET:1252
COMPRESSION:NONE
OLDFILEUID:NONE
NEWFILEUID:NONE

<OFX>
<SIGNONMSGSRSV1><SONRS><STATUS><CODE>0<SEVERITY>INFO</STATUS>
<DTSERVER>20260131<LANGUAGE>ENG</SONRS></SIGNONMSGSRSV1>
<BANKMSGSRSV1><STMTTRNRS><TRNUID>1<STATUS><CODE>0<SEVERITY>INFO</STATUS>
<STMTRS><CURDEF>USD
<BANKACCTFROM><BANKID>123<ACCTID>999<ACCTTYPE>CHECKING</BANKACCTFROM>
<BANKTRANLIST><DTSTART>20260101<DTEND>20260131
<STMTTRN><TRNTYPE>CREDIT<DTPOSTED>20260102120000<TRNAMT>1800.00<FITID>A1<NAME>TENANT RENT UNIT 4</STMTTRN>
<STMTTRN><TRNTYPE>DEBIT<DTPOSTED>20260105<TRNAMT>-123.45<FITID>A2<NAME>HOME DEPOT #4410<MEMO>repairs &amp; parts</STMTTRN>
<STMTTRN><TRNTYPE>DEBIT<DTPOSTED>20260106<TRNAMT>-20.00<FITID>A3<MEMO>MEMO ONLY ITEM</STMTTRN>
<STMTTRN><TRNTYPE>DEBIT<DTPOSTED>20260107<TRNAMT>-5.00<FITID>A3<NAME>DUP FITID</STMTTRN>
</BANKTRANLIST></STMTRS></STMTTRNRS></BANKMSGSRSV1></OFX>
"""

OFX_V2 = """<?xml version="1.0" encoding="UTF-8"?>
<?OFX OFXHEADER="200" VERSION="211" SECURITY="NONE" OLDFILEUID="NONE" NEWFILEUID="NONE"?>
<OFX><CREDITCARDMSGSRSV1><CCSTMTTRNRS><CCSTMTRS><CURDEF>USD</CURDEF>
<CCACCTFROM><ACCTID>4111</ACCTID></CCACCTFROM>
<BANKTRANLIST>
<STMTTRN><TRNTYPE>DEBIT</TRNTYPE><DTPOSTED>20260110</DTPOSTED><TRNAMT>-42.10</TRNAMT><FITID>X1</FITID><NAME>LOWES #1234</NAME></STMTTRN>
<STMTTRN><TRNTYPE>CREDIT</TRNTYPE><DTPOSTED>20260112</DTPOSTED><TRNAMT>500.00</TRNAMT><FITID>X2</FITID><NAME>ONLINE PAYMENT THANK YOU</NAME></STMTTRN>
</BANKTRANLIST></CCSTMTRS></CCSTMTTRNRS></CREDITCARDMSGSRSV1></OFX>
"""
