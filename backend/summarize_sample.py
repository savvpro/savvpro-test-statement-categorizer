"""Print category counts and Needs Review rows for a statement CSV (default: the sample)."""

import sys
from collections import Counter
from decimal import Decimal
from pathlib import Path

from app.engine import categorize_all
from app.parser import parse_csv

path = Path(
    sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parent.parent / "sample_statement_pkr.csv"
)
result = parse_csv(path.read_text(encoding="utf-8-sig"))
rows = categorize_all(result.transactions)

print(f"{len(rows)} rows parsed, {len(result.errors)} bad rows")
for error in result.errors:
    print(f"  ! {error}")

totals: Counter[str] = Counter()
sums: dict[str, Decimal] = {}
for tx in rows:
    totals[tx.category] += 1
    sums[tx.category] = sums.get(tx.category, Decimal(0)) + tx.amount
print("\nCategory counts (net PKR)")
for category, count in totals.most_common():
    print(f"  {category:<18}{count:>3}  {sums[category]:>12,}")

print("\nNeeds Review rows")
for tx in rows:
    if tx.needs_review:
        print(f"  #{tx.id:<3}{tx.date}  {tx.amount:>10,}  {tx.description}\n        {tx.reason}")

print("\nFlagged rows")
for tx in rows:
    if tx.flags:
        print(f"  #{tx.id:<3}{','.join(tx.flags):<10} {tx.category:<10} {tx.description}")
