"""
Tests for the statement parser.
"""

import pytest

from app.parser import Transaction, parse_csv, parse_ofx, parse_statement


# ---------------------------------------------------------------------------
# CSV parsing
# ---------------------------------------------------------------------------

SIMPLE_CSV = b"""Date,Description,Amount
2024-01-05,STARBUCKS STORE 1234,-4.75
2024-01-06,ADOBE CREATIVE CLOUD,-54.99
2024-01-07,TRANSFER TO SAVINGS,-500.00
2024-01-08,REFUND AMAZON,54.99
"""

ALT_HEADERS_CSV = b"""Transaction Date,Merchant,Payment
01/10/2024,UBER * TRIP,-18.50
01/11/2024,FIGMA INC,-15.00
"""

MESSY_AMOUNTS_CSV = b"""Date,Description,Amount
2024-02-01,LYFT RIDE,(22.00)
2024-02-02,ZOOM SUBSCRIPTION,$14.99
2024-02-03,GOOGLE ADS,"-100,000.00"
"""


class TestCSVParser:
    def test_basic_parse(self):
        txns = parse_csv(SIMPLE_CSV)
        assert len(txns) == 4

    def test_description_extracted(self):
        txns = parse_csv(SIMPLE_CSV)
        assert txns[0].description == "STARBUCKS STORE 1234"

    def test_amount_negative(self):
        txns = parse_csv(SIMPLE_CSV)
        assert txns[0].amount == pytest.approx(-4.75)

    def test_amount_positive_refund(self):
        txns = parse_csv(SIMPLE_CSV)
        assert txns[3].amount == pytest.approx(54.99)

    def test_date_normalised(self):
        txns = parse_csv(SIMPLE_CSV)
        assert txns[0].date == "2024-01-05"

    def test_date_from_mm_dd_yyyy(self):
        txns = parse_csv(ALT_HEADERS_CSV)
        assert txns[0].date == "2024-01-10"

    def test_alternative_column_names(self):
        txns = parse_csv(ALT_HEADERS_CSV)
        assert txns[0].description == "UBER * TRIP"
        assert txns[0].amount == pytest.approx(-18.50)

    def test_parentheses_negative_amount(self):
        txns = parse_csv(MESSY_AMOUNTS_CSV)
        assert txns[0].amount == pytest.approx(-22.00)

    def test_dollar_sign_stripped(self):
        txns = parse_csv(MESSY_AMOUNTS_CSV)
        assert txns[1].amount == pytest.approx(14.99)

    def test_comma_in_large_amount(self):
        txns = parse_csv(MESSY_AMOUNTS_CSV)
        assert txns[2].amount == pytest.approx(-100_000.00)

    def test_blank_rows_skipped(self):
        csv_with_blanks = b"Date,Description,Amount\n2024-01-01,STARBUCKS,-4.75\n,,\n2024-01-02,ADOBE,-54.99\n"
        txns = parse_csv(csv_with_blanks)
        assert len(txns) == 2

    def test_no_header_raises(self):
        with pytest.raises(ValueError):
            parse_csv(b"")

    def test_unknown_desc_column_raises(self):
        csv_bad = b"col1,col2,col3\n1,2,3\n"
        with pytest.raises(ValueError, match="description"):
            parse_csv(csv_bad)

    def test_ids_are_unique(self):
        txns = parse_csv(SIMPLE_CSV)
        ids = [t.id for t in txns]
        assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# OFX parsing
# ---------------------------------------------------------------------------

OFX_SAMPLE = b"""OFXHEADER:100
DATA:OFXSGML
<OFX>
<BANKMSGSRSV1>
<STMTTRNRS>
<STMTRS>
<BANKTRANLIST>
<STMTTRN>
<TRNTYPE>DEBIT
<DTPOSTED>20240115
<TRNAMT>-54.99
<NAME>ADOBE CREATIVE CLOUD
<MEMO>Adobe subscription
</STMTTRN>
<STMTTRN>
<TRNTYPE>DEBIT
<DTPOSTED>20240116
<TRNAMT>-18.50
<NAME>UBER * TRIP
<MEMO>Uber ride
</STMTTRN>
</BANKTRANLIST>
</STMTRS>
</STMTTRNRS>
</BANKMSGSRSV1>
</OFX>
"""


class TestOFXParser:
    def test_finds_transactions(self):
        txns = parse_ofx(OFX_SAMPLE)
        assert len(txns) == 2

    def test_description_from_memo(self):
        txns = parse_ofx(OFX_SAMPLE)
        assert "adobe" in txns[0].description.lower() or "subscription" in txns[0].description.lower()

    def test_amount_parsed(self):
        txns = parse_ofx(OFX_SAMPLE)
        assert txns[0].amount == pytest.approx(-54.99)

    def test_date_normalised(self):
        txns = parse_ofx(OFX_SAMPLE)
        assert txns[0].date == "2024-01-15"


# ---------------------------------------------------------------------------
# parse_statement router
# ---------------------------------------------------------------------------

class TestParseStatement:
    def test_routes_csv(self):
        txns = parse_statement("statement.csv", SIMPLE_CSV)
        assert len(txns) > 0

    def test_routes_ofx(self):
        txns = parse_statement("bank.ofx", OFX_SAMPLE)
        assert len(txns) > 0

    def test_routes_qfx(self):
        txns = parse_statement("bank.qfx", OFX_SAMPLE)
        assert len(txns) > 0

    def test_unsupported_extension_raises(self):
        with pytest.raises(ValueError, match="Unsupported"):
            parse_statement("file.xls", b"some binary data")

    def test_fallback_to_csv_no_extension(self):
        txns = parse_statement("noext", SIMPLE_CSV)
        assert len(txns) > 0
