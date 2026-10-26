"""Create the fake statements in sample_data/.

Everything here is invented: the bank, the account holder, the account
numbers and every transaction. Run it again to rebuild the files:

    python scripts/make_samples.py
"""

import csv
import random
from decimal import Decimal
from pathlib import Path

from PIL import ImageFilter
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

OUT = Path(__file__).resolve().parent.parent / "sample_data"
BANK = "Margalla Demo Bank Ltd (fictional)"
HOLDER = "Sana Example, freelance developer"

# (date, description, amount) with negative amounts for money out.
PKR_MARCH = [
    ("02/03/2026", "PAYONEER INWARD REF 77120", "280000.00"),
    ("02/03/2026", "ADV TAX ON EXPORT PROCEEDS", "-700.00"),
    ("03/03/2026", "POS GITHUB.COM SAN FRANCISCO", "-1120.00"),
    ("04/03/2026", "NAYATEL INTERNET BILL MAR", "-4999.00"),
    ("05/03/2026", "AMAZON WEB SERVICES AWS.AMAZON.COM", "-8450.00"),
    ("06/03/2026", "FOODPANDA ORDER 5512", "-2350.00"),
    ("06/03/2026", "FOODPANDA ORDER 5512", "-2350.00"),
    ("08/03/2026", "SMS ALERT CHARGES", "-200.00"),
    ("08/03/2026", "FED ON SMS ALERT CHARGES", "-32.00"),
    ("10/03/2026", "TRANSFER TO SAVINGS A/C", "-50000.00"),
    ("12/03/2026", "JOES CAFE 9921", "-1800.00"),
    ("14/03/2026", "CAREEM RIDE", "-950.00"),
    ("15/03/2026", "IBFT OUTWARD 0213XXXX", "-15000.00"),
    ("18/03/2026", "JETBRAINS SRO PRAGUE", "-3980.00"),
    ("20/03/2026", "GITHUB.COM REFUND", "1120.00"),
    ("22/03/2026", "ATM CASH WITHDRAWAL F-7", "-10000.00"),
    ("25/03/2026", "K-ELECTRIC BILL 0402", "-6750.00"),
    ("26/03/2026", "CLIENT PAYMENT ACME LTD", "95000.00"),
    ("27/03/2026", "NETFLIX.COM", "-1100.00"),
    ("28/03/2026", "DARAZ ORDER 99812", "-12400.00"),
]

USD_APRIL = [
    ("2026-04-01", "UPWORK ESCROW RELEASE", "1800.00"),
    ("2026-04-01", "UPWORK SERVICE FEE", "-180.00"),
    ("2026-04-03", "ADOBE CREATIVE CLOUD", "-54.99"),
    ("2026-04-04", "FIGMA PROFESSIONAL", "-15.00"),
    ("2026-04-06", "DIGITALOCEAN.COM", "-24.00"),
    ("2026-04-08", "SQ *48392", "-18.50"),
    ("2026-04-09", "TOPTAL PAYMENT", "3200.00"),
    ("2026-04-10", "UBER EATS ORDER", "-22.40"),
    ("2026-04-12", "WISE TRANSFER IN", "450.00"),
    ("2026-04-14", "REFUND FIGMA", "15.00"),
    ("2026-04-15", "CURRENCY CONVERSION TO PKR ACCOUNT", "-2000.00"),
    ("2026-04-18", "AWS EMEA", "31.2O"),  # an 'O' where a zero should be: the app must refuse it
    ("2026-04-20", "CLIENT PAYMENT NORTHWIND", "1250.00"),
    ("2026-04-22", "PAYPAL *STEAMGAMES", "-19.99"),
    ("2026-04-25", "GOOGLE WORKSPACE", "-7.20"),
]

