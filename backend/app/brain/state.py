"""Mutable per-row working state used while the brain analyzes a statement."""

import re
from dataclasses import dataclass, field

from app.domain.enums import Category, Direction, Flag
from app.domain.models import Candidate, Transaction

REFUND_RE = re.compile(r"\b(REFUND|RETURN|RETURNED|REVERSAL|CREDIT ADJ(USTMENT)?|CREDIT VOUCHER)\b")
P2P_CHANNELS = frozenset({"ZELLE", "VENMO", "CASH_APP", "PAYPAL"})


@dataclass(slots=True)
class RowState:
    txn: Transaction
    text: str  # upper-cased description + memo, used by regex stages
    candidates: list[Candidate] = field(default_factory=list)
    flags: set[Flag] = field(default_factory=set)
    extra_reasons: list[str] = field(default_factory=list)
    is_refund: bool = False  # set by a rule that explicitly reverses money (refund / NSF)
    refund_evidence: bool = False  # inflow that looks like money returned by a merchant
    short_circuit: bool = False
    memory_hit: bool = False
    merchant_hit: bool = False
    duplicate_of_row: int | None = None
    is_duplicate: bool = False

    @property
    def direction(self) -> Direction:
        return self.txn.direction

    @property
    def is_p2p(self) -> bool:
        return self.txn.channel in P2P_CHANNELS

    def add(self, category: Category, score: float, source: str, rule_id: str, reason: str) -> None:
        self.candidates.append(Candidate(category, round(score, 4), source, rule_id, reason))


def new_state(txn: Transaction) -> RowState:
    text = f"{txn.description} {txn.memo or ''}".upper()
    state = RowState(txn=txn, text=text)
    state.refund_evidence = txn.direction is Direction.INFLOW and bool(REFUND_RE.search(text))
    return state
