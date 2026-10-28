from collections.abc import Callable, Mapping
from datetime import date
from typing import Any

import pytest

from app.brain.context import BrainContext
from app.brain.engine import categorize
from app.brain.rules import DEFAULT_RULES_DIR, RuleSet, load_ruleset
from app.domain.enums import AccountType, Category, Direction
from app.domain.models import Decision, Transaction


@pytest.fixture(scope="session")
def rules() -> RuleSet:
    return load_ruleset(DEFAULT_RULES_DIR)


def txn(
    description: str,
    cents: int,
    *,
    row: int = 1,
    day: date = date(2026, 3, 4),
    merchant_key: str | None = None,
    memo: str | None = None,
    channel: str | None = "CARD",
    counterparty: str | None = None,
    account: AccountType = AccountType.CHECKING,
    fitid: str | None = None,
    pending: bool = False,
    fingerprint: str | None = None,
) -> Transaction:
    return Transaction(
        row_index=row,
        posted_date=day,
        amount_cents=cents,
        direction=Direction.INFLOW if cents > 0 else Direction.OUTFLOW,
        description=description,
        memo=memo,
        merchant_key=merchant_key or description.upper(),
        channel=channel,
        counterparty=counterparty,
        account_type=account,
        fitid=fitid,
        fingerprint=fingerprint or f"fp-{row}-{description}-{cents}",
        is_pending=pending,
    )


Run = Callable[..., list[Decision]]


@pytest.fixture
def run(rules: RuleSet) -> Run:
    def _run(
        *txns: Transaction, memory: Mapping[str, Category] | None = None, **ctx: Any
    ) -> list[Decision]:
        context = BrainContext(rules=rules, memory=memory or {}, **ctx)
        return categorize(list(txns), context)

    return _run
