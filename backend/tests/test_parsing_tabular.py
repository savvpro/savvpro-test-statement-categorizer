from datetime import date
from decimal import Decimal

import pytest

from app.domain.models import SourceFormat
from app.errors import FileProblem
from app.parsing.csv_reader import decode_text, read_csv, sniff_delimiter
from app.parsing.ofx_reader import read_ofx
from app.parsing.tabular import find_columns, normalize_label
from app.parsing.xlsx_reader import read_xlsx
from tests.factories import CARD_ROWS, OFX_SAMPLE, csv_bytes, xlsx_bytes

MAX = 5000


def test_reads_a_plain_card_csv():
    parsed = read_csv(csv_bytes(CARD_ROWS), max_rows=MAX)
    assert parsed.source_format is SourceFormat.CSV
    assert [r.amount for r in parsed.rows] == [
        Decimal("54.99"),
        Decimal("23.40"),
        Decimal("-500.00"),
    ]
    assert parsed.rows[0].date == date(2026, 3, 1)
    assert parsed.rows[0].line == 2
    assert not parsed.rejected


def test_utf8_bom_and_windows_line_endings():
    raw = b"\xef\xbb\xbf" + b"Date,Description,Amount\r\n2026-03-01,ADOBE,10.00\r\n"
    assert len(read_csv(raw, max_rows=MAX).rows) == 1


def test_cp1252_bytes_are_decoded_not_rejected():
    raw = "Date,Description,Amount\n2026-03-01,CAF\xc9 DU MONDE,10.00\n".encode("cp1252")
    parsed = read_csv(raw, max_rows=MAX)
    assert parsed.rows[0].description == "CAFÉ DU MONDE"


def test_utf16_export():
    raw = "Date,Description,Amount\n2026-03-01,ADOBE,10.00\n".encode("utf-16")
    assert len(read_csv(raw, max_rows=MAX).rows) == 1


def test_semicolon_and_tab_delimiters_are_sniffed():
    semi = b"Date;Description;Amount\n2026-03-01;ADOBE;10,50\n"
    tab = b"Date\tDescription\tAmount\n2026-03-01\tADOBE\t10.50\n"
    assert read_csv(semi, max_rows=MAX).rows[0].amount == Decimal("10.50")
    assert read_csv(tab, max_rows=MAX).rows[0].amount == Decimal("10.50")
    assert sniff_delimiter(["a;b;c", "1;2;3"]) == ";"


def test_preamble_before_the_header_is_skipped():
    raw = b"Business Checking\nPeriod: March\n\nDate,Details,Amount\n2026-03-01,ADOBE,10.00\n"
    parsed = read_csv(raw, max_rows=MAX)
    assert len(parsed.rows) == 1
    assert parsed.rows[0].line == 5


def test_excel_sep_hint_line_is_ignored():
    raw = b"sep=;\nDate;Description;Amount\n2026-03-01;ADOBE;10.00\n"
    assert len(read_csv(raw, max_rows=MAX).rows) == 1


def test_quoted_fields_with_commas_and_thousands_separators():
    raw = b'Date,Description,Amount\n2026-03-01,"MICROSOFT 365, SEATTLE","1,250.00"\n'
    row = read_csv(raw, max_rows=MAX).rows[0]
    assert row.description == "MICROSOFT 365, SEATTLE"
    assert row.amount == Decimal("1250.00")


def test_debit_and_credit_columns():
    raw = (
        b"Date,Description,Debit,Credit\n"
        b"2026-03-01,GITHUB,4.00,\n"
        b"2026-03-02,CLIENT INVOICE,,900.00\n"
    )
    rows = read_csv(raw, max_rows=MAX).rows
    assert rows[0].debit == Decimal("4.00") and rows[0].credit is None
    assert rows[1].credit == Decimal("900.00") and rows[1].debit is None


def test_cr_dr_suffixes_become_debit_and_credit():
    raw = b"Date,Description,Amount\n2026-03-01,ADOBE,10.00 DR\n2026-03-02,REFUND,10.00 CR\n"
    rows = read_csv(raw, max_rows=MAX).rows
    assert rows[0].debit == Decimal("10.00")
    assert rows[1].credit == Decimal("10.00")


