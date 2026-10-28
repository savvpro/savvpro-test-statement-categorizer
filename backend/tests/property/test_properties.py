"""Property tests (hypothesis): invariants that must hold for arbitrary input."""

from dataclasses import replace
from datetime import date
from decimal import Decimal

from hypothesis import given, settings
from hypothesis import strategies as st

from app.brain.context import BrainContext
from app.brain.engine import categorize
from app.brain.rules import DEFAULT_RULES_DIR, load_ruleset
from app.domain.enums import NON_BLOCKING_FLAGS, AccountType, Direction, Status
from app.domain.models import Transaction
from app.ingest.amounts import format_cents, parse_amount, to_cents
from app.normalize.merchant import clean_description
from app.normalize.normalizer import make_fingerprint

CTX = BrainContext(rules=load_ruleset(DEFAULT_RULES_DIR))
text = st.text(max_size=300)


@given(st.integers(min_value=-(10**11), max_value=10**11))
def test_amount_format_parse_round_trip(cents: int) -> None:
    assert to_cents(parse_amount(format_cents(cents))) == cents
    assert to_cents(Decimal(format_cents(cents))) == cents


@given(text)
def test_merchant_key_never_empty_bounded_and_idempotent(raw: str) -> None:
    key, _, _ = clean_description(raw)
    assert key
    assert len(key) <= 128
    assert clean_description(key)[0] == key


@st.composite
def transactions(draw: st.DrawFn) -> Transaction:
    desc = draw(text)
    cents = draw(st.integers(min_value=-(10**9), max_value=10**9).filter(lambda c: c != 0))
    posted = draw(st.dates(min_value=date(2000, 1, 1), max_value=date(2035, 12, 31)))
    acct = draw(st.sampled_from(list(AccountType)))
    key, channel, cp = clean_description(desc)
    return Transaction(
        row_index=1,
        posted_date=posted,
        amount_cents=cents,
        direction=Direction.INFLOW if cents > 0 else Direction.OUTFLOW,
        description=desc,
        memo=draw(st.none() | text),
        merchant_key=key,
        channel=channel,
        counterparty=cp,
        account_type=acct,
        fitid=None,
        fingerprint=make_fingerprint(acct, posted, cents, key, 0),
        is_pending=draw(st.booleans()),
    )


@settings(max_examples=200, deadline=None)
@given(st.lists(transactions(), min_size=1, max_size=4))
def test_brain_never_crashes_and_auto_is_safe(txns: list[Transaction]) -> None:
    txns = [replace(t, row_index=i) for i, t in enumerate(txns, 1)]
    decisions = categorize(txns, CTX)
    assert len(decisions) == len(txns)
    for d in decisions:
        if d.status is Status.AUTO:
            assert d.category is not None
            assert not (d.flags - NON_BLOCKING_FLAGS)
