#!/usr/bin/env python3
"""Generate deterministic, fictional statement fixtures and labels for Ledgerly.

Usage: python scripts/generate_samples.py   (Python 3.10+, stdlib only)

Every expected label is written by hand in the tables below and mirrors the
catalog in docs/plan/04-edge-cases-and-fixtures.md. Conventions:
- CSV row_index: 1-based position among non-blank lines after the header.
  Malformed lines and footer rows count; blank lines do not.
- OFX row_index: STMTTRN order.
- Rows that are not catalog cases still get their obvious category (case_id null).
- needs_review and duplicate rows have category null.
"""

from __future__ import annotations

import csv
import io
import json
import random
import xml.etree.ElementTree as ET
from dataclasses import dataclass, replace
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "samples"

random.seed(2026)
CONF_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
CHECKING_OPENING = 823500  # cents, 8235.00
MESSY_OPENING = 300000  # cents, 3000,00


@dataclass(frozen=True)
class Txn:
    date: str  # MM/DD/YYYY
    desc: str
    cents: int  # signed: +inflow, -outflow
    status: str  # auto | needs_review | duplicate
    category: str | None = None
    flags: tuple[str, ...] = ()
    case: str | None = None


def auto(date: str, desc: str, cents: int, category: str, case: str | None = None,
         flags: list[str] | tuple[str, ...] = ()) -> Txn:
    return Txn(date, desc, cents, "auto", category, tuple(flags), case)


def review(date: str, desc: str, cents: int, flags: list[str] | tuple[str, ...],
           case: str | None = None) -> Txn:
    return Txn(date, desc, cents, "needs_review", None, tuple(flags), case)


def conf() -> str:
    return "".join(random.choice(CONF_ALPHABET) for _ in range(5))


def zelle_in(name: str, memo: str | None = None) -> str:
    text = f"ZELLE FROM {name} CONF# {conf()}"
    return f"{text} MEMO: {memo}" if memo else text


def zelle_out(name: str, memo: str | None = None) -> str:
    text = f"ZELLE TO {name} CONF# {conf()}"
    return f"{text} MEMO: {memo}" if memo else text


