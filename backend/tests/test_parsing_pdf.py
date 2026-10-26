import io
from datetime import date
from decimal import Decimal

import pdfplumber
import pytest
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from app.errors import FileProblem
from app.parsing import pdf_reader
from app.parsing.pdf_reader import read_pdf
from tests.factories import (
    pdf_blank_bytes,
    pdf_encrypted_bytes,
    pdf_table_bytes,
    pdf_text_bytes,
)

MAX = 5000
PAGES = 40

TABLE = [
    ["Date", "Description", "Debit", "Credit", "Balance"],
    ["03/01/2026", "ADOBE CREATIVE CLOUD", "54.99", "", "945.01"],
    ["03/02/2026", "CLIENT INVOICE 12", "", "400.00", "1345.01"],
    ["03/03/2026", "UBER TRIP", "23.40", "", "1321.61"],
]

CARD_LINES = [
    "Business Card Statement  March 2026",
    "Date       Description                          Amount",
    "03/01/2026 ADOBE CREATIVE CLOUD                   54.99",
    "03/02/2026 UBER *TRIP                             23.40",
    "03/03/2026 ONLINE PAYMENT THANK YOU             -500.00",
    "Page 1 of 1",
]

BALANCE_LINES = [
    "Date        Description                 Amount     Balance",
    "03/01/2026  OPENING DEPOSIT              1000.00    1000.00",
    "03/02/2026  ADOBE CREATIVE CLOUD           54.99     945.01",
    "03/03/2026  CLIENT INVOICE 12             400.00    1345.01",
    "03/04/2026  UBER TRIP                      23.40    1321.61",
    "03/05/2026  GITHUB                          4.00    1317.61",
]


def test_ruled_table_with_debit_and_credit_columns():
    parsed = read_pdf(pdf_table_bytes(TABLE), max_rows=MAX, max_pages=PAGES)
    assert [r.description for r in parsed.rows] == [
        "ADOBE CREATIVE CLOUD",
        "CLIENT INVOICE 12",
        "UBER TRIP",
    ]
    assert parsed.rows[0].debit == Decimal("54.99")
    assert parsed.rows[1].credit == Decimal("400.00")
    assert parsed.rows[0].date == date(2026, 3, 1)


def test_repeated_table_header_on_later_pages_is_not_a_row():
    parsed = read_pdf(pdf_table_bytes(TABLE, pages=2), max_rows=MAX, max_pages=PAGES)
    assert len(parsed.rows) == 6
    assert not [r for r in parsed.rejected if "date" in r.reason.lower()]


def test_plain_text_lines_with_single_amount():
    parsed = read_pdf(pdf_text_bytes(CARD_LINES), max_rows=MAX, max_pages=PAGES)
    assert [r.amount for r in parsed.rows] == [
        Decimal("54.99"),
        Decimal("23.40"),
        Decimal("-500.00"),
    ]
    assert parsed.rows[0].description == "ADOBE CREATIVE CLOUD"


def test_running_balance_decides_money_in_or_out():
    parsed = read_pdf(pdf_text_bytes(BALANCE_LINES), max_rows=MAX, max_pages=PAGES)
    by_name = {r.description: r for r in parsed.rows}
    assert by_name["ADOBE CREATIVE CLOUD"].debit == Decimal("54.99")
    assert by_name["CLIENT INVOICE 12"].credit == Decimal("400.00")
    assert by_name["GITHUB"].debit == Decimal("4.00")


def test_dates_without_a_year_use_the_year_in_the_document():
    lines = [
        "Statement period March 1 - March 31, 2026",
        "Mar 01  ADOBE CREATIVE CLOUD    54.99",
        "Mar 02  UBER TRIP    23.40",
    ]
    parsed = read_pdf(pdf_text_bytes(lines), max_rows=MAX, max_pages=PAGES)
    assert parsed.rows[0].date == date(2026, 3, 1)
    assert any("no year" in w for w in parsed.warnings)


def test_december_rows_on_a_january_statement_get_the_previous_year():
    lines = [
        "Statement closing January 15, 2026",
        "Dec 28  ADOBE CREATIVE CLOUD    54.99",
        "Jan 03  UBER TRIP    23.40",
    ]
    parsed = read_pdf(pdf_text_bytes(lines), max_rows=MAX, max_pages=PAGES)
    assert [r.date for r in parsed.rows] == [date(2025, 12, 28), date(2026, 1, 3)]


