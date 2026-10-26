"""Decide which sign means "money out" when a file has a single signed amount column.

Banks disagree: card exports usually print purchases as positive numbers, current account
exports print them as negative. The statement's own lines give the answer away: a payment
toward the card, a refund or a deposit is always money in, so its sign is the inflow sign.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from decimal import Decimal

from app.brain.classifier import REFUND_WORDS
from app.domain.models import Convention, RawRow

_MONEY_IN = re.compile(
    r"\b(PAYMENT\b.{0,20}\bTHANK|AUTO ?PAY|ONLINE PAYMENT|PAYMENT RECEIVED|DEPOSIT|PAYOUT|"
    r"TRANSFER FROM|XFER FROM|INTEREST PAID|INTEREST EARNED)\b"
)
_MONEY_OUT = re.compile(
    r"\b(PURCHASE|TRANSFER TO|XFER TO|WITHDRAWAL|INTEREST CHARGE|FINANCE CHARGE|LATE FEE|"
    r"ANNUAL FEE|ATM|CHECKCARD|POS DEBIT)\b"
)


def _sign(value: Decimal) -> int:
    return 1 if value > 0 else -1


def _majority(votes: list[int]) -> int | None:
    positive = votes.count(1)
    negative = votes.count(-1)
    if positive == negative:
        return None
    return 1 if positive > negative else -1


def choose_convention(
    rows: Sequence[RawRow],
    *,
    requested: Convention | None,
    hint: Convention | None,
) -> tuple[Convention, list[str]]:
    """Pick the sign convention for rows that only have a single amount."""
    if requested is not None:
        return requested, []
    if hint is not None:
        return hint, []

    single = [r for r in rows if r.amount is not None]
    if not single:
        return Convention.POSITIVE_IS_SPENDING, []

    in_votes: list[int] = []
    out_votes: list[int] = []
    all_votes: list[int] = []
    for row in single:
        assert row.amount is not None
        text = row.description.upper()
        sign = _sign(row.amount)
        all_votes.append(sign)
        if _MONEY_IN.search(text) or REFUND_WORDS.search(text):
            in_votes.append(sign)
        elif _MONEY_OUT.search(text):
            out_votes.append(sign)

    # Spending sign according to each kind of evidence.
    evidence: list[int] = []
    inflow_sign = _majority(in_votes)
    if inflow_sign is not None:
        evidence.append(-inflow_sign)
    outflow_sign = _majority(out_votes)
    if outflow_sign is not None:
        evidence.append(outflow_sign)

    warnings: list[str] = []
    majority = _majority(all_votes)
    if evidence:
        if len(set(evidence)) == 1:
            spending = evidence[0]
        else:
            spending = majority or 1
            warnings.append(
                "The signs in this file were contradictory; verify which amounts are purchases."
            )
        if majority is not None and majority != spending:
            warnings.append(
                "Most amounts have the opposite sign to the purchases detected from descriptions; "
                "check the amount convention."
            )
    elif majority is not None:
        spending = majority
        warnings.append(
            "The amount convention was guessed from the most common sign. "
            "If totals look inverted, choose it manually."
        )
    else:
        spending = 1
        warnings.append(
            "Could not tell purchases from credits; assumed positive amounts are spending."
        )

    return (
        Convention.POSITIVE_IS_SPENDING if spending == 1 else Convention.NEGATIVE_IS_SPENDING,
        warnings,
    )


def spend_amount(row: RawRow, convention: Convention) -> Decimal:
    """Positive = money out, negative = money in."""
    if row.debit is not None or row.credit is not None:
        return (row.debit or Decimal(0)) - (row.credit or Decimal(0))
    assert row.amount is not None
    return row.amount if convention is Convention.POSITIVE_IS_SPENDING else -row.amount
