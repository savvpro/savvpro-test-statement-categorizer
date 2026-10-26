import pytest

from app.brain.engine import DEFAULT_THRESHOLDS, Thresholds, aggregate, direction_allows
from app.brain.models import AccountType, Candidate, SignalSource, TxnStatus
from app.brain.taxonomy import load_taxonomy
from tests.brain.helpers import decide, one

CARD = AccountType.credit_card


def cand(category: str, score: float, source: SignalSource) -> Candidate:
    return Candidate(category, score, f"{source.value} says {category}", source)


def test_known_merchant_is_auto() -> None:
    d = one("ADOBE CREATIVE CLOUD", "-59.99", account=CARD)

    assert d.status is TxnStatus.auto
    assert d.category_id == "software_subscriptions"
    assert d.rule_id == "merchant:ADOBE"
    assert d.merchant_key == "ADOBE CREATIVE CLOUD"
    assert "known merchant 'ADOBE'" in d.reasons


def test_no_match_goes_to_review() -> None:
    d = one("ZYLOPHANE STUDIOS 4471", "-80.00")

    assert d.status is TxnStatus.needs_review
    assert d.category_id == "needs_review"
    assert d.suggested_category_id is None
    assert d.reasons[0].startswith("no match")


def test_keyword_alone_is_low_confidence() -> None:
    d = one("SQ *MARLOW BAKERY", "-12.50", account=CARD)

    assert d.status is TxnStatus.needs_review
    assert d.suggested_category_id == "meals"
    assert d.reasons[0] == "low confidence: best guess meals (keyword)"


def test_fuzzy_near_miss_suggests_only() -> None:
    d = one("ADOBEE", "-10.00", account=CARD)

    assert d.status is TxnStatus.needs_review
    assert d.suggested_category_id == "software_subscriptions"
    assert 0.70 <= d.confidence < 0.80


# --- aggregation and thresholds -------------------------------------------------------------


def test_aggregate_keeps_best_score_and_adds_agreement_bonus() -> None:
    ranked = aggregate(
        [
            cand("travel", 0.85, SignalSource.pattern),
            cand("travel", 0.92, SignalSource.merchant),
            cand("meals", 0.60, SignalSource.keyword),
        ],
        DEFAULT_THRESHOLDS,
    )

    assert [s.category_id for s in ranked] == ["travel", "meals"]
    assert ranked[0].score == pytest.approx(0.95)  # 0.92 + 0.03
    assert ranked[1].score == pytest.approx(0.60)


def test_same_source_twice_gets_no_bonus() -> None:
    ranked = aggregate(
        [cand("travel", 0.85, SignalSource.pattern), cand("travel", 0.85, SignalSource.pattern)],
        DEFAULT_THRESHOLDS,
    )

    assert ranked[0].score == pytest.approx(0.85)


def test_conflict_between_close_candidates_goes_to_review() -> None:
    # "UBER" with both trip and eats wording: two 0.85 patterns, zero margin.
    d = one("UBER *TRIP UBER *EATS", "-20.00", account=CARD)

    assert d.status is TxnStatus.needs_review
    assert d.reasons[0] == "conflict: meals vs travel"


def test_stricter_threshold_sends_pattern_matches_to_review() -> None:
    strict = Thresholds(auto_min=0.90)

    assert one("UBER *TRIP", "-20.00", account=CARD).status is TxnStatus.auto
    d = one("UBER *TRIP", "-20.00", account=CARD, thresholds=strict)
    assert d.status is TxnStatus.needs_review
    assert d.suggested_category_id == "travel"


def test_wider_margin_threshold_turns_a_win_into_conflict() -> None:
    # merchant 0.92 vs keyword 0.60 -> margin 0.32, auto by default but not with margin 0.40.
    assert one("WEWORK COFFEE BAR", "-5.00").status is TxnStatus.auto
    d = one("WEWORK COFFEE BAR", "-5.00", thresholds=Thresholds(margin_min=0.40))
    assert d.status is TxnStatus.needs_review
    assert d.reasons[0].startswith("conflict")


def test_recurring_boost_lifts_monthly_charge() -> None:
    rows = [("MERIDIAN FAKE CAFE", "-9.99", 3, month, False) for month in (1, 2, 3)]
    boosted = decide(*rows, account=CARD)
    single = decide(rows[0], account=CARD)

    assert boosted[0].confidence == pytest.approx(single[0].confidence + 0.05)
    assert any("recurring: same amount in 3 months" in r for r in boosted[0].reasons)


