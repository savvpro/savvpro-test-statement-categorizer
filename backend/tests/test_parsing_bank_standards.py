"""ISO 20022 camt.053 and SWIFT MT940 readers."""

from __future__ import annotations

import contextlib
import random
import re
import xml.etree.ElementTree as ET
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from app.domain.models import SourceFormat
from app.errors import FileProblem
from app.parsing.camt053_reader import read_camt053
from app.parsing.csv_reader import decode_text
from app.parsing.mt940_reader import read_mt940

MAX = 5000
CACHE = Path(__file__).resolve().parent / "reference_cache"

NS_V02 = "urn:iso:std:iso:20022:tech:xsd:camt.053.001.02"
NS_V08 = "urn:iso:std:iso:20022:tech:xsd:camt.053.001.08"


# --------------------------------------------------------------------------- camt.053 builders


def ntry(
    amount: str = "10.00",
    indicator: str = "DBIT",
    *,
    ccy: str = "EUR",
    reversal: bool | None = None,
    status: str | None = "BOOK",
    nested_status: bool = False,
    booked: str | None = "<Dt>2024-03-01</Dt>",
    valued: str | None = None,
    refs: str = "",
    body: str = "",
) -> str:
    parts = ["<Ntry>"]
    parts.append(f'<Amt Ccy="{ccy}">{amount}</Amt><CdtDbtInd>{indicator}</CdtDbtInd>')
    if reversal is not None:
        parts.append(f"<RvslInd>{str(reversal).lower()}</RvslInd>")
    if status:
        parts.append(f"<Sts><Cd>{status}</Cd></Sts>" if nested_status else f"<Sts>{status}</Sts>")
    if booked:
        parts.append(f"<BookgDt>{booked}</BookgDt>")
    if valued:
        parts.append(f"<ValDt>{valued}</ValDt>")
    parts.append(refs)
    parts.append(body)
    parts.append("</Ntry>")
    return "".join(parts)


def tx(amount: str, *, ccy: str = "EUR", body: str = "", ref: str = "") -> str:
    refs = f"<Refs><AcctSvcrRef>{ref}</AcctSvcrRef></Refs>" if ref else ""
    return f'<TxDtls>{refs}<Amt Ccy="{ccy}">{amount}</Amt>{body}</TxDtls>'


def details(*txs: str) -> str:
    return "<NtryDtls>" + "".join(txs) + "</NtryDtls>"


def stmt(*entries: str, ccy: str | None = "EUR", tag: str = "Stmt") -> str:
    acct = f"<Acct><Id><IBAN>DE00</IBAN></Id><Ccy>{ccy}</Ccy></Acct>" if ccy else ""
    return f"<{tag}><Id>1</Id>{acct}{''.join(entries)}</{tag}>"


def camt(*statements: str, ns: str = NS_V02) -> bytes:
    xml = (
        f'<?xml version="1.0" encoding="UTF-8"?><Document xmlns="{ns}"><BkToCstmrStmt>'
        f"<GrpHdr><MsgId>m</MsgId></GrpHdr>{''.join(statements)}</BkToCstmrStmt></Document>"
    )
    return xml.encode("utf-8")


# ------------------------------------------------------------------------ camt.053: happy paths


@pytest.mark.parametrize("ns", [NS_V02, NS_V08])
def test_camt_credit_and_debit_across_schema_versions(ns):
    data = camt(
        stmt(
            ntry("1500.00", "CRDT", body="<AddtlNtryInf>Salary March</AddtlNtryInf>"),
            ntry("54.9", "DBIT", body="<AddtlNtryInf>Adobe</AddtlNtryInf>"),
        ),
        ns=ns,
    )
    parsed = read_camt053(data, max_rows=MAX)
    assert parsed.source_format is SourceFormat.CAMT053
    assert parsed.currency_hint == "EUR"
    first, second = parsed.rows
    assert (first.credit, first.debit, first.amount) == (Decimal("1500.00"), None, None)
    assert (second.debit, second.credit) == (Decimal("54.90"), None)
    assert first.date == date(2024, 3, 1)
    assert first.currency == "EUR"
    assert (first.line, second.line) == (1, 2)
    assert not parsed.rejected and not parsed.warnings


def test_camt_nested_status_code_is_understood():
    data = camt(stmt(ntry("5.00", status="PDNG", nested_status=True)), ns=NS_V08)
    parsed = read_camt053(data, max_rows=MAX)
    assert parsed.warnings == ["1 pending entries included"]