def test_scanned_pdf_without_text_gets_a_helpful_error():
    with pytest.raises(FileProblem) as info:
        read_pdf(pdf_blank_bytes(), max_rows=MAX, max_pages=PAGES)
    assert info.value.code == "pdf_no_text"
    assert "CSV" in info.value.message


def test_password_protected_pdf():
    with pytest.raises(FileProblem) as info:
        read_pdf(pdf_encrypted_bytes(), max_rows=MAX, max_pages=PAGES)
    assert info.value.code == "pdf_encrypted"


def test_corrupt_pdf():
    with pytest.raises(FileProblem) as info:
        read_pdf(b"%PDF-1.4\nthis is not a real pdf at all", max_rows=MAX, max_pages=PAGES)
    assert info.value.code == "file_corrupt"


def test_page_cap():
    with pytest.raises(FileProblem) as info:
        read_pdf(pdf_text_bytes(CARD_LINES, pages=5), max_rows=MAX, max_pages=3)
    assert info.value.code == "pdf_too_many_pages"
    assert info.value.status_code == 413


def test_pdf_without_transactions():
    with pytest.raises(FileProblem) as info:
        read_pdf(
            pdf_text_bytes(["Welcome to your account", "Thank you for banking with us today"]),
            max_rows=MAX,
            max_pages=PAGES,
        )
    assert info.value.code == "no_transactions_found"


# -- laid out statements -------------------------------------------------------------------
# These are drawn at fixed x positions, the way a bank's template places columns, so the
# reader has to work from positions and not from the order of the text.

COLUMNS = {
    "date": (40, "l"),
    "date2": (95, "l"),
    "text": (150, "l"),
    "debit": (400, "r"),
    "credit": (470, "r"),
    "amount": (440, "r"),
    "balance": (550, "r"),
}
HEADER_BALANCE = {"date": "Date", "text": "Description", "debit": "Withdrawal (-)",
                  "credit": "Deposit (+)", "balance": "Balance"}  # fmt: skip
HEADER_AMOUNT = {"date": "Date", "text": "Description", "amount": "Amount",
                 "balance": "Balance"}  # fmt: skip


def _layout_pdf(pages, *, watermark=False):
    """Pages of (y, {column: text}) lines, drawn at the positions in COLUMNS."""
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    for page in pages:
        if watermark:
            pdf.saveState()
            pdf.setFont("Helvetica-Bold", 44)
            pdf.setFillGray(0.85)
            pdf.translate(70, 330)
            pdf.rotate(30)
            pdf.drawString(0, 0, "CONFIDENTIAL COPY")
            pdf.restoreState()
            pdf.saveState()
            pdf.setFont("Helvetica", 9)
            pdf.translate(585, 120)
            pdf.rotate(90)
            pdf.drawString(0, 0, "VOID IF ALTERED  SECURITY MARK 2026")
            pdf.restoreState()
        for y, cells in page:
            for key, text in cells.items():
                x, align = COLUMNS.get(key, (40, "l"))
                text, size = text if isinstance(text, tuple) else (text, 9)
                pdf.setFont("Helvetica", size)
                (pdf.drawRightString if align == "r" else pdf.drawString)(x, y, text)
        pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def _rows(header, rows, *, top=700, step=14, title=()):
    """Header plus one line per row, `step` points apart; returns the lines of one page."""
    lines = [(top + 40 - 14 * i, {"text": t}) for i, t in enumerate(title)]
    lines.append((top, header))
    for i, cells in enumerate(rows, start=1):
        lines.append((top - step * i, cells))
    return lines


BALANCE_ROWS = [
    {"date": "01/03/2026", "text": "ADOBE CREATIVE CLOUD", "debit": "54.99", "balance": "945.01"},
    {"date": "02/03/2026", "text": "CLIENT INVOICE 12", "credit": "400.00", "balance": "1,345.01"},
    {"date": "03/03/2026", "text": "UBER TRIP", "debit": "23.40", "balance": "1,321.61"},
    {"date": "14/03/2026", "text": "GITHUB", "debit": "4.00", "balance": "1,317.61"},
]


