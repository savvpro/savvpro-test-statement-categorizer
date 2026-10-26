from datetime import date
from decimal import Decimal

import pytest

from app.brain.classifier import classify
from app.brain.models import UserRule
from app.brain.rules import RuleSet
from app.core.domain import AccountType
from app.ingest.models import ParsedRow


def make_row(description: str, amount: str, account_type: AccountType = "card") -> ParsedRow:
    return ParsedRow(
        row_number=1,
        date=date(2026, 9, 1),
        raw_description=description,
        amount=Decimal(amount),
        currency="PKR",
        account_type=account_type,
    )


def r(rule_id: str, contains: str, category: str, **extra) -> dict:
    return {
        "id": rule_id,
        "match": {"contains": contains},
        "category": category,
        "reason": f"rule {rule_id}",
        **extra,
    }


def ruleset(**sections: list[dict]) -> RuleSet:
    return RuleSet.model_validate(sections)


# ---------- stage order ----------


def test_structural_beats_merchant() -> None:
    rules = ruleset(
        structural=[r("fee", "FOREIGN TXN FEE", "Bank Fees", kind="fee")],
        merchants=[r("aws", "AWS", "Hosting & Cloud")],
    )
    d = classify(make_row("FOREIGN TXN FEE AWS EMEA", "-376"), rules=rules)
    assert (d.rule_id, d.category, d.kind) == ("fee", "Bank Fees", "fee")


def test_merchant_beats_review() -> None:
    rules = ruleset(
        merchants=[r("aws", "AWS", "Hosting & Cloud")],
        review=[r("amazon", "AMAZON", "Needs Review")],
    )
    d = classify(make_row("AWS EMEA AWS.AMAZON.CO LU", "-38.42"), rules=rules)
    assert (d.rule_id, d.category, d.needs_review) == ("aws", "Hosting & Cloud", False)


def test_review_beats_keywords() -> None:
    rules = ruleset(
        review=[r("daraz", "DARAZ", "Needs Review")],
        keywords=[r("kw_store", "STORE", "Office Supplies", confidence=0.9)],
    )
    d = classify(make_row("DARAZ STORE KARACHI", "-100"), rules=rules)
    assert (d.rule_id, d.category, d.needs_review) == ("daraz", "Needs Review", True)


def test_first_match_in_a_section_wins() -> None:
    rules = ruleset(merchants=[r("a", "UBER EATS", "Meals"), r("b", "UBER", "Travel")])
    assert classify(make_row("UBER EATS LAHORE", "-1450"), rules=rules).rule_id == "a"
    assert classify(make_row("UBER TRIP", "-850"), rules=rules).rule_id == "b"


def test_rules_see_normalized_text() -> None:
    rules = ruleset(merchants=[{**r("joes", "x", "Meals"), "match": {"starts_with": "JOES"}}])
    d = classify(make_row("sq *joes  cafe 9921", "-1850"), rules=rules)
    assert d.rule_id == "joes"


# ---------- review section ----------


def test_review_rule_sets_needs_review_with_its_reason() -> None:
    rules = ruleset(review=[r("amazon", "AMAZON", "Needs Review")])
    d = classify(make_row("AMAZON.COM*RT4KX9", "-89.99"), rules=rules)
    assert d.category == "Needs Review" and d.needs_review is True
    assert d.reason == "rule amazon" and d.suggested_category is None


def test_review_rule_keeps_suggestion_and_explicit_kind() -> None:
    rules = ruleset(review=[r("atm", "ATM CASH", "Personal", kind="transfer")])
    d = classify(make_row("ATM CASH WDL F-7", "-20000", "bank"), rules=rules)
    assert (d.category, d.kind, d.suggested_category) == ("Needs Review", "transfer", "Personal")


# ---------- keywords ----------


def test_single_keyword_category_wins() -> None:
    rules = ruleset(keywords=[r("kw", "HOSTING", "Hosting & Cloud", confidence=0.85)])
    d = classify(make_row("SKYLINE HOSTING SVCS KARACHI", "-4500"), rules=rules)
    assert (d.category, d.needs_review, d.rule_id) == ("Hosting & Cloud", False, "kw")


def test_two_keyword_rules_same_category_do_not_conflict() -> None:
    rules = ruleset(
        keywords=[
            r("k1", "CLOUD", "Hosting & Cloud", confidence=0.85),
            r("k2", "HOSTING", "Hosting & Cloud", confidence=0.9),
        ]
    )
    d = classify(make_row("CLOUD HOSTING CO", "-10"), rules=rules)
    assert d.category == "Hosting & Cloud" and d.rule_id == "k2"  # the more confident rule