def test_camt_reversal_flips_direction_and_is_labelled():
    data = camt(
        stmt(
            ntry("20.00", "DBIT", reversal=True, body="<AddtlNtryInf>Shop refund</AddtlNtryInf>"),
            ntry("30.00", "CRDT", reversal=True, body="<AddtlNtryInf>Salary</AddtlNtryInf>"),
            ntry("40.00", "DBIT", reversal=False, body="<AddtlNtryInf>Plain</AddtlNtryInf>"),
        )
    )
    reversed_debit, reversed_credit, plain = read_camt053(data, max_rows=MAX).rows
    assert reversed_debit.credit == Decimal("20.00") and reversed_debit.debit is None
    assert reversed_debit.description == "Reversal: Shop refund"
    assert reversed_credit.debit == Decimal("30.00") and reversed_credit.credit is None
    assert plain.debit == Decimal("40.00") and plain.description == "Plain"


def test_camt_batch_entry_is_split_into_one_row_per_transaction():
    batch = ntry(
        "100.00",
        "DBIT",
        refs="<AcctSvcrRef>BATCH1</AcctSvcrRef>",
        body=details(
            tx("60.00", body="<RmtInf><Ustrd>Invoice 1</Ustrd></RmtInf>", ref="TX-A"),
            tx("40.00", body="<RmtInf><Ustrd>Invoice 2</Ustrd></RmtInf>"),
        ),
    )
    parsed = read_camt053(camt(stmt(batch)), max_rows=MAX)
    first, second = parsed.rows
    assert [r.debit for r in parsed.rows] == [Decimal("60.00"), Decimal("40.00")]
    assert [r.description for r in parsed.rows] == ["Invoice 1", "Invoice 2"]
    assert first.external_id == "TX-A"
    assert second.external_id == "BATCH1"
    assert first.line == second.line == 1


def test_camt_details_that_do_not_add_up_stay_one_row():
    entry = ntry(
        "100.00",
        "DBIT",
        body=details(tx("60.00"), tx("30.00")) + "<AddtlNtryInf>Mixed payments</AddtlNtryInf>",
    )
    parsed = read_camt053(camt(stmt(entry)), max_rows=MAX)
    assert len(parsed.rows) == 1
    assert parsed.rows[0].debit == Decimal("100.00")
    assert parsed.rows[0].description == "Mixed payments"


def test_camt_details_in_another_currency_are_not_split():
    entry = ntry(
        "100.00",
        "DBIT",
        body=details(tx("60.00", ccy="USD"), tx("40.00", ccy="USD")),
    )
    assert len(read_camt053(camt(stmt(entry)), max_rows=MAX).rows) == 1


def test_camt_pending_entries_are_kept_with_a_warning():
    data = camt(
        stmt(
            ntry("1.00", status="BOOK"),
            ntry("2.00", status="PDNG"),
            ntry("3.00", status="PDNG"),
        )
    )
    parsed = read_camt053(data, max_rows=MAX)
    assert len(parsed.rows) == 3
    assert parsed.warnings == ["2 pending entries included"]


def test_camt_informational_entries_are_skipped():
    data = camt(stmt(ntry("1.00", status="BOOK"), ntry("2.00", status="INFO")))
    parsed = read_camt053(data, max_rows=MAX)
    assert [r.debit for r in parsed.rows] == [Decimal("1.00")]
    assert parsed.warnings == ["1 informational entries were skipped"]


def test_camt_missing_status_counts_as_booked():
    parsed = read_camt053(camt(stmt(ntry("1.00", status=None))), max_rows=MAX)
    assert len(parsed.rows) == 1 and not parsed.warnings


def test_camt_booking_date_can_be_a_datetime_or_fall_back_to_value_date():
    data = camt(
        stmt(
            ntry("1.00", booked="<DtTm>2024-05-06T13:45:00</DtTm>"),
            ntry("2.00", booked=None, valued="<Dt>2024-05-08</Dt>"),
            ntry("3.00", booked="<Dt>2024-05-09</Dt>", valued="<Dt>2024-05-12</Dt>"),
        )
    )
    dates = [r.date for r in read_camt053(data, max_rows=MAX).rows]
    assert dates == [date(2024, 5, 6), date(2024, 5, 8), date(2024, 5, 9)]


# --------------------------------------------------------------------- camt.053: descriptions


def test_camt_description_prefers_unstructured_remittance_and_joins_lines():
    body = details(
        tx(
            "10.00",
            body=(
                "<RmtInf><Ustrd>  Invoice\n   4711 </Ustrd><Ustrd>March rent</Ustrd></RmtInf>"
                "<AddtlTxInf>ignored</AddtlTxInf>"
            ),
        )
    )
    row = read_camt053(camt(stmt(ntry(body=body))), max_rows=MAX).rows[0]
    assert row.description == "Invoice 4711 March rent"