def _read(data, **kwargs):
    return read_pdf(data, max_rows=kwargs.get("max_rows", MAX), max_pages=PAGES)


def test_columns_are_found_by_position():
    parsed = _read(_layout_pdf([_rows(HEADER_BALANCE, BALANCE_ROWS)]))
    assert [r.description for r in parsed.rows] == [
        "ADOBE CREATIVE CLOUD", "CLIENT INVOICE 12", "UBER TRIP", "GITHUB",
    ]  # fmt: skip
    assert [(r.debit, r.credit) for r in parsed.rows] == [
        (Decimal("54.99"), None),
        (None, Decimal("400.00")),
        (Decimal("23.40"), None),
        (Decimal("4.00"), None),
    ]
    assert parsed.rows[3].date == date(2026, 3, 14)  # 14 settles day/month order


def test_diagonal_and_sideways_watermarks_do_not_reach_the_text():
    plain = _read(_layout_pdf([WRAPPED_ROWS]))
    marked = _read(_layout_pdf([WRAPPED_ROWS], watermark=True))
    assert [r.description for r in marked.rows] == [r.description for r in plain.rows]
    assert [(r.debit, r.credit) for r in marked.rows] == [(r.debit, r.credit) for r in plain.rows]
    assert len(marked.rows) == 3 and not marked.rejected


def test_orientation_filter_drops_rotated_characters():
    data = _layout_pdf([_rows(HEADER_BALANCE, BALANCE_ROWS)], watermark=True)
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        page = pdf.pages[0]
        everything = "".join(c["text"] for c in page.chars)
        kept = "".join(c["text"] for c in pdf_reader._page_chars(page))
    assert "CONFIDENTIAL" in everything and "VOID" in everything
    assert "CONFIDENTIAL" not in kept and "VOID" not in kept and "SECURITY" not in kept
    assert len(kept) < len(everything)
    assert "ADOBE" in kept


WRAPPED_ROWS = [
    (700, HEADER_BALANCE),
    (686, {"date": "01/03/2026", "text": "PAYNOW TRANSFER", "debit": "54.99", "balance": "945.01"}),
    (677, {"text": "TO: Corp Holdings"}),
    (668, {"text": "REF 8373579"}),
    (
        654,
        {
            "date": "02/03/2026",
            "text": "CLIENT INVOICE 12",
            "credit": "400.00",
            "balance": "1,345.01",
        },
    ),
    (645, {"text": "FROM: Northbridge"}),
    (631, {"date": "20/03/2026", "text": "UBER TRIP", "debit": "23.40", "balance": "1,321.61"}),
    (622, {"text": "HELP.UBER.COM"}),
    (613, {"text": "AMSTERDAM NL"}),
]


def test_wrapped_text_inside_a_cell_is_joined():
    parsed = _read(_layout_pdf([WRAPPED_ROWS]))
    assert [r.description for r in parsed.rows] == [
        "PAYNOW TRANSFER TO: Corp Holdings REF 8373579",
        "CLIENT INVOICE 12 FROM: Northbridge",
        "UBER TRIP HELP.UBER.COM AMSTERDAM NL",
    ]
    assert parsed.rows[0].debit == Decimal("54.99")


def test_description_lines_above_and_below_a_vertically_centred_date():
    def block(y, name, date_text, amount, balance):
        return [
            (y, {"text": name}),
            (y - 7.5, {"date": date_text, "debit": amount, "balance": balance}),
            (y - 10.5, {"text": "VPA " + name.lower().replace(" ", "") + "@bank"}),
            (y - 21, {"text": "UTR 6101" + date_text[:2]}),
        ]

    rows = [(700, HEADER_BALANCE)]
    rows += block(670, "UPI/DR/GROCERS", "01/03/2026", "126.40", "874.60")
    rows += block(630, "UPI/DR/COFFEE HOUSE", "04/03/2026", "84.00", "790.60")
    rows += block(590, "UPI/DR/CAB RIDE", "09/03/2026", "300.00", "490.60")
    parsed = _read(_layout_pdf([rows]))
    assert [r.description for r in parsed.rows] == [
        "UPI/DR/GROCERS VPA upi/dr/grocers@bank UTR 610101",
        "UPI/DR/COFFEE HOUSE VPA upi/dr/coffeehouse@bank UTR 610104",
        "UPI/DR/CAB RIDE VPA upi/dr/cabride@bank UTR 610109",
    ]
    assert [r.debit for r in parsed.rows] == [
        Decimal("126.40"),
        Decimal("84.00"),
        Decimal("300.00"),
    ]


