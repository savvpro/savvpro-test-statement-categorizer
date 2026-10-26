"""
Unit tests for the rule-based categorization brain.
Tests normal categorization, edge cases, refunds, income, and fallback behavior.
"""
import pytest
from brain import (
    categorize_transaction,
    get_category_summary,
    normalize_text,
    is_ambiguous_description,
    match_keywords,
    Category,
    Confidence
)


class TestNormalization:
    """Test text normalization utilities."""
    
    def test_normalize_text_basic(self):
        assert normalize_text("ADOBE CREATIVE CLOUD") == "adobe creative cloud"
        assert normalize_text("Uber *Trip 123") == "uber trip 123"
    
    def test_normalize_text_special_chars(self):
        assert normalize_text("AMAZON.COM*123XYZ") == "amazon com 123xyz"
        assert normalize_text("Payment - Transfer") == "payment transfer"
    
    def test_normalize_text_multiple_spaces(self):
        assert normalize_text("TRANSFER   IN    PAYMENT") == "transfer in payment"
    
    def test_normalize_text_empty(self):
        assert normalize_text("") == ""
        assert normalize_text("   ") == ""


class TestAmbiguousDetection:
    """Test detection of ambiguous/vague descriptions."""
    
    def test_ambiguous_patterns(self):
        assert is_ambiguous_description("payment") == True
        assert is_ambiguous_description("transfer") == True
        assert is_ambiguous_description("123456") == True
    
    def test_short_descriptions(self):
        assert is_ambiguous_description("AB") == True
        assert is_ambiguous_description("X") == True
    
    def test_clear_descriptions(self):
        assert is_ambiguous_description("ADOBE CREATIVE CLOUD") == False
        assert is_ambiguous_description("Uber Trip to Airport") == False


class TestKeywordMatching:
    """Test keyword matching functionality."""
    
    def test_match_keywords_exact(self):
        keywords = ["adobe", "figma", "github"]
        assert match_keywords("ADOBE CREATIVE CLOUD", keywords) == True
        assert match_keywords("Purchase from Figma", keywords) == True
    
    def test_match_keywords_no_match(self):
        keywords = ["adobe", "figma"]
        assert match_keywords("Random coffee shop", keywords) == False
    
    def test_match_keywords_word_boundaries(self):
        keywords = ["uber"]
        assert match_keywords("UBER TRIP", keywords) == True
        assert match_keywords("SUPERUBER", keywords) == False  # Should not match


class TestSoftwareToolsCategorization:
    """Test Software & Tools category."""
    
    def test_adobe_subscription(self):
        result = categorize_transaction("ADOBE CREATIVE CLOUD", -49.99)
        assert result["category"] == Category.SOFTWARE_TOOLS
        assert result["confidence"] == Confidence.HIGH
    
    def test_github_subscription(self):
        result = categorize_transaction("GITHUB SUBSCRIPTION", -20.00)
        assert result["category"] == Category.SOFTWARE_TOOLS
        assert result["confidence"] == Confidence.HIGH
    
    def test_vercel_hosting(self):
        result = categorize_transaction("VERCEL HOSTING FEE", -35.00)
        assert result["category"] == Category.SOFTWARE_TOOLS
        assert result["confidence"] == Confidence.HIGH
    
    def test_aws_services(self):
        result = categorize_transaction("AWS SERVICES", -150.25)
        assert result["category"] == Category.SOFTWARE_TOOLS
        assert result["confidence"] == Confidence.HIGH
    
    def test_figma_pro(self):
        result = categorize_transaction("FIGMA PROFESSIONAL", -15.00)
        assert result["category"] == Category.SOFTWARE_TOOLS
        assert result["confidence"] == Confidence.HIGH


class TestTravelTransportCategorization:
    """Test Travel & Transport category."""
    
    def test_uber_ride(self):
        result = categorize_transaction("UBER *TRIP 9921", -25.50)
        assert result["category"] == Category.TRAVEL_TRANSPORT
        assert result["confidence"] == Confidence.HIGH
    
    def test_careem_ride(self):
        result = categorize_transaction("CAREEM RIDE TO OFFICE", -18.00)
        assert result["category"] == Category.TRAVEL_TRANSPORT
        assert result["confidence"] == Confidence.HIGH
    
    def test_petrol_station(self):
        result = categorize_transaction("SHELL PETROL STATION", -60.00)
        assert result["category"] == Category.TRAVEL_TRANSPORT
        assert result["confidence"] == Confidence.HIGH
    
    def test_airline_ticket(self):
        result = categorize_transaction("AIRBLUE FLIGHT TICKET", -350.00)
        assert result["category"] == Category.TRAVEL_TRANSPORT
        assert result["confidence"] == Confidence.HIGH


