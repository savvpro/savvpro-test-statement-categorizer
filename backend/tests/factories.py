"""Builders that create small fake statements in every supported format, in memory."""

from __future__ import annotations

import io
from collections.abc import Sequence

from openpyxl import Workbook
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle

CARD_ROWS = [
    ["Transaction Date", "Description", "Amount"],
    ["03/01/2026", "ADOBE *CREATIVE CLOUD", "54.99"],
    ["03/02/2026", "UBER *TRIP", "23.40"],
    ["03/03/2026", "ONLINE PAYMENT - THANK YOU", "-500.00"],
]


def csv_bytes(rows: Sequence[Sequence[str]], delimiter: str = ",") -> bytes:
    lines = []
    for row in rows:
        cells = [f'"{c}"' if delimiter in c or '"' in c else c for c in row]
        lines.append(delimiter.join(cells))
    return ("\n".join(lines) + "\n").encode("utf-8")


def xlsx_bytes(sheets: dict[str, Sequence[Sequence[object]]]) -> bytes:
    workbook = Workbook()
    workbook.remove(workbook.active)
    for title, rows in sheets.items():
        sheet = workbook.create_sheet(title)
        for row in rows:
            sheet.append(list(row))
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def pdf_table_bytes(rows: Sequence[Sequence[str]], pages: int = 1) -> bytes:
    """A statement with a ruled table, repeated header on each page when `pages` > 1."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    style = TableStyle([("GRID", (0, 0), (-1, -1), 0.5, (0, 0, 0))])
    story = [Table([list(r) for r in rows], style=style)]
    for _ in range(pages - 1):
        from reportlab.platypus import PageBreak

        story.extend([PageBreak(), Table([list(r) for r in rows], style=style)])
    doc.build(story)
    return buffer.getvalue()


def pdf_text_bytes(lines: Sequence[str], pages: int = 1) -> bytes:
    """A statement printed as plain text lines, no ruling."""
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    for _ in range(pages):
        y = 740
        for line in lines:
            pdf.drawString(50, y, line)
            y -= 16
        pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def pdf_blank_bytes() -> bytes:
    """A page with no text layer, like a scan."""
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    pdf.rect(50, 50, 200, 200, fill=1)
    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def pdf_encrypted_bytes(password: str = "secret") -> bytes:
    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(io.BytesIO(pdf_text_bytes(["03/01/2026 ADOBE 54.99"])))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.encrypt(password)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


OFX_SAMPLE = b"""OFXHEADER:100
DATA:OFXSGML
VERSION:102

<OFX><BANKMSGSRSV1><STMTTRNRS><STMTRS><CURDEF>USD<BANKTRANLIST>
<STMTTRN><TRNTYPE>DEBIT<DTPOSTED>20260302<TRNAMT>-54.99<FITID>1<NAME>ADOBE *CREATIVE CLOUD</STMTTRN>
<STMTTRN><TRNTYPE>CREDIT<DTPOSTED>20260305<TRNAMT>1200.00<FITID>2<NAME>CLIENT INVOICE 5</STMTTRN>
</BANKTRANLIST></STMTRS></STMTTRNRS></BANKMSGSRSV1></OFX>
"""
