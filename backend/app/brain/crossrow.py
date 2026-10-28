"""Passes that need the whole statement: duplicates, recurring payments, outliers, 1099 totals."""

from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from statistics import median

from app.brain import explain
from app.brain.context import BrainSettings
from app.brain.resolver import preliminary_top
from app.brain.state import RowState
from app.domain.enums import Category, Direction, Flag

PENDING_WINDOW_DAYS = 5
RECURRING_TOLERANCE = 0.10
RECURRING_SCORE = 0.55
RENT_OUTLIER_RATIO = 1.5
GENERIC_OUTLIER_RATIO = 5.0


def duplicates(states: Sequence[RowState], prior_fingerprints: Mapping[str, str]) -> None:
    seen_fitid: dict[str, int] = {}
    posted = [s for s in states if not s.txn.is_pending]
    for state in states:
        txn = state.txn
        if txn.fitid:
            if txn.fitid in seen_fitid:
                _mark(state, Flag.DUPLICATE_FITID, seen_fitid[txn.fitid])
                continue
            seen_fitid[txn.fitid] = txn.row_index
        if txn.is_pending:
            match = next(
                (
                    p
                    for p in posted
                    if p.txn.amount_cents == txn.amount_cents
                    and p.txn.merchant_key == txn.merchant_key
                    and abs((p.txn.posted_date - txn.posted_date).days) <= PENDING_WINDOW_DAYS
                ),
                None,
            )
            if match is not None:
                _mark(state, Flag.DUPLICATE_PENDING, match.txn.row_index)
                continue
        if txn.fingerprint in prior_fingerprints:
            _mark(state, Flag.DUPLICATE_PRIOR_UPLOAD, None)


def _mark(state: RowState, flag: Flag, of_row: int | None) -> None:
    state.is_duplicate = True
    state.duplicate_of_row = of_row
    state.flags.add(flag)


def _party(state: RowState) -> str:
    return state.txn.counterparty or state.txn.merchant_key


def recurring_and_outliers(states: Sequence[RowState]) -> None:
    groups: dict[tuple[str, Direction], list[RowState]] = defaultdict(list)
    for state in states:
        if state.is_duplicate or state.short_circuit or state.txn.amount_cents == 0:
            continue
        groups[(_party(state), state.direction)].append(state)

    for members in groups.values():
        if len(members) < 2:
            continue
        amounts = [abs(m.txn.amount_cents) for m in members]
        typical = median(amounts)
        _boost_recurring(members, typical)
        _flag_outliers(members)


def _boost_recurring(members: list[RowState], typical: float) -> None:
    steady = [
        m
        for m in members
        if abs(abs(m.txn.amount_cents) - typical) <= typical * RECURRING_TOLERANCE
    ]
    months = {(m.txn.posted_date.year, m.txn.posted_date.month) for m in steady}
    if len(months) < 2:
        return
    for state in steady:
        top = preliminary_top(state)
        if top is None:
            continue
        state.add(top, RECURRING_SCORE, "recurring", "x.recurring", explain.recurring(top))
        state.flags.add(Flag.RECURRING)


def _regular_amount(amounts: list[int]) -> int | None:
    """The amount that repeats most in a group (e.g. monthly rent), if any repeats."""
    amount, count = Counter(amounts).most_common(1)[0]
    return amount if count >= 2 else None


def _flag_outliers(members: list[RowState]) -> None:
    if len(members) < 3:
        return
    for state in members:
        others = [abs(m.txn.amount_cents) for m in members if m is not state]
        regular = _regular_amount(others)
        is_rent = preliminary_top(state) is Category.RENT
        base = regular if regular is not None else median(others)
        ratio = RENT_OUTLIER_RATIO if is_rent and regular is not None else GENERIC_OUTLIER_RATIO
        if base > 0 and abs(state.txn.amount_cents) > base * ratio:
            state.flags.add(Flag.AMOUNT_OUTLIER)
            state.flags.discard(Flag.RECURRING)


def contractor_totals(
    states: Sequence[RowState], ytd: Mapping[str, int], settings: BrainSettings
) -> None:
    totals: dict[str, int] = defaultdict(int)
    paid: dict[str, list[RowState]] = defaultdict(list)
    for state in states:
        if state.is_duplicate or Flag.PAYMENT_TO_INDIVIDUAL not in state.flags:
            continue
        who = state.txn.counterparty or state.txn.merchant_key
        totals[who] += abs(state.txn.amount_cents)
        paid[who].append(state)
    for who, total in totals.items():
        if total + ytd.get(who, 0) >= settings.contractor_1099_cents:
            for state in paid[who]:
                state.flags.add(Flag.POSSIBLE_1099)


def link_refunds(states: Sequence[RowState]) -> None:
    purchases: dict[str, list[RowState]] = defaultdict(list)
    for state in states:
        if state.direction is Direction.OUTFLOW:
            purchases[state.txn.merchant_key].append(state)
    for state in states:
        if not state.refund_evidence:
            continue
        earlier = [
            p
            for p in purchases.get(state.txn.merchant_key, [])
            if p.txn.posted_date <= state.txn.posted_date
        ]
        if earlier:
            if abs(state.txn.amount_cents) > max(abs(p.txn.amount_cents) for p in earlier):
                state.flags.add(Flag.REFUND_EXCEEDS_PURCHASE)
            original = max(earlier, key=lambda p: p.txn.posted_date)
            state.extra_reasons.append(
                f"Matches the {original.txn.posted_date:%b %d} purchase "
                f"(row {original.txn.row_index})."
            )