def test_camt_description_fallback_chain():
    party = (
        "<RltdPties><Cdtr><Nm>Landlord Ltd</Nm></Cdtr><Dbtr><Nm>Me Myself</Nm></Dbtr></RltdPties>"
    )
    info = "<AddtlNtryInf>entry info</AddtlNtryInf>"
    cases = [
        # additional transaction info beats the counterparty
        (
            "DBIT",
            details(tx("10.00", body="<AddtlTxInf>Card payment</AddtlTxInf>" + party)) + info,
            "Card payment",
        ),
        # a debit names the creditor, a credit names the debtor
        ("DBIT", details(tx("10.00", body=party)) + info, "Landlord Ltd"),
        ("CRDT", details(tx("10.00", body=party)) + info, "Me Myself"),
        ("DBIT", "<AddtlNtryInf>entry   info</AddtlNtryInf>", "entry info"),
        ("DBIT", "<NtryDtls><Btch><PmtInfId>PAY-77</PmtInfId></Btch></NtryDtls>", "PAY-77"),
        (
            "DBIT",
            "<BkTxCd><Domn><Cd>PMNT</Cd><Fmly><Cd>ICDT</Cd><SubFmlyCd>ESCT</SubFmlyCd></Fmly>"
            "</Domn></BkTxCd>",
            "PMNT/ICDT/ESCT",
        ),
        ("DBIT", "<BkTxCd><Prtry><Cd>NTRF+805</Cd></Prtry></BkTxCd>", "NTRF+805"),
    ]
    for indicator, body, expected in cases:
        row = read_camt053(camt(stmt(ntry(indicator=indicator, body=body))), max_rows=MAX).rows[0]
        assert row.description == expected, (indicator, body)


def test_camt_entry_without_any_text_still_gets_a_description():
    row = read_camt053(camt(stmt(ntry())), max_rows=MAX).rows[0]
    assert row.description


def test_camt_external_id_prefers_service_reference_and_is_not_deduplicated():
    entries = [
        ntry("1.00", refs="<NtryRef>N1</NtryRef><AcctSvcrRef>SAME</AcctSvcrRef>"),
        ntry("2.00", refs="<NtryRef>N2</NtryRef><AcctSvcrRef>SAME</AcctSvcrRef>"),
        ntry("3.00", refs="<NtryRef>N3</NtryRef>"),
        ntry("4.00"),
    ]
    rows = read_camt053(camt(stmt(*entries)), max_rows=MAX).rows
    assert [r.external_id for r in rows] == ["SAME", "SAME", "N3", None]


# -------------------------------------------------------------- camt.053: structure and limits


def test_camt_reads_every_statement_with_continuous_line_numbers():
    data = camt(
        stmt(ntry("1.00"), ntry("2.00"), ccy="CHF"),
        stmt(ntry("3.00", "CRDT", ccy="USD"), ccy="USD"),
    )
    parsed = read_camt053(data, max_rows=MAX)
    assert [r.line for r in parsed.rows] == [1, 2, 3]
    assert [r.currency for r in parsed.rows] == ["EUR", "EUR", "USD"]
    assert parsed.currency_hint == "CHF"


def test_camt_account_currency_falls_back_to_opening_balance_then_entries():
    balance = (
        '<Bal><Tp><CdOrPrtry><Cd>OPBD</Cd></CdOrPrtry></Tp><Amt Ccy="GBP">5.00</Amt>'
        "<CdtDbtInd>CRDT</CdtDbtInd></Bal>"
    )
    with_balance = f"<Stmt><Id>1</Id>{balance}{ntry(ccy='GBP')}</Stmt>"
    assert read_camt053(camt(with_balance), max_rows=MAX).currency_hint == "GBP"
    bare = f"<Stmt><Id>1</Id>{ntry(ccy='SEK')}</Stmt>"
    assert read_camt053(camt(bare), max_rows=MAX).currency_hint == "SEK"


def test_camt_reports_and_notifications_are_read_too():
    data = camt(stmt(ntry("1.00"), tag="Ntfctn"), stmt(ntry("2.00"), tag="Rpt"))
    assert len(read_camt053(data, max_rows=MAX).rows) == 2


