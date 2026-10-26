"""Write the fake sample statements into samples/. Deterministic: same output on every run.

Everything here is invented. The persona is "Sam Rivera Design LLC"; clients, people and the
bank are made up. Well-known merchant names (ADOBE, UBER, AWS, ...) appear only as merchants.

Usage: python scripts/make_samples.py [output_dir]
"""

import codecs
import csv
import datetime as dt
import io
import re
import sys
import zipfile
from decimal import Decimal
from pathlib import Path

from openpyxl import Workbook

ROOT = Path(__file__).resolve().parents[2]
FIXED_TIME = dt.datetime(2026, 4, 1, 9, 0, 0)

# (month, day, description, amount) with checking signs: + money in, - money out.
CHECKING = [
    (1, 2, "ACH DEPOSIT HARBOR & PINE CO INV-2026-001", "3200.00"),
    (1, 3, "WEWORK MEMBERSHIP FEES", "-450.00"),
    (1, 5, "ONLINE TRANSFER TO SAVINGS XXXX5521", "-1000.00"),
    (1, 6, "STRIPE TRANSFER ST-8F3K2L9Q", "1845.30"),
    (1, 8, "XFINITY INTERNET 800-555-0142", "-79.99"),
    (1, 9, "VERIZON WIRELESS PAYMENT", "-65.00"),
    (1, 12, "ZELLE TO MORGAN ELLIS", "-250.00"),
    (1, 14, "CARD SERVICES AUTOPAY PAYMENT", "-1520.44"),
    (1, 15, "IRS USATAXPYMT EST TAX 2025 Q4", "-1800.00"),
    (1, 16, "UPWORK WITHDRAWAL 7731042", "960.00"),
    (1, 20, "ATM WITHDRAWAL #4412 MAIN ST", "-200.00"),
    (1, 22, "CHECK #1043", "-350.00"),
    (1, 23, "ACH DEPOSIT LUMEN ATLAS INC INV-2026-002", "2750.00"),
    (1, 27, "VENMO PAYMENT RILEY CHEN", "-45.00"),
    (1, 31, "MONTHLY SERVICE FEE", "-15.00"),
    (1, 31, "INTEREST PAID", "1.84"),
    (2, 2, "WEWORK MEMBERSHIP FEES", "-450.00"),
    (2, 3, "STRIPE TRANSFER ST-2M7N4B1X", "1210.75"),
    (2, 5, "ONLINE TRANSFER TO SAVINGS XXXX5521", "-1000.00"),
    (2, 6, "ACH DEPOSIT CEDARLINE GOODS INV-2026-003", "4100.00"),
    (2, 8, "XFINITY INTERNET 800-555-0142", "-79.99"),
    (2, 9, "VERIZON WIRELESS PAYMENT", "-65.00"),
    (2, 13, "CARD SERVICES AUTOPAY PAYMENT", "-1890.12"),
    (2, 17, "UPWORK WITHDRAWAL 7731988", "1425.50"),
    (2, 19, "ZELLE TO MORGAN ELLIS", "-300.00"),
    (2, 21, "ATM WITHDRAWAL #4412 MAIN ST", "-100.00"),
    (2, 24, "ACH DEPOSIT HARBOR & PINE CO INV-2026-004", "1800.00"),
    (2, 26, "STRIPE TRANSFER ST-9Q1W5E3R", "655.20"),
    (2, 28, "MONTHLY SERVICE FEE", "-15.00"),
    (2, 28, "INTEREST PAID", "1.62"),
    (3, 2, "WEWORK MEMBERSHIP FEES", "-450.00"),
    (3, 4, "ACH DEPOSIT LUMEN ATLAS INC INV-2026-005", "2750.00"),
    (3, 5, "ONLINE TRANSFER TO SAVINGS XXXX5521", "-1000.00"),
    (3, 9, "XFINITY INTERNET 800-555-0142", "-79.99"),
    (3, 9, "VERIZON WIRELESS PAYMENT", "-65.00"),
    (3, 10, "STRIPE TRANSFER ST-4T6Y8U0I", "2034.90"),
    (3, 13, "CARD SERVICES AUTOPAY PAYMENT", "-1650.00"),
    (3, 16, "UPWORK WITHDRAWAL 7732410", "780.00"),
    (3, 18, "CHECK #1044", "-125.00"),
    (3, 20, "VENMO PAYMENT RILEY CHEN", "-60.00"),
    (3, 23, "ACH DEPOSIT CEDARLINE GOODS INV-2026-006", "3300.00"),
    (3, 25, "ZELLE FROM JAMIE OKAFOR", "400.00"),
    (3, 27, "ATM WITHDRAWAL #4412 MAIN ST", "-200.00"),
    (3, 31, "MONTHLY SERVICE FEE", "-15.00"),
    (3, 31, "INTEREST PAID", "1.97"),
]
CHECKING_OPENING = Decimal("8500.00")

