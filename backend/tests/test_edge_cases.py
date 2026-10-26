from datetime import date

from app.engine.brain import CategorizationBrain
from app.models.transaction import RawTransaction, TransactionType


def test_refund_is_not_income_and_links_to_expense():
    brain = CategorizationBrain()
    # Original expense debit
    tx1 = RawTransaction(
        id="tx_1",
        line_number=1,
        date=date(2024, 3, 5),
        description="AWS AMAZON WEB SERVICES",
        amount=120.00,
        transaction_type=TransactionType.DEBIT,
    )
    # Reversal credit a few days later
    tx2 = RawTransaction(
        id="tx_2",
        line_number=2,
        date=date(2024, 3, 8),
        description="AWS REFUND",
        amount=120.00,
        transaction_type=TransactionType.CREDIT,
    )
    results = brain.categorize_batch([tx1, tx2])
    assert len(results) == 2

    # AWS debit categorized as Cloud
    assert results[0].category == "Cloud & Infrastructure"

    # AWS refund credit categorized as Refunds & Reversals, linked to tx_1, NOT income!
    refund_res = results[1]
    assert refund_res.is_refund is True
    assert refund_res.category == "Refunds & Reversals"
    assert refund_res.refund_parent_id == "tx_1"
    assert "not taxable revenue" in refund_res.reason.lower()


def test_internal_transfers_and_credit_card_payments():
    brain = CategorizationBrain()
    t1 = RawTransaction(
        id="tx_1",
        line_number=1,
        date=date(2024, 3, 1),
        description="ONLINE TRANSFER TO SAVINGS ACCT 1234",
        amount=1000.00,
        transaction_type=TransactionType.DEBIT,
    )
    t2 = RawTransaction(
        id="tx_2",
        line_number=2,
        date=date(2024, 3, 2),
        description="AUTOPAY PAYMENT THANK YOU",
        amount=450.00,
        transaction_type=TransactionType.CREDIT,
    )
    results = brain.categorize_batch([t1, t2])

    assert results[0].is_transfer is True
    assert results[0].category == "Transfers & Card Payments"
    assert "non-spending" in results[0].reason.lower()

    assert results[1].is_transfer is True
    assert results[1].category == "Transfers & Card Payments"


def test_duplicate_transactions_detection():
    brain = CategorizationBrain()
    # Two identical charges on the same day for same amount and merchant
    t1 = RawTransaction(
        id="tx_1",
        line_number=1,
        date=date(2024, 3, 10),
        description="FIGMA SUBSCRIPTION",
        amount=15.00,
        transaction_type=TransactionType.DEBIT,
    )
    t2 = RawTransaction(
        id="tx_2",
        line_number=2,
        date=date(2024, 3, 10),
        description="FIGMA SUBSCRIPTION",
        amount=15.00,
        transaction_type=TransactionType.DEBIT,
    )
    results = brain.categorize_batch([t1, t2])
    assert not results[0].is_duplicate
    assert results[1].is_duplicate is True
    assert "duplicate" in results[1].reason.lower()


def test_personal_vs_business_ambiguity():
    brain = CategorizationBrain()
    retailers = [
        "AMAZON.COM*2K489 BILL",
        "TARGET STORE #104",
        "COSTCO WHOLESALE",
        "STARBUCKS STORE 2940",
    ]
    for r in retailers:
        tx = RawTransaction(
            id="tx_1",
            line_number=1,
            date=date(2024, 3, 1),
            description=r,
            amount=65.00,
            transaction_type=TransactionType.DEBIT,
        )
        res = brain.categorize_batch([tx])[0]
        assert res.category == "Needs Review"
        assert res.needs_review is True
        assert res.is_personal_ambiguous is True
        assert "personal vs business" in res.reason.lower()


def test_foreign_currency_and_merchant_fees():
    brain = CategorizationBrain()
    tx = RawTransaction(
        id="tx_1",
        line_number=1,
        date=date(2024, 3, 1),
        description="FOREIGN TRANSACTION FEE - EUR 140.00",
        amount=4.20,
        transaction_type=TransactionType.DEBIT,
    )
    res = brain.categorize_batch([tx])[0]
    assert res.category == "Bank & Merchant Fees"
    assert res.confidence >= 0.95
