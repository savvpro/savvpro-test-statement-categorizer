from decimal import Decimal
from typing import Dict, List, Tuple

from ..domain.models import CategorizedTransaction, Category, CategoryTotal


def compute_totals(transactions: List[CategorizedTransaction]) -> List[CategoryTotal]:
    buckets: Dict[Category, Tuple[Decimal, int]] = {}
    for tx in transactions:
        total, count = buckets.get(tx.category, (Decimal("0"), 0))
        buckets[tx.category] = (total + tx.amount, count + 1)
    order = list(Category)
    return [
        CategoryTotal(category=c, total=total, count=count)
        for c, (total, count) in sorted(buckets.items(), key=lambda kv: order.index(kv[0]))
    ]