def test_a_small_cr_tag_under_the_balance_is_not_description_text():
    rows = [
        (700, HEADER_BALANCE),
        (
            686,
            {"date": "01/03/2026", "text": "SALARY", "credit": "5,000.00", "balance": "6,000.00"},
        ),
        (681, {"balance": ("CR", 6)}),
        (677, {"text": "ACME LTD"}),
        (660, {"date": "20/03/2026", "text": "RENT", "debit": "900.00", "balance": "5,100.00"}),
    ]
    parsed = _read(_layout_pdf([rows]))
    assert parsed.rows[0].description == "SALARY ACME LTD"
    assert parsed.rows[0].credit == Decimal("5000.00")


def test_a_running_balance_decides_direction_for_a_single_amount_column():
    rows = [
        {"text": "Balance Brought Forward", "balance": "1,000.00"},
        {"date": "02/03/2026", "text": "ADOBE", "amount": "54.99", "balance": "945.01"},
        {"date": "03/03/2026", "text": "CLIENT INVOICE", "amount": "400.00", "balance": "1,345.01"},
        {"date": "20/03/2026", "text": "UBER", "amount": "23.40", "balance": "1,321.61"},
    ]
    parsed = _read(_layout_pdf([_rows(HEADER_AMOUNT, rows)]))
    assert [(r.debit, r.credit, r.amount) for r in parsed.rows] == [
        (Decimal("54.99"), None, None),
        (None, Decimal("400.00"), None),
        (Decimal("23.40"), None, None),
    ]


def test_cr_and_dr_suffixes_in_the_amount_column():
    rows = [
        {"date": "02/03/2026", "text": "ADOBE", "amount": "54.99 DR"},
        {"date": "03/03/2026", "text": "REFUND", "amount": "10.00 CR"},
        {"date": "20/03/2026", "text": "UBER", "amount": "23.40 Dr"},
    ]
    header = {"date": "Date", "text": "Description", "amount": "Amount"}
    parsed = _read(_layout_pdf([_rows(header, rows)]))
    assert [(r.debit, r.credit) for r in parsed.rows] == [
        (Decimal("54.99"), None),
        (None, Decimal("10.00")),
        (Decimal("23.40"), None),
    ]


def test_printed_signs_are_kept_when_nothing_states_the_direction():
    rows = [
        {"date": "02/03/2026", "text": "ADOBE", "amount": "54.99"},
        {"date": "03/03/2026", "text": "PAYMENT THANK YOU", "amount": "-500.00"},
        {"date": "20/03/2026", "text": "UBER", "amount": "23.40"},
    ]
    header = {"date": "Date", "text": "Description", "amount": "Amount"}
    parsed = _read(_layout_pdf([_rows(header, rows)]))
    assert [r.amount for r in parsed.rows] == [
        Decimal("54.99"),
        Decimal("-500.00"),
        Decimal("23.40"),
    ]


def test_two_date_columns_use_the_transaction_date():
    columns = {
        "date": "Post Date",
        "date2": "Trans Date",
        "text": "Description",
        "amount": "$ Amount",
    }
    rows = [
        {"date": "09/12", "date2": "09/11", "text": "REWARDS REDEMPTION", "amount": "-13.84"},
        {"date": "09/13", "date2": "09/13", "text": "STARBUCKS", "amount": "1,520.75"},
    ]
    title = [(740, {"text": "Statement closing 09/30/2025"})]
    parsed = _read(_layout_pdf([title + _rows(columns, rows)]))
    assert [r.date for r in parsed.rows] == [date(2025, 9, 11), date(2025, 9, 13)]
    assert parsed.currency_hint == "USD"


