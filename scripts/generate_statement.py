"""Print a reproducible synthetic statement; no real people or financial data."""

import argparse
import csv
import sys
from datetime import date, timedelta

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--rows", type=int, default=5000)
args = parser.parse_args()
if not 1 <= args.rows <= 5000:
    parser.error("--rows must be between 1 and 5000")
writer = csv.writer(sys.stdout)
writer.writerow(["Date", "Description", "Amount"])
merchants = [
    "FIGMA",
    "ADOBE CREATIVE CLOUD",
    "UNKNOWN SYNTHETIC VENDOR",
    "TRANSFER TO SAVINGS",
    "GOOGLE ADS",
    "GITHUB",
]
for index in range(args.rows):
    day = date(2020, 1, 1) + timedelta(days=index)
    minor = 101 + (index * 97) % 40000
    writer.writerow(
        [
            day.isoformat(),
            merchants[index % len(merchants)],
            f"-{minor // 100}.{minor % 100:02d}",
        ]
    )