PKR_APRIL_PDF = [
    ("02 Apr 2026", "PAYONEER INWARD REF 80211", "", "310,000.00"),
    ("02 Apr 2026", "ADV TAX ON EXPORT PROCEEDS", "775.00", ""),
    ("03 Apr 2026", "POS GITHUB.COM SAN FRANCISCO", "1,120.00", ""),
    ("05 Apr 2026", "PTCL BROADBAND BILL APRIL", "3,600.00", ""),
    ("07 Apr 2026", "HETZNER ONLINE GMBH SERVER RENTAL", "5,210.00", ""),
    ("09 Apr 2026", "IMTIAZ SUPER MARKET", "8,940.00", ""),
    ("11 Apr 2026", "TRANSFER FROM SAVINGS A/C", "", "40,000.00"),
    ("13 Apr 2026", "HOME REMITTANCE FROM ABROAD", "", "60,000.00"),
    ("15 Apr 2026", "SERVICE CHARGES APRIL", "150.00", ""),
    ("16 Apr 2026", "INDRIVE TRIP", "720.00", ""),
    ("18 Apr 2026", "NAMECHEAP DOMAIN RENEWAL", "2,950.00", ""),
    ("20 Apr 2026", "JAZZ MOBILE TOP UP", "1,000.00", ""),
    ("22 Apr 2026", "CLOUDFLARE INC", "1,400.00", ""),
    ("24 Apr 2026", "RAAST P2P TRANSFER", "7,500.00", ""),
    ("26 Apr 2026", "SLACK TECHNOLOGIES", "2,240.00", ""),
    ("27 Apr 2026", "SPOTIFY PREMIUM", "499.00", ""),
    ("28 Apr 2026", "FIVERR PAYOUT VIA PAYONEER", "", "42,500.00"),
    ("29 Apr 2026", "NOTION LABS INC", "2,800.00", ""),
]
PKR_MAY_SCAN = [
    ("02 May 2026", "PAYONEER INWARD REF 81530", "", "295,000.00"),
    ("02 May 2026", "ADV TAX ON EXPORT PROCEEDS", "737.50", ""),
    ("04 May 2026", "POS GITHUB.COM SAN FRANCISCO", "1,120.00", ""),
    ("06 May 2026", "NAYATEL INTERNET BILL MAY", "4,999.00", ""),
    ("09 May 2026", "VERCEL INC", "5,600.00", ""),
    ("12 May 2026", "TRANSFER TO SAVINGS A/C", "60,000.00", ""),
    ("15 May 2026", "CAREEM RIDE", "1,150.00", ""),
    ("19 May 2026", "SMS ALERT CHARGES", "200.00", ""),
    ("23 May 2026", "HASSAN TRADERS 4471", "2,300.00", ""),
    ("28 May 2026", "UPWORK ESCROW RELEASE", "", "88,000.00"),
]
WRAPPED = {"HETZNER ONLINE GMBH SERVER RENTAL": ("HETZNER ONLINE GMBH", "SERVER RENTAL")}


def money(value: Decimal) -> str:
    return f"{value:,.2f}"


def write_pkr_csv() -> None:
    balance = Decimal("245000.00")
    path = OUT / "pkr_business_account_march.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Bank", BANK])
        w.writerow(["Account holder", HOLDER])
        w.writerow(["Account", "0000-DEMO-0001 (PKR current account)"])
        w.writerow([])
        w.writerow(["Date", "Description", "Debit", "Credit", "Balance"])
        w.writerow(["01/03/2026", "Opening Balance", "", "", money(balance)])
        for when, text, amount in PKR_MARCH:
            value = Decimal(amount)
            balance += value
            debit = money(-value) if value < 0 else ""
            credit = money(value) if value > 0 else ""
            w.writerow([when, text, debit, credit, money(balance)])
        w.writerow(["31/03/2026", "Closing Balance", "", "", money(balance)])


def write_usd_csv() -> None:
    """Newest first, one signed Amount column and a Currency column: a different bank's export style."""
    balance = Decimal("1200.00")
    rows = []
    for when, text, amount in USD_APRIL:
        try:
            balance += Decimal(amount)
        except Exception:  # noqa: BLE001 - the deliberately broken row
            pass
        rows.append([when, text, amount, "USD", f"{balance:.2f}"])
    path = OUT / "usd_freelance_account_april.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Transaction Date", "Details", "Amount", "Currency", "Running Balance"])
        w.writerows(reversed(rows))