def test_a_date_hidden_in_the_description_is_split_off():
    header = {
        "text": "Détails",
        "debit": "Débits ($)",
        "credit": "Crédits ($)",
        "balance": "Solde ($)",
    }
    rows = [
        {"text": "02 janv. 25 SKIP PLATS", "debit": "151,30 $", "balance": "10 598,70 $"},
        {"text": "03 janv. 25 DEPOT PAIE", "credit": "1 200,45 $", "balance": "11 799,15 $"},
        {"text": "Frais sur compte: 23,00 $"},
    ]
    parsed = _read(_layout_pdf([_rows(header, rows)]))
    assert [(r.date, r.description) for r in parsed.rows] == [
        (date(2025, 1, 2), "SKIP PLATS"),
        (date(2025, 1, 3), "DEPOT PAIE"),
    ]
    assert parsed.rows[0].debit == Decimal("151.30")
    assert parsed.rows[1].credit == Decimal("1200.45")


def test_european_amounts_with_symbols():
    header = {"date": "Datum", "text": "Omschrijving", "amount": "Bedrag"}
    rows = [
        {"date": "1 mei", "text": "SALARIS", "amount": "1.234,56 €"},
        {"date": "7 mei", "text": "JUMBO", "amount": "-12,50 €"},
        {"date": "9 mei", "text": "ZIGGO", "amount": "€ 1 500,00"},
    ]
    parsed = _read(_layout_pdf([[(740, {"text": "Overzicht 31.05.2025"})] + _rows(header, rows)]))
    assert [r.amount for r in parsed.rows] == [
        Decimal("1234.56"),
        Decimal("-12.50"),
        Decimal("1500.00"),
    ]
    assert [r.date for r in parsed.rows] == [date(2025, 5, 1), date(2025, 5, 7), date(2025, 5, 9)]
    assert parsed.currency_hint == "EUR"


def test_summary_rows_and_page_footers_are_not_transactions():
    rows = BALANCE_ROWS + [
        {"text": "Balance Carried Forward", "balance": "1,317.61"},
        {"text": "Page 1 of 1"},
    ]
    parsed = _read(_layout_pdf([_rows(HEADER_BALANCE, rows)]))
    assert len(parsed.rows) == 4
    assert (
        "Forward" not in parsed.rows[-1].description and "Page" not in parsed.rows[-1].description
    )


def test_a_second_account_table_starts_its_own_balance_chain_and_currency():
    first = _rows(HEADER_BALANCE, BALANCE_ROWS[:2], top=700, title=("HKD Current Account 1",))
    second = _rows(HEADER_BALANCE, [
        {"date": "05/03/2026", "text": "WATSONS", "debit": "10.00", "balance": "90.00"},
        {"date": "06/03/2026", "text": "MTR", "credit": "5.00", "balance": "95.00"},
    ], top=500, title=("USD Savings Account 2",))  # fmt: skip
    parsed = _read(_layout_pdf([first + second]))
    assert [r.currency for r in parsed.rows] == ["HKD", "HKD", "USD", "USD"]
    assert parsed.rows[2].debit == Decimal("10.00") and parsed.rows[3].credit == Decimal("5.00")


def test_header_repeated_on_each_page_and_a_page_without_one():
    page1 = _rows(HEADER_BALANCE, BALANCE_ROWS[:2])
    page2 = _rows(HEADER_BALANCE, BALANCE_ROWS[2:3])
    page3 = [(700 - 14 * i, cells) for i, cells in enumerate(BALANCE_ROWS[3:])]  # no header
    parsed = _read(_layout_pdf([page1, page2, page3]))
    assert [r.description for r in parsed.rows] == [
        "ADOBE CREATIVE CLOUD", "CLIENT INVOICE 12", "UBER TRIP", "GITHUB",
    ]  # fmt: skip
    assert not parsed.rejected


def test_a_second_amount_on_a_line_without_a_date_is_another_transaction():
    rows = [
        {"date": "02/03/2026", "text": "COFFEE", "debit": "3.50", "balance": "96.50"},
        {"text": "BAGEL", "debit": "2.50", "balance": "94.00"},
        {"date": "15/03/2026", "text": "TRAIN", "debit": "10.00", "balance": "84.00"},
    ]
    parsed = _read(_layout_pdf([_rows(HEADER_BALANCE, rows)]))
    assert [(r.date, r.description) for r in parsed.rows] == [
        (date(2026, 3, 2), "COFFEE"),
        (date(2026, 3, 2), "BAGEL"),
        (date(2026, 3, 15), "TRAIN"),
    ]