def test_bad_rows_are_rejected_with_reasons_and_good_rows_survive():
    raw = (
        b"Date,Description,Amount\n"
        b"2026-03-01,ADOBE,10.00\n"
        b"not a date,MYSTERY,5.00\n"
        b"2026-03-03,,5.00\n"
        b"2026-03-04,SOMETHING,abc\n"
        b"2026-03-05,FREEBIE,0.00\n"
        b"2026-03-06,SOMETHING ELSE,\n"
        b"\n"
        b"TOTAL,,10.00\n"
    )
    parsed = read_csv(raw, max_rows=MAX)
    assert len(parsed.rows) == 1
    reasons = {r.line: r.reason for r in parsed.rejected}
    assert "date" in reasons[3].lower()
    assert "description" in reasons[4].lower()
    assert "amount" in reasons[5].lower()
    assert "zero" in reasons[6].lower()
    assert "amount" in reasons[7].lower()
    assert "summary" in reasons[9].lower()


def test_ambiguous_dates_produce_a_warning():
    raw = b"Date,Description,Amount\n01/02/2026,ADOBE,10.00\n03/04/2026,FIGMA,5.00\n"
    parsed = read_csv(raw, max_rows=MAX)
    assert parsed.rows[0].date == date(2026, 1, 2)
    assert any("month/day/year" in w for w in parsed.warnings)


def test_day_first_dates_are_detected_from_the_column():
    raw = b"Date,Description,Amount\n25/02/2026,ADOBE,10.00\n03/04/2026,FIGMA,5.00\n"
    parsed = read_csv(raw, max_rows=MAX)
    assert parsed.rows[1].date == date(2026, 4, 3)
    assert not parsed.warnings


def test_localised_headers():
    raw = b"Buchungstag;Beschreibung;Betrag;Waehrung\n15.05.2026;ADOBE;-59,49;EUR\n"
    row = read_csv(raw, max_rows=MAX).rows[0]
    assert row.amount == Decimal("-59.49") and row.currency == "EUR"


def test_missing_columns_has_a_clear_code():
    with pytest.raises(FileProblem) as info:
        read_csv(b"Name,Age\nAda,36\n", max_rows=MAX)
    assert info.value.code == "missing_columns"


def test_row_cap_is_enforced():
    rows = [["Date", "Description", "Amount"]] + [
        ["2026-03-01", f"SHOP {i}", "1.00"] for i in range(30)
    ]
    with pytest.raises(FileProblem) as info:
        read_csv(csv_bytes(rows), max_rows=10)
    assert info.value.code == "too_many_rows"
    assert info.value.status_code == 413


def test_nul_bytes_and_garbage_do_not_crash():
    with pytest.raises(FileProblem):
        read_csv(b"\x00\x01\x02garbage\x00", max_rows=MAX)


def test_decode_never_raises():
    assert isinstance(decode_text(bytes(range(256))), str)


# -- xlsx ------------------------------------------------------------------------------------


def test_xlsx_with_real_dates_and_numbers():
    data = xlsx_bytes(
        {
            "March": [
                ["Date", "Description", "Amount"],
                [date(2026, 3, 1), "ADOBE", 54.99],
                [date(2026, 3, 2), "UBER", 23.4],
            ]
        }
    )
    parsed = read_xlsx(data, max_rows=MAX)
    assert parsed.source_format is SourceFormat.XLSX
    assert [r.amount for r in parsed.rows] == [Decimal("54.99"), Decimal("23.40")]
    assert parsed.rows[0].date == date(2026, 3, 1)


def test_xlsx_picks_the_sheet_with_transactions():
    data = xlsx_bytes(
        {
            "Cover": [["Statement for Ada"], ["Page 1"]],
            "Transactions": [["Date", "Description", "Amount"], ["2026-03-01", "ADOBE", "10.00"]],
        }
    )
    parsed = read_xlsx(data, max_rows=MAX)
    assert len(parsed.rows) == 1
    assert any("Transactions" in w for w in parsed.warnings)


