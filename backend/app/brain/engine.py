"""The brain: deterministic, explainable categorization. No AI model decides anything here.

Pipeline per row: structural → channel → memory → merchant → keyword → fuzzy → policy flags.
Then whole-statement passes (duplicates, recurring, outliers, 1099, refund links), then the
resolver turns evidence into a decision, choosing "needs review" whenever it is not sure.
"""

from collections.abc import Sequence

from app.brain import crossrow
from app.brain.context import BrainContext
from app.brain.resolver import resolve
from app.brain.stages import channel, matching, structural
from app.brain.state import RowState, new_state
from app.domain.enums import Flag
from app.domain.models import Decision, Transaction

MIN_MEANINGFUL_CHARS = 3


def _policy(state: RowState, ctx: BrainContext) -> None:
    txn = state.txn
    if txn.amount_cents == 0:
        state.flags.add(Flag.ZERO_AMOUNT)
    meaningful = txn.merchant_key.replace("UNKNOWN", "").strip()
    if len(meaningful) < MIN_MEANINGFUL_CHARS and not (txn.memo or "").strip():
        state.flags.add(Flag.LOW_INFORMATION)
    if not state.memory_hit and any(p.search(txn.merchant_key) for p in ctx.rules.mixed_use):
        state.flags.add(Flag.MIXED_USE_MERCHANT)


def analyze(txn: Transaction, ctx: BrainContext) -> RowState:
    state = new_state(txn)
    structural.apply(state, ctx.rules)
    if not state.short_circuit:
        channel.apply(state)
        matching.memory(state, ctx.memory)
        matching.merchants(state, ctx.rules)
        matching.keywords(state, ctx.rules)
        matching.fuzzy(state, ctx.rules, ctx.settings)
        channel.person_inflow_fallback(state)
    _policy(state, ctx)
    return state


def categorize(txns: Sequence[Transaction], ctx: BrainContext) -> list[Decision]:
    """Return one decision per transaction, in input order. Pure and deterministic."""
    states = [analyze(txn, ctx) for txn in txns]
    crossrow.duplicates(states, ctx.prior_fingerprints)
    crossrow.recurring_and_outliers(states)
    crossrow.contractor_totals(states, ctx.ytd_by_counterparty, ctx.settings)
    crossrow.link_refunds(states)
    return [resolve(state, ctx.settings) for state in states]