# Credit card with charges POSITIVE and payments/credits NEGATIVE.
CARD = [
    (1, 3, "ADOBE CREATIVE CLOUD", "59.99"),
    (1, 4, "FIGMA MONTHLY", "15.00"),
    (1, 4, "NOTION LABS INC", "10.00"),
    (1, 5, "GOOGLE *WORKSPACE SAMRIV", "14.40"),
    (1, 6, "AWS EMEA AWS.AMAZON.CO", "23.41"),
    (1, 8, "UBER *TRIP HELP.UBER.COM", "18.72"),
    (1, 9, "SQ *JOES CAFE 9921", "8.75"),
    (1, 11, "AMAZON MKTPLACE PMTS AMZN.COM/BILL", "42.18"),
    (1, 13, "LINKEDIN ADS 7720193", "150.00"),
    (1, 14, "PAYMENT THANK YOU", "-1520.44"),
    (1, 15, "TRADER JOES #552", "64.31"),
    (1, 17, "NETFLIX.COM", "15.49"),
    (1, 19, "TST* BLUE FIG BISTRO", "64.80"),
    (1, 21, "BEST BUY 00123", "129.99"),
    (1, 24, "UPWORK *SERVICE FEE", "48.00"),
    (1, 27, "PXL*GRN 88231", "27.50"),
    (2, 1, "BEST BUY 00123 RETURN", "-129.99"),
    (2, 3, "ADOBE CREATIVE CLOUD", "59.99"),
    (2, 4, "FIGMA MONTHLY", "15.00"),
    (2, 4, "NOTION LABS INC", "10.00"),
    (2, 5, "GOOGLE *WORKSPACE SAMRIV", "14.40"),
    (2, 6, "AWS EMEA AWS.AMAZON.CO", "27.88"),
    (2, 7, "DELTA AIR LINES 0062391", "412.60"),
    (2, 9, "MARRIOTT AUSTIN DOWNTOWN", "389.22"),
    (2, 9, "UBER *TRIP HELP.UBER.COM", "31.05"),
    (2, 10, "UBER *EATS PENDING.UBER.COM", "26.40"),
    (2, 11, "SQ *JOES CAFE 9921", "8.75"),
    (2, 11, "SQ *JOES CAFE 9921", "8.75"),  # exact duplicate row
    (2, 12, "PAYMENT THANK YOU", "-1890.12"),
    (2, 14, "KLARO PRINT SHOP", "60.00"),
    (2, 16, "APPLE.COM/BILL", "2.99"),
    (2, 17, "NETFLIX.COM", "15.49"),
    (2, 19, "MERIDIAN SUPPLY 4410", "88.20"),
    (2, 23, "CASA AZUL LISBOA PT", "87.40"),
    (2, 23, "FOREIGN TRANSACTION FEE", "2.62"),
    (2, 26, "TRADER JOES #552", "51.07"),
    (3, 1, "DISPUTE CREDIT KLARO PRINT SHOP", "-60.00"),
    (3, 3, "ADOBE CREATIVE CLOUD", "59.99"),
    (3, 4, "FIGMA MONTHLY", "15.00"),
    (3, 4, "NOTION LABS INC", "10.00"),
    (3, 5, "GOOGLE *WORKSPACE SAMRIV", "14.40"),
    (3, 6, "AWS EMEA AWS.AMAZON.CO", "25.12"),
    (3, 8, "UBER *EATS PENDING.UBER.COM", "33.15"),
    (3, 10, "TST* NORTHSIDE TACOS", "23.10"),
    (3, 12, "PAYMENT THANK YOU", "-1650.00"),
    (3, 14, "AMAZON MKTPLACE PMTS AMZN.COM/BILL", "19.99"),
    (3, 18, "UBER *TRIP HELP.UBER.COM", "22.40"),
    (3, 20, "QUILLFIRE LLC", "140.00"),
    (3, 24, "LINKEDIN ADS 7720193", "150.00"),
    (3, 28, "UPWORK *SERVICE FEE", "35.70"),
]