def test_camt_row_cap():
    entries = [ntry(f"{i}.00") for i in range(1, 6)]
    assert len(read_camt053(camt(stmt(*entries)), max_rows=5).rows) == 5
    with pytest.raises(FileProblem) as caught:
        read_camt053(camt(stmt(*entries)), max_rows=4)
    assert caught.value.code == "too_many_rows"
    assert caught.value.status_code == 413


def test_camt_row_cap_counts_split_batch_rows():
    batch = ntry("30.00", body=details(tx("10.00"), tx("10.00"), tx("10.00")))
    assert len(read_camt053(camt(stmt(batch)), max_rows=3).rows) == 3
    with pytest.raises(FileProblem) as caught:
        read_camt053(camt(stmt(batch)), max_rows=2)
    assert caught.value.code == "too_many_rows"


def test_camt_bad_entries_are_rejected_without_aborting_the_file():
    entries = [
        ntry("10.00"),
        ntry("abc"),
        ntry("0.00"),
        ntry("-5.00"),
        ntry("NaN"),
        ntry("5.00", booked=None),
        ntry("5.00", indicator="XXXX"),
        ntry("7.00"),
    ]
    parsed = read_camt053(camt(stmt(*entries)), max_rows=MAX)
    assert [r.debit for r in parsed.rows] == [Decimal("10.00"), Decimal("7.00")]
    assert [r.line for r in parsed.rejected] == [2, 3, 4, 5, 6, 7]
    assert all(r.reason and len(r.raw) <= 200 for r in parsed.rejected)


def test_camt_amounts_are_rounded_to_two_places():
    row = read_camt053(camt(stmt(ntry("12.345"))), max_rows=MAX).rows[0]
    assert row.debit == Decimal("12.35")


# ------------------------------------------------------------------ camt.053: hostile / broken


@pytest.mark.parametrize(
    "prefix",
    [
        '<!DOCTYPE foo [<!ENTITY x "boom">]>',
        "<!doctype Document>",
        '<!ENTITY y SYSTEM "file:///etc/passwd">',
    ],
)
def test_camt_doctype_and_entities_are_refused(prefix):
    data = camt(stmt(ntry()))
    declaration, _, rest = data.partition(b"?>")
    hostile = declaration + b"?>" + prefix.encode() + rest
    with pytest.raises(FileProblem) as caught:
        read_camt053(hostile, max_rows=MAX)
    assert caught.value.code == "file_corrupt"


def test_camt_doctype_is_refused_in_utf16_too():
    data = camt(stmt(ntry())).decode().replace("<Document", "<!DOCTYPE d><Document", 1)
    with pytest.raises(FileProblem) as caught:
        read_camt053(data.encode("utf-16"), max_rows=MAX)
    assert caught.value.code == "file_corrupt"


def test_camt_billion_laughs_is_never_expanded():
    bomb = (
        b'<?xml version="1.0"?><!DOCTYPE lolz [<!ENTITY a "aaaaaaaaaa">'
        b'<!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;">]><Document>&b;</Document>'
    )
    with pytest.raises(FileProblem) as caught:
        read_camt053(bomb, max_rows=MAX)
    assert caught.value.code == "file_corrupt"


@pytest.mark.parametrize(
    "data",
    [b"", b"not xml at all", b"<Document><Stmt>", b"\xff\xfe\x00garbage", b"<a></b>"],
)
def test_camt_malformed_xml_is_file_corrupt(data):
    with pytest.raises(FileProblem) as caught:
        read_camt053(data, max_rows=MAX)
    assert caught.value.code == "file_corrupt"


def test_camt_xml_that_is_not_a_statement_is_file_corrupt():
    with pytest.raises(FileProblem) as caught:
        read_camt053(b"<Document><Other/></Document>", max_rows=MAX)
    assert caught.value.code == "file_corrupt"


def test_camt_empty_statement_has_no_transactions():
    with pytest.raises(FileProblem) as caught:
        read_camt053(camt(stmt()), max_rows=MAX)
    assert caught.value.code == "no_transactions_found"


def test_camt_deeply_nested_xml_does_not_escape():
    deep = b"<Document>" + b"<a>" * 50_000 + b"</a>" * 50_000 + b"</Document>"
    with pytest.raises(FileProblem):
        read_camt053(deep, max_rows=MAX)


# --------------------------------------------------------------------------- MT940 builders


def mt940(*lines: str, crlf: bool = False, wrapped: bool = False) -> bytes:
    body = "\n".join(lines)
    if wrapped:
        body = (
            "{1:F01BANKDEFFAXXX0000000000}{2:I940BANKDEFFXXXXN}{3:{108:REF}}{4:\n" + body + "\n-}"
        )
    if crlf:
        body = body.replace("\n", "\r\n")
    return body.encode("utf-8")


