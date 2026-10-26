"""Context signal: the same merchant charging the same amount in different months."""

from collections import defaultdict
from decimal import Decimal

from app.brain.models import ParsedRow

MIN_MONTHS = 2


def recurring_months(rows: list[ParsedRow], keys: list[str]) -> list[int]:
    """For each row, how many distinct months saw the same merchant_key + amount (0 if < 2)."""
    months: dict[tuple[str, Decimal], set[tuple[int, int]]] = defaultdict(set)
    for row, key in zip(rows, keys, strict=True):
        months[(key, row.amount)].add((row.date.year, row.date.month))
    counts = []
    for row, key in zip(rows, keys, strict=True):
        n = len(months[(key, row.amount)])
        counts.append(n if n >= MIN_MONTHS else 0)
    return counts
