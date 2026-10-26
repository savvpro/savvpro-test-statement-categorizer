from datetime import date
from decimal import Decimal

from app.categorizer import categorize, summarize
from app.models import RawTransaction
from app.normalize import merchant_key


def tx(description, amount, day=1):
    return RawTransaction(line=day + 1, date=date(2024, 3, day), description=description, amount=Decimal(str(amount)))


def one(description, amount):
    return categorize([tx(description, amount)])[0]


def test_known_merchants():
    assert one("ADOBE CREATIVE CLOUD", -54.99).category == "Software & Subscriptions"
    assert one("UBER *TRIP HELP.UBER.COM", -20).category == "Travel"
    assert one("DELTA AIR LINES 0062345", -600).category == "Travel"


def test_more_specific_rule_wins():
    assert one("UBER *EATS 8841", -30).category == "Meals & Entertainment"


def test_transfer_is_not_spending_or_income():
    out = one("TRANSFER TO SAVINGS", -500)
    back = one("CARD PAYMENT THANK YOU", 1200)
    assert (out.kind, back.kind) == ("transfer", "transfer")
    summary = summarize([out, back])
    assert summary.business_expenses == 0 and summary.income == 0
    assert summary.transfers_excluded == 1700


def test_unknown_merchant_goes_to_review():
    t = one("JOES CAFE 9921", -12.5)
    assert t.needs_review and t.category == "Needs Review" and t.kind == "review"
    assert t.suggested_category == "Meals & Entertainment"


def test_totally_unknown_has_no_suggestion():
    t = one("XQZ HOLDINGS 12", -9)
    assert t.needs_review and t.suggested_category is None


def test_ambiguous_merchants_are_asked_not_guessed():
    for name in ("AMAZON MKTPLACE PMTS", "PAYPAL *SOMESELLER", "ATM WITHDRAWAL"):
        assert one(name, -40).needs_review, name


def test_known_merchant_beats_paypal_prefix():
    assert one("PAYPAL *ADOBE", -20).category == "Software & Subscriptions"


def test_refund_reduces_category_and_is_not_income():
    rows = categorize([tx("ADOBE CREATIVE CLOUD", -54.99, 1), tx("ADOBE CREATIVE CLOUD REFUND", 54.99, 2)])
    assert rows[1].kind == "refund"
    summary = summarize(rows)
    assert summary.income == 0
    assert summary.business_expenses == 0


def test_partial_refund_nets_out():
    rows = categorize([tx("FIGMA", -100, 1), tx("FIGMA CREDIT", 40, 2)])
    assert summarize(rows).business_expenses == 60


def test_unknown_deposit_is_not_assumed_to_be_income():
    t = one("MYSTERY DEPOSIT", 300)
    assert t.needs_review and t.kind == "review"
    assert summarize([t]).income == 0


def test_client_payout_is_income():
    assert one("UPWORK ESCROW REL INVOICE 44", 2400).kind == "income"
    assert one("PAYONEER INC", 1850).category == "Income"


def test_income_keywords_do_not_count_when_money_goes_out():
    assert one("PAYONEER INC", -20).category != "Income"


def test_foreign_fee_is_a_fee():
    assert one("FOREIGN TRANSACTION FEE", -3.6).category == "Bank & Platform Fees"


def test_personal_spending_kept_separate():
    rows = categorize([tx("NETFLIX.COM", -15.49), tx("FIGMA", -10)])
    summary = summarize(rows)
    assert summary.personal_spending == Decimal("15.49")
    assert summary.business_expenses == 10


def test_duplicate_is_flagged_but_first_is_kept():
    rows = categorize([tx("FIGMA MONTHLY", -15, 7), tx("FIGMA MONTHLY", -15, 7), tx("FIGMA MONTHLY", -15, 8)])
    assert [r.needs_review for r in rows] == [False, True, False]
    assert "duplicate" in rows[1].reason.lower()


def test_large_meal_and_large_expense_need_review():
    assert one("UBER *EATS", -450).needs_review
    assert one("ADOBE CREATIVE CLOUD", -9000).needs_review


def test_user_override_wins_and_applies_to_same_merchant():
    rows = categorize(
        [tx("JOES CAFE 9921", -12.5, 1), tx("JOES CAFE 4410", -8, 2)],
        {merchant_key("JOES CAFE"): "Meals & Entertainment"},
    )
    assert all(r.category == "Meals & Entertainment" and r.confidence == 1.0 for r in rows)


def test_override_can_mark_transfer_and_ignores_invalid_category():
    rows = categorize([tx("JOES CAFE", -50)], {"JOES CAFE": "Transfer"})
    assert rows[0].kind == "transfer"
    rows = categorize([tx("JOES CAFE", -50)], {"JOES CAFE": "Not A Category"})
    assert rows[0].needs_review


def test_override_on_deposit_makes_it_income():
    rows = categorize([tx("MYSTERY DEPOSIT", 300)], {"MYSTERY DEPOSIT": "Income"})
    assert rows[0].kind == "income"


def test_whole_word_matching():
    assert one("PLATMAN SUPPLY", -10).category == "Needs Review"
    assert one("LAWS OF UX BOOK", -10).category != "Software & Subscriptions"


def test_review_total_in_summary():
    rows = categorize([tx("JOES CAFE", -12.5), tx("MYSTERY DEPOSIT", 300)])
    assert summarize(rows).needs_review_count == 2


def test_merchant_key_groups_store_numbers():
    assert merchant_key("SQ *JOES CAFE 9921 SEATTLE") == merchant_key("JOES CAFE 4410")
