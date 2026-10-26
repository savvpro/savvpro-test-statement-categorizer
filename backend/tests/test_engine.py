"""The brain. Each test checks the status and the reason, not only the category."""

from app.categorizer.engine import AUTO, REVIEW

from .conftest import engine, past, txn, user


def test_known_developer_tool_is_decided():
    d = engine().decide(txn("POS GITHUB.COM SAN FRANCISCO", "-1120"))
    assert (d.status, d.category, d.rule_id) == (AUTO, "Software & Subscriptions", "SW-GITHUB")
    assert "GITHUB" in d.reason


def test_unknown_merchant_goes_to_review():
    d = engine().decide(txn("JOES CAFE 9921", "-800"))
    assert d.status == REVIEW and d.category is None
    assert d.reason.startswith("Unknown merchant")


def test_unknown_money_in_goes_to_review():
    d = engine().decide(txn("SOMEONE SENT MONEY", "5000"))
    assert d.status == REVIEW and "unknown source" in d.reason


def test_design_example_sq_reference_is_unknown():
    assert engine().decide(txn("SQ *48392", "-18.50", currency="USD")).status == REVIEW


def test_longer_pattern_beats_shorter_one():
    d = engine().decide(txn("AMAZON WEB SERVICES EMEA", "-30"))
    assert (d.status, d.category, d.rule_id) == (AUTO, "Cloud & Hosting", "CLOUD-AWS-LONG")
    d = engine().decide(txn("UBER EATS ORDER", "-22"))
    assert d.suggested_category == "Meals"  # not Travel from the shorter UBER rule


def test_equally_specific_rules_that_disagree_go_to_review():
    d = engine().decide(txn("CAREEM FOODPANDA COMBO", "-500"))
    assert d.status == REVIEW
    assert "Rules disagree" in d.reason and "TRAVEL-CAREEM" in d.reason and "FOOD-FOODPANDA" in d.reason


def test_stage_order_tax_before_bank_charges():
    d = engine().decide(txn("FED ON SMS ALERT CHARGES", "-32"))
    assert (d.category, d.rule_id) == ("Tax Deducted", "TAX-FED")


def test_clear_transfer_is_not_income_or_spending():
    d = engine().decide(txn("TRANSFER TO SAVINGS A/C", "-50000"))
    assert (d.status, d.category, d.txn_type) == (AUTO, "Transfer", "transfer")
    assert "isn't income or spending" in d.reason


def test_ambiguous_bank_transfer_is_reviewed_with_a_suggestion():
    d = engine().decide(txn("IBFT OUTWARD 0213", "-15000"))
    assert (d.status, d.suggested_category) == (REVIEW, "Transfer")


def test_cash_withdrawal_is_always_reviewed():
    d = engine().decide(txn("ATM CASH WITHDRAWAL F-7", "-10000"))
    assert d.status == REVIEW and "cash" in d.reason.lower()


def test_ambiguous_client_payment_is_reviewed():
    d = engine().decide(txn("CLIENT PAYMENT ACME LTD", "95000"))
    assert (d.status, d.suggested_category) == (REVIEW, "Business Income")


def test_home_remittance_could_be_family_money():
    d = engine().decide(txn("HOME REMITTANCE FROM ABROAD", "60000"))
    assert d.status == REVIEW and "family" in d.reason


def test_usually_business_depends_on_account_type():
    business = engine("business").decide(txn("NAYATEL INTERNET BILL", "-4999"))
    mixed = engine("mixed").decide(txn("NAYATEL INTERNET BILL", "-4999"))
    assert (business.status, business.category) == (AUTO, "Internet & Phone")
    assert (mixed.status, mixed.suggested_category) == (REVIEW, "Internet & Phone")


def test_sometimes_business_is_always_reviewed():
    d = engine("business").decide(txn("DARAZ ORDER 99812", "-12400"))
    assert (d.status, d.suggested_category) == (REVIEW, "Office & Equipment")


def test_clearly_personal_spending_is_decided_as_personal():
    d = engine().decide(txn("NETFLIX.COM", "-1100"))
    assert (d.status, d.category, d.txn_type) == (AUTO, "Personal", "personal")


def test_expense_rule_on_money_in_is_reviewed():
    d = engine().decide(txn("ADOBE CREATIVE CLOUD", "54.99", currency="USD"))
    assert d.status == REVIEW and "money coming in" in d.reason


