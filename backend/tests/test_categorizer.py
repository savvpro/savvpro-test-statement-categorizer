from decimal import Decimal

import pytest
from app.categorizer import categorize
from app.models import Category


@pytest.mark.parametrize(
    "description,amount,transaction_type,category",
    [
        ("ADOBE CREATIVE CLOUD", "-59.99", "", Category.SOFTWARE),
        ("github copilot 123456", "-19", "", Category.SOFTWARE),
        ("AWS BILLING", "-84", "", Category.CLOUD),
        ("UBER *TRIP", "-18.50", "", Category.TRAVEL),
        ("MONTHLY ACCOUNT FEE", "-6.50", "", Category.FEES),
        ("NOTGITHUB COPILOT", "-19", "", Category.REVIEW),
        ("GITHUB COPILOT CONSULTING", "-19", "", Category.REVIEW),
        ("AWSOME SHOP", "-19", "", Category.REVIEW),
        ("AMAZON MARKETPLACE", "-79", "", Category.REVIEW),
        ("JOES CAFE 9921", "-12", "", Category.REVIEW),
        ("ADOBE CREATIVE CLOUD", "59.99", "", Category.REVIEW),
        ("MONEY RECEIVED", "300", "", Category.REVIEW),
        ("CLIENT PAYMENT NORTHSTAR INV 1042", "3200", "", Category.INCOME),
        ("NORTHSTAR INV 1042", "3200", "Client Payment", Category.INCOME),
        ("CLIENT PAYMENT NORTHSTAR", "-3200", "", Category.REVIEW),
        ("REFUND ADOBE", "59.99", "", Category.REFUND),
        ("ADOBE REFUND", "59.99", "", Category.REFUND),
        ("GITHUB COPILOT", "19", "Refund", Category.REFUND),
        ("REFUND ADOBE", "-59.99", "", Category.REVIEW),
        ("TRANSFER TO SAVINGS", "-600", "", Category.TRANSFER),
        ("TRANSFER FROM SAVINGS", "600", "", Category.TRANSFER),
        ("AWS BILLING", "-80", "Internal Transfer", Category.TRANSFER),
        ("CLIENT PAYMENT NORTHSTAR", "100", "Transfer", Category.INCOME),
        ("TRANSFER TO SAVINGS", "100", "Refund", Category.REVIEW),
        ("GITHUB COPILOT", "0", "Refund", Category.REVIEW),
        (
            "CLIENT PAYMENT NORTHSTAR NO REFUND",
            "1000",
            "Client Payment",
            Category.REVIEW,
        ),
        ("REFUND ADOBE", "4500", "Client Payment", Category.REVIEW),
        ("CLIENT PAYMENT NORTHSTAR REFUND", "1000", "", Category.REVIEW),
    ],
)
def test_conservative_classification_and_precedence(
    description, amount, transaction_type, category
):
    decision = categorize(description, Decimal(amount), transaction_type)
    assert decision.category == category
    assert decision.explanation


@pytest.mark.parametrize(
    "description,amount,transaction_type,category",
    [
        ("TRANSFER TO OWN SAVINGS ACCOUNT", "-50000", "Transfer", Category.TRANSFER),
        ("TRANSFER BETWEEN OWN ACCOUNTS", "-25000", "", Category.TRANSFER),
        ("INTERNAL TRANSFER TO SAVINGS", "-25000", "", Category.TRANSFER),
        ("TRANSFER FROM OWN SAVINGS", "10000", "", Category.TRANSFER),
        ("TRANSFER TO SUPPLIER", "-32000", "Transfer", Category.REVIEW),
        ("TRANSFER FROM SUPPLIER", "32000", "Transfer", Category.REVIEW),
        ("IBFT TO CONTRACTOR", "-18000", "IBFT", Category.REVIEW),
        ("RAAST PAYMENT RECEIVED", "12500", "Raast", Category.REVIEW),
        ("ATM CASH WITHDRAWAL", "-20000", "", Category.REVIEW),
        ("AWS BILLING", "-5000", "Transfer", Category.REVIEW),
        ("TRANSFER TO SAVINGS SUPPLIER", "-5000", "", Category.REVIEW),
        ("TRANSFER TO OWN SAVINGS ACCOUNT", "5000", "Refund", Category.REVIEW),
        ("REFUND ADOBE", "4500", "Transfer", Category.REFUND),
        ("CLIENT PAYMENT NORTHSTAR TECH INV 1042", "250000", "", Category.INCOME),
        ("NAYATEL INTERNET BILL", "-6500", "", Category.TELECOM),
        ("NAYATEL", "-6500", "", Category.REVIEW),
        ("DARAZ MARKETPLACE", "-7999", "", Category.REVIEW),
    ],
)
def test_local_payments_require_explicit_purpose(
    description, amount, transaction_type, category
):
    assert (
        categorize(description, Decimal(amount), transaction_type).category == category
    )