# --- direction check ------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("category", "direction", "allowed"),
    [
        ("software_subscriptions", "out", True),
        ("software_subscriptions", "in", False),
        ("client_income", "in", True),
        ("client_income", "out", False),
        ("refund", "in", True),
        ("refund", "out", False),
        ("tax_payment", "in", False),
        ("transfer", "in", True),
        ("transfer", "out", True),
        ("card_payment", "in", True),
        ("meals", None, True),
    ],
)
def test_direction_allows(category: str, direction: str | None, allowed: bool) -> None:
    assert direction_allows(category, direction, load_taxonomy()) is allowed


def test_money_in_from_expense_merchant_is_not_an_expense() -> None:
    d = one("ADOBE", "20.00", account=CARD)

    assert d.status is TxnStatus.needs_review
    assert d.suggested_category_id is None
    assert "ignored software_subscriptions: does not fit money in" in d.reasons


def test_money_out_never_income() -> None:
    d = one("STRIPE TRANSFER", "-50.00")

    assert d.category_id != "client_income"
    assert d.suggested_category_id != "client_income"


# --- ambiguity and user rules -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("description", "amount", "suggested"),
    [
        ("AMAZON MKTPLACE PMTS AMZN.COM/BILL", "-42.18", None),
        ("WALMART #2231", "-40.00", None),
        ("TARGET 00012345", "-18.00", None),
        ("COSTCO WHSE #0442", "-210.00", None),
        ("VENMO PAYMENT RILEY CHEN", "-45.00", None),
        ("ZELLE TO MORGAN ELLIS", "-250.00", None),
        ("CASH APP*FAKE PERSON", "-30.00", None),
        ("PAYPAL *FAKESHOP", "-12.00", None),
        ("APPLE.COM/BILL", "-2.99", None),
        ("ATM WITHDRAWAL #4412", "-200.00", "owner_draw"),
        ("CHECK #1043", "-350.00", None),
        ("MOBILE DEPOSIT", "500.00", "client_income"),
    ],
)
def test_ambiguous_merchants_always_review(
    description: str, amount: str, suggested: str | None
) -> None:
    d = one(description, amount)

    assert d.status is TxnStatus.needs_review
    assert "ambiguous" in d.flags
    assert d.reasons[0].startswith("ambiguous:")
    assert d.suggested_category_id == suggested


def test_amazon_web_services_is_not_ambiguous() -> None:
    d = one("AMAZON WEB SERVICES AWS.AMAZON.CO", "-25.00", account=CARD)

    assert d.status is TxnStatus.auto
    assert d.category_id == "hosting_cloud"


def test_user_rule_wins_and_clears_ambiguity() -> None:
    d = one(
        "ZELLE TO MORGAN ELLIS", "-250.00", user_rules={"ZELLE TO MORGAN ELLIS": "contract_labor"}
    )

    assert d.status is TxnStatus.auto
    assert d.category_id == "contract_labor"
    assert d.confidence == pytest.approx(0.99)
    assert d.rule_id == "user:ZELLE TO MORGAN ELLIS"


def test_user_rule_beats_dictionary() -> None:
    d = one("SQ *JOES CAFE 9921", "-8.75", account=CARD, user_rules={"joes cafe": "meals"})

    assert (d.status, d.category_id) == (TxnStatus.auto, "meals")


def test_user_rule_still_respects_direction() -> None:
    d = one("JOES CAFE", "8.75", account=CARD, user_rules={"JOES CAFE": "meals"})

    assert d.status is TxnStatus.needs_review


def test_user_rule_with_unknown_category_raises() -> None:
    with pytest.raises(ValueError, match="invalid category"):
        one("JOES CAFE", "-1.00", user_rules={"JOES CAFE": "snacks"})


def test_structural_refund_clears_amazon_ambiguity() -> None:
    d = one("AMAZON MKTPLACE REFUND", "19.99", account=CARD)

    assert (d.status, d.category_id) == (TxnStatus.auto, "refund")


def test_output_is_deterministic() -> None:
    rows = [("UBER *TRIP", "-10.00"), ("AMAZON MKTPLACE", "-5.00"), ("WEWORK", "-450.00")]
    assert decide(*rows) == decide(*rows)