def test_income_rule_on_money_out_is_reviewed():
    d = engine().decide(txn("UPWORK ESCROW", "-100", currency="USD"))
    assert d.status == REVIEW and "money going out" in d.reason


# --- refunds -------------------------------------------------------------------

def test_refund_links_to_the_one_matching_purchase():
    history = [past(7, "SW-GITHUB", "-1120", "2026-03-03")]
    d = engine(history=history).decide(txn("GITHUB.COM REFUND", "1120", when="2026-03-20"))
    assert (d.status, d.category, d.txn_type, d.linked_txn_id) == (AUTO, "Software & Subscriptions", "refund", 7)
    assert "instead of counting as income" in d.reason


def test_partial_refund_still_links():
    history = [past(7, "SW-FIGMA", "-45", "2026-04-04", currency="USD")]
    d = engine(history=history).decide(txn("REFUND FIGMA", "15", when="2026-04-14", currency="USD"))
    assert d.linked_txn_id == 7


def test_refund_with_no_matching_purchase_is_reviewed_and_not_income():
    d = engine().decide(txn("REFUND ADOBE", "54.99", currency="USD"))
    assert (d.status, d.category, d.txn_type) == (REVIEW, None, "refund")
    assert "won't count as income" in d.reason


def test_refund_with_several_possible_purchases_is_reviewed():
    history = [past(1, "SW-GITHUB", "-1120", "2026-03-03"), past(2, "SW-GITHUB", "-1120", "2026-02-03")]
    d = engine(history=history).decide(txn("GITHUB.COM REFUND", "1120", when="2026-03-20"))
    assert d.status == REVIEW and "2 earlier purchases" in d.reason


def test_equal_amount_alone_does_not_link_a_refund():
    history = [past(1, "SW-ADOBE", "-1120", "2026-03-03")]
    d = engine(history=history).decide(txn("GITHUB.COM REFUND", "1120", when="2026-03-20"))
    assert d.status == REVIEW and d.linked_txn_id is None


def test_refund_in_another_currency_or_too_old_does_not_link():
    history = [past(1, "SW-GITHUB", "-1120", "2026-03-03", currency="USD"),
               past(2, "SW-GITHUB", "-1120", "2025-10-01")]
    assert engine(history=history).decide(txn("GITHUB.COM REFUND", "1120", when="2026-03-20")).status == REVIEW


def test_refund_word_on_money_out_is_reviewed():
    d = engine().decide(txn("REFUND GITHUB.COM", "-1120"))
    assert d.status == REVIEW and "money went out" in d.reason


def test_reversal_of_bank_charges_reduces_bank_charges():
    history = [past(3, "FEE-SMS", "-200", "2026-03-08", category="Bank Charges")]
    d = engine(history=history).decide(txn("REVERSAL SMS ALERT CHARGES", "200", when="2026-03-12"))
    assert (d.status, d.category, d.txn_type) == (AUTO, "Bank Charges", "refund")


# --- user rules and flags ------------------------------------------------------

def test_user_rule_is_checked_before_built_in_stages():
    rules = [user(1, "IBFT FROM 0213XXXX", "Business Income")]
    d = engine(user_rules=rules).decide(txn("IBFT FROM 0213XXXX", "25000"))
    assert (d.status, d.category, d.rule_id) == (AUTO, "Business Income", "USER-1")
    assert d.reason.startswith("Your rule")


def test_two_user_rules_that_disagree_go_to_review():
    rules = [user(1, "JOES CAFE", "Meals"), user(2, "CAFE 9921", "Personal")]
    assert engine(user_rules=rules).decide(txn("JOES CAFE 9921", "-800")).status == REVIEW


def test_exact_and_starts_with_rules():
    rules = [user(1, "JOES CAFE", "Meals", match="exact"), user(2, "HASSAN", "Office & Equipment", match="starts_with")]
    e = engine(user_rules=rules)
    assert e.decide(txn("JOES CAFE", "-800")).category == "Meals"
    assert e.decide(txn("JOES CAFE 9921", "-800")).status == REVIEW
    assert e.decide(txn("HASSAN TRADERS 4471", "-800")).category == "Office & Equipment"


def test_flags_from_reading_the_file_hold_the_row_for_review():
    d = engine().decide(txn("POS GITHUB.COM", "-1120"), flags=["The running balance doesn't add up."])
    assert (d.status, d.category, d.suggested_category) == (REVIEW, None, "Software & Subscriptions")
    assert d.reason.startswith("The running balance") and "would have chosen" in d.reason
