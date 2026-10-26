"""Generate clearly fictional, reproducible spreadsheet and supported PDF fixtures."""

import csv
from pathlib import Path

from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parents[1] / "sample_data"
with (ROOT / "developer-bank.csv").open(encoding="utf-8", newline="") as source:
    bank_rows = list(csv.reader(source))
book = Workbook()
sheet = book.active
sheet.title = "Synthetic bank statement"
for row in bank_rows:
    sheet.append(row)
sheet.freeze_panes = "A2"
for column, width in {"A": 22, "B": 44, "C": 20, "D": 20, "E": 14}.items():
    sheet.column_dimensions[column].width = width
book.save(ROOT / "developer-statement.xlsx")

pdf = SimpleDocTemplate(
    str(ROOT / "developer-statement.pdf"),
    pagesize=A4,
    rightMargin=35,
    leftMargin=35,
    topMargin=40,
    bottomMargin=40,
    title="SortedHisab synthetic bank statement - fictional data",
    invariant=1,
)
styles = getSampleStyleSheet()
body = [
    Paragraph("SortedHisab Synthetic Statement v1", styles["Title"]),
    Paragraph("DEMO BANK - FICTIONAL DATA ONLY", styles["Heading2"]),
    Paragraph(
        "Account: Developer Demo | Account reference: DEMO-0001<br/>"
        "Statement period: 01 Sep 2026 - 30 Sep 2026 | Currency: PKR<br/>"
        "Transaction count: 12",
        styles["Normal"],
    ),
    Spacer(1, 22),
]
table = Table(
    [["Date", "Description", "Debit", "Credit", "Currency"], *bank_rows[1:]],
    colWidths=[63, 256, 67, 67, 52],
    repeatRows=1,
)
table.setStyle(
    TableStyle(
        [
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#153f3b")),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d9e3df")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f6f3")]),
            ("TOPPADDING", (0, 0), (-1, -1), 11),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 11),
            ("ALIGN", (2, 1), (3, -1), "RIGHT"),
        ]
    )
)
body += [
    table,
    Spacer(1, 20),
    Paragraph(
        "All names, references and transactions are invented. "
        "This is a software test fixture, not a real bank statement. No tax or bank endorsement is implied.",
        styles["Normal"],
    ),
]
pdf.build(body)
print("Generated synthetic XLSX and text PDF.")
