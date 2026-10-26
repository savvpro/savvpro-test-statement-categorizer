"""
Unit tests for deterministic rules categorization engine.
Verifies precedence, confidence scoring, explainability, and edge cases.
"""

from decimal import Decimal

from app.categorizer import categorize_transaction
from app.models import CANONICAL_CATEGORIES


def test_canonical_categories_defined():
    assert "Software" in CANONICAL_CATEGORIES
    assert "Needs Review" in CANONICAL_CATEGORIES
    assert "Transfer (not spending)" in CANONICAL_CATEGORIES
    assert "Refund" in CANONICAL_CATEGORIES


def test_software_categorization():
    cat, conf, reason, needs_rev, direction = categorize_transaction(
        "ADOBE CREATIVE CLOUD", Decimal("-59.99")
    )
    assert cat == "Software"
    assert conf >= 0.90
    assert "Adobe" in reason
    assert not needs_rev
    assert direction == "expense"


def test_mangled_saas_vendor():
    cat, conf, _reason, needs_rev, _ = categorize_transaction(
        "ADBE*CREATIVECLOUD", Decimal("-59.99")
    )
    assert cat == "Software"
    assert conf >= 0.90
    assert not needs_rev


def test_travel_rideshare():
    cat, conf, _reason, needs_rev, direction = categorize_transaction(
        "UBER *TRIP 1421", Decimal("-32.40")
    )
    assert cat == "Travel & Transport"
    assert conf >= 0.85
    assert not needs_rev
    assert direction == "expense"


def test_meals_and_coffee_50_percent_deduction():
    cat, _conf, reason, needs_rev, _ = categorize_transaction(
        "BLUE BOTTLE COFFEE", Decimal("-8.75")
    )
    assert cat == "Meals & Coffee"
    assert "50%" in reason
    assert not needs_rev


def test_office_equipment_and_hardware():
    cat, conf, _reason, needs_rev, _ = categorize_transaction(
        "BEST BUY - EXTERNAL MONITOR", Decimal("-289.99")
    )
    assert cat == "Office Supplies & Equipment"
    assert conf >= 0.90
    assert not needs_rev


def test_internet_telecom():
    cat, conf, _reason, needs_rev, _ = categorize_transaction(
        "COMCAST BUSINESS INTERNET", Decimal("-120.00")
    )
    assert cat == "Internet & Utilities"
    assert conf >= 0.90
    assert not needs_rev


def test_advertising_networks():
    cat, conf, _reason, needs_rev, _ = categorize_transaction(
        "GOOGLE ADS 492049", Decimal("-250.00")
    )
    assert cat == "Advertising & Marketing"
    assert conf >= 0.95
    assert not needs_rev


def test_professional_legal_tax():
    cat, conf, _reason, needs_rev, _ = categorize_transaction(
        "H&R BLOCK TAX PREPARATION", Decimal("-350.00")
    )
    assert cat == "Professional Services"
    assert conf >= 0.90
    assert not needs_rev


def test_bank_fees():
    cat, conf, _reason, needs_rev, _ = categorize_transaction(
        "MONTHLY ACCOUNT SERVICE FEE", Decimal("-12.00")
    )
    assert cat == "Bank Fees"
    assert conf >= 0.90
    assert not needs_rev


def test_inbound_client_revenue():
    cat, conf, _reason, needs_rev, direction = categorize_transaction(
        "CLIENT ACME CORP INVOICE #104", Decimal("3200.00")
    )
    assert cat == "Income"
    assert conf >= 0.90
    assert not needs_rev
    assert direction == "income"


def test_internal_transfers_excluded_from_spending():
    cat, _conf, reason, needs_rev, direction = categorize_transaction(
        "ONLINE TRANSFER TO SAVINGS ACC #4019", Decimal("-1000.00")
    )
    assert cat == "Transfer (not spending)"
    assert "transfer" in reason.lower()
    assert not needs_rev
    assert direction == "transfer"


def test_autopay_card_payment_is_transfer():
    cat, _conf, _reason, needs_rev, direction = categorize_transaction(
        "AUTOPAY CREDIT CARD BILL PAYMENT", Decimal("-750.00")
    )
    assert cat == "Transfer (not spending)"
    assert not needs_rev
    assert direction == "transfer"


def test_refund_is_not_income():
    cat, _conf, reason, needs_rev, direction = categorize_transaction(
        "RETURN/REFUND PRINTER PAPER ERROR", Decimal("45.50")
    )
    assert cat == "Refund"
    assert "never counted as operating income" in reason
    assert not needs_rev
    assert direction == "refund"


def test_personal_owner_draw():
    cat, _conf, _reason, needs_rev, _ = categorize_transaction(
        "GROCERY OUTLET PERSONAL FOOD", Decimal("-78.40")
    )
    assert cat == "Personal / Owner Draw"
    assert not needs_rev


def test_ambiguous_merchant_joes_cafe():
    # Joe's cafe from TASK.md must go to Needs Review
    cat, conf, reason, needs_rev, _ = categorize_transaction(
        "JOES CAFE 9921", Decimal("-22.00")
    )
    assert cat == "Needs Review"
    assert needs_rev is True
    assert conf < 0.60
    assert "Ambiguous merchant" in reason


def test_ambiguous_merchant_amazon():
    cat, conf, reason, needs_rev, _ = categorize_transaction(
        "AMAZON.COM*DIRECT 9812", Decimal("-64.80")
    )
    assert cat == "Needs Review"
    assert needs_rev is True
    assert conf < 0.60
    assert "Amazon transactions vary widely" in reason


def test_unknown_merchant_conservative_fallback():
    cat, conf, _reason, needs_rev, _ = categorize_transaction(
        "RANDOM MYSTERIOUS POPUP SHOP 449", Decimal("-45.00")
    )
    assert cat == "Needs Review"
    assert needs_rev is True
    assert conf <= 0.30


def test_unidentified_inflow_not_assumed_income():
    # A positive number without invoice keywords must NOT be silently called income
    cat, _conf, reason, needs_rev, _ = categorize_transaction(
        "UNRECOGNIZED DEPOSIT REF 881", Decimal("400.00")
    )
    assert cat == "Needs Review"
    assert needs_rev is True
    assert "Unidentified incoming deposit" in reason


def test_processor_mangled_merchant():
    cat, _conf, _reason, needs_rev, _ = categorize_transaction(
        "SQ *ARTISAN BAKERY", Decimal("-14.25")
    )
    assert cat == "Meals & Coffee"
    assert not needs_rev
