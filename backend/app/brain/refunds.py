"""Link refunds (and chargebacks) to the purchase they reverse.

A refund stays a refund whether or not a match is found: money back is never income.
"""

from app.brain.models import Decision, ParsedRow, TxnStatus

_REFUND_WORDS = {
    "REFUND", "RETURN", "REVERSAL", "REVERSED", "CREDIT", "VOUCHER", "MERCHANDISE",
    "DISPUTE", "CHARGEBACK", "CHARGE", "BACK", "PROVISIONAL",
}  # fmt: skip


def base_key(merchant_key: str) -> str:
    return " ".join(word for word in merchant_key.split() if word not in _REFUND_WORDS)


def _same_merchant(a: str, b: str) -> bool:
    return bool(a and b) and (a == b or a.startswith(b + " ") or b.startswith(a + " "))


def _category_of(decision: Decision) -> str | None:
    if decision.status is TxnStatus.auto:
        return decision.category_id
    return decision.suggested_category_id


def link_refunds(rows: list[ParsedRow], decisions: list[Decision], window_days: int) -> None:
    used: set[int] = set()
    for index, decision in enumerate(decisions):
        refund = rows[index]
        is_refund = decision.category_id == "refund" or "chargeback" in decision.flags
        if not is_refund or refund.amount <= 0:
            continue

        target = base_key(decision.merchant_key)
        best: int | None = None
        for j, purchase in enumerate(rows):
            if j == index or j in used or purchase.amount >= 0:
                continue
            if not 0 <= (refund.date - purchase.date).days <= window_days:
                continue
            if refund.amount > -purchase.amount:
                continue
            if not _same_merchant(target, base_key(decisions[j].merchant_key)):
                continue
            if best is None or purchase.date >= rows[best].date:
                best = j

        if best is not None:
            used.add(best)
            decision.linked_row_index = best
            category = _category_of(decisions[best]) or "unknown category"
            decision.reasons.append(f"reverses row {best} ({category}); nets against that expense")
        elif decision.category_id == "refund":
            decision.reasons.append(
                f"no matching purchase in the last {window_days} days; still a refund, not income"
            )
