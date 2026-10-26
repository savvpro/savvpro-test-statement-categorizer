from app.brain import categorize


def test_known_merchants_file_without_review():
    cases = {
        "ADOBE *CREATIVE CLOUD 800-833-6687": "software",
        "FIGMA INC. SAN FRANCISCO CA": "software",
        "UBER *TRIP HELP.UBER.COM": "travel",
        "UBER *EATS SAN FRANCISCO": "meals",
        "STAPLES 01428 NEW YORK NY": "supplies",
        "B&H PHOTO 800-606-6969": "equipment",
        "UPWORK *ESCROW": "contractors",
        "GOOGLE *ADS 650-253-0000": "marketing",
        "COMCAST CABLE COMM": "utilities",
        "SKILLSHARE.COM": "education",
        "STARBUCKS STORE 54821": "meals",
        "SEPHORA TIMES SQUARE": "personal",
        "ZOOM.US 888-799-9666": "software",
        "PARKING GARAGE 12": "travel",
    }
    for description, category in cases.items():
        decision = categorize(description, 20)
        assert decision.category == category, description
        assert decision.needs_review is False


def test_uber_eats_is_not_travel():
    decision = categorize("UBER *EATS SAN FRANCISCO", 18)
    assert decision.category == "meals"
    assert decision.fingerprint == "uber_eats"


def test_unknown_cafe_is_not_filed():
    decision = categorize("JOES CAFE 9921 BROOKLYN NY", 14.80)
    assert decision.needs_review is True
    assert decision.category == "needs_review"
    assert decision.suggestion == "meals"
    assert decision.fingerprint == "JOES CAFE"


def test_toast_prefix_shares_the_cafe_fingerprint():
    decision = categorize("TST* JOES CAFE BROOKLYN", 22.5)
    assert decision.needs_review is True
    assert decision.suggestion == "meals"
    assert decision.fingerprint == "JOES CAFE"


def test_ambiguous_marketplaces_ask():
    amazon = categorize("AMAZON.COM*AB3X91 SEATTLE", 67.4)
    paypal = categorize("PAYPAL *INSTANT TRANSFER", 75)
    atm = categorize("ATM WITHDRAWAL 400 OAK ST", 80)
    phone = categorize("T-MOBILE*AUTO PAY", 70)
    assert amazon.needs_review and amazon.suggestion == "supplies"
    assert paypal.needs_review and paypal.category == "needs_review"
    assert "Cash withdrawal" in atm.reason
    assert phone.needs_review and phone.suggestion == "utilities"
    assert phone.category != "card_payment"


def test_shape_rules():
    payment = categorize("PAYMENT THANK YOU", -1200)
    transfer = categorize("TRANSFER TO SAVINGS", -300)
    fee = categorize("INTEREST CHARGE", 12.44)
    annual = categorize("ANNUAL MEMBERSHIP FEE", 95)
    income = categorize("STRIPE PAYOUT", -840)
    client = categorize("CLIENT PAYMENT INV-1042", -500)
    assert payment.category == "card_payment"
    assert transfer.category == "transfer"
    assert fee.category == "fees"
    assert annual.category == "fees"
    assert income.category == "income"
    assert client.category == "income"


def test_refund_reduces_a_category_and_is_not_income():
    decision = categorize("ADOBE *CREATIVE CLOUD REFUND", -54.99)
    assert decision.category == "refund"
    assert decision.offsets_category == "software"
    assert decision.needs_review is False

    equipment = categorize("RETURN B&H PHOTO", -120)
    assert equipment.category == "refund"
    assert equipment.offsets_category == "equipment"


def test_positive_refund_word_flips_the_sign():
    decision = categorize("ADOBE REFUND", 54.99)
    assert decision.category == "refund"
    assert decision.offsets_category == "software"
    assert decision.sign_flip is True


def test_saved_merchant_is_reused_and_does_not_override_a_payment():
    saved = {"JOES CAFE": "meals", "PAYMENT THANK": "software"}
    cafe = categorize("JOES CAFE 1002", 9)
    learned = categorize("JOES CAFE 1002", 9, saved)
    payment = categorize("PAYMENT THANK YOU", -40, saved)
    assert cafe.needs_review is True
    assert learned.category == "meals"
    assert learned.source == "memory"
    assert payment.category == "card_payment"


def test_close_rules_ask():
    decision = categorize("ADOBE FIGMA MONTHLY", 30)
    assert decision.needs_review is True
    assert "Close call" in decision.reason


def test_money_in_without_a_story_asks():
    decision = categorize("ACME STUDIO", -200)
    assert decision.needs_review is True
    assert decision.category == "needs_review"


def test_empty_description_asks():
    decision = categorize("   ", 12)
    assert decision.needs_review is True
