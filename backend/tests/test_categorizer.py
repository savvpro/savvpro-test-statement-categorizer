from decimal import Decimal

from app.categorizer import categorize
from app.models import Transaction


def tx(desc, amount):
    return Transaction(row_number=1, description=desc, amount=Decimal(amount))


def test_software_subscription():
    r = categorize(tx("ADOBE CREATIVE CLOUD", "54.99"))
    assert r.category == "Software" and not r.needs_review


def test_paypal_prefix_still_matches():
    assert categorize(tx("PAYPAL *FIGMA", "15.00")).category == "Software"


def test_uber_trip_is_travel_but_uber_eats_is_meals():
    assert categorize(tx("UBER *TRIP HELP.UBER.COM", "23.40")).category == "Travel"
    assert categorize(tx("UBER EATS", "28.30")).category == "Meals"


def test_refund_is_not_income():
    r = categorize(tx("UBER *TRIP REFUND", "-23.40"))
    assert r.category == "Refund" and not r.needs_review


def test_card_payment_is_not_spending():
    assert categorize(tx("AUTOPAY PAYMENT THANK YOU", "-750.00")).category == "Transfer"


def test_transfer_to_savings_is_not_spending():
    assert categorize(tx("TRANSFER TO SAVINGS ****4417", "300.00")).category == "Transfer"


def test_cashback_credit():
    assert categorize(tx("CASHBACK REWARD CREDIT", "-12.40")).category == "Credit"


def test_fees_and_interest():
    assert categorize(tx("FOREIGN TRANSACTION FEE", "2.35")).category == "Fees & Interest"


def test_unknown_merchant_goes_to_review():
    r = categorize(tx("MYSTERY MERCHANT XJ29", "75.00"))
    assert r.needs_review and r.category == "Needs Review"


def test_joes_cafe_is_unknown_like_the_task_example():
    assert categorize(tx("JOES CAFE 9921", "12.50")).needs_review


def test_ambiguous_merchants_are_never_guessed():
    assert categorize(tx("AMZN Mktp US*2K4H81", "89.99")).needs_review
    assert categorize(tx("APPLE.COM/BILL", "1299.00")).needs_review
    assert categorize(tx("WALMART SUPERCENTER #1123", "64.20")).needs_review


def test_unknown_credit_goes_to_review():
    assert categorize(tx("DEPOSIT 8899", "-100")).needs_review


def test_invalid_row_goes_to_review_without_crashing():
    bad = Transaction(row_number=2, description="DROPBOX", errors=["amount is not a number"])
    r = categorize(bad)
    assert r.needs_review and r.confidence == 0.0


def test_short_keyword_needs_whole_word():
    assert categorize(tx("ZOOMER SHOP", "9.00")).needs_review


def test_user_correction_memory_wins():
    r = categorize(tx("JOES CAFE 9921", "12.50"), {"JOES CAFE": "Meals"})
    assert r.category == "Meals" and r.confidence == 1.0 and not r.needs_review


def test_refund_not_overridden_by_merchant_memory():
    r = categorize(
        tx("ADOBE REFUND", "-54.99"),
        {"ADOBE REFUND": "Software"},
    )
    assert r.category == "Refund"


def test_incoming_payment_not_overridden_by_memory():
    r = categorize(
        tx("AUTOPAY PAYMENT THANK YOU", "-750"),
        {"AUTOPAY PAYMENT": "Software"},
    )
    assert r.category == "Transfer"


def test_outgoing_refund_keyword_requires_review():
    r = categorize(tx("ADOBE REFUND ADJUSTMENT", "54.99"))
    assert r.needs_review