def test_xlsx_without_a_transaction_table():
    with pytest.raises(FileProblem) as info:
        read_xlsx(xlsx_bytes({"Cover": [["hello"]]}), max_rows=MAX)
    assert info.value.code == "missing_columns"


def test_corrupt_xlsx_is_a_file_problem():
    with pytest.raises(FileProblem):
        read_xlsx(b"PK\x03\x04 not really a workbook", max_rows=MAX)


# -- ofx -------------------------------------------------------------------------------------


def test_ofx_signs_and_currency():
    parsed = read_ofx(OFX_SAMPLE, max_rows=MAX)
    assert parsed.currency_hint == "USD"
    assert parsed.convention_hint is not None
    assert [r.amount for r in parsed.rows] == [Decimal("-54.99"), Decimal("1200.00")]
    assert parsed.rows[0].date == date(2026, 3, 2)


def test_ofx_repeated_transaction_ids_are_ignored_with_a_warning():
    doubled = OFX_SAMPLE.replace(b"<FITID>2<", b"<FITID>1<")
    parsed = read_ofx(doubled, max_rows=MAX)
    assert len(parsed.rows) == 1
    assert any("repeated" in w for w in parsed.warnings)


def test_ofx_without_transactions():
    with pytest.raises(FileProblem) as info:
        read_ofx(b"<OFX><BANKMSGSRSV1></BANKMSGSRSV1></OFX>", max_rows=MAX)
    assert info.value.code == "no_transactions_found"


# -- header normalisation and aliases --------------------------------------------------------


@pytest.mark.parametrize(
    ("label", "normalised"),
    [
        ("Gross Amount (£)", "gross amount"),
        ("$ Amount", "amount"),
        ("Supplier (Beneficiary)", "supplier"),
        ("Procurement (Merchant) Category", "procurement category"),
        ("Withdrawal (-)", "withdrawal"),
        ("Chèques et débits ($)", "cheques et debits"),
        ("Libellé", "libelle"),
        ("  Trans. Date ", "trans date"),
        ("Date\n日期", "date"),
        ("Date de l'opération", "date de l operation"),
        ("(Amount)", "amount"),
        ("Af/Bij", "af bij"),
    ],
)
def test_labels_are_normalised_before_matching(label, normalised):
    assert normalize_label(label) == normalised


def _columns(*labels):
    columns = find_columns([list(labels)])
    assert columns is not None, labels
    return columns


def test_headers_with_symbols_and_brackets_are_recognised():
    columns = _columns(
        "Organisation Name", "Supplier (Beneficiary)", "Procurement (Merchant) Category",
        "Purchase Date", "Settlement Date", "Gross Amount (£)",
    )  # fmt: skip
    assert (columns.date, columns.description, columns.amount) == (3, 1, 5)
    assert columns.header_currency == "GBP"


def test_the_transaction_date_beats_posting_and_settlement_dates():
    assert _columns("Post Date", "Trans Date", "Description", "$ Amount").date == 1
    assert _columns("Value Date", "Booking Date", "Details", "Amount").date == 1
    assert _columns("Settlement Date", "Purchase Date", "Merchant", "Amount").date == 1
    # With only a secondary date available it is still used.
    assert _columns("Posted", "Description", "Amount").date == 0


def test_the_earlier_date_column_wins_a_tie():
    assert _columns("Date", "Description", "Transaction Date", "Amount").date == 0


def test_counterparty_and_description_are_both_used():
    columns = _columns("Date", "Counterparty", "Description", "Amount")
    assert (columns.description, columns.extra_description) == (1, (2,))
    raw = b"Date,Counterparty,Description,Amount\n2026-03-01,Jumbo,SEPA DEBIT,-5.00\n"
    assert read_csv(raw, max_rows=MAX).rows[0].description == "Jumbo SEPA DEBIT"
    other = b"Date,Merchant,Description,Amount\n2026-03-01,Amazon,AMZN Mktp US,-5.00\n"
    assert read_csv(other, max_rows=MAX).rows[0].description == "Amazon AMZN Mktp US"
    repeated = b"Date,Merchant,Description,Amount\n2026-03-01,Amazon,AMAZON.COM AMZN,-5.00\n"
    assert read_csv(repeated, max_rows=MAX).rows[0].description == "AMAZON.COM AMZN"
    same = b"Date,Merchant,Description,Amount\n2026-03-01,Amazon,Amazon Prime,-5.00\n"
    assert read_csv(same, max_rows=MAX).rows[0].description == "Amazon Prime"