def statement_lines(*entries: str, currency: str = "EUR", opening: str = "100,00") -> list[str]:
    return [
        ":20:STMT1",
        ":25:DE00123",
        ":28C:1/1",
        f":60F:C240301{currency}{opening}",
        *entries,
        f":62F:C240331{currency}100,00",
    ]


# --------------------------------------------------------------------------- MT940: happy paths


@pytest.mark.parametrize("wrapped", [False, True])
@pytest.mark.parametrize("crlf", [False, True])
def test_mt940_bare_and_block_wrapped_files(wrapped, crlf):
    data = mt940(
        *statement_lines(
            ":61:2403050305C1500,NTRFNONREF//BANKREF1",
            ":86:Salary March",
            ":61:2403060306D54,90NMSCINV-77",
            ":86:Adobe",
        ),
        wrapped=wrapped,
        crlf=crlf,
    )
    parsed = read_mt940(data, max_rows=MAX)
    assert parsed.source_format is SourceFormat.MT940
    assert parsed.currency_hint == "EUR"
    first, second = parsed.rows
    assert (first.credit, first.debit, first.amount) == (Decimal("1500.00"), None, None)
    assert (second.debit, second.credit) == (Decimal("54.90"), None)
    assert first.external_id == "BANKREF1"
    assert second.external_id is None
    assert [r.description for r in parsed.rows] == ["Salary March", "Adobe"]
    assert [r.line for r in parsed.rows] == [1, 2]
    assert first.currency == "EUR"
    assert first.date == date(2024, 3, 5)


def test_mt940_debit_and_credit_marks_including_reversals():
    data = mt940(
        *statement_lines(
            ":61:240305C10,00NTRFREF",
            ":61:240305D20,00NTRFREF",
            ":61:240305RC30,00NTRFREF",
            ":61:240305RD40,00NTRFREF",
            ":61:240305CR50,00NTRFREF",
        )
    )
    rows = read_mt940(data, max_rows=MAX).rows
    assert [(r.credit, r.debit) for r in rows] == [
        (Decimal("10.00"), None),
        (None, Decimal("20.00")),
        (None, Decimal("30.00")),
        (Decimal("40.00"), None),
        (Decimal("50.00"), None),
    ]
    assert rows[2].description.startswith("Reversal: ")
    assert rows[3].description.startswith("Reversal: ")
    assert not rows[0].description.startswith("Reversal")


def test_mt940_amount_without_decimals_and_with_large_values():
    data = mt940(*statement_lines(":61:240305D1500,NTRFX", ":61:240305C1234567,89NTRFX"))
    amounts = [r.debit or r.credit for r in read_mt940(data, max_rows=MAX).rows]
    assert amounts == [Decimal("1500.00"), Decimal("1234567.89")]


def test_mt940_entry_date_is_the_booking_date_and_value_date_is_the_fallback():
    data = mt940(
        *statement_lines(
            ":61:2403040307C1,00NTRFX",
            ":61:240304C2,00NTRFX",
        )
    )
    first, second = read_mt940(data, max_rows=MAX).rows
    assert first.date == date(2024, 3, 7)
    assert second.date == date(2024, 3, 4)


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        (":61:2412300102C1,00NTRFX", date(2025, 1, 2)),  # booked after the new year
        (":61:2501021230C1,00NTRFX", date(2024, 12, 30)),  # booked before the value date
        (":61:2403040229C1,00NTRFX", date(2024, 2, 29)),  # leap day only exists in 2024
        (":61:2403041118C1,00NTRFX", date(2024, 3, 4)),  # implausibly far: keep the value date
        (":61:2403040230C1,00NTRFX", date(2024, 3, 4)),  # impossible entry date
    ],
)
def test_mt940_entry_date_year_rollover(line, expected):
    row = read_mt940(mt940(*statement_lines(line)), max_rows=MAX).rows[0]
    assert row.date == expected


def test_mt940_two_digit_years_pivot_at_seventy():
    data = mt940(*statement_lines(":61:690101C1,00NTRFX", ":61:700101C1,00NTRFX"))
    rows = read_mt940(data, max_rows=MAX).rows
    assert [r.date.year for r in rows] == [2069, 1970]


