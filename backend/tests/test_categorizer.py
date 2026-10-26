"""
Tests for the categorizer brain.

Run with: pytest backend/tests/ -v
"""

import pytest

from app.categorizer import Category, CategorizationResult, categorize


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def cat(description: str, amount: float | None = None) -> str:
    return categorize(description, amount).category.value


def result(description: str, amount: float | None = None) -> CategorizationResult:
    return categorize(description, amount)


# ---------------------------------------------------------------------------
# Software & Subscriptions
# ---------------------------------------------------------------------------

class TestSoftware:
    def test_adobe_exact(self):
        assert cat("ADOBE CREATIVE CLOUD") == Category.SOFTWARE.value

    def test_adobe_lower(self):
        assert cat("adobe") == Category.SOFTWARE.value

    def test_figma(self):
        assert cat("FIGMA INC") == Category.SOFTWARE.value

    def test_github(self):
        assert cat("GITHUB COM") == Category.SOFTWARE.value

    def test_notion_subscription(self):
        assert cat("NOTION SUBSCRIPTION MONTHLY") == Category.SOFTWARE.value

    def test_zoom_monthly(self):
        assert cat("ZOOM VIDEO COMMUNICATIONS") == Category.SOFTWARE.value

    def test_aws_cloud(self):
        assert cat("AWS CLOUD HOSTING") == Category.SOFTWARE.value

    def test_apple_store(self):
        # Physical Apple Store visit → hardware/equipment → Office & Supplies
        # Apple subscriptions (iCloud, Music, TV+) → Software (see test_apple_subscriptions below)
        assert cat("APPLE STORE") == Category.OFFICE_SUPPLIES.value

    def test_apple_subscriptions(self):
        assert cat("APPLE ICLOUD STORAGE") == Category.SOFTWARE.value

    def test_generic_saas_keyword(self):
        r = result("ACME SAAS PLATFORM")
        assert r.category == Category.SOFTWARE

    def test_subscription_keyword(self):
        r = result("XYZAPP SUBSCRIPTION")
        assert r.category == Category.SOFTWARE


# ---------------------------------------------------------------------------
# Travel & Transport
# ---------------------------------------------------------------------------

class TestTravel:
    def test_uber_star(self):
        assert cat("UBER * TRIP") == Category.TRAVEL.value

    def test_lyft_star(self):
        assert cat("LYFT * RIDE") == Category.TRAVEL.value

    def test_delta_airlines(self):
        assert cat("DELTA AIRLINES 12345") == Category.TRAVEL.value

    def test_airbnb(self):
        assert cat("AIRBNB * ACCOMMODATION") == Category.TRAVEL.value

    def test_hotel_keyword(self):
        assert cat("DOWNTOWN MARRIOTT HOTEL") == Category.TRAVEL.value

    def test_parking(self):
        assert cat("SP+ PARKING GARAGE") == Category.TRAVEL.value

    def test_amtrak(self):
        assert cat("AMTRAK TRAIN TICKET") == Category.TRAVEL.value


# ---------------------------------------------------------------------------
# Food & Dining
# ---------------------------------------------------------------------------

class TestFoodDining:
    def test_starbucks(self):
        assert cat("STARBUCKS STORE 1234") == Category.FOOD_DINING.value

    def test_doordash(self):
        assert cat("DOORDASH*PIZZA") == Category.FOOD_DINING.value

    def test_uber_eats(self):
        assert cat("UBER EATS") == Category.FOOD_DINING.value

    def test_restaurant_keyword(self):
        assert cat("JOES CAFE 9921") == Category.FOOD_DINING.value

    def test_pizza_keyword(self):
        assert cat("DOMINOS PIZZA ORDER") == Category.FOOD_DINING.value

    def test_grocery_keyword(self):
        assert cat("CITY GROCERY MART") == Category.FOOD_DINING.value


# ---------------------------------------------------------------------------
# Office & Supplies
# ---------------------------------------------------------------------------

class TestOfficeSupplies:
    def test_amazon(self):
        assert cat("AMAZON MKTP US") == Category.OFFICE_SUPPLIES.value

    def test_amzn(self):
        assert cat("AMZN MKTP") == Category.OFFICE_SUPPLIES.value

    def test_staples(self):
        assert cat("STAPLES OFFICE SUPPLIES") == Category.OFFICE_SUPPLIES.value

    def test_best_buy(self):
        assert cat("BEST BUY 1234") == Category.OFFICE_SUPPLIES.value

    def test_fedex(self):
        assert cat("FEDEX SHIPPING CHARGE") == Category.OFFICE_SUPPLIES.value


