"""Generate sample credit card statement CSVs for the Statement Categorizer demo.

Uses only the standard library with a fixed random seed so output is deterministic.
Produces two CSVs:
  1. statements/amount_single.csv   - Single "Amount" column, ISO dates (YYYY-MM-DD)
  2. statements/debit_credit.csv    - Separate "Debit"/"Credit" columns, $ signs,
                                      commas, MM/DD/YYYY dates

Each includes ~60 random rows plus deliberate tricky rows to exercise the parser
and brain edge cases.
"""

import csv
import os
import random
from datetime import date, timedelta

SEED = 42
random.seed(SEED)

# --- Fake merchants (no real people or real statements) -----------------------

MERCHANTS = [
    ("ADOBE CREATIVE CLOUD", "Software"),
    ("GITHUB INC", "Software"),
    ("FIGMA SUBSCRIPTION", "Software"),
    ("UBER *TRIP", "Travel"),
    ("LYFT RIDE", "Travel"),
    ("DELTA AIRLINES", "Travel"),
    ("SOUTHWEST AIR", "Travel"),
    ("STARBUCKS", "Meals"),
    ("CHIPOTLE", "Meals"),
    ("GOOGLE ADS", "Marketing"),
    ("META ADS", "Marketing"),
    ("COMCAST INTERNET", "Utilities"),
    ("AT&T WIRELESS", "Utilities"),
    ("STAPLES", "Office Supplies"),
    ("NETFLIX", "Subscriptions"),
    ("SPOTIFY", "Subscriptions"),
    ("AMAZON MARKETPLACE", "Software"),
    ("AMAZON.COM", "Software"),
    ("PAYPAL TRANSFER", "Marketing"),
    ("MICROSOFT 365", "Software"),
    ("DROPBOX", "Software"),
    ("SLACK", "Software"),
    ("ZOOM", "Software"),
    ("HEROKU", "Software"),
    ("AWS", "Software"),
    ("DIGITALOCEAN", "Software"),
    ("AMERICAN AIRLINES", "Travel"),
    ("UNITED AIRLINES", "Travel"),
    ("HILTON HOTELS", "Travel"),
    ("MARRIOTT", "Travel"),
    ("MCDONALDS", "Meals"),
    ("SUBWAY", "Meals"),
    ("PANERA BREAD", "Meals"),
    ("FACEBOOK ADS", "Marketing"),
    ("LINKEDIN ADS", "Marketing"),
    ("VERIZON", "Utilities"),
    ("DUKE ENERGY", "Utilities"),
    ("OFFICE DEPOT", "Office Supplies"),
    ("HOME DEPOT", "Office Supplies"),
    ("HULU", "Subscriptions"),
    ("DISNEY PLUS", "Subscriptions"),
    ("APPLE ICLOUD", "Subscriptions"),
    ("NEW YORK TIMES", "Subscriptions"),
    ("WALL STREET JOURNAL", "Subscriptions"),
]

TRICKY_ROWS = [
    # Duplicate Adobe charge (same date/description/amount)
    ("2025-01-15", "ADOBE CREATIVE CLOUD", -29.99),
    ("2025-01-15", "ADOBE CREATIVE CLOUD", -29.99),
    # Refund from Uber
    ("2025-01-16", "REFUND UBER *TRIP", 15.50),
    # Transfer to savings
    ("2025-01-17", "TRANSFER TO SAVINGS 1234", -500.00),
    # Payment thank you (card payment)
    ("2025-01-18", "PAYMENT THANK YOU", -1200.00),
    # Invoice deposit (income)
    ("2025-01-19", "INVOICE DEPOSIT CLIENT ACME", 2500.00),
    # Blank description
    ("2025-01-20", "", -45.00),
    # Foreign currency line
    ("2025-01-21", "FOREIGN CURRENCY FEE EUR", -3.50),
    # Ambiguous Amazon
    ("2025-01-22", "AMZN Mktp US*BOOKS", -22.99),
    # Ambiguous PayPal
    ("2025-01-23", "PAYPAL *EBAY SELLER", -8.75),
]


def _random_date(start: date, end: date) -> date:
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


def _random_amount() -> float:
    return round(-random.uniform(5.0, 500.0), 2)


def generate_rows() -> list[tuple[str, str, float]]:
    """Return a list of (date_str, description, amount) rows."""
    start = date(2025, 1, 1)
    end = date(2025, 1, 31)

    rows: list[tuple[str, str, float]] = []

    # ~60 random normal rows
    for _ in range(60):
        merchant, _ = random.choice(MERCHANTS)
        d = _random_date(start, end).isoformat()
        amt = _random_amount()
        rows.append((d, merchant, amt))

    # Deliberate tricky rows
    for d, desc, amt in TRICKY_ROWS:
        rows.append((d, desc, amt))

    # Shuffle so tricky rows are not all at the end
    random.shuffle(rows)
    return rows


def write_amount_single_csv(path: str) -> None:
    """Write a CSV with a single Amount column and ISO dates."""
    rows = generate_rows()
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Date", "Description", "Amount"])
        for d, desc, amt in rows:
            writer.writerow([d, desc, f"{amt:.2f}"])


def write_debit_credit_csv(path: str) -> None:
    """Write a CSV with Debit/Credit columns, $ signs, commas, MM/DD/YYYY dates."""
    rows = generate_rows()
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Transaction Date", "Details", "Debit", "Credit"])
        for d, desc, amt in rows:
            # Convert ISO date to MM/DD/YYYY
            y, m, day = d.split("-")
            us_date = f"{m}/{day}/{y}"
            if amt < 0:
                debit = f"${abs(amt):,.2f}"
                credit = ""
            else:
                debit = ""
                credit = f"${amt:,.2f}"
            writer.writerow([us_date, desc, debit, credit])


def main() -> None:
    out_dir = os.path.join(os.path.dirname(__file__))
    os.makedirs(out_dir, exist_ok=True)

    write_amount_single_csv(os.path.join(out_dir, "amount_single.csv"))
    write_debit_credit_csv(os.path.join(out_dir, "debit_credit.csv"))

    print(f"Generated {os.path.join(out_dir, 'amount_single.csv')}")
    print(f"Generated {os.path.join(out_dir, 'debit_credit.csv')}")


if __name__ == "__main__":
    main()