# Messy checking export: written line by line so every quirk is explicit.
MESSY_LINES = [
    "Account: Sam Rivera Design LLC - Business Checking ****1234",
    "Statement period: 01 Jan 2026 to 31 Mar 2026",
    "",
    "Posting Date;Details;Debit;Credit;Balance",
    "02 Jan 2026;OPENING BALANCE;;;4,250.00",
    "05 Jan 2026;ACH DEPOSIT HARBOR & PINE CO INV-2026-001;;$3,200.00;7,450.00",
    "06 Jan 2026;WEWORK MEMBERSHIP FEES;450.00-;;7,000.00",
    "09 Jan 2026;XFINITY INTERNET;$79.99;;6,920.01",
    "",
    "12 Jan 2026;ONLINE TRANSFER TO SAVINGS XXXX5521;$1,000.00;;5,920.01",
    "15 Jan 2026;IRS USATAXPYMT EST TAX 2025 Q4;$1,800.00;;4,120.01",
    "20 Jan 2026;STRIPE TRANSFER ST-8F3K2L9Q;;$1,845.30;5,965.31",
    "31 Feb 2026;CHECK #1043;350.00-;;5,615.31",
    "03 Feb 2026;VERIZON WIRELESS PAYMENT;65.00-;;5,550.31",
    "10 Feb 2026;CARD SERVICES AUTOPAY PAYMENT;$1,890.12;;3,660.19",
    "",
    "",
    "17 Feb 2026;UPWORK WITHDRAWAL 7731988;;$1,425.50;5,085.69",
    "28 Feb 2026;MONTHLY SERVICE FEE;15.00-;;5,070.69",
    "28 Feb 2026;INTEREST PAID;;1.62;5,072.31",
    "04 Mar 2026;ACH DEPOSIT LUMEN ATLAS INC INV-2026-005;;$2,750.00;7,822.31",
    "13 Mar 2026;ZELLE TO MORGAN ELLIS;300.00-;;7,522.31",
    "27 Mar 2026;PENDING UBER *TRIP HELP.UBER.COM;24.60-;;7,497.71",
    "TOTAL;;$5,974.71;$9,222.42;",
]

# Same idea as CARD in a different layout: charges NEGATIVE, real date and number cells.
# (month, day, posted_offset_days, description, bank category, amount)
CARD_XLSX = [
    (1, 3, 1, "ADOBE CREATIVE CLOUD", "Software", -59.99),
    (1, 4, 1, "FIGMA MONTHLY", "Software", -15.00),
    (1, 6, 2, "AWS EMEA AWS.AMAZON.CO", "Services", -23.41),
    (1, 8, 1, "UBER *TRIP HELP.UBER.COM", "Travel", -18.72),
    (1, 9, 2, "SQ *JOES CAFE 9921", "Food & Drink", -8.75),
    (1, 14, 0, "AUTOPAY PAYMENT - THANK YOU", "Payment", 1520.44),
    (1, 15, 1, "TRADER JOES #552", "Groceries", -64.31),
    (1, 21, 2, "BEST BUY 00123", "Shopping", -129.99),
    (1, 24, 1, "UPWORK *SERVICE FEE", "Services", -48.00),
    (2, 1, 1, "BEST BUY 00123 RETURN", "Shopping", 129.99),
    (2, 3, 1, "ADOBE CREATIVE CLOUD", "Software", -59.99),
    (2, 4, 1, "FIGMA MONTHLY", "Software", -15.00),
    (2, 7, 2, "DELTA AIR LINES 0062391", "Travel", -412.60),
    (2, 9, 1, "MARRIOTT AUSTIN DOWNTOWN", "Travel", -389.22),
    (2, 10, 1, "UBER *EATS PENDING.UBER.COM", "Food & Drink", -26.40),
    (2, 12, 0, "AUTOPAY PAYMENT - THANK YOU", "Payment", 1890.12),
    (2, 16, 1, "APPLE.COM/BILL", "Shopping", -2.99),
    (2, 23, 2, "CASA AZUL LISBOA PT", "Food & Drink", -87.40),
    (2, 23, 2, "FOREIGN TRANSACTION FEE", "Fees", -2.62),
    (3, 3, 1, "ADOBE CREATIVE CLOUD", "Software", -59.99),
    (3, 4, 1, "FIGMA MONTHLY", "Software", -15.00),
    (3, 10, 1, "TST* NORTHSIDE TACOS", "Food & Drink", -23.10),
    (3, 12, 0, "AUTOPAY PAYMENT - THANK YOU", "Payment", 1650.00),
    (3, 20, 2, "QUILLFIRE LLC", "Services", -140.00),
    (3, 24, 1, "LINKEDIN ADS 7720193", "Advertising", -150.00),
]