@pytest.mark.parametrize(
    "labels",
    [
        ("Date", "Libellé", "Débit", "Crédit", "Solde"),
        ("Date de l'opération", "Libellé", "Retrait", "Dépôt", "Solde"),
        ("Datum", "Omschrijving", "Af", "Bij", "Saldo"),
        ("Datum", "Naam / Omschrijving", "Bedrag (EUR)"),
        ("Fecha", "Concepto", "Importe", "Saldo"),
        ("Buchungstag", "Verwendungszweck", "Soll", "Haben"),
        ("Date", "Transaction Details", "Paid out", "Paid in", "Balance"),
        ("Date", "Narration", "Withdrawals", "Deposits"),
        ("Date", "Merchant Name or Transaction Description", "$ Amount"),
        ("Date", "Payee", "Money out", "Money in"),
    ],
)
def test_localised_and_bank_style_headers(labels):
    columns = _columns(*labels)
    assert columns.date == 0 and columns.description == 1


def test_debit_credit_columns_are_not_mistaken_for_a_direction_flag():
    columns = _columns("Date", "Description", "Debit", "Credit")
    assert (columns.debit, columns.credit, columns.direction) == (2, 3, None)
    flagged = _columns("Date", "Description", "Amount", "Debit/Credit")
    assert flagged.direction == 3


def test_unrelated_columns_are_not_picked_up():
    assert find_columns([["Date", "Category", "Notes"]]) is None
    assert find_columns([["Organisation Name", "Procurement (Merchant) Category", "Gross"]]) is None


# -- currency ---------------------------------------------------------------------------------


def test_currency_from_the_amount_header():
    raw = "Date,Description,Amount (£)\n2026-03-01,SHOP,10.00\n".encode()
    assert read_csv(raw, max_rows=MAX).currency_hint == "GBP"
    raw = "Date;Omschrijving;Bedrag (€)\n01-03-2026;SHOP;10,00\n".encode()
    assert read_csv(raw, max_rows=MAX).currency_hint == "EUR"
    raw = b"Date,Description,$ Amount\n2026-03-01,SHOP,10.00\n"
    assert read_csv(raw, max_rows=MAX).currency_hint == "USD"


def test_currency_from_the_amount_cells_and_from_a_currency_column():
    cells = "Date,Description,Amount\n2026-03-01,A,€10.00\n2026-03-02,B,€5.00\n".encode()
    assert read_csv(cells, max_rows=MAX).currency_hint == "EUR"
    column = b"Date,Description,Amount,Currency\n2026-03-01,A,10.00,CHF\n2026-03-02,B,5.00,CHF\n"
    assert read_csv(column, max_rows=MAX).currency_hint == "CHF"
    plain = b"Date,Description,Amount\n2026-03-01,A,10.00\n"
    assert read_csv(plain, max_rows=MAX).currency_hint is None


def test_a_sterling_file_with_ambiguous_dates_is_read_day_first():
    raw = "Date,Description,Amount (£)\n01/02/2026,A,10.00\n03/04/2026,B,5.00\n".encode()
    parsed = read_csv(raw, max_rows=MAX)
    assert parsed.rows[0].date == date(2026, 2, 1)
    assert any("day/month/year" in w for w in parsed.warnings)


# -- rows spread over several lines, direction and running balance ------------------------------


def test_a_row_without_a_date_continues_the_previous_one():
    raw = (
        b"Date,Description,Amount\n"
        b"2026-03-01,TRANSFER TO,-10.00\n"
        b",J SMITH REF 1234,\n"
        b",,\n"
        b"2026-03-02,GITHUB,-4.00\n"
    )
    parsed = read_csv(raw, max_rows=MAX)
    assert [r.description for r in parsed.rows] == ["TRANSFER TO J SMITH REF 1234", "GITHUB"]
    assert not parsed.rejected