def test_zero_amount_detail_lines_stay_out_of_the_description():
    rows = [
        {"date": "09/01", "date2": "09/01", "text": "UBER TRIP", "amount": "531.56"},
        {"text": "Chevron station 38.2gal", "amount": "0.00"},
        {"date": "09/13", "date2": "09/13", "text": "STARBUCKS", "amount": "20.00"},
    ]
    header = {"date": "Post Date", "date2": "Trans Date", "text": "Description", "amount": "Amount"}
    parsed = _read(
        _layout_pdf([[(740, {"text": "Closing date 09/30/2025"})] + _rows(header, rows)])
    )
    assert [r.description for r in parsed.rows] == ["UBER TRIP", "STARBUCKS"]


def test_december_and_january_rows_without_a_year_in_a_laid_out_table():
    header = {"date": "Date", "text": "Description", "amount": "Amount"}
    rows = [
        {"date": "28 Dec", "text": "ADOBE", "amount": "54.99"},
        {"date": "03 Jan", "text": "UBER", "amount": "23.40"},
    ]
    title = [(740, {"text": "Statement closing January 15, 2026"})]
    parsed = _read(_layout_pdf([title + _rows(header, rows)]))
    assert [r.date for r in parsed.rows] == [date(2025, 12, 28), date(2026, 1, 3)]
    assert any("no year" in w for w in parsed.warnings)


def test_row_cap_applies_to_laid_out_statements():
    rows = [
        {
            "date": f"{d:02d}/03/2026",
            "text": f"SHOP {d}",
            "debit": "1.00",
            "balance": f"{100 - d}.00",
        }
        for d in range(1, 21)
    ]
    data = _layout_pdf([_rows(HEADER_BALANCE, rows, step=12)])
    with pytest.raises(FileProblem) as info:
        read_pdf(data, max_rows=10, max_pages=PAGES)
    assert info.value.code == "too_many_rows" and info.value.status_code == 413


def test_a_truncated_pdf_is_a_file_problem_not_an_exception():
    data = _layout_pdf([_rows(HEADER_BALANCE, BALANCE_ROWS)])
    for cut in (len(data) // 2, len(data) - 40):
        try:
            read_pdf(data[:cut], max_rows=MAX, max_pages=PAGES)
        except FileProblem as problem:
            assert problem.code


def test_ruled_table_with_headings_wrapped_inside_their_cells():
    rows = [
        ["Transaction\nDate", "Details", "Money\nout", "Money\nin", "Balance"],
        ["03/01/2026", "ADOBE CREATIVE CLOUD", "54.99", "", "945.01"],
        ["03/02/2026", "CLIENT INVOICE 12", "", "400.00", "1345.01"],
        ["03/21/2026", "UBER TRIP", "23.40", "", "1321.61"],
    ]
    parsed = _read(pdf_table_bytes(rows))
    assert [r.description for r in parsed.rows] == [
        "ADOBE CREATIVE CLOUD", "CLIENT INVOICE 12", "UBER TRIP",
    ]  # fmt: skip
    assert parsed.rows[1].credit == Decimal("400.00")
    assert parsed.rows[2].date == date(2026, 3, 21)


def test_balance_carried_forward_at_a_page_foot_does_not_end_the_table():
    page1 = _rows(HEADER_BALANCE, BALANCE_ROWS[:2]) + [
        (640, {"text": "Balance Carried Forward", "balance": "1,345.01"}),
    ]
    page2 = [
        (700, {"text": "Balance Brought Forward", "balance": "1,345.01"}),
        (686, BALANCE_ROWS[2]),
        (672, BALANCE_ROWS[3]),
    ]  # no header repeated
    parsed = _read(_layout_pdf([page1, page2]))
    assert [r.description for r in parsed.rows] == [
        "ADOBE CREATIVE CLOUD", "CLIENT INVOICE 12", "UBER TRIP", "GITHUB",
    ]  # fmt: skip
    assert parsed.rows[2].debit == Decimal("23.40")