def fmt(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    a = abs(cents)
    return f"{sign}{a // 100}.{a % 100:02d}"


def fmt_comma(cents: int) -> str:
    return fmt(cents).replace(".", ",")


def running(txns: list[Txn], opening: int) -> tuple[list[int], int]:
    balances: list[int] = []
    bal = opening
    for t in txns:
        bal += t.cents
        balances.append(bal)
    return balances, bal


# --- Checking Q1 2026 (Dana Reyes, Jan-Mar) ---------------------------------

CHECKING_Q1: list[Txn] = [
    # January
    auto("01/02/2026", zelle_in("MARIA K LOPEZ", "rent january"), 125000, "RENT"),
    auto("01/02/2026", zelle_in("PRIYA N DESAI", "security deposit"), 140000,
         "SECURITY_DEPOSIT_RECEIVED", "D04"),
    auto("01/03/2026", zelle_in("JORDAN T WRIGHT"), 117500, "RENT", "D02", ["RECURRING"]),
    auto("01/05/2026", zelle_in("PRIYA N DESAI", "rent january"), 140000, "RENT"),
    review("01/06/2026", "GRANITE HOME LENDING MTG PMT", -118437,
           ["MORTGAGE_SPLIT_REQUIRED"], "D15"),
    auto("01/07/2026", "HEARTHSTONE MUTUAL INS PREMIUM HM-20417", -38500, "INSURANCE", "D17"),
    auto("01/08/2026", "ASPEN RIDGE HOA DUES JAN", -21000, "OTHER_EXPENSE", "D19"),
    auto("01/09/2026", "RIVERBEND PROPERTY MGMT MGMT FEE", -16500, "MANAGEMENT_FEES", "D20"),
    auto("01/10/2026", "CITY WATER SEWER UTILITY", -9240, "UTILITIES", "D18"),
    auto("01/10/2026", "BRIGHTWATER ELECTRIC", -5810, "UTILITIES"),
    auto("01/10/2026", "WASTE HAULERS TRASH", -3400, "UTILITIES"),
    auto("01/12/2026", "LISTWELL RENTAL ADS", -7900, "ADVERTISING", "D21"),
    review("01/14/2026", "BEAN LEAF COFFEE #22", -475, ["UNKNOWN_MERCHANT"], "D39"),
    review("01/14/2026", "BEAN LEAF COFFEE #22", -475, ["UNKNOWN_MERCHANT"], "D39"),
    auto("01/15/2026", zelle_out("SAM R OKAFOR", "security deposit return"), -80000,
         "SECURITY_DEPOSIT_RETURNED", "D07"),
    auto("01/18/2026", "OWNER CONTRIBUTION DEPOSIT", 200000, "OWNER_CONTRIBUTION", "D38"),
    review("01/20/2026", zelle_out("TOM PRUITT"), -18000, ["PAYMENT_TO_INDIVIDUAL"], "D24"),
    auto("01/22/2026", "EVERGREEN COMMUNITY BANK INTEREST EARNED", 184, "INTEREST_EARNED", "D31"),
    auto("01/31/2026", "MONTHLY MAINTENANCE FEE", -1200, "OTHER_EXPENSE", "D32"),
    # February
    auto("02/02/2026", zelle_in("MARIA K LOPEZ", "rent february"), 125000, "RENT"),
    auto("02/02/2026", zelle_in("PRIYA N DESAI", "rent february"), 140000, "RENT"),
    auto("02/03/2026", zelle_in("JORDAN T WRIGHT"), 117500, "RENT", None, ["RECURRING"]),
    review("02/03/2026", zelle_out("LEO HARTMAN"), -38000, ["PAYMENT_TO_INDIVIDUAL"], "D25"),
    auto("02/05/2026", "CITY WATER SEWER UTILITY", -9240, "UTILITIES"),
    review("02/06/2026", "GRANITE HOME LENDING MTG PMT", -118437,
           ["MORTGAGE_SPLIT_REQUIRED"], "D15"),
    auto("02/07/2026", "ASPEN RIDGE HOA DUES FEB", -21000, "OTHER_EXPENSE"),
    auto("02/08/2026", "RIVERBEND PROPERTY MGMT MGMT FEE", -16500, "MANAGEMENT_FEES"),
    auto("02/09/2026", "BRIGHTWATER ELECTRIC", -6125, "UTILITIES"),
    auto("02/10/2026", zelle_in("MARIA K LOPEZ", "late fee february"), 5000, "RENT", "D06"),
    review("02/11/2026", zelle_in("MARIA K LOPEZ"), 7500, [], "D03"),
    review("02/14/2026", "CHECK #1042", -45000, ["CHECK_NO_PAYEE"], "D26"),
    auto("02/16/2026", "RETURNED ITEM ZELLE FROM JORDAN T WRIGHT", -117500, "RENT", "D08",
         ["RENT_REVERSAL"]),
    auto("02/16/2026", "NSF FEE RETURNED ITEM", -3500, "OTHER_EXPENSE", "D09"),
    auto("02/18/2026", "TRANSFER TO SAVINGS 9187", -100000, "TRANSFER", "D27"),
    auto("02/20/2026", "SUMMIT REWARDS CARD AUTOPAY", -41255, "CARD_PAYMENT", "D29"),
    auto("02/21/2026", "FOREIGN TXN FEE", -85, "OTHER_EXPENSE", "D37"),
    review("02/24/2026", zelle_out("LEO HARTMAN"), -34000,
           ["PAYMENT_TO_INDIVIDUAL", "POSSIBLE_1099"], "D25"),
    auto("02/25/2026", "TRANSFER FROM SAVINGS 9187", 100000, "TRANSFER", "D28"),
    auto("02/28/2026", "EVERGREEN COMMUNITY BANK INTEREST EARNED", 179, "INTEREST_EARNED"),
    auto("02/28/2026", "MONTHLY MAINTENANCE FEE", -1200, "OTHER_EXPENSE"),
    # March
    auto("03/02/2026", zelle_in("MARIA K LOPEZ", "rent march"), 125000, "RENT", "D01"),
    review("03/03/2026", zelle_in("PRIYA N DESAI"), 280000, ["AMOUNT_OUTLIER"], "D05"),
    auto("03/03/2026", zelle_in("JORDAN T WRIGHT"), 117500, "RENT", None, ["RECURRING"]),
    review("03/04/2026", "GRANITE HOME LENDING MTG PMT", -118437,
           ["MORTGAGE_SPLIT_REQUIRED"], "D15"),
    auto("03/06/2026", "ASPEN RIDGE HOA DUES MAR", -21000, "OTHER_EXPENSE"),
    auto("03/07/2026", "RIVERBEND PROPERTY MGMT MGMT FEE", -16500, "MANAGEMENT_FEES"),
    auto("03/09/2026", "HARLAN COUNTY TREASURER PROPERTY TAX", -184260, "TAXES", "D16"),
    auto("03/10/2026", "CITY WATER SEWER UTILITY", -9240, "UTILITIES"),
    auto("03/11/2026", "HARLOW PIKE CPA PLLC", -47500, "LEGAL_PROFESSIONAL", "D22"),
    auto("03/12/2026", "WASTE HAULERS TRASH", -3400, "UTILITIES"),
    auto("03/13/2026", "BRIGHTWATER ELECTRIC", -5810, "UTILITIES"),
    auto("03/15/2026", "EVERGREEN COMMUNITY BANK INTEREST EARNED", 161, "INTEREST_EARNED"),
    auto("03/16/2026", "MONTHLY MAINTENANCE FEE", -1200, "OTHER_EXPENSE"),
]

# Apr rows appended only to the overlap file.
APRIL_ROWS: list[Txn] = [
    auto("04/02/2026", zelle_in("MARIA K LOPEZ", "rent april"), 125000, "RENT"),
    auto("04/02/2026", zelle_in("PRIYA N DESAI", "rent april"), 140000, "RENT"),
    auto("04/03/2026", zelle_in("JORDAN T WRIGHT"), 117500, "RENT", None, ["RECURRING"]),
    review("04/06/2026", "GRANITE HOME LENDING MTG PMT", -118437, ["MORTGAGE_SPLIT_REQUIRED"]),
    auto("04/08/2026", "ASPEN RIDGE HOA DUES APR", -21000, "OTHER_EXPENSE"),
    auto("04/09/2026", "RIVERBEND PROPERTY MGMT MGMT FEE", -16500, "MANAGEMENT_FEES"),
    auto("04/10/2026", "CITY WATER SEWER UTILITY", -9240, "UTILITIES"),
    auto("04/12/2026", "EVERGREEN COMMUNITY BANK INTEREST EARNED", 150, "INTEREST_EARNED"),
    review("04/14/2026", "BEAN LEAF COFFEE #22", -475, ["UNKNOWN_MERCHANT"]),
    review("04/20/2026", zelle_out("TOM PRUITT"), -18000, ["PAYMENT_TO_INDIVIDUAL"]),
]


def bank_csv(rows: list[tuple[Txn, int]]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(["Date", "Description", "Amount", "Balance"])
    for t, bal in rows:
        writer.writerow([t.date, t.desc, fmt(t.cents), fmt(bal)])
    return buf.getvalue()


def overlap_rows(q1_rows: list[tuple[Txn, int]], q1_final: int) -> list[tuple[Txn, int]]:
    """Feb-Mar rows copied verbatim from Q1 (labels become cross-upload duplicates)."""
    copied = [
        (replace(t, status="duplicate", category=None,
                 flags=("DUPLICATE_PRIOR_UPLOAD",), case="D41"), bal)
        for t, bal in q1_rows
        if t.date[:3] in ("02/", "03/")
    ]
    apr_balances, _ = running(APRIL_ROWS, q1_final)
    return copied + list(zip(APRIL_ROWS, apr_balances))


# --- Credit card Q1 2026 (Debit/Credit columns) ------------------------------

def card(tdate: str, pdate: str, desc: str, cents: int, status: str,
         category: str | None = None, flags: tuple[str, ...] = (),
         case: str | None = None) -> tuple[Txn, str]:
    return Txn(tdate, desc, cents, status, category, flags, case), pdate


CARD_ROWS: list[tuple[Txn, str]] = [
    card("01/04/2026", "01/05/2026", "HOME DEPOT #4410", -8412, "auto", "REPAIRS", (), "D10"),
    card("01/09/2026", "01/10/2026", "KEYSTONE PLUMBING CO", -32500, "auto", "REPAIRS", (), "D23"),
    card("01/12/2026", "01/13/2026", "AMAZON MKTPLACE PMTS", -5620, "needs_review", None,
         ("MIXED_USE_MERCHANT",), "D13"),
    card("01/15/2026", "01/16/2026", "WALMART SUPERCENTER 4187", -4173, "needs_review", None,
         ("MIXED_USE_MERCHANT",), "D14"),
    card("01/18/2026", "01/19/2026", "TARGET 1123", -6790, "needs_review", None,
         ("MIXED_USE_MERCHANT",), "D14"),
    card("01/20/2026", "01/21/2026", "COSTCO WHSE #1190", -21244, "needs_review", None,
         ("MIXED_USE_MERCHANT",), "D14"),
    card("01/22/2026", "01/23/2026", "SHELL OIL 57412", -4819, "needs_review", None,
         ("AMBIGUOUS_MATCH",), "D33"),
    card("01/25/2026", "01/26/2026", "JOES CAFE", -950, "needs_review", None,
         ("UNKNOWN_MERCHANT",), "D34"),
    card("01/28/2026", "01/29/2026", "PAYMENT THANK YOU", 60000, "auto", "CARD_PAYMENT", (), "D30"),
    card("02/02/2026", "02/03/2026", "HOME DEPOT #4410", -341200, "needs_review", None,
         ("POSSIBLE_CAPITAL_IMPROVEMENT",), "D11"),
    card("02/08/2026", "02/09/2026", "HOME DEPOT #4410 REFUND", 4210, "auto", "REPAIRS", (), "D12"),
    card("02/10/2026", "02/11/2026", "HOEM DEPOT #4410", -2736, "needs_review", None, (), "D35"),
    card("02/12/2026", "02/13/2026", "CITY WATER UTILITY CREDIT", 4800, "needs_review", None,
         ("DIRECTION_CONFLICT",), "D36"),
    card("02/14/2026", "02/15/2026", "HOME DEPOT #4410", -1988, "auto", "REPAIRS", (), "P08"),
    card("02/18/2026", "02/19/2026", "AMAZON MKTPLACE PMTS", -1499, "needs_review", None,
         ("MIXED_USE_MERCHANT",)),
    card("02/22/2026", "02/23/2026", "SHELL OIL 57412", -3970, "needs_review", None,
         ("AMBIGUOUS_MATCH",)),
    card("03/03/2026", "03/04/2026", "WALMART SUPERCENTER 4187", -8830, "needs_review", None,
         ("MIXED_USE_MERCHANT",)),
    card("03/05/2026", "03/06/2026", "COSTCO WHSE #1190", -15502, "needs_review", None,
         ("MIXED_USE_MERCHANT",)),
    card("03/09/2026", "03/10/2026", "HOME DEPOT #4410", -3146, "auto", "REPAIRS"),
    card("03/15/2026", "03/16/2026", "PAYMENT THANK YOU", 41255, "auto", "CARD_PAYMENT"),
    card("03/18/2026", "03/19/2026", "TARGET 1123", -2210, "needs_review", None,
         ("MIXED_USE_MERCHANT",)),
    card("03/22/2026", "03/23/2026", "JOES CAFE", -625, "needs_review", None,
         ("UNKNOWN_MERCHANT",)),
    card("03/27/2026", "03/28/2026", "HOME DEPOT #4410 REFUND", 999, "auto", "REPAIRS"),
]


def card_csv(rows: list[tuple[Txn, str]]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(["Transaction Date", "Posted Date", "Description", "Debit", "Credit"])
    for t, posted in rows:
        debit = fmt(-t.cents) if t.cents < 0 else ""
        credit = fmt(t.cents) if t.cents > 0 else ""
        writer.writerow([t.date, posted, t.desc, debit, credit])
    return buf.getvalue()


# --- Messy checking: BOM, preamble, ';', decimal comma, CRLF, footer ---------
# Entries: ("txn", Txn, amount_text) | ("raw", line) | ("blank",)

MESSY_BODY: list[tuple] = [
    ("txn", Txn("01/02/2026", "ZELLE FROM MARIA K LOPEZ RENT JANUARY", 125000, "auto", "RENT",
                (), "P01"), "1250,00"),
    ("txn", Txn("01/05/2026", "ZELLE FROM JORDAN T WRIGHT, RENT JANUARY", 117500, "auto",
                "RENT", (), "P07"), "1175,00"),
    ("txn", Txn("01/06/2026", "AUTH HOLD CITY PARKING", 0, "needs_review", None,
                ("ZERO_AMOUNT",), "P24"), "0,00"),
    ("raw", "01/07/2026;ZELLE TO VENDOR"),  # malformed: missing amount field
    ("blank",),
    ("txn", Txn("02/03/2026", "ZELLE FROM PRIYA N DESAI RENT FEBRUARY", 140000, "auto",
                "RENT", (), "P06"), "1400,00"),
    ("txn", Txn("02/05/2026", "HOME DEPOT #4410", -8412, "auto", "REPAIRS", (), "P03"),
     "-84,12"),
    ("raw", "02/07/2026;BAD ROW;12,3,4,5x;"),  # malformed: unparseable amount
    ("txn", Txn("02/09/2026", "CITY WATER SEWER UTILITY", -9240, "auto", "UTILITIES", (),
                "P22"), "-92,40"),
    ("txn", Txn("02/10/2026", "CITY WATER SEWER UTILITY LATE CHARGE", -4500, "auto",
                "UTILITIES", (), "P09"), "(45,00)"),
    ("txn", Txn("03/02/2026", "ZELLE FROM MARIA K LOPEZ RENT MARCH", 125000, "auto", "RENT",
                (), "P10"), "1250,00"),
    ("txn", Txn("03/04/2026", "HEARTHSTONE MUTUAL INS PREMIUM", -38500, "auto", "INSURANCE"),
     "-385,00"),
    ("txn", Txn("03/06/2026", "ZELLE FROM JORDAN T WRIGHT RENT MARCH", 117500, "auto", "RENT"),
     "1175,00"),
    ("txn", Txn("03/08/2026", "CITY WATER SEWER UTILITY", -9240, "auto", "UTILITIES"), "-92,40"),
    ("txn", Txn("03/10/2026", "BRIGHTWATER ELECTRIC", -5810, "auto", "UTILITIES"), "-58,10"),
]


def messy_text() -> tuple[str, list[tuple[int, Txn]]]:
    lines = [
        "Evergreen Community Bank - Business Checking",
        "Statement period: 01/01/2026 to 03/31/2026",
        "Account ending 4471",
        "Date;Description;Amount;Balance",
    ]
    pairs: list[tuple[int, Txn]] = []
    bal = MESSY_OPENING
    index = 0
    for item in MESSY_BODY:
        kind = item[0]
        if kind == "blank":
            lines.append("")
            continue
        index += 1
        if kind == "raw":
            lines.append(item[1])
            continue
        _, t, amount_text = item
        bal += t.cents
        desc = f'"{t.desc}"' if "," in t.desc else t.desc
        lines.append(f"{t.date};{desc};{amount_text};{fmt_comma(bal)}")
        pairs.append((index, t))
    index += 1
    lines.append(f"Ending Balance;;;{fmt_comma(bal)}")
    return "\r\n".join(lines) + "\r\n", pairs


# --- OFX 1.x (SGML) checking ---------------------------------------------------

def ofx1(dt: str, trntype: str, cents: int, fitid: str, name: str | None, memo: str | None,
         status: str, category: str | None, flags: tuple[str, ...] = (),
         case: str | None = None) -> tuple[Txn, str, str, str, str | None, str | None]:
    date = f"{dt[4:6]}/{dt[6:8]}/{dt[:4]}"
    txn = Txn(date, name or memo or "", cents, status, category, flags, case)
    return txn, dt, trntype, fitid, name, memo


OFX1_ROWS = [
    ofx1("20260102", "CREDIT", 125000, "OFX0001", "MARIA K LOPEZ", "RENT JANUARY",
         "auto", "RENT", case="P17"),
    ofx1("20260102", "CREDIT", 140000, "OFX0002", "PRIYA N DESAI", "RENT JANUARY",
         "auto", "RENT"),
    ofx1("20260106", "DEBIT", -9240, "OFX0003", "CITY WATER SEWER UTILITY", None,
         "auto", "UTILITIES"),
    ofx1("20260107", "DEBIT", -38500, "OFX0004", "HEARTHSTONE MUTUAL INS", "PREMIUM HM-20417",
         "auto", "INSURANCE"),
    ofx1("20260108", "DEBIT", -21000, "OFX0005", "ASPEN RIDGE HOA", None,
         "auto", "OTHER_EXPENSE"),
    ofx1("20260109", "DEBIT", -16500, "OFX0006", "RIVERBEND PROPERTY MGMT", None,
         "auto", "MANAGEMENT_FEES"),
    ofx1("20260110", "DEBIT", -1200, "OFX0007", "EVERGREEN COMMUNITY BANK",
         "MONTHLY MAINTENANCE FEE", "auto", "OTHER_EXPENSE"),
    ofx1("20260122", "CREDIT", 184, "OFX0008", "EVERGREEN COMMUNITY BANK", "INTEREST EARNED",
         "auto", "INTEREST_EARNED"),
    ofx1("20260115", "DEBIT", -47500, "OFX0009", "HARLOW PIKE CPA PLLC", None,
         "auto", "LEGAL_PROFESSIONAL"),
    ofx1("20260112", "DEBIT", -7900, "OFX0010", "LISTWELL RENTAL ADS", None,
         "auto", "ADVERTISING"),
    ofx1("20260118", "XFER", -100000, "OFX0011", "EVERGREEN COMMUNITY BANK",
         "TRANSFER TO SAVINGS 9187", "auto", "TRANSFER"),
    ofx1("20260118", "XFER", 100000, "OFX0012", "EVERGREEN COMMUNITY BANK",
         "TRANSFER FROM SAVINGS 9187", "auto", "TRANSFER"),
    ofx1("20260120", "PAYMENT", -41255, "OFX0013", "SUMMIT REWARDS CARD", "AUTOPAY",
         "auto", "CARD_PAYMENT"),
    ofx1("20260125", "DEBIT", -5810, "OFX0014", "BRIGHTWATER ELECTRIC", None,
         "auto", "UTILITIES"),
    ofx1("20260126", "DEBIT", -3400, "OFX0015", "WASTE HAULERS TRASH", None,
         "auto", "UTILITIES"),
    ofx1("20260128", "DEBIT", -85, "OFX0016", "EVERGREEN COMMUNITY BANK", "FOREIGN TXN FEE",
         "auto", "OTHER_EXPENSE"),
    ofx1("20260129", "CREDIT", 200000, "OFX0017", "DANA REYES", "OWNER CONTRIBUTION",
         "auto", "OWNER_CONTRIBUTION"),
    ofx1("20260205", "CREDIT", 117500, "OFX0018", "JORDAN T WRIGHT", "RENT FEBRUARY",
         "auto", "RENT"),
    # P19: FITID reused from row 14, so this second occurrence is a duplicate.
    ofx1("20260120", "DEBIT", -5810, "OFX0014", "BRIGHTWATER ELECTRIC", None,
         "duplicate", None, ("DUPLICATE_FITID",), case="P19"),
    # P20: MEMO only, no NAME.
    ofx1("20260310", "CREDIT", 117500, "OFX0020", None, "RENT UNIT B MARCH",
         "auto", "RENT", case="P20"),
]


def ofx1_text(rows: list[tuple], opening: int) -> str:
    _, final = running([r[0] for r in rows], opening)
    parts = [
        "OFXHEADER:100", "DATA:OFXSGML", "VERSION:102", "SECURITY:NONE",
        "ENCODING:USASCII", "CHARSET:1252", "COMPRESSION:NONE",
        "OLDFILEUID:NONE", "NEWFILEUID:NONE", "",
        "<OFX>",
        "<SIGNONMSGSRSV1><SONRS><STATUS><CODE>0<SEVERITY>INFO</STATUS>"
        "<DTSERVER>20260331120000<LANGUAGE>ENG</SONRS></SIGNONMSGSRSV1>",
        "<BANKMSGSRSV1><STMTTRNRS><TRNUID>1001<STATUS><CODE>0<SEVERITY>INFO</STATUS>",
        "<STMTRS><CURDEF>USD<BANKACCTFROM><BANKID>000000000<ACCTID>4471000001"
        "<ACCTTYPE>CHECKING</BANKACCTFROM>",
        "<BANKTRANLIST><DTSTART>20260101120000<DTEND>20260331120000",
    ]
    for txn, dt, trntype, fitid, name, memo in rows:
        block = [
            "<STMTTRN>",
            f"<TRNTYPE>{trntype}",
            f"<DTPOSTED>{dt}120000",
            f"<TRNAMT>{fmt(txn.cents)}",
            f"<FITID>{fitid}",
        ]
        if name:
            block.append(f"<NAME>{name}")
        if memo:
            block.append(f"<MEMO>{memo}")
        block.append("</STMTTRN>")
        parts.append("\n".join(block))
    parts += [
        "</BANKTRANLIST>",
        f"<LEDGERBAL><BALAMT>{fmt(final)}<DTASOF>20260331120000</LEDGERBAL>",
        "</STMTRS></STMTTRNRS></BANKMSGSRSV1>",
        "</OFX>",
    ]
    return "\n".join(parts) + "\n"


# --- OFX 2.x (XML) credit card -----------------------------------------------

def ofx2(dt: str, cents: int, fitid: str, name: str, status: str, category: str | None,
         flags: tuple[str, ...] = (), case: str | None = None) -> tuple:
    date = f"{dt[4:6]}/{dt[6:8]}/{dt[:4]}"
    trntype = "CREDIT" if cents > 0 else "DEBIT"
    return Txn(date, name, cents, status, category, flags, case), dt, trntype, fitid, name


OFX2_ROWS = [
    ofx2("20260104", -8412, "CC0001", "HOME DEPOT #4410", "auto", "REPAIRS", case="P18"),
    ofx2("20260209", 4210, "CC0002", "HOME DEPOT #4410 REFUND", "auto", "REPAIRS"),
    ofx2("20260113", -5620, "CC0003", "AMAZON MKTPLACE PMTS", "needs_review", None,
         ("MIXED_USE_MERCHANT",)),
    ofx2("20260123", -4819, "CC0004", "SHELL OIL 57412", "needs_review", None,
         ("AMBIGUOUS_MATCH",)),
    ofx2("20260121", -21244, "CC0005", "COSTCO WHSE #1190", "needs_review", None,
         ("MIXED_USE_MERCHANT",)),
    ofx2("20260129", 60000, "CC0006", "PAYMENT THANK YOU", "auto", "CARD_PAYMENT"),
    ofx2("20260211", -3146, "CC0007", "HOME DEPOT #4410", "auto", "REPAIRS"),
    ofx2("20260226", -950, "CC0008", "JOES CAFE", "needs_review", None, ("UNKNOWN_MERCHANT",)),
    ofx2("20260213", 4800, "CC0009", "CITY WATER UTILITY", "needs_review", None,
         ("DIRECTION_CONFLICT",)),
]


def ofx2_text(rows: list[tuple]) -> str:
    total = sum(r[0].cents for r in rows)
    lines = [
        '<?xml version="1.0" encoding="UTF-8" standalone="no"?>',
        '<?OFX OFXHEADER="200" VERSION="220" SECURITY="NONE" OLDFILEUID="NONE" '
        'NEWFILEUID="NONE"?>',
        "<OFX>",
        "<SIGNONMSGSRSV1><SONRS><STATUS><CODE>0</CODE><SEVERITY>INFO</SEVERITY></STATUS>"
        "<DTSERVER>20260331120000</DTSERVER><LANGUAGE>ENG</LANGUAGE></SONRS></SIGNONMSGSRSV1>",
        "<CREDITCARDMSGSRSV1><CCSTMTTRNRS><TRNUID>2001</TRNUID>"
        "<STATUS><CODE>0</CODE><SEVERITY>INFO</SEVERITY></STATUS>",
        "<CCSTMTRS><CURDEF>USD</CURDEF><CCACCTFROM><ACCTID>5500000002</ACCTID></CCACCTFROM>",
        "<BANKTRANLIST><DTSTART>20260101120000</DTSTART><DTEND>20260331120000</DTEND>",
    ]
    for txn, dt, trntype, fitid, name in rows:
        lines.append(
            f"<STMTTRN><TRNTYPE>{trntype}</TRNTYPE><DTPOSTED>{dt}120000</DTPOSTED>"
            f"<TRNAMT>{fmt(txn.cents)}</TRNAMT><FITID>{fitid}</FITID>"
            f"<NAME>{escape(name)}</NAME></STMTTRN>"
        )
    lines += [
        "</BANKTRANLIST>",
        f"<LEDGERBAL><BALAMT>{fmt(total)}</BALAMT><DTASOF>20260331120000</DTASOF></LEDGERBAL>",
        "</CCSTMTRS></CCSTMTTRNRS></CREDITCARDMSGSRSV1>",
        "</OFX>",
    ]
    return "\n".join(lines) + "\n"


# --- Output ------------------------------------------------------------------

def expected_json(pairs: list[tuple[int, Txn]]) -> str:
    items = [
        {
            "row_index": index,
            "case_id": t.case,
            "category": t.category,
            "status": t.status,
            "flags_contains": list(t.flags),
        }
        for index, t in pairs
    ]
    return json.dumps(items, indent=2) + "\n"


def check_labels(txns: list[Txn]) -> None:
    for t in txns:
        if t.status == "auto":
            assert t.category, f"auto row needs category: {t}"
        else:
            assert t.category is None, f"{t.status} row must have null category: {t}"


def write_bytes(name: str, data: bytes) -> None:
    (SAMPLES / name).write_bytes(data)


def main() -> None:
    SAMPLES.mkdir(parents=True, exist_ok=True)
    all_labelled: dict[str, list[tuple[int, Txn]]] = {}

    # Checking Q1
    check_labels(CHECKING_Q1)
    q1_balances, q1_final = running(CHECKING_Q1, CHECKING_OPENING)
    q1_rows = list(zip(CHECKING_Q1, q1_balances))
    write_bytes("checking_q1_2026.csv", bank_csv(q1_rows).encode("utf-8"))
    all_labelled["checking_q1_2026.csv"] = list(enumerate(CHECKING_Q1, start=1))

    # Card Q1
    check_labels([t for t, _ in CARD_ROWS])
    write_bytes("card_q1_2026.csv", card_csv(CARD_ROWS).encode("utf-8"))
    all_labelled["card_q1_2026.csv"] = list(enumerate([t for t, _ in CARD_ROWS], start=1))

    # Messy checking (BOM + CRLF + ';')
    messy, messy_pairs = messy_text()
    write_bytes("checking_messy_bom_crlf.csv", b"\xef\xbb\xbf" + messy.encode("utf-8"))
    all_labelled["checking_messy_bom_crlf.csv"] = messy_pairs
    check_labels([t for _, t in messy_pairs])

    # OFX 1.x
    check_labels([r[0] for r in OFX1_ROWS])
    write_bytes("checking_q1_2026.ofx", ofx1_text(OFX1_ROWS, CHECKING_OPENING).encode("ascii"))
    all_labelled["checking_q1_2026.ofx"] = list(enumerate([r[0] for r in OFX1_ROWS], start=1))

    # OFX 2.x (must be well-formed XML)
    ofx2_xml = ofx2_text(OFX2_ROWS)
    ET.fromstring(ofx2_xml.encode("utf-8"))
    write_bytes("card_q1_2026_v2.ofx", ofx2_xml.encode("utf-8"))
    all_labelled["card_q1_2026_v2.ofx"] = list(enumerate([r[0] for r in OFX2_ROWS], start=1))

    # Overlap Feb-Apr
    overlap = overlap_rows(q1_rows, q1_final)
    overlap_txns = [t for t, _ in overlap]
    check_labels(overlap_txns)
    write_bytes("checking_overlap_feb_apr.csv", bank_csv(overlap).encode("utf-8"))
    all_labelled["checking_overlap_feb_apr.csv"] = list(enumerate(overlap_txns, start=1))

    for name, pairs in all_labelled.items():
        (SAMPLES / f"{name}.expected.json").write_text(
            expected_json(pairs), encoding="utf-8", newline="\n"
        )

    readme = [
        "# Ledgerly sample statements",
        "",
        "Fictional data only (persona Dana Reyes; fictional tenants, lenders and vendors). "
        "Generated by `scripts/generate_samples.py`. Each `<file>.expected.json` holds the "
        "labels for that file. Row index: CSV = data line after the header (malformed and "
        "footer lines count, blank lines do not); OFX = STMTTRN order.",
        "",
        "- `checking_q1_2026.csv`: Jan-Mar business checking, signed amounts; tenant Zelle rent, "
        "deposits, mortgage, bills, transfers and Zelle edge cases (D01-D09, D15-D22, D24-D29, "
        "D31, D32, D37-D39).",
        "- `card_q1_2026.csv`: credit card with separate Debit/Credit columns; merchant "
        "mixed-use, refunds, capital-improvement and direction-conflict cases (D10-D14, D23, "
        "D30, D33-D36, P08).",
        "- `checking_messy_bom_crlf.csv`: UTF-8 BOM, CRLF, 3 preamble lines, `;` delimiter, "
        "decimal comma, ambiguous MM/DD dates, blank line, 2 malformed rows, zero amount, "
        "`(45,00)` negative, Ending Balance footer (P01, P03, P06, P07, P09, P10, P22, P24). "
        "P04, P05 and P15 are line-level and produce no transaction row.",
        "- `checking_q1_2026.ofx`: OFX 1.x SGML with no closing tags on leaf elements; duplicate "
        "FITID and a MEMO-only row (P17, P19, P20).",
        "- `card_q1_2026_v2.ofx`: OFX 2.x XML credit card statement (P18).",
        "- `checking_overlap_feb_apr.csv`: Feb-Mar rows copied verbatim from the Q1 checking "
        "file plus April rows; overlapping rows are cross-upload duplicates (D41).",
        "",
    ]
    (SAMPLES / "README.md").write_text("\n".join(readme), encoding="utf-8", newline="\n")

    counts = {name: len(pairs) for name, pairs in all_labelled.items()}
    for name, n in counts.items():
        print(f"{name}: {n} labelled rows")
    print(f"Wrote samples to {SAMPLES}")


if __name__ == "__main__":
    main()
