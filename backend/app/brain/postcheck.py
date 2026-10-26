from collections.abc import Sequence
from datetime import date
from decimal import Decimal

from app.brain.models import Decision
from app.brain.normalizer import normalize
from app.ingest.models import ParsedRow


def postcheck(rows: Sequence[ParsedRow], decisions: Sequence[Decision]) -> list[Decision]:
    """Checks that need the whole file. Rows and decisions are parallel lists from one file.

    Duplicates: same date, same normalized text and same amount as an earlier row.
    Every occurrence after the first goes to review but keeps its category.
    """
    if len(rows) != len(decisions):
        raise ValueError("rows and decisions must have the same length")

    first_seen: dict[tuple[date, str, Decimal], int] = {}
    checked: list[Decision] = []
    for row, decision in zip(rows, decisions, strict=True):
        key = (row.date, normalize(row.raw_description).text, row.amount)
        original = first_seen.setdefault(key, row.row_number)
        if original == row.row_number:
            checked.append(decision)
            continue
        reason = f"possible duplicate of row {original}"
        if decision.needs_review:
            reason = f"{reason}; {decision.reason}"
        checked.append(decision.model_copy(update={"needs_review": True, "reason": reason}))
    return checked