def test_keywords_from_different_categories_conflict() -> None:
    rules = ruleset(
        keywords=[
            r("kw_cafe", "CAFE", "Meals", confidence=0.9),
            r("kw_hosting", "HOSTING", "Hosting & Cloud", confidence=0.9),
        ]
    )
    d = classify(make_row("CAFE HOSTING", "-10"), rules=rules)
    assert d.category == "Needs Review" and d.needs_review is True
    assert d.reason.startswith("conflicting rules:")
    assert "kw_cafe (Meals)" in d.reason and "kw_hosting (Hosting & Cloud)" in d.reason
    assert d.suggested_category is None


# ---------- threshold ----------


@pytest.mark.parametrize(
    ("confidence", "trusted"),
    [(0.79, False), (0.8, True), (0.81, True), (0.95, True), (0.0, False)],
)
def test_threshold(confidence: float, trusted: bool) -> None:
    rules = ruleset(merchants=[r("m", "ACME", "Software & Subscriptions", confidence=confidence)])
    d = classify(make_row("ACME LTD", "-10"), rules=rules)
    assert d.needs_review is (not trusted)
    if trusted:
        assert d.category == "Software & Subscriptions" and d.suggested_category is None
    else:
        assert d.category == "Needs Review"
        assert d.suggested_category == "Software & Subscriptions"
        assert "low confidence" in d.reason


def test_keyword_default_confidence_is_below_the_threshold() -> None:
    rules = ruleset(keywords=[r("kw", "CAFE", "Meals")])
    d = classify(make_row("BLUE BIRD CAFE", "-2200"), rules=rules)
    assert (d.category, d.needs_review, d.suggested_category) == ("Needs Review", True, "Meals")
    assert d.confidence == 0.75


# ---------- direction fallback ----------


def test_card_money_in_with_no_rule_is_a_refund() -> None:
    d = classify(make_row("SOME SHOP", "500"), rules=ruleset())
    assert (d.category, d.kind, d.confidence, d.needs_review) == ("Refund", "refund", 0.85, False)
    assert d.reason == "money back from a merchant on a card"


@pytest.mark.parametrize(
    ("amount", "account_type", "kind"),
    [("-500", "card", "expense"), ("500", "bank", "income"), ("-500", "bank", "expense")],
)
def test_other_unmatched_rows_go_to_review(amount: str, account_type: AccountType, kind) -> None:
    d = classify(make_row("SOME SHOP", amount, account_type), rules=ruleset())
    assert (d.category, d.kind, d.needs_review) == ("Needs Review", kind, True)
    assert d.reason == "no rule matched" and d.rule_id is None


def test_fallback_is_not_used_when_a_rule_matched() -> None:
    rules = ruleset(merchants=[r("adobe", "ADOBE", "Software & Subscriptions")])
    d = classify(make_row("ADOBE CREATIVE CLOUD", "59.99"), rules=rules)
    # a rule with no direction filter also matches the refund, as income: use direction: out
    assert d.category == "Software & Subscriptions" and d.kind == "income"


def test_direction_filter_lets_a_refund_fall_through_to_the_fallback() -> None:
    rules = ruleset(merchants=[r("adobe", "ADOBE", "Software & Subscriptions", direction="out")])
    charge = classify(make_row("ADOBE CREATIVE CLOUD", "-59.99"), rules=rules)
    refund = classify(make_row("ADOBE CREATIVE CLOUD", "59.99"), rules=rules)
    assert charge.category == "Software & Subscriptions"
    assert (refund.category, refund.kind) == ("Refund", "refund")


# ---------- filters ----------


def test_account_type_filter() -> None:
    rules = ruleset(
        structural=[r("pay", "PAYMENT", "Transfer", kind="transfer", account_type="card")]
    )
    assert classify(make_row("PAYMENT", "-1", "card"), rules=rules).rule_id == "pay"
    assert classify(make_row("PAYMENT", "-1", "bank"), rules=rules).rule_id is None


def test_direction_filter() -> None:
    rules = ruleset(
        structural=[r("pay", "PAYMENT", "Transfer", kind="transfer", direction="in")]
    )
    assert classify(make_row("PAYMENT", "10", "bank"), rules=rules).rule_id == "pay"
    assert classify(make_row("PAYMENT", "-10", "bank"), rules=rules).rule_id is None


# ---------- kind ----------


@pytest.mark.parametrize(("amount", "kind"), [("-10", "expense"), ("10", "income")])
def test_kind_derived_from_sign(amount: str, kind: str) -> None:
    rules = ruleset(merchants=[r("m", "ACME", "Office Supplies")])
    assert classify(make_row("ACME", amount, "bank"), rules=rules).kind == kind


def test_rule_kind_overrides_sign() -> None:
    rules = ruleset(merchants=[r("m", "ACME", "Bank Fees", kind="fee")])
    assert classify(make_row("ACME", "-10"), rules=rules).kind == "fee"


