"""
Unit tests for transaction cash-flow direction analyzer.
"""

import pytest
from app.brain.direction import analyze_direction_and_type
from app.models.transaction import TransactionDirection


def test_direction_internal_transfer():
    direction, amount, reason = analyze_direction_and_type("TRANSFER TO SAVINGS", "TRANSFER TO SAVINGS", -500.0)
    assert direction == TransactionDirection.TRANSFER
    assert amount == 500.0


def test_direction_automatic_payment():
    direction, amount, reason = analyze_direction_and_type("AUTOMATIC PAYMENT - THANK YOU", "PAYMENT", -2500.0)
    assert direction == TransactionDirection.TRANSFER
    assert amount == 2500.0


def test_direction_credit_card_payment():
    direction, amount, reason = analyze_direction_and_type("CREDIT CARD PAYMENT CHASE", "CHASE", -1000.0)
    assert direction == TransactionDirection.TRANSFER
    assert amount == 1000.0


def test_direction_refund_by_keyword():
    direction, amount, reason = analyze_direction_and_type("REFUND AMAZON MKTP", "AMAZON", 89.99)
    assert direction == TransactionDirection.REFUND
    assert amount == 89.99


def test_direction_return_credit():
    direction, amount, reason = analyze_direction_and_type("RETURN CREDIT BEST BUY", "BEST BUY", 79.99)
    assert direction == TransactionDirection.REFUND
    assert amount == 79.99


def test_direction_stripe_revenue_inflow():
    direction, amount, reason = analyze_direction_and_type("STRIPE PAYOUT", "STRIPE PAYOUT", 8500.0)
    assert direction == TransactionDirection.INFLOW
    assert amount == 8500.0


def test_direction_upwork_revenue_inflow():
    direction, amount, reason = analyze_direction_and_type("UPWORK DIRECT DEPOSIT", "UPWORK", 3200.0)
    assert direction == TransactionDirection.INFLOW
    assert amount == 3200.0


def test_direction_inflow_from_expense_vendor_is_refund():
    # If Amazon deposits money into bank, it's a refund/credit, not taxable income
    direction, amount, reason = analyze_direction_and_type("AMAZON.COM WA", "AMAZON", 89.99)
    assert direction == TransactionDirection.REFUND
    assert amount == 89.99


def test_direction_standard_expense_outflow():
    direction, amount, reason = analyze_direction_and_type("GITHUB INC", "GITHUB", -25.0)
    assert direction == TransactionDirection.OUTFLOW
    assert amount == 25.0


def test_direction_credit_card_statement_mode():
    # In credit card statements: positive is purchase, negative is card payoff
    dir_charge, amt_charge, _ = analyze_direction_and_type("AWS CLOUD", "AWS", 150.0, is_credit_statement=True)
    assert dir_charge == TransactionDirection.OUTFLOW

    dir_pay, amt_pay, _ = analyze_direction_and_type("AUTOPAY PAYMENT THANK YOU", "AUTOPAY", -500.0, is_credit_statement=True)
    assert dir_pay == TransactionDirection.TRANSFER
