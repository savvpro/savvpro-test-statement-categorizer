"""Cross-row passes run after the rules: they see the whole statement, not one row."""

import re
from datetime import timedelta

from .schemas import Transaction

OWN_TRANSFER = re.compile(r"\b(IBFT|FUND TRANSFER|ITFT)\b.*\b(TO|FROM)\b.*\b(SAVINGS|OWN|SELF)\b")
REFUND = re.compile(r"\b(REFUND|CHARGEBACK)\b")
REVERSAL_WINDOW = timedelta(days=7)


def _flag(tx: Transaction, flag: str) -> None:
    if flag not in tx.flags:
        tx.flags = [*tx.flags, flag]


def transfers(transactions: list[Transaction]) -> None:
    """Moves between the user's own accounts are not spending."""
    for tx in transactions:
        if OWN_TRANSFER.search(tx.normalized):
            tx.assign("Transfer", 0.95, "Transfer between own accounts, not spending")
            _flag(tx, "transfer")


def refunds(transactions: list[Transaction]) -> None:
    """A credit labelled refund is money back, not income."""
    for tx in transactions:
        if tx.amount <= 0 or not REFUND.search(tx.normalized):
            continue
        merchant = tx.normalized.split()[0]
        earlier = [
            t
            for t in transactions
            if t.amount < 0 and t.date <= tx.date and t.normalized.startswith(merchant)
        ]
        match = next(
            (t for t in reversed(earlier) if -t.amount == tx.amount),
            earlier[-1] if earlier else None,
        )
        if match is not None:
            tx.refund_of = match.id
        if match is None:
            tx.assign(
                "Refund",
                0.75,
                f"Refund from {merchant}, not income; no matching purchase in this statement",
            )
        elif -match.amount == tx.amount:
            tx.assign(
                "Refund", 0.95, f"Refund from {merchant}, not income; full refund of row {match.id}"
            )
        else:
            tx.assign(
                "Refund",
                0.85,
                f"Refund from {merchant}, not income; partial refund against row {match.id}",
            )


def reversals(transactions: list[Transaction]) -> None:
    """Pair each failed debit with a same-amount reversal credit; the pair nets to zero."""
    used: set[int] = set()
    for failed in transactions:
        if failed.amount >= 0 or "FAILED" not in failed.normalized:
            continue
        for rev in transactions:
            if (
                rev.id not in used
                and rev.amount == -failed.amount
                and "REVERSAL" in rev.normalized
                and timedelta(0) <= rev.date - failed.date <= REVERSAL_WINDOW
            ):
                used.add(rev.id)
                note = f"Failed transaction of PKR {-failed.amount:,} reversed (rows {failed.id} and {rev.id}); net 0, not spending"
                for tx in (failed, rev):
                    tx.assign("Transfer", 0.9, note)
                    _flag(tx, "reversal")
                break


def duplicates(transactions: list[Transaction]) -> None:
    """Same merchant, amount and day charged twice: flag the later row for review."""
    seen: dict[tuple, int] = {}
    for tx in transactions:
        if tx.amount >= 0:
            continue
        key = (tx.date, tx.normalized, tx.amount)
        if key in seen:
            _flag(tx, "duplicate")
            tx.needs_review = True
            tx.reason += f" | Possible duplicate of row {seen[key]}"
        else:
            seen[key] = tx.id


def apply_passes(transactions: list[Transaction]) -> None:
    transfers(transactions)
    refunds(transactions)
    reversals(transactions)
    duplicates(transactions)
