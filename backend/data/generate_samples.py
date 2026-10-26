"""Generate fake landlord bank statements in two different CSV formats.

All names, merchants and amounts are fictional. Run:
    python backend/data/generate_samples.py
"""
import csv
import random
from datetime import date
from pathlib import Path

random.seed(42)  # deterministic, so tests stay stable
OUT = Path(__file__).parent
YEAR = 2025
MORTGAGE_PAYMENT = 1199.10  # $200k loan, 6%, 30 years


def build_rows():
    rows = []  # (date, description, amount) ; negative = money out

    for m in range(1, 13):
        rows.append((date(YEAR, m, 1), "ZELLE FROM JOHN TENANT", 1500.00))
        rows.append((date(YEAR, m, 3), "WELLS FARGO HOME MTG PYMT", -MORTGAGE_PAYMENT))
        rows.append((date(YEAR, m, 5), "STATE FARM INS PREMIUM", -95.00))
        rows.append((date(YEAR, m, 12), "CITY WATER UTILITY", -round(random.uniform(40, 70), 2)))
        rows.append((date(YEAR, m, 15), "ELECTRIC CO *AUTOPAY", -round(random.uniform(60, 130), 2)))
        rows.append((date(YEAR, m, 28), "MONTHLY SERVICE FEE", -12.00))

    # --- Edge cases: these are what the brain must handle well ---
    rows.append((date(YEAR, 4, 1), "ZELLE FROM JOHN TENANT", 750.00))   # rent paid in two parts
    rows.append((date(YEAR, 4, 9), "ZELLE FROM JOHN TENANT", 750.00))
    rows.append((date(YEAR, 2, 20), "ZELLE FROM NEW TENANT SEC DEPOSIT", 1500.00))  # not income
    rows.append((date(YEAR, 9, 14), "CHECK 1042 DEPOSIT REFUND", -1500.00))          # not an expense
    rows.append((date(YEAR, 3, 8), "ACE PLUMBING 4412", -340.00))
    rows.append((date(YEAR, 3, 20), "ACE PLUMBING REFUND", 120.00))     # refund, NOT income
    rows.append((date(YEAR, 5, 2), "HOME DEPOT 0117", -286.45))          # ambiguous -> review
    rows.append((date(YEAR, 6, 6), "AMAZON MKTPLACE PMTS", -54.99))      # ambiguous -> review
    rows.append((date(YEAR, 7, 7), "JOES CAFE 9921", -18.50))            # unknown -> review
    rows.append((date(YEAR, 6, 30), "TRANSFER TO SAVINGS ****1234", -500.00))  # not spending
    rows.append((date(YEAR, 4, 15), "COUNTY TREASURER PROPERTY TAX", -1050.00))
    rows.append((date(YEAR, 10, 15), "COUNTY TREASURER PROPERTY TAX", -1050.00))
    rows.append((date(YEAR, 8, 3), "MAPLE GROVE HOA DUES", -150.00))
    dup = (date(YEAR, 8, 22), "LOCKSMITH EXPRESS 220", -85.00)
    rows.extend([dup, dup])                                              # duplicate row

    # --- ADD YOUR OWN EDGE-CASE ROWS HERE ---
    # rows.append((date(YEAR, 5, 10), "SOME DESCRIPTION", -42.00))

    return sorted(rows, key=lambda r: r[0])


def write_format_a(rows):
    """One signed 'Amount' column, US dates."""
    with open(OUT / "bank_a.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Date", "Description", "Amount"])
        for d, desc, amt in rows:
            w.writerow([d.strftime("%m/%d/%Y"), desc, f"{amt:.2f}"])


def write_format_b(rows):
    """Separate Debit/Credit columns, ISO dates, different headers."""
    with open(OUT / "bank_b.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Posting Date", "Details", "Debit", "Credit"])
        for d, desc, amt in rows:
            debit = f"{-amt:.2f}" if amt < 0 else ""
            credit = f"{amt:.2f}" if amt > 0 else ""
            w.writerow([d.isoformat(), desc, debit, credit])


if __name__ == "__main__":
    data = build_rows()
    write_format_a(data)
    write_format_b(data)
    print(f"Wrote {len(data)} rows to bank_a.csv and bank_b.csv")