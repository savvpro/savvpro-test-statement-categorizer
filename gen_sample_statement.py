"""Generate a fake PKR bank statement CSV for a freelance developer in Lahore.

Bank: "Ravi Commerce Bank Ltd" (fictional). All names/numbers are fake.
Columns: Date (DD-MM-YYYY), Description, Debit, Credit, Balance
Positive amount = money in (credit), negative = money out (debit).
"""
import csv
from datetime import datetime

OPENING_BALANCE = 842_350

# (date, description, amount in PKR)
ROWS = [
    # ---- September 2026 ----
    ("01-09-2026", "PAYONEER INC FUNDS TRF REF 88213", 385000),
    ("01-09-2026", "RENT COWORKING - OFFICE HUB GULBERG LHR", -35000),
    ("02-09-2026", "LESCO ONLINE BILL PAY 1234567890", -18420),
    ("02-09-2026", "SNGPL BILL PAYMENT", -2150),
    ("03-09-2026", "NAYATEL BROADBAND ACCT 55123", -6500),
    ("03-09-2026", "FOODPANDA*ORDER 4471920", -1840),
    ("04-09-2026", "CAREEM *TRIP LHR", -890),
    ("04-09-2026", "GITHUB.COM SAN FRANCISCO USD 4.00", -1120),
    ("05-09-2026", "OPENAI *CHATGPT SUBSCR USD 20.00", -5600),
    ("05-09-2026", "AMZN MKTP US*2K4LP8 USD 34.99", -9790),
    ("06-09-2026", "IBFT TO SAVINGS A/C 0042****7781", -100000),
    ("06-09-2026", "ATM CASH WDL GULBERG BRANCH", -20000),
    ("06-09-2026", "WHT ON CASH WDL", -120),
    ("07-09-2026", "DARAZ.PK ORDER 7782316", -14500),
    ("08-09-2026", "IMTIAZ SUPER MARKET DHA PH5", -7620),
    ("09-09-2026", "JAZZ MOBILE BUNDLE 0300****412", -1500),
    ("10-09-2026", "BHATTI CHICKEN CORNER 0231", -2400),
    ("10-09-2026", "CAREEM *TRIP LHR", -640),
    ("11-09-2026", "NAMECHEAP.COM USD 13.98", -3910),
    ("12-09-2026", "FOODPANDA*ORDER 4488102", -2260),
    ("12-09-2026", "FOODPANDA*ORDER 4488102", -2260),  # duplicate charge
    ("13-09-2026", "RAAST P2P TO ALI RAZA 0333****918", -5000),
    ("14-09-2026", "DARAZ.PK REFUND ORD 7782316", 6500),  # partial refund
    ("14-09-2026", "SMS ALERT CHARGES SEP", -45),
    ("15-09-2026", "AWS EMEA USD 12.40", -3470),
    ("16-09-2026", "payoneer inc funds trf ref 88954", 120000),  # lowercase
    ("17-09-2026", "PSO FUEL PUMP JAIL ROAD", -8000),
    ("18-09-2026", "ZONG 4G POSTPAID BILL", -3200),
    ("19-09-2026", "NETFLIX.COM USD 9.99", -2800),
    ("20-09-2026", "JAZZCASH MOBILE ACCOUNT TOPUP", -10000),
    ("21-09-2026", "MEDICARE PHARMACY GULBERG", -1380),
    ("22-09-2026", "FBR ADVANCE TAX PMT CPR 2609001452", -45000),
    ("23-09-2026", "CAREEM *TRIP LHR", -1150),
    ("24-09-2026", "AMZN MKTP US*8H2QW1 USD 59.00", -16520),
    ("25-09-2026", "COURSERA.ORG USD 49.00", -13720),
    ("26-09-2026", "ATM CASH WDL MM ALAM RD", -15000),
    ("26-09-2026", "WHT ON CASH WDL", -90),
    ("28-09-2026", "CHECKOUT.COM*FIGMA USD 15.00", -4200),
    ("30-09-2026", "ANNUAL DEBIT CARD FEE", -1500),
    ("30-09-2026", "FED ON BANK CHARGES", -247),
    # ---- October 2026 ----
    ("01-10-2026", "PAYONEER INC FUNDS TRF REF 89377", 410000),
    ("01-10-2026", "RENT COWORKING - OFFICE HUB GULBERG LHR", -35000),
    ("02-10-2026", "LESCO ONLINE BILL PAY 1234567890", -21310),
    ("02-10-2026", "SNGPL BILL PAYMENT", -3480),
    ("03-10-2026", "NAYATEL BROADBAND ACCT 55123", -6500),
    ("04-10-2026", "CAREEM *TRIP LHR", -720),
    ("04-10-2026", "GITHUB.COM SAN FRANCISCO USD 4.00", -1124),
    ("05-10-2026", "OPENAI *CHATGPT SUBSCR USD 20.00", -5610),
    ("05-10-2026", "IBFT TO SAVINGS A/C 0042****7781", -150000),
    ("06-10-2026", "ATM CASH WDL GULBERG BRANCH", -25000),
    ("06-10-2026", "WHT ON CASH WDL", -150),
    ("07-10-2026", "M/S AL-NOOR TRADERS PVT LTD", -32000),
    ("08-10-2026", "FOODPANDA*ORDER 4502771", -1590),
    ("09-10-2026", "CAREEM *TRIP REFUND", 640),
    ("10-10-2026", "KFC  DHA RAYA 0112", -3120),  # double space
    ("11-10-2026", "IMTIAZ SUPER MARKET DHA PH5", -9340),
    ("12-10-2026", "JAZZ MOBILE BUNDLE 0300****412", -1500),
    ("12-10-2026", "ATM CASH WDL FAILED TXN", -5000),
    ("12-10-2026", "REVERSAL - FAILED ATM TXN", 5000),
    ("13-10-2026", "DARAZ.PK ORDER 7934410", -28900),
    ("14-10-2026", "AWS EMEA USD 14.15", -3960),
    ("15-10-2026", "PAYONEER INC FUNDS TRF REF 89802", 95000),
    ("16-10-2026", "NAMECHEAP.COM USD 8.88", -2490),
    ("17-10-2026", "PSO FUEL PUMP JAIL ROAD", -7500),
    ("18-10-2026", "ZONG 4G POSTPAID BILL", -3200),
    ("19-10-2026", "NETFLIX.COM USD 9.99", -2800),
    ("20-10-2026", "FBR ADVANCE TAX PMT CPR 2610000731", -52000),
    ("21-10-2026", "CHECKOUT.COM*FIGMA USD 15.00", -4210),
    ("22-10-2026", "RAAST P2P FROM USMAN TARIQ 0321****554", 25000),
    ("22-10-2026", "FOODPANDA*ORDER 4510025", -2740),
    ("24-10-2026", "LIBERTY BOOKS GULBERG", -3450),
    ("24-10-2026", "MEDICARE PHARMACY GULBERG", -2100),
    ("25-10-2026", "ATM CASH WDL MM ALAM RD", -10000),
    ("25-10-2026", "WHT ON CASH WDL", -60),
    ("25-10-2026", "SMS ALERT CHARGES OCT", -45),
]


def main(path: str = "sample_statement_pkr.csv") -> None:
    rows = sorted(
        enumerate(ROWS),
        key=lambda x: (datetime.strptime(x[1][0], "%d-%m-%Y"), x[0]),
    )
    balance = OPENING_BALANCE
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Date", "Description", "Debit", "Credit", "Balance"])
        for _, (date, desc, amt) in rows:
            balance += amt
            debit = -amt if amt < 0 else ""
            credit = amt if amt > 0 else ""
            w.writerow([date, desc, debit, credit, balance])
    print(f"Wrote {len(rows)} rows to {path}; closing balance PKR {balance:,}")


if __name__ == "__main__":
    main()
