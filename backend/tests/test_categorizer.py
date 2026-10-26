from decimal import Decimal as D
from pathlib import Path

from app.categorizer import (categorize, categorize_all, merchant_key,
                             summarize)
from app.parser import Transaction, parse_statement

SAMPLE = Path(__file__).parent.parent / "sample_data" / "fake_statement.csv"


# ---------- merchant key ----------
def test_merchant_key_removes_noise():
    assert merchant_key("JOES CAFE 9921") == "JOES CAFE"
    assert merchant_key("UBER *TRIP 8841") == "UBER TRIP"
    assert merchant_key("SQ *JOES COFFEE #12") == "JOES COFFEE"


# ---------- money out ----------
def test_known_merchant():
    r = categorize("ADOBE CREATIVE CLOUD", D("-54.99"))
    assert r.category == "Software & Subscriptions"
    assert r.confidence >= 0.75 and not r.needs_review


def test_unknown_goes_to_review():
    r = categorize("JOES CAFE 9921", D("-12.50"))
    assert r.needs_review and r.category == "Needs Review"


def test_transfer_is_not_spending():
    assert categorize("TRANSFER TO SAVINGS", D("-500")).category == "Not Spending"


def test_ambiguous_merchants_never_guessed():
    assert categorize("AMAZON MKTPLACE", D("-89")).needs_review
    assert categorize("PAYPAL *SOMEONE", D("-20")).needs_review
    assert categorize("SQ *JOES COFFEE", D("-6")).needs_review


def test_conflicting_keywords_go_to_review():
    r = categorize("UBER ADOBE", D("-5"))
    assert r.needs_review and len(r.candidates) == 2


def test_whole_word_matching():
    # RESTAURANT must not match inside RESTAURANTS
    assert categorize("RESTAURANTS DEPOT", D("-30")).needs_review
    assert categorize("THE RESTAURANT 22", D("-30")).category == "Meals (50%)"


def test_cash_withdrawal_needs_review():
    assert categorize("ATM WITHDRAWAL", D("-100")).needs_review


def test_zero_amount_needs_review():
    assert categorize("ADOBE", D("0")).needs_review


# ---------- money in ----------
def test_income_keyword():
    assert categorize("STRIPE PAYOUT", D("2400")).category == "Income"


def test_paypal_transfer_in_is_income_not_transfer():
    assert categorize("PAYPAL TRANSFER IN", D("300")).category == "Income"


def test_transfer_in_is_not_income():
    assert categorize("TRANSFER FROM SAVINGS", D("500")).category == "Not Spending"


def test_unexplained_credit_is_not_income():
    r = categorize("MYSTERY DEPOSIT", D("40"))
    assert r.needs_review


def test_refund_matches_earlier_charge():
    r = categorize("UBER REFUND 8841", D("23.40"), seen_charges={"UBER": "Travel"})
    assert r.category == "Refund: Travel" and r.confidence == 0.9


def test_refund_without_charge_but_one_keyword_match():
    r = categorize("UBER REFUND", D("10"))
    assert r.category == "Refund: Travel" and not r.needs_review


def test_refund_unknown_merchant_goes_to_review():
    assert categorize("JOES CAFE REFUND", D("10")).needs_review


def test_credit_from_known_merchant_without_refund_word_is_review():
    r = categorize("UBER 8841", D("10"), seen_charges={"UBER": "Travel"})
    assert r.needs_review


# ---------- user rules ----------
def test_user_rule_wins():
    key = merchant_key("JOES CAFE 9921")
    r = categorize("JOES CAFE 1234", D("-12"), {key: "Meals (50%)"})
    assert r.category == "Meals (50%)" and r.confidence == 1.0


# ---------- whole statement ----------
def _rows(user_rules=None):
    txns, _ = parse_statement(SAMPLE.read_bytes())
    return categorize_all(txns, user_rules)


def test_sample_statement_categories():
    cats = [r["category"] for r in _rows()]
    assert cats == [
        "Software & Subscriptions",   # ADOBE
        "Travel",                     # UBER *TRIP
        "Not Spending",               # TRANSFER TO SAVINGS
        "Needs Review",               # JOES CAFE
        "Needs Review",               # AMAZON
        "Income",                     # STRIPE PAYOUT
        "Refund: Travel",             # UBER REFUND (matched to the trip)
        "Software & Subscriptions",   # ADOBE again
    ]


def test_sample_summary_refund_offsets_travel():
    s = summarize(_rows())
    assert D(s["expenses"]["Software & Subscriptions"]) == D("109.98")
    assert D(s["expenses"]["Travel"]) == D("0")          # charge fully refunded
    assert D(s["income"]) == D("2400.00")                # refund NOT counted as income
    assert s["needs_review_count"] == 2
    assert D(s["needs_review_total"]) == D("-101.50")
    assert s["excluded_count"] == 1


def test_refund_dated_same_day_still_matches():
    txns = [Transaction(2, "2026-09-01", "UBER REFUND", D("5")),
            Transaction(3, "2026-09-01", "UBER *TRIP 1", D("-5"))]
    rows = categorize_all(txns)
    assert rows[0]["category"] == "Refund: Travel"


def test_same_word_two_categories_is_not_trusted_for_refunds():
    txns = [Transaction(2, "2026-09-01", "ZOOM VIDEO", D("-10")),
            Transaction(3, "2026-09-02", "ZOOM RESTAURANT", D("-20")),
            Transaction(4, "2026-09-03", "ZOOM REFUND", D("5"))]
    rows = categorize_all(txns)
    assert rows[2]["needs_review"]


def test_duplicate_flagged():
    t1 = Transaction(2, "2026-09-01", "ADOBE", D("-5"))
    t2 = Transaction(3, "2026-09-01", "ADOBE", D("-5"))
    rows = categorize_all([t1, t2])
    assert rows[0]["possible_duplicate"] is False
    assert rows[1]["possible_duplicate"] is True


def test_rows_keep_file_order():
    rows = _rows()
    assert [r["row"] for r in rows] == sorted(r["row"] for r in rows)