def _date(month: int, day: int) -> dt.date:
    return dt.date(2026, month, day)


def checking_csv() -> str:
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(["Date", "Description", "Amount", "Balance"])
    balance = CHECKING_OPENING
    for month, day, description, amount in CHECKING:
        balance += Decimal(amount)
        writer.writerow([_date(month, day).strftime("%m/%d/%Y"), description, amount, balance])
    return out.getvalue()


def card_csv() -> str:
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(["Date", "Description", "Amount"])
    for month, day, description, amount in CARD:
        writer.writerow([_date(month, day).strftime("%m/%d/%Y"), description, amount])
    return out.getvalue()


def messy_csv() -> bytes:
    return codecs.BOM_UTF8 + "\n".join(MESSY_LINES).encode() + b"\n"


def card_xlsx(path: Path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Transactions"
    sheet.append(["Transaction Date", "Post Date", "Description", "Category", "Amount"])
    for month, day, offset, description, category, amount in CARD_XLSX:
        txn = dt.datetime(2026, month, day)
        sheet.append([txn, txn + dt.timedelta(days=offset), description, category, amount])
    for cell in sheet["A"][1:] + sheet["B"][1:]:
        cell.number_format = "mm/dd/yyyy"
    workbook.properties.creator = "make_samples.py"
    workbook.properties.created = FIXED_TIME
    workbook.properties.modified = FIXED_TIME
    workbook.save(path)
    _freeze_zip_timestamps(path)


def _freeze_zip_timestamps(path: Path) -> None:
    """openpyxl stamps the zip entries and core.xml "modified" with the current time on save.

    Pin both so reruns are byte-stable.
    """
    with zipfile.ZipFile(path) as src:
        entries = [(info.filename, src.read(info)) for info in src.infolist()]
    stamp = FIXED_TIME.strftime("%Y-%m-%dT%H:%M:%SZ").encode()
    entries = [
        (name, re.sub(rb"(<dcterms:modified[^>]*>)[^<]*", rb"\g<1>" + stamp, data))
        if name == "docProps/core.xml"
        else (name, data)
        for name, data in entries
    ]
    with zipfile.ZipFile(path, "w") as dst:
        for name, data in entries:
            info = zipfile.ZipInfo(name, date_time=FIXED_TIME.timetuple()[:6])
            info.compress_type = zipfile.ZIP_DEFLATED
            dst.writestr(info, data)


def write_samples(out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "checking_simple.csv": checking_csv().encode(),
        "credit_card.csv": card_csv().encode(),
        "bank_messy.csv": messy_csv(),
    }
    written = []
    for name, data in paths.items():
        (out_dir / name).write_bytes(data)
        written.append(out_dir / name)
    card_xlsx(out_dir / "credit_card.xlsx")
    written.append(out_dir / "credit_card.xlsx")
    return written


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "samples"
    for path in write_samples(target):
        print(f"wrote {path}")