def test_mt940_information_lines_are_joined_by_wrap_width():
    full = "A" * 65  # a full-width line was cut mid-word
    short = "SHORT LINE"
    data = mt940(
        *statement_lines(
            ":61:240305C1,00NTRFX",
            f":86:{full}",
            "BBB",
            ":61:240305C2,00NTRFX",
            f":86:{short}",
            "CCC",
        )
    )
    first, second = read_mt940(data, max_rows=MAX).rows
    assert first.description == "A" * 65 + "BBB"
    assert second.description == "SHORT LINE CCC"


def test_mt940_trailing_space_on_a_full_line_is_not_doubled():
    line = ("WORD " * 20)[:65]
    assert len(line) == 65 and line.endswith(" ")
    data = mt940(*statement_lines(":61:240305C1,00NTRFX", f":86:{line}", "NEXT"))
    assert read_mt940(data, max_rows=MAX).rows[0].description.endswith("WORD NEXT")


def test_mt940_german_structured_information_is_reduced_to_text():
    data = mt940(
        *statement_lines(
            ":61:240305D25,00NTRFX",
            ":86:166?00LASTSCHRIFT?10931?20EREF+12345 SVWZ+Monatsbeitrag?21 Maerz 2024?30COBADEFF"
            "?31DE0012345?32Sportverein Muster?33e.V.",
        )
    )
    row = read_mt940(data, max_rows=MAX).rows[0]
    assert row.description.startswith("Sportverein Muster e.V.")
    assert "Monatsbeitrag" in row.description
    assert "?" not in row.description and "COBADEFF" not in row.description


def test_mt940_german_style_with_only_a_posting_text():
    data = mt940(*statement_lines(":61:240305D25,00NTRFX", ":86:805?00DAUERAUFTRAG"))
    assert read_mt940(data, max_rows=MAX).rows[0].description == "DAUERAUFTRAG"


def test_mt940_slash_structured_information_is_reduced_to_text():
    data = mt940(
        *statement_lines(
            ":61:240305D25,00NTRFX",
            ":86:/TRCD/01000/EREF/E2E-1/NAME/Coffee Corner BV/REMI/Invoice 7/IBAN/NL00BANK",
        )
    )
    row = read_mt940(data, max_rows=MAX).rows[0]
    assert row.description == "Coffee Corner BV Invoice 7"


def test_mt940_unstructured_text_with_slashes_is_left_alone():
    data = mt940(*statement_lines(":61:240305D25,00NTRFX", ":86:PAYMENT 12/03 TO A/B SHOP"))
    assert read_mt940(data, max_rows=MAX).rows[0].description == "PAYMENT 12/03 TO A/B SHOP"


def test_mt940_description_falls_back_to_reference_then_type_code():
    data = mt940(
        *statement_lines(
            ":61:240305D1,00NTRFINV-9//B1",
            "supplementary words",
            ":61:240305D2,00NCHGNONREF",
            ":61:240305D3,00NMSC",
        )
    )
    rows = read_mt940(data, max_rows=MAX).rows
    assert rows[0].description == "INV-9 supplementary words"
    assert rows[1].description == "NCHG"
    assert rows[2].description == "NMSC"


def test_mt940_information_does_not_leak_into_the_next_statement_line():
    data = mt940(
        *statement_lines(":61:240305C1,00NTRFX", ":61:240306C2,00NTRFX", ":86:second only")
    )
    first, second = read_mt940(data, max_rows=MAX).rows
    assert first.description == "X"
    assert second.description == "second only"


def test_mt940_reads_every_statement_with_its_own_currency():
    one = statement_lines(":61:240305C1,00NTRFX", currency="CHF")
    two = statement_lines(":61:240306D2,00NTRFX", ":61:240307D3,00NTRFX", currency="USD")
    parsed = read_mt940(mt940(*one, *two, wrapped=True), max_rows=MAX)
    assert [r.currency for r in parsed.rows] == ["CHF", "USD", "USD"]
    assert [r.line for r in parsed.rows] == [1, 2, 3]
    assert parsed.currency_hint == "CHF"


def test_mt940_statements_without_a_reference_tag_are_split_on_the_opening_balance():
    lines = [
        ":60F:C240301CHF10,00",
        ":61:240305C1,00NTRFX",
        ":62F:C240331CHF11,00",
        ":60F:C240401USD10,00",
        ":61:240405C2,00NTRFX",
        ":62F:C240430USD12,00",
    ]
    rows = read_mt940(mt940(*lines), max_rows=MAX).rows
    assert [r.currency for r in rows] == ["CHF", "USD"]


