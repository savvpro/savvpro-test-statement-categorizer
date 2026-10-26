"""Same date + amount + merchant_key twice in one statement: flag the repeat, never drop it."""

from app.brain.models import Decision, ParsedRow, TxnStatus

FLAG = "possible_duplicate"


def mark_duplicates(rows: list[ParsedRow], decisions: list[Decision]) -> None:
    first_seen: dict[tuple[object, ...], int] = {}
    for index, (row, decision) in enumerate(zip(rows, decisions, strict=True)):
        key = (row.date, row.amount, decision.merchant_key)
        original = first_seen.setdefault(key, index)
        if original == index:
            continue
        guess = decisions[original]
        decision.suggested_category_id = (
            guess.category_id if guess.status is TxnStatus.auto else guess.suggested_category_id
        )
        decision.category_id = "needs_review"
        decision.status = TxnStatus.needs_review
        decision.flags.append(FLAG)
        decision.reasons.insert(
            0, f"possible duplicate of row {original}: same date, amount and merchant"
        )
