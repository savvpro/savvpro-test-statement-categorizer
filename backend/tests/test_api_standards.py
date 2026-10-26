from pathlib import Path

import pytest

from app.domain.models import SourceFormat
from app.errors import FileProblem
from app.parsing.detect import detect_format
from tests.conftest import upload

CACHE = Path(__file__).parent / "reference_cache"

MT940 = b""":20:STMT0001
:25:DE89370400440532013000
:28C:1/1
:60F:C260301EUR1000,00
:61:2603020302D54,99NMSCNONREF
:86:ADOBE CREATIVE CLOUD
:61:2603050305C1200,00NTRFNONREF
:86:CLIENT INVOICE 5
:61:2603060306D500,00NTRFNONREF
:86:TRANSFER TO SAVINGS
:62F:C260306EUR1645,01
"""

SWIFT_WRAPPED = b"{1:F01BANKDEFFAXXX0000000000}{2:I940BANKDEFFXXXXN}{4:\r\n" + MT940 + b"-}"

CAMT = b"""<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.08">
  <BkToCstmrStmt>
    <GrpHdr><MsgId>1</MsgId></GrpHdr>
    <Stmt>
      <Id>1</Id>
      <Acct><Id><IBAN>CH0000000000000000000</IBAN></Id><Ccy>CHF</Ccy></Acct>
      <Ntry>
        <Amt Ccy="CHF">54.99</Amt><CdtDbtInd>DBIT</CdtDbtInd><Sts><Cd>BOOK</Cd></Sts>
        <BookgDt><Dt>2026-03-02</Dt></BookgDt>
        <AddtlNtryInf>ADOBE CREATIVE CLOUD</AddtlNtryInf>
      </Ntry>
      <Ntry>
        <Amt Ccy="CHF">1200.00</Amt><CdtDbtInd>CRDT</CdtDbtInd><Sts><Cd>BOOK</Cd></Sts>
        <BookgDt><Dt>2026-03-05</Dt></BookgDt>
        <AddtlNtryInf>CLIENT INVOICE 5</AddtlNtryInf>
      </Ntry>
    </Stmt>
  </BkToCstmrStmt>
</Document>
"""


def test_detection():
    assert detect_format("s.sta", MT940)[0] is SourceFormat.MT940
    assert detect_format("s.mt940", SWIFT_WRAPPED)[0] is SourceFormat.MT940
    assert detect_format("s.xml", CAMT)[0] is SourceFormat.CAMT053
    # Wrong extension, right content: read by content, with a warning.
    fmt, warnings = detect_format("s.csv", CAMT)
    assert fmt is SourceFormat.CAMT053 and warnings


def test_other_xml_is_refused_with_a_clear_message():
    pain = (
        b'<?xml version="1.0"?><Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.001.001.03"/>'
    )
    with pytest.raises(FileProblem) as info:
        detect_format("payments.xml", pain)
    assert info.value.code == "unsupported_format"


def test_csv_with_colons_is_not_mistaken_for_mt940():
    csv = b"Date,Description,Amount\n2026-03-01,NOTE: :20: off,5.00\n"
    assert detect_format("a.csv", csv)[0] is SourceFormat.CSV


@pytest.mark.parametrize(
    ("name", "data", "fmt", "currency"),
    [
        ("march.sta", MT940, "mt940", "EUR"),
        ("march.mt940", SWIFT_WRAPPED, "mt940", "EUR"),
        ("march.xml", CAMT, "camt053", "CHF"),
    ],
)
def test_standards_are_categorized_end_to_end(client, name, data, fmt, currency):
    response = upload(client, name, data)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["source_format"] == fmt and body["currency"] == currency
    rows = body["transactions"]
    adobe = next(t for t in rows if "ADOBE" in t["description"])
    income = next(t for t in rows if "INVOICE" in t["description"])
    assert adobe["category_id"] == "software" and adobe["spend_amount"] == 54.99
    assert income["category_id"] == "income" and income["spend_amount"] == -1200.0
    assert body["summary"]["income_total"] == 1200.0


def test_mt940_transfer_row_is_excluded(client):
    rows = upload(client, "march.sta", MT940).json()["transactions"]
    transfer = next(t for t in rows if "SAVINGS" in t["description"])
    assert transfer["status"] == "excluded"


def test_malformed_standards_files_return_clear_errors(client):
    bad_xml = upload(client, "a.xml", CAMT[:200])
    assert bad_xml.status_code == 422 and bad_xml.json()["detail"]["code"] == "file_corrupt"
    entity = b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "b">]>' + CAMT.split(b"?>", 1)[1]
    refused = upload(client, "a.xml", entity)
    assert refused.status_code == 422 and refused.json()["detail"]["code"] == "file_corrupt"


@pytest.mark.skipif(not (CACHE / "camt053_v2019.xml").exists(), reason="run fetch script")
def test_official_postfinance_samples_through_the_api(client):
    for name in ("camt053_v2019.xml", "camt053_v2009.xml", "mt940_nocode.dat", "mt940_code.dat"):
        response = upload(client, name, (CACHE / name).read_bytes())
        assert response.status_code == 201, (name, response.text)
        body = response.json()
        assert body["currency"] == "CHF" and body["summary"]["transaction_count"] >= 3