# ---------------------------------------------------------------------------
# Marketing & Advertising
# ---------------------------------------------------------------------------

class TestMarketing:
    def test_facebook_ads(self):
        assert cat("FACEBOOK ADS") == Category.MARKETING.value

    def test_google_ads(self):
        assert cat("GOOGLE ADS PAYMENT") == Category.MARKETING.value

    def test_meta_ads(self):
        assert cat("META ADS MANAGER") == Category.MARKETING.value

    def test_mailchimp(self):
        assert cat("MAILCHIMP SUBSCRIPTION") == Category.MARKETING.value


# ---------------------------------------------------------------------------
# Education & Training
# ---------------------------------------------------------------------------

class TestEducation:
    def test_udemy(self):
        assert cat("UDEMY COURSE PURCHASE") == Category.EDUCATION.value

    def test_coursera(self):
        assert cat("COURSERA INC") == Category.EDUCATION.value

    def test_skillshare(self):
        assert cat("SKILLSHARE ANNUAL") == Category.EDUCATION.value

    def test_conference_keyword(self):
        assert cat("AWWWARDS CONFERENCE TICKET") == Category.EDUCATION.value

    def test_workshop_keyword(self):
        assert cat("DESIGN WORKSHOP REGISTRATION") == Category.EDUCATION.value


# ---------------------------------------------------------------------------
# Transfers / Non-Expense
# ---------------------------------------------------------------------------

class TestTransfer:
    def test_transfer_to_savings(self):
        assert cat("TRANSFER TO SAVINGS") == Category.TRANSFER.value

    def test_ach_transfer(self):
        assert cat("ACH TRANSFER OUTGOING") == Category.TRANSFER.value

    def test_refund_keyword(self):
        r = result("AMAZON REFUND")
        assert r.category == Category.TRANSFER

    def test_positive_amount_is_credit(self):
        """A positive amount on a credit-card statement is a refund/credit."""
        r = result("ADOBE CREATIVE CLOUD", amount=54.99)
        assert r.category == Category.TRANSFER
        assert "refund" in r.reason.lower() or "credit" in r.reason.lower()

    def test_negative_amount_is_expense(self):
        """A negative amount is a normal purchase."""
        r = result("ADOBE CREATIVE CLOUD", amount=-54.99)
        assert r.category == Category.SOFTWARE

    def test_payroll(self):
        assert cat("DIRECT DEPOSIT PAYROLL") == Category.TRANSFER.value

    def test_zelle(self):
        assert cat("ZELLE PAYMENT SENT") == Category.TRANSFER.value


# ---------------------------------------------------------------------------
# Needs Review — uncertain transactions
# ---------------------------------------------------------------------------

class TestNeedsReview:
    def test_random_gibberish(self):
        r = result("XQZR9291 PMT A82")
        assert r.category == Category.NEEDS_REVIEW

    def test_very_short_description(self):
        r = result("POS")
        # No keywords match → low confidence
        assert r.is_review is True

    def test_empty_string(self):
        r = result("")
        assert r.category == Category.NEEDS_REVIEW

    def test_unknown_local_business(self):
        r = result("JOES CORNER 9921")
        # Could be anything; may fall to NEEDS_REVIEW or FOOD_DINING
        # Either is acceptable — just verify it returned a valid result
        assert r.category in {c for c in Category}


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_mixed_case_input(self):
        assert cat("Adobe Creative Cloud") == Category.SOFTWARE.value

    def test_description_with_numbers(self):
        r = result("UBER * TRIP 12345678")
        assert r.category == Category.TRAVEL

    def test_confidence_is_between_0_and_1(self):
        for description in [
            "ADOBE CREATIVE CLOUD", "STARBUCKS", "UBER * TRIP",
            "DOORDASH ORDER", "XQZR9291 PMT", "",
        ]:
            r = result(description)
            assert 0.0 <= r.confidence <= 1.0, f"Confidence out of range for: {description!r}"

    def test_result_has_reason(self):
        r = result("FIGMA SUBSCRIPTION")
        assert r.reason and isinstance(r.reason, str)

    def test_is_review_matches_category(self):
        """is_review must be True iff category is NEEDS_REVIEW."""
        for description in ["ADOBE", "JOES CAFE", "XQZR92"]:
            r = result(description)
            assert r.is_review == (r.category == Category.NEEDS_REVIEW)