def test_review_and_threshold_rows_still_get_a_kind_from_the_sign() -> None:
    rules = ruleset(
        review=[r("p2p", "RAAST", "Needs Review")],
        keywords=[r("kw", "CAFE", "Meals")],
    )
    assert classify(make_row("RAAST P2P FROM X", "15000", "bank"), rules=rules).kind == "income"
    assert classify(make_row("BLUE BIRD CAFE", "-2200"), rules=rules).kind == "expense"


# ---------- user rules ----------


def test_user_rule_wins_over_every_stage() -> None:
    rules = ruleset(
        structural=[r("s", "JOES", "Bank Fees", kind="fee")],
        merchants=[r("m", "JOES", "Travel")],
        review=[r("v", "JOES", "Needs Review")],
    )
    user = [UserRule(merchant_key="JOES CAFE ISLAMABAD", category="Meals")]
    d = classify(make_row("SQ *JOES CAFE 9921 ISLAMABAD", "-1850"), user, rules)
    assert (d.category, d.kind, d.confidence, d.needs_review) == ("Meals", "expense", 1.0, False)
    assert d.rule_id == "user:JOES CAFE ISLAMABAD"


def test_user_rule_matches_across_store_numbers_and_case() -> None:
    user = [UserRule(merchant_key="JOES CAFE ISLAMABAD", category="Meals")]
    d = classify(make_row("sq *joes cafe 1002 islamabad", "-900"), user, ruleset())
    assert d.category == "Meals"


def test_user_rule_needs_an_exact_key() -> None:
    user = [UserRule(merchant_key="JOES CAFE", category="Meals")]
    d = classify(make_row("SQ *JOES CAFE 9921 ISLAMABAD", "-1850"), user, ruleset())
    assert d.category == "Needs Review"


def test_user_rule_explicit_kind_and_sign_kind() -> None:
    user = [UserRule(merchant_key="ACME", category="Income", kind="income")]
    assert classify(make_row("ACME 12", "100", "bank"), user, ruleset()).kind == "income"
    plain = [UserRule(merchant_key="ACME", category="Meals")]
    assert classify(make_row("ACME 12", "-100", "bank"), plain, ruleset()).kind == "expense"


def test_user_rule_cannot_match_an_empty_key() -> None:
    with pytest.raises(ValueError):
        UserRule(merchant_key="", category="Meals")
    d = classify(make_row("12345", "-5"), [UserRule(merchant_key="X", category="Meals")], ruleset())
    assert d.category == "Needs Review"


# ---------- misc ----------


def test_zero_amount_goes_to_review() -> None:
    d = classify(make_row("ADOBE", "0.00"), rules=ruleset(merchants=[r("a", "ADOBE", "Travel")]))
    assert d.needs_review is True and d.category == "Needs Review"


def test_every_decision_has_a_reason() -> None:
    rules = ruleset(merchants=[r("a", "ACME", "Travel")])
    for desc, amount in [("ACME", "-1"), ("NOPE", "-1"), ("NOPE", "1"), ("ACME", "0")]:
        assert classify(make_row(desc, amount), rules=rules).reason


def test_classify_with_shipped_rules_runs() -> None:
    d = classify(make_row("ADOBE CREATIVE CLOUD SAN JOSE CA", "-59.99"))
    assert d.category == "Software & Subscriptions" and d.rule_id == "adobe"


# ---------- shipped rules: regression tests for fixed rules.yaml problems ----------


def test_card_credit_from_upwork_is_not_income() -> None:
    d = classify(make_row("UPWORK HOURLY PAYMENT", "100", "card"))
    assert d.category != "Income" and d.kind != "income"
    assert (d.category, d.kind, d.rule_id) == ("Refund", "refund", "card_money_in")
    # the same words on a bank statement are still client income
    assert classify(make_row("UPWORK ESCROW INC", "100", "bank")).category == "Income"


def test_bare_rev_does_not_make_a_credit_a_reversal() -> None:
    d = classify(make_row("REV CHARGE ADJ", "100", "bank"))
    assert d.rule_id != "reversal" and d.category != "Refund"
    # real reversals are still caught
    assert classify(make_row("REVERSAL PTCL BILL PAYMENT", "4299", "bank")).rule_id == "reversal"


def test_railway_alone_is_not_hosting() -> None:
    d = classify(make_row("PAKISTAN RAILWAY TICKET", "-1500", "card"))
    assert d.category != "Hosting & Cloud" and d.rule_id != "cloud_providers"
    # the hosting company is still recognised
    assert classify(make_row("RAILWAY.APP", "-5", "card")).category == "Hosting & Cloud"
