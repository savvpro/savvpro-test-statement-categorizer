from datetime import date
from decimal import Decimal

import pytest

from app.ingest.reader import SignConvention, StatementParseError, read_statement
from tests.conftest import SAMPLES, csv_bytes


def amounts(parsed):
    return [t.amount for t in parsed.transactions]


def test_basic_bank_export():
    parsed = read_statement(
        csv_bytes(
            "Date,Description,Amount",
            "01/03/2026,SHELL OIL,-45.20",
            "01/06/2026,UBER USA EDI PYMNTS,612.33",
            "01/07/2026,KROGER,-20.00",
        )
    )
    assert amounts(parsed) == [Decimal("-45.20"), Decimal("612.33"), Decimal("-20.00")]
    assert parsed.transactions[0].date == date(2026, 1, 3)
    assert parsed.sign_convention is SignConvention.NEGATIVE_IS_SPENDING


def test_credit_card_export_is_flipped_using_card_payment_row():
    parsed = read_statement(
        csv_bytes(
            "Transaction Date,Description,Amount",
            "2026-01-03,CHEVRON,52.10",
            "2026-01-15,PAYMENT THANK YOU,-800.00",
        )
    )
    assert parsed.sign_convention is SignConvention.POSITIVE_IS_SPENDING
    assert amounts(parsed) == [Decimal("-52.10"), Decimal("800.00")]


def test_explicit_sign_convention_overrides_detection():
    data = csv_bytes("Date,Description,Amount", "01/03/2026,SHELL,45.20", "01/04/2026,KROGER,5")
    parsed = read_statement(data, sign_convention=SignConvention.NEGATIVE_IS_SPENDING)
    assert amounts(parsed) == [Decimal("45.20"), Decimal("5.00")]


def test_debit_credit_columns():
    parsed = read_statement(
        csv_bytes(
            "Date,Description,Debit,Credit",
            "01/03/2026,SHELL OIL,45.20,",
            "01/06/2026,LYFT PAYOUT,,288.10",
        )
    )
    assert amounts(parsed) == [Decimal("-45.20"), Decimal("288.10")]


def test_type_column_gives_direction_for_unsigned_amounts():
    parsed = read_statement(
        csv_bytes(
            "Date,Description,Amount,Type",
            "01/03/2026,SHELL OIL,45.20,Debit",
            "01/06/2026,LYFT PAYOUT,288.10,Credit",
        )
    )
    assert amounts(parsed) == [Decimal("-45.20"), Decimal("288.10")]


def test_preamble_bom_semicolons_and_european_numbers():
    text = (
        "﻿Account;Example\n"
        "Period;Q1\n"
        "\n"
        "Booking Date;Details;Amount\n"
        "13.01.2026;SHELL OIL;-1.234,50\n"
        "14.01.2026;UBER PAYOUT;99,90\n"
    )
    parsed = read_statement(text.encode("utf-8"))
    assert amounts(parsed) == [Decimal("-1234.50"), Decimal("99.90")]
    assert parsed.transactions[0].date == date(2026, 1, 13)
    assert any("account info" in w for w in parsed.warnings)


def test_windows_1252_encoding():
    data = "Date,Description,Amount\n01/03/2026,CAF\xc9 R\xc9AL,-4.00\n".encode("cp1252")
    parsed = read_statement(data)
    assert parsed.transactions[0].description == "CAFÉ RÉAL"


def test_pending_zero_and_total_rows_are_skipped_with_reasons():
    parsed = read_statement(
        csv_bytes(
            "Date,Description,Amount,Status",
            "01/03/2026,SHELL OIL,-45.20,Posted",
            "01/04/2026,SHELL OIL,-30.00,Pending",
            "01/05/2026,CARD VERIFICATION,0.00,Posted",
            ",Total,-75.20,",
            "",
        )
    )
    assert len(parsed.transactions) == 1
    reasons = [s.reason for s in parsed.skipped]
    assert any("Pending" in r for r in reasons)
    assert any("Zero" in r for r in reasons)
    assert any("Summary" in r for r in reasons)


def test_bad_amount_row_is_skipped_not_fatal():
    parsed = read_statement(
        csv_bytes("Date,Description,Amount", "01/03/2026,SHELL,-45.20", "01/04/2026,X,abc")
    )
    assert len(parsed.transactions) == 1
    assert "Not an amount" in parsed.skipped[0].reason


def test_memo_column_is_appended():
    parsed = read_statement(
        csv_bytes("Date,Description,Memo,Amount", "01/03/2026,POS PURCHASE,SHELL OIL,-45.20")
    )
    assert parsed.transactions[0].description == "POS PURCHASE SHELL OIL"


def test_headerless_export_columns_are_inferred():
    parsed = read_statement(
        csv_bytes(
            '"01/03/2026","-45.20","*","","SHELL OIL 57444"',
            '"01/06/2026","612.33","*","","UBER USA EDI PYMNTS"',
        )
    )
    assert amounts(parsed) == [Decimal("-45.20"), Decimal("612.33")]
    assert parsed.transactions[1].description == "UBER USA EDI PYMNTS"


def test_bank_category_column_is_kept():
    parsed = read_statement(
        csv_bytes("Date,Description,Category,Amount", "01/03/2026,CHEVRON,Gas,-52.10")
    )
    assert parsed.transactions[0].bank_category == "Gas"


def test_ofx_file():
    ofx = b"""OFXHEADER:100
<OFX><BANKMSGSRSV1><STMTTRNRS><STMTRS><BANKTRANLIST>
<STMTTRN><TRNTYPE>DEBIT<DTPOSTED>20260103120000<TRNAMT>-45.20<NAME>SHELL OIL 57444
<STMTTRN><TRNTYPE>CREDIT<DTPOSTED>20260106<TRNAMT>612.33<NAME>UBER USA<MEMO>EDI PYMNTS
</BANKTRANLIST></STMTRS></STMTTRNRS></BANKMSGSRSV1></OFX>"""
    parsed = read_statement(ofx)
    assert parsed.file_format == "ofx"
    assert amounts(parsed) == [Decimal("-45.20"), Decimal("612.33")]
    assert parsed.transactions[1].description == "UBER USA EDI PYMNTS"


@pytest.mark.parametrize(
    ("data", "message"),
    [
        (b"", "empty"),
        (b"just some text\nwith no columns\n", "columns"),
        (csv_bytes("Date,Description,Amount", "soon,SHELL,-1"), "date format"),
    ],
)
def test_unreadable_files_raise_friendly_errors(data, message):
    with pytest.raises(StatementParseError, match=message):
        read_statement(data)


def test_sample_files_parse():
    checking = read_statement((SAMPLES / "gig_driver_checking.csv").read_bytes())
    card = read_statement((SAMPLES / "gig_driver_credit_card.csv").read_bytes())
    assert len(checking.transactions) == 41
    assert card.sign_convention is SignConvention.POSITIVE_IS_SPENDING
    assert len(card.skipped) == 2  # one pending row, one total row