class TestOfficeSuppliesCategorization:
    """Test Office & Supplies category."""
    
    def test_staples_purchase(self):
        result = categorize_transaction("STAPLES STORE #123", -45.00)
        assert result["category"] == Category.OFFICE_SUPPLIES
        assert result["confidence"] == Confidence.HIGH
    
    def test_printing_services(self):
        result = categorize_transaction("PRINTING SERVICES", -30.00)
        assert result["category"] == Category.OFFICE_SUPPLIES
        assert result["confidence"] == Confidence.HIGH
    
    def test_paper_supplies(self):
        result = categorize_transaction("OFFICE PAPER SUPPLIES", -25.50)
        assert result["category"] == Category.OFFICE_SUPPLIES
        assert result["confidence"] == Confidence.HIGH


class TestClientIncomeCategorization:
    """Test Client Income category (positive amounts + income keywords)."""
    
    def test_upwork_payment(self):
        result = categorize_transaction("UPWORK PAYMENT", 2500.00)
        assert result["category"] == Category.CLIENT_INCOME
        assert result["confidence"] == Confidence.HIGH
    
    def test_stripe_transfer(self):
        result = categorize_transaction("STRIPE TRANSFER IN", 1800.50)
        assert result["category"] == Category.CLIENT_INCOME
        assert result["confidence"] == Confidence.HIGH
    
    def test_payoneer_payment(self):
        result = categorize_transaction("PAYONEER PAYMENT RECEIVED", 3200.00)
        assert result["category"] == Category.CLIENT_INCOME
        assert result["confidence"] == Confidence.HIGH
    
    def test_negative_amount_with_income_keyword(self):
        # Negative amount should NOT be categorized as income
        result = categorize_transaction("UPWORK FEE", -50.00)
        assert result["category"] != Category.CLIENT_INCOME


class TestExpenseRefundCategorization:
    """Test Expense Refund category."""
    
    def test_refund_keyword(self):
        result = categorize_transaction("AMAZON REFUND", 45.00)
        assert result["category"] == Category.EXPENSE_REFUND
        assert result["confidence"] == Confidence.HIGH
    
    def test_reversal_keyword(self):
        result = categorize_transaction("TRANSACTION REVERSAL", 120.00)
        assert result["category"] == Category.EXPENSE_REFUND
        assert result["confidence"] == Confidence.HIGH
    
    def test_return_keyword(self):
        result = categorize_transaction("RETURN CREDIT", 75.50)
        assert result["category"] == Category.EXPENSE_REFUND
        assert result["confidence"] == Confidence.HIGH
    
    def test_chargeback(self):
        result = categorize_transaction("CHARGEBACK PROCESSED", 200.00)
        assert result["category"] == Category.EXPENSE_REFUND
        assert result["confidence"] == Confidence.HIGH
    
    def test_refund_negative_amount(self):
        # Even negative amounts with refund keyword should be refund
        result = categorize_transaction("REFUND PROCESSING FEE", -5.00)
        assert result["category"] == Category.EXPENSE_REFUND
        assert result["confidence"] == Confidence.HIGH


class TestNeedsReviewCategorization:
    """Test Needs Review fallback category."""
    
    def test_unknown_merchant(self):
        result = categorize_transaction("JOES CAFE 9921", -35.00)
        assert result["category"] == Category.NEEDS_REVIEW
        assert result["confidence"] == Confidence.LOW
    
    def test_ambiguous_description(self):
        result = categorize_transaction("PAYMENT", -100.00)
        assert result["category"] == Category.NEEDS_REVIEW
        assert result["confidence"] == Confidence.LOW
    
    def test_empty_description(self):
        result = categorize_transaction("", -50.00)
        assert result["category"] == Category.NEEDS_REVIEW
        assert result["confidence"] == Confidence.LOW
    
    def test_only_numbers(self):
        result = categorize_transaction("1234567890", -80.00)
        assert result["category"] == Category.NEEDS_REVIEW
        assert result["confidence"] == Confidence.LOW
    
    def test_very_short_code(self):
        result = categorize_transaction("XY", -25.00)
        assert result["category"] == Category.NEEDS_REVIEW
        assert result["confidence"] == Confidence.LOW


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_invalid_amount_string(self):
        result = categorize_transaction("ADOBE", "invalid")
        assert result["category"] == Category.NEEDS_REVIEW
        assert result["confidence"] == Confidence.LOW
    
    def test_none_description(self):
        result = categorize_transaction(None, -50.00)
        assert result["category"] == Category.NEEDS_REVIEW
        assert result["confidence"] == Confidence.LOW
    
    def test_zero_amount(self):
        result = categorize_transaction("ADOBE CREATIVE CLOUD", 0.00)
        assert result["category"] == Category.SOFTWARE_TOOLS
        assert result["confidence"] == Confidence.HIGH
    
    def test_very_large_amount(self):
        result = categorize_transaction("UPWORK PAYMENT", 50000.00)
        assert result["category"] == Category.CLIENT_INCOME
        assert result["confidence"] == Confidence.HIGH
    
    def test_whitespace_only_description(self):
        result = categorize_transaction("   ", -30.00)
        assert result["category"] == Category.NEEDS_REVIEW
        assert result["confidence"] == Confidence.LOW