def test_mt940_multiple_wrapped_messages_in_one_file():
    one = mt940(*statement_lines(":61:240305C1,00NTRFX"), wrapped=True)
    two = mt940(*statement_lines(":61:240306C2,00NTRFX"), wrapped=True)
    parsed = read_mt940(one + b"\n" + two, max_rows=MAX)
    assert [r.credit for r in parsed.rows] == [Decimal("1.00"), Decimal("2.00")]


def test_mt940_currency_comes_from_the_closing_balance_when_there_is_no_opening_one():
    lines = [":20:X", ":61:240305C1,00NTRFX", ":62F:C240331SEK5,00"]
    parsed = read_mt940(mt940(*lines), max_rows=MAX)
    assert parsed.rows[0].currency == "SEK"
    assert parsed.currency_hint == "SEK"


def test_mt940_funds_code_letter_is_accepted():
    data = mt940(*statement_lines(":61:240305DR12,50NTRFX"))
    assert read_mt940(data, max_rows=MAX).rows[0].debit == Decimal("12.50")


# ----------------------------------------------------------------------- MT940: bad input


def test_mt940_malformed_statement_lines_are_rejected_not_fatal():
    data = mt940(
        *statement_lines(
            ":61:240305C1,00NTRFX",
            ":61:garbage",
            ":86:ignored text",
            ":61:240305X5,00NTRFX",
            ":61:241305C5,00NTRFX",
            ":61:240305C0,00NTRFX",
            ":61:240305C,NTRFX",
            ":61:240306C9,00NTRFX",
        )
    )
    parsed = read_mt940(data, max_rows=MAX)
    assert [r.credit for r in parsed.rows] == [Decimal("1.00"), Decimal("9.00")]
    assert [r.line for r in parsed.rejected] == [2, 3, 4, 5, 6]
    reasons = [r.reason for r in parsed.rejected]
    assert reasons[0] == "Unreadable :61: statement line"
    assert "Impossible value date" in reasons
    assert "Zero amount" in reasons
    assert all(len(r.raw) <= 200 for r in parsed.rejected)


def test_mt940_row_cap():
    entries = [f":61:240305C{i},00NTRFX" for i in range(1, 6)]
    data = mt940(*statement_lines(*entries))
    assert len(read_mt940(data, max_rows=5).rows) == 5
    with pytest.raises(FileProblem) as caught:
        read_mt940(data, max_rows=4)
    assert caught.value.code == "too_many_rows"
    assert caught.value.status_code == 413


def test_mt940_statement_without_entries():
    with pytest.raises(FileProblem) as caught:
        read_mt940(mt940(*statement_lines()), max_rows=MAX)
    assert caught.value.code == "no_transactions_found"


@pytest.mark.parametrize("data", [b"", b"hello world\nnothing here", b"{1:F01}{4:\n-}"])
def test_mt940_text_without_fields_is_file_corrupt(data):
    with pytest.raises(FileProblem) as caught:
        read_mt940(data, max_rows=MAX)
    assert caught.value.code == "file_corrupt"


def test_mt940_cp1252_text_is_decoded():
    data = mt940(*statement_lines(":61:240305D1,00NTRFX", ":86:CAFÉ DU MONDE")).decode()
    row = read_mt940(data.encode("cp1252"), max_rows=MAX).rows[0]
    assert row.description == "CAFÉ DU MONDE"


# ----------------------------------------------------------------- totality on arbitrary bytes


def test_readers_never_raise_anything_but_file_problem():
    rng = random.Random(940)
    valid_camt = camt(stmt(ntry("1.00", body=details(tx("0.50"), tx("0.50")))))
    valid_mt = mt940(*statement_lines(":61:240305C1,00NTRFX", ":86:text"), wrapped=True)
    samples: list[bytes] = [rng.randbytes(rng.randint(0, 400)) for _ in range(150)]
    for original in (valid_camt, valid_mt):
        samples += [original[:cut] for cut in range(0, len(original), 9)]
        for _ in range(60):
            mutated = bytearray(original)
            for _ in range(rng.randint(1, 6)):
                mutated[rng.randrange(len(mutated))] = rng.randrange(256)
            samples.append(bytes(mutated))
    for data in samples:
        for reader in (read_camt053, read_mt940):
            with contextlib.suppress(FileProblem):
                reader(data, max_rows=50)


# ------------------------------------------------------------------- reference sample files

PENDING_HINT = "reference sample missing, run scripts/fetch_reference_samples.py"


def _sample(name: str) -> bytes:
    path = CACHE / name
    if not path.exists():
        pytest.skip(f"{name}: {PENDING_HINT}")
    return path.read_bytes()


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _sub(elem: ET.Element, *path: str) -> ET.Element | None:
    for name in path:
        nxt = [c for c in elem if _local(c.tag) == name]
        if not nxt:
            return None
        elem = nxt[0]
    return elem


