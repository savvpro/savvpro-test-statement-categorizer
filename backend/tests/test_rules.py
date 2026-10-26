import pytest

from app.engine import MATCHERS, categorize
from app.parser import parse_csv
from app.rules import CATEGORIES, RULES
from app.schemas import NEEDS_REVIEW, REVIEW_THRESHOLD, Transaction


def one(description: str, amount: str = "-100") -> Transaction:
    debit, credit = ("", amount[1:]) if amount.startswith("+") else (amount.lstrip("-"), "")
    tx = parse_csv(
        f"Date,Description,Debit,Credit,Balance\n01-09-2026,{description},{debit},{credit},0\n"
    )
    tx = tx.transactions[0]
    categorize(tx)
    return tx


def test_matchers():
    assert MATCHERS["exact"]("A B", "A B") and not MATCHERS["exact"]("A", "A B")
    assert MATCHERS["keyword"]("AWS", "AWS EMEA") and not MATCHERS["keyword"]("AWS", "LAWSON")
    assert MATCHERS["regex"](r"^WHT\b", "WHT ON CASH WDL")


def test_every_rule_uses_a_known_category_and_valid_confidence():
    assert all(rule.category in CATEGORIES and 0 <= rule.confidence <= 1 for rule in RULES)


@pytest.mark.parametrize(
    ("description", "amount", "category"),
    [
        ("GITHUB.COM SAN FRANCISCO USD 4.00", "-1120", "Software & Tools"),
        ("CHECKOUT.COM*FIGMA USD 15.00", "-4200", "Software & Tools"),
        ("OPENAI *CHATGPT SUBSCR USD 20.00", "-5600", "Software & Tools"),
        ("LESCO ONLINE BILL PAY 1234567890", "-18420", "Utilities"),
        ("NAYATEL BROADBAND ACCT 55123", "-6500", "Internet & Phone"),
        ("JAZZ MOBILE BUNDLE 0300****412", "-1500", "Internet & Phone"),
        ("RENT COWORKING - OFFICE HUB GULBERG LHR", "-35000", "Rent/Office"),
        ("CAREEM *TRIP LHR", "-890", "Travel & Transport"),
        ("PSO FUEL STATION DHA", "-8000", "Travel & Transport"),
        ("NETFLIX.COM USD 9.99", "-2800", "Entertainment"),
        ("FOODPANDA*ORDER 4471920", "-1840", "Food"),
        ("IMTIAZ SUPER MARKET DHA PH5", "-7620", "Groceries"),
        ("DARAZ.PK ORDER 7782316", "-14500", "Shopping"),
        ("MEDICARE PHARMACY GULBERG", "-1380", "Health"),
        ("COURSERA.ORG USD 49.00", "-13720", "Education"),
        ("FBR ADVANCE TAX PMT CPR 2609001452", "-45000", "Taxes"),
        ("ATM CASH WDL GULBERG BRANCH", "-20000", "Cash Withdrawal"),
        ("PAYONEER INC FUNDS TRF REF 88213", "+385000", "Income"),
    ],
)
def test_known_merchants(description, amount, category):
    tx = one(description, amount)
    assert tx.category == category
    assert tx.confidence >= REVIEW_THRESHOLD
    assert not tx.needs_review
    assert tx.reason


@pytest.mark.parametrize(
    "description",
    ["WHT ON CASH WDL", "FED ON BANK CHARGES", "SMS ALERT CHARGES SEP", "ANNUAL DEBIT CARD FEE"],
)
def test_bank_fees_beat_cash_withdrawal(description):
    assert one(description).category == "Bank Fees"


def test_lowercase_double_spaced_still_matches():
    assert one("payoneer  inc funds trf ref 88954", "+120000").category == "Income"
    assert one("kfc  dha raya 0112").category == "Food"


def test_direction_hint_payoneer_debit_is_not_income():
    assert one("PAYONEER INC FUNDS TRF REF 88213", "-100").category == NEEDS_REVIEW


@pytest.mark.parametrize(
    ("description", "amount"),
    [
        ("AMZN MKTP US*2K4LP8 USD 34.99", "-9790"),
        ("M/S AL-NOOR TRADERS PVT LTD", "-32000"),
        ("RAAST P2P TO ALI RAZA 0333****918", "-5000"),
        ("RAAST P2P FROM USMAN TARIQ 0321****554", "+25000"),
        ("JAZZCASH MOBILE ACCOUNT TOPUP", "-10000"),
        ("LIBERTY BOOKS GULBERG", "-3450"),
    ],
)
def test_ambiguous_rows_need_review(description, amount):
    tx = one(description, amount)
    assert tx.category == NEEDS_REVIEW and tx.needs_review


def test_unknown_merchant_is_never_guessed():
    tx = one("ZXQ UNKNOWN SHOP 77")
    assert tx.category == NEEDS_REVIEW and tx.confidence == 0
    assert "unknown merchant" in tx.reason


def test_unknown_usd_merchant_keeps_suggestion_but_goes_to_review():
    tx = one("SOMESAAS.IO USD 10.00")
    assert tx.category == NEEDS_REVIEW
    assert "suggested Software & Tools" in tx.reason


def test_unknown_credit_is_not_assumed_income():
    assert one("MYSTERY DEPOSIT 123", "+5000").category == NEEDS_REVIEW


def test_threshold_boundary():
    tx = one("ZXQ UNKNOWN SHOP 77")
    tx.assign("Food", REVIEW_THRESHOLD, "at threshold")
    assert tx.category == "Food" and not tx.needs_review
    tx.assign("Food", REVIEW_THRESHOLD - 0.01, "just under")
    assert tx.category == NEEDS_REVIEW and tx.needs_review
    assert "suggested Food" in tx.reason