def test_a_row_without_a_date_but_with_an_amount_is_still_rejected():
    raw = b"Date,Description,Amount\n2026-03-01,A,-10.00\n,B,-4.00\n"
    parsed = read_csv(raw, max_rows=MAX)
    assert len(parsed.rows) == 1 and "date" in parsed.rejected[0].reason.lower()


def test_direction_column_turns_an_unsigned_amount_into_debit_or_credit():
    raw = (
        b"Datum;Naam / Omschrijving;Af/Bij;Bedrag (EUR)\n"
        b"01-03-2026;JUMBO;Af;12,50\n"
        b"02-03-2026;SALARIS;Bij;2.500,00\n"
    )
    rows = read_csv(raw, max_rows=MAX).rows
    assert rows[0].debit == Decimal("12.50") and rows[0].amount is None
    assert rows[1].credit == Decimal("2500.00")


BALANCE_CSV = (
    "Date,Description,Amount,Balance\n"
    "2026-03-01,Balance brought forward,,1000.00\n"
    "2026-03-02,ADOBE,54.99,945.01\n"
    "2026-03-03,CLIENT INVOICE,400.00,1345.01\n"
    "2026-03-04,UBER,23.40,1321.61\n"
    "2026-03-05,GITHUB,4.00,1317.61\n"
)


def test_a_running_balance_decides_the_direction_of_unsigned_amounts():
    parsed = read_csv(BALANCE_CSV.encode(), max_rows=MAX)
    assert [(r.debit, r.credit, r.amount) for r in parsed.rows] == [
        (Decimal("54.99"), None, None),
        (None, Decimal("400.00"), None),
        (Decimal("23.40"), None, None),
        (Decimal("4.00"), None, None),
    ]
    assert not parsed.warnings


def test_a_running_balance_also_works_newest_first():
    lines = BALANCE_CSV.splitlines()
    reversed_csv = "\n".join([lines[0], *reversed(lines[2:])]) + "\n"
    rows = read_csv(reversed_csv.encode(), max_rows=MAX).rows
    assert [(r.debit, r.credit) for r in rows[:3]] == [
        (Decimal("4.00"), None),
        (Decimal("23.40"), None),
        (None, Decimal("400.00")),
    ]


def test_a_balance_column_that_does_not_chain_is_ignored_with_a_warning():
    raw = (
        b"Date,Description,Amount,Balance\n"
        b"2026-03-02,ADOBE,54.99,12.00\n"
        b"2026-03-03,CLIENT INVOICE,400.00,99.00\n"
        b"2026-03-04,UBER,23.40,7.00\n"
    )
    parsed = read_csv(raw, max_rows=MAX)
    assert [r.amount for r in parsed.rows] == [
        Decimal("54.99"),
        Decimal("400.00"),
        Decimal("23.40"),
    ]
    assert any("running balance" in w for w in parsed.warnings)


def test_balance_overrides_a_misplaced_debit_credit_column():
    raw = (
        b"Date,Description,Debit,Credit,Balance\n"
        b"2026-03-02,ADOBE,54.99,,945.01\n"
        b"2026-03-03,CLIENT INVOICE,,400.00,1345.01\n"
        b"2026-03-04,UBER,,23.40,1321.61\n"
        b"2026-03-05,GITHUB,4.00,,1317.61\n"
    )
    rows = read_csv(raw, max_rows=MAX).rows
    assert rows[2].debit == Decimal("23.40") and rows[2].credit is None


def test_summary_lines_are_rejected_but_total_wine_is_a_merchant():
    raw = (
        b"Date,Description,Amount\n"
        b"2026-03-01,TOTAL WINE & MORE,25.00\n"
        b"2026-03-02,Total,100.00\n"
        b"2026-03-03,Closing balance,100.00\n"
    )
    parsed = read_csv(raw, max_rows=MAX)
    assert [r.description for r in parsed.rows] == ["TOTAL WINE & MORE"]
    assert len(parsed.rejected) == 2