def write_pdf(path: Path, rows, *, account: str, period: str, first_day: str, opening: str, per_page: int) -> None:
    c = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4
    cols = {"date": 40, "desc": 112, "debit": 392, "credit": 470, "balance": 555}
    balance = Decimal(opening)
    pages = [rows[i:i + per_page] for i in range(0, len(rows), per_page)]

    for number, chunk in enumerate(pages, start=1):
        c.setFont("Helvetica-Bold", 13)
        c.drawString(40, height - 50, BANK)
        c.setFont("Helvetica", 9.5)
        c.drawString(40, height - 68, f"Account holder: {HOLDER}")
        c.drawString(40, height - 82, f"Account: {account}    Statement period: {period}")
        c.drawString(40, height - 96, "Currency: PKR")

        y = height - 130
        c.setFont("Helvetica-Bold", 9.5)
        c.drawString(cols["date"], y, "Date")
        c.drawString(cols["desc"], y, "Description")
        c.drawRightString(cols["debit"], y, "Debit")
        c.drawRightString(cols["credit"], y, "Credit")
        c.drawRightString(cols["balance"], y, "Balance")
        c.setLineWidth(0.6)
        c.line(40, y - 5, cols["balance"], y - 5)
        c.setFont("Helvetica", 9.5)
        y -= 22

        if number == 1:
            c.drawString(cols["date"], y, first_day)
            c.drawString(cols["desc"], y, "Opening Balance")
            c.drawRightString(cols["balance"], y, money(balance))
            y -= 20

        for when, text, debit, credit in chunk:
            amount = Decimal(credit.replace(",", "")) if credit else -Decimal(debit.replace(",", ""))
            balance += amount
            first, second = WRAPPED.get(text, (text, None))
            c.drawString(cols["date"], y, when)
            c.drawString(cols["desc"], y, first)
            if debit:
                c.drawRightString(cols["debit"], y, debit)
            if credit:
                c.drawRightString(cols["credit"], y, credit)
            c.drawRightString(cols["balance"], y, money(balance))
            if second:
                y -= 12
                c.drawString(cols["desc"], y, second)
            y -= 20

        c.setFont("Helvetica", 8)
        c.drawString(40, 40, f"Page {number} of {len(pages)}    This is a fictional statement made for testing.")
        c.showPage()
    c.save()


def write_scanned_pdf(target: Path) -> None:
    """Draw a text PDF, render it to images and add scanner noise, so there is no text layer left."""
    import pypdfium2 as pdfium

    source = target.with_suffix(".tmp.pdf")
    write_pdf(source, PKR_MAY_SCAN, account="0000-DEMO-0002", period="01 May 2026 to 31 May 2026",
              first_day="01 May 2026", opening="150000.00", per_page=20)

    random.seed(7)
    images = []
    pdf = pdfium.PdfDocument(str(source))
    for page in pdf:
        image = page.render(scale=200 / 72).to_pil().convert("L")
        pixels = image.load()
        w, h = image.size
        for _ in range(w * h // 300):
            x, y = random.randrange(w), random.randrange(h)
            pixels[x, y] = random.choice((150, 190, 230))
        images.append(image.filter(ImageFilter.GaussianBlur(0.6)))
    pdf.close()
    source.unlink()
    images[0].save(target, "PDF", resolution=200, save_all=True, append_images=images[1:])


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    write_pkr_csv()
    write_usd_csv()
    write_pdf(OUT / "pkr_statement_april.pdf", PKR_APRIL_PDF, account="0000-DEMO-0002",
              period="01 Apr 2026 to 30 Apr 2026", first_day="01 Apr 2026", opening="118500.00", per_page=11)
    write_scanned_pdf(OUT / "pkr_statement_may_scanned.pdf")
    for path in sorted(OUT.iterdir()):
        print(f"{path.name}  {path.stat().st_size:,} bytes")
