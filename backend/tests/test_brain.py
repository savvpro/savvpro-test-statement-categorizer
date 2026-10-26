from datetime import date
from decimal import Decimal

import pytest

from app.brain import Brain, normalise_merchant
from app.models import Category, Kind, RawTransaction


def tx(desc, amount, kind=Kind.DEBIT, day=1, row=1):
    return RawTransaction(row, date(2026, 9, day), desc, Decimal(str(amount)), kind)


def run(*txs, brain=None):
    return {raw.description: d for raw, _, d in (brain or Brain()).categorise(list(txs))}


@pytest.mark.parametrize("desc,expected", [
    ("ADOBE *CREATIVE CLOUD 800-833", Category.SOFTWARE),
    ("UBER *TRIP HELP.UBER.COM", Category.TRAVEL),
    ("GOOGLE *ADS 123456", Category.ADVERTISING),
    ("ANNUAL FEE", Category.BANK_FEES),
    ("NETFLIX.COM", Category.PERSONAL),
])
def test_known_merchants(desc, expected):
    assert run(tx(desc, 10))[desc].category == expected


def test_unknown_merchant_goes_to_review():
    d = run(tx("JOES CAFE 9921", 12.8))["JOES CAFE 9921"]
    assert d.category == Category.NEEDS_REVIEW


def test_transfer_and_card_payment_are_not_spending():
    out = run(tx("TRANSFER TO SAVINGS", 500), tx("PAYMENT THANK YOU", 1500, Kind.CREDIT))
    assert out["TRANSFER TO SAVINGS"].category == Category.TRANSFER
    assert out["PAYMENT THANK YOU"].category == Category.CARD_PAYMENT


def test_refund_is_linked_to_original_category_not_income():
    out = run(tx("STAPLES #0421", 42, day=1), tx("STAPLES REFUND #0421", 12, Kind.CREDIT, day=5, row=2))
    refund = out["STAPLES REFUND #0421"]
    assert refund.is_refund and refund.category == Category.OFFICE


def test_refund_without_known_purchase_needs_review():
    d = run(tx("RFND MYSTERY SHOP", 20, Kind.CREDIT))["RFND MYSTERY SHOP"]
    assert d.is_refund and d.category == Category.NEEDS_REVIEW


def test_client_income_vs_p2p_credit():
    out = run(tx("STRIPE PAYOUT INV-1042", 1800, Kind.CREDIT), tx("ZELLE FROM SAM", 250, Kind.CREDIT, row=2))
    assert out["STRIPE PAYOUT INV-1042"].category == Category.CLIENT_INCOME
    assert out["ZELLE FROM SAM"].category == Category.NEEDS_REVIEW


def test_mixed_use_store_is_never_auto_filed():
    assert run(tx("AMAZON MKTPLACE PMTS", 90))["AMAZON MKTPLACE PMTS"].category == Category.NEEDS_REVIEW


def test_duplicate_is_flagged():
    out = Brain().categorise([tx("VERIZON WIRELESS", 75, row=1), tx("VERIZON WIRELESS", 75, row=2)])
    assert out[1][2].category == Category.NEEDS_REVIEW
    assert any(f.startswith("possible_duplicate") for f in out[1][2].flags)


def test_large_purchase_needs_confirmation():
    d = run(tx("APPLE STORE #R102", 2499))["APPLE STORE #R102"]
    assert d.category == Category.NEEDS_REVIEW and "large_amount" in d.flags


def test_brain_learns_from_user():
    brain = Brain()
    brain.learn(normalise_merchant("JOES CAFE 9921"), Category.MEALS)
    assert run(tx("JOES CAFE 1234", 9), brain=brain)["JOES CAFE 1234"].category == Category.MEALS


def test_normalise_merchant_strips_noise():
    assert normalise_merchant("POS PURCHASE SQ *BLUE BOTTLE #123 08/14 CA 94105") == "blue bottle"