def _signed(amount: str, indicator: str) -> Decimal:
    value = Decimal(amount)
    return value if indicator == "CRDT" else -value


def _camt_balances(root: ET.Element) -> dict[str, tuple[Decimal, date]]:
    out: dict[str, tuple[Decimal, date]] = {}
    for bal in root.iter():
        if _local(bal.tag) != "Bal":
            continue
        code = _sub(bal, "Tp", "CdOrPrtry", "Cd")
        amt, ind, when = _sub(bal, "Amt"), _sub(bal, "CdtDbtInd"), _sub(bal, "Dt", "Dt")
        if code is None or amt is None or ind is None or when is None:
            continue
        out[(code.text or "").strip()] = (
            _signed((amt.text or "").strip(), (ind.text or "").strip()),
            date.fromisoformat((when.text or "").strip()[:10]),
        )
    return out


CAMT_SAMPLES = ["camt053_v2009.xml", "camt053_v2019.xml"]
MT940_SAMPLES = ["mt940_nocode.dat", "mt940_code.dat"]


@pytest.mark.parametrize("name", CAMT_SAMPLES)
def test_reference_camt053_postfinance_sample(name):
    data = _sample(name)
    parsed = read_camt053(data, max_rows=MAX)

    assert parsed.rows and not parsed.rejected
    assert parsed.currency_hint == "CHF"
    for row in parsed.rows:
        assert (row.debit is None) != (row.credit is None)
        assert row.currency == "CHF"
        assert row.description and row.external_id

    # The bank's closing balance is value-dated: an entry booked on the closing date but
    # valued the day after is not in CLBD yet. Everything else must reconcile exactly.
    root = ET.fromstring(data)
    balances = _camt_balances(root)
    opening, _ = balances["OPBD"]
    closing, closing_date = balances["CLBD"]
    movement = sum((r.credit or Decimal(0)) - (r.debit or Decimal(0)) for r in parsed.rows)

    not_yet_valued = Decimal(0)
    for entry in root.iter():
        if _local(entry.tag) != "Ntry":
            continue
        valued = _sub(entry, "ValDt", "Dt")
        if valued is not None and date.fromisoformat((valued.text or "")[:10]) > closing_date:
            amt, ind = _sub(entry, "Amt"), _sub(entry, "CdtDbtInd")
            assert amt is not None and ind is not None
            not_yet_valued += _signed((amt.text or "").strip(), (ind.text or "").strip())

    assert movement - not_yet_valued == closing - opening


def test_reference_camt053_sample_versions_agree_on_amounts():
    old = read_camt053(_sample("camt053_v2009.xml"), max_rows=MAX).rows
    new = read_camt053(_sample("camt053_v2019.xml"), max_rows=MAX).rows
    assert [(r.debit, r.credit, r.date) for r in old] == [(r.debit, r.credit, r.date) for r in new]


def _mt940_balance(text: str, tag: str) -> Decimal:
    match = re.search(rf"^:{tag}:([CD])\d{{6}}[A-Z]{{3}}([\d,]+)", text, re.M)
    assert match, f"no :{tag}: in sample"
    value = Decimal(match.group(2).replace(",", "."))
    return value if match.group(1) == "C" else -value


@pytest.mark.parametrize("name", MT940_SAMPLES)
def test_reference_mt940_postfinance_sample(name):
    data = _sample(name)
    parsed = read_mt940(data, max_rows=MAX)

    assert parsed.rows and not parsed.rejected
    assert parsed.currency_hint == "CHF"
    for row in parsed.rows:
        assert (row.debit is None) != (row.credit is None)
        assert row.currency == "CHF"
        assert row.description and row.external_id
        assert "?" not in row.description

    text = decode_text(data)
    movement = sum((r.credit or Decimal(0)) - (r.debit or Decimal(0)) for r in parsed.rows)
    assert movement == _mt940_balance(text, "62F") - _mt940_balance(text, "60F")


def test_reference_mt940_code_and_nocode_samples_describe_the_same_payments():
    plain = read_mt940(_sample("mt940_nocode.dat"), max_rows=MAX).rows
    coded = read_mt940(_sample("mt940_code.dat"), max_rows=MAX).rows
    assert [(r.credit, r.external_id) for r in plain] == [(r.credit, r.external_id) for r in coded]
    # The GVC code and ?61 marker of the coded variant are stripped from the text.
    assert coded[0].description == plain[0].description
