"""Schedule E summary (01-architecture section 6).

Totals count `auto` and `user_confirmed` rows only. Amounts are signed, so a refund (positive
amount in an expense category) nets against that category automatically.
"""

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Protocol

from app.domain.enums import Category, CategoryKind, Status
from app.domain.taxonomy import TAXONOMY

COUNTED = {Status.AUTO.value, Status.USER_CONFIRMED.value}


class SummaryRow(Protocol):
    @property
    def category(self) -> str | None: ...
    @property
    def status(self) -> str: ...
    @property
    def amount_cents(self) -> int: ...


@dataclass
class Summary:
    income: dict[str, int] = field(default_factory=dict)
    expenses: dict[str, int] = field(default_factory=dict)
    schedule_e: list[dict[str, object]] = field(default_factory=list)
    total_income_cents: int = 0
    total_expense_cents: int = 0
    net_cents: int = 0
    excluded: dict[str, int] = field(default_factory=dict)
    unresolved_count: int = 0
    unresolved_total_abs_cents: int = 0
    duplicate_count: int = 0


def _line_key(line: str | None) -> int:
    return int(line) if line and line.isdigit() else 999


def compute_summary(rows: Iterable[SummaryRow]) -> Summary:
    totals: dict[Category, int] = defaultdict(int)
    seen: set[Category] = set()
    out = Summary()
    for row in rows:
        if row.status == Status.NEEDS_REVIEW.value:
            out.unresolved_count += 1
            out.unresolved_total_abs_cents += abs(row.amount_cents)
        elif row.status == Status.DUPLICATE.value:
            out.duplicate_count += 1
        if row.status not in COUNTED or row.category is None:
            continue
        category = Category(row.category)
        totals[category] += row.amount_cents
        seen.add(category)

    for category in sorted(seen, key=lambda c: (_line_key(TAXONOMY[c].schedule_e_line), c.value)):
        info = TAXONOMY[category]
        total = totals[category]
        if info.kind is CategoryKind.INCOME:
            out.income[category.value] = total
        elif info.kind is CategoryKind.EXPENSE:
            out.expenses[category.value] = total
        else:
            out.excluded[category.value] = total
            continue
        out.schedule_e.append(
            {
                "line": info.schedule_e_line,
                "label": info.label,
                "category": category.value,
                "total_cents": total,
            }
        )
    out.total_income_cents = sum(out.income.values())
    out.total_expense_cents = sum(out.expenses.values())
    out.net_cents = out.total_income_cents + out.total_expense_cents
    return out