class TestCategorySummary:
    """Test summary generation functionality."""
    
    def test_summary_generation(self):
        transactions = [
            {"category": Category.SOFTWARE_TOOLS, "confidence": Confidence.HIGH},
            {"category": Category.SOFTWARE_TOOLS, "confidence": Confidence.HIGH},
            {"category": Category.TRAVEL_TRANSPORT, "confidence": Confidence.HIGH},
            {"category": Category.CLIENT_INCOME, "confidence": Confidence.HIGH},
            {"category": Category.NEEDS_REVIEW, "confidence": Confidence.LOW},
        ]
        
        summary = get_category_summary(transactions)
        
        assert summary["Software & Tools"] == 2
        assert summary["Travel & Transport"] == 1
        assert summary["Client Income"] == 1
        assert summary["Needs Review"] == 1
        assert summary["Office & Supplies"] == 0
        assert summary["Expense Refund"] == 0
    
    def test_summary_empty_list(self):
        summary = get_category_summary([])
        
        # Should return all categories with 0 count
        assert all(count == 0 for count in summary.values())
        assert len(summary) == 6  # All 6 categories


class TestRealWorldScenarios:
    """Test real-world transaction scenarios."""
    
    def test_freelancer_monthly_expenses(self):
        """Simulate a freelancer's typical monthly transactions."""
        transactions = [
            ("ADOBE CREATIVE CLOUD", -49.99),
            ("FIGMA PROFESSIONAL", -15.00),
            ("UBER TO CLIENT MEETING", -32.50),
            ("UPWORK PAYMENT PROJECT X", 2500.00),
            ("STRIPE TRANSFER", 1200.00),
            ("AWS SERVICES", -87.45),
            ("COFFEE SHOP DOWNTOWN", -12.50),  # Should be Needs Review
            ("AMAZON REFUND", 45.00),
            ("GITHUB PRO", -20.00),
        ]
        
        results = [categorize_transaction(desc, amt) for desc, amt in transactions]
        
        # Verify key categorizations
        assert results[0]["category"] == Category.SOFTWARE_TOOLS
        assert results[2]["category"] == Category.TRAVEL_TRANSPORT
        assert results[3]["category"] == Category.CLIENT_INCOME
        assert results[6]["category"] == Category.NEEDS_REVIEW
        assert results[7]["category"] == Category.EXPENSE_REFUND
    
    def test_agency_expense_report(self):
        """Simulate an agency's expense report."""
        transactions = [
            ("VERCEL HOSTING - CLIENT SITE", -120.00),
            ("OPENAI API USAGE", -250.00),
            ("OFFICE SUPPLIES STAPLES", -156.78),
            ("CLIENT PAYMENT VIA PAYONEER", 5000.00),
            ("CAREEM RIDE TO OFFICE", -15.00),
            ("PRINTING BUSINESS CARDS", -89.00),
        ]
        
        results = [categorize_transaction(desc, amt) for desc, amt in transactions]
        
        assert results[0]["category"] == Category.SOFTWARE_TOOLS
        assert results[1]["category"] == Category.SOFTWARE_TOOLS
        assert results[2]["category"] == Category.OFFICE_SUPPLIES
        assert results[3]["category"] == Category.CLIENT_INCOME
        assert results[4]["category"] == Category.TRAVEL_TRANSPORT
        assert results[5]["category"] == Category.OFFICE_SUPPLIES


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
