"""
Rule-based transaction categorization engine.
NO external LLM/AI models - pure Python logic only.
"""
import re
from typing import Dict, Tuple
from enum import Enum


class Category(str, Enum):
    """Transaction categories for freelancer/agency expenses."""
    SOFTWARE_TOOLS = "Software & Tools"
    TRAVEL_TRANSPORT = "Travel & Transport"
    OFFICE_SUPPLIES = "Office & Supplies"
    CLIENT_INCOME = "Client Income"
    EXPENSE_REFUND = "Expense Refund"
    NEEDS_REVIEW = "Needs Review"


class Confidence(str, Enum):
    """Confidence levels for categorization."""
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


# Rule-based keyword mappings with exact patterns
CATEGORY_RULES = {
    Category.SOFTWARE_TOOLS: [
        "adobe", "figma", "github", "convex", "vercel", "aws", "openai",
        "microsoft", "google cloud", "digitalocean", "heroku", "slack",
        "notion", "zoom", "canva", "spotify", "netflix", "dropbox",
        "creative cloud", "subscription"
    ],
    Category.TRAVEL_TRANSPORT: [
        "uber", "careem", "airblue", "petrol", "shell", "lyft", "grab",
        "airline", "flight", "hotel", "airbnb", "taxi", "car rental",
        "parking", "toll", "gas station", "fuel"
    ],
    Category.OFFICE_SUPPLIES: [
        "staples", "printing", "paper", "office depot", "stationery",
        "printer", "ink", "toner", "supplies", "furniture", "desk"
    ]
}

# Income-related keywords
INCOME_KEYWORDS = [
    "upwork", "stripe", "payoneer", "transfer in", "payment received",
    "freelance", "client payment", "invoice payment", "consulting fee",
    "project payment", "fiverr", "toptal"
]

# Refund/reversal keywords
REFUND_KEYWORDS = [
    "refund", "reversal", "return", "chargeback", "credit adjustment",
    "reimbursement", "cashback"
]

# Patterns that should always go to review
AMBIGUOUS_PATTERNS = [
    r"^payment$",
    r"^transfer$",
    r"^transaction$",
    r"^purchase$",
    r"^\d+$",  # Only numbers
    r"^[a-z]{1,3}$",  # Very short codes
]


def normalize_text(text: str) -> str:
    """Normalize text for consistent matching."""
    if not isinstance(text, str):
        text = str(text)
    # Remove special characters but keep spaces and alphanumeric
    text = re.sub(r'[^a-zA-Z0-9\s]', ' ', text)
    # Collapse multiple spaces
    text = re.sub(r'\s+', ' ', text)
    return text.lower().strip()


def is_ambiguous_description(description: str) -> bool:
    """Check if description is too vague to categorize."""
    normalized = normalize_text(description)
    
    # Check against ambiguous patterns
    for pattern in AMBIGUOUS_PATTERNS:
        if re.match(pattern, normalized):
            return True
    
    # Too short to be meaningful
    if len(normalized) < 3:
        return True
    
    return False


def match_keywords(description: str, keywords: list) -> bool:
    """Check if any keyword matches in the description."""
    normalized_desc = normalize_text(description)
    
    for keyword in keywords:
        # Use word boundaries for more precise matching
        pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
        if re.search(pattern, normalized_desc):
            return True
    
    return False


def categorize_by_amount_and_keywords(
    description: str,
    amount: float
) -> Tuple[Category, Confidence]:
    """
    Categorize based on amount sign and specific keywords.
    
    Logic:
    - Positive amount + income keywords -> Client Income
    - Refund keywords (regardless of amount) -> Expense Refund
    """
    normalized_desc = normalize_text(description)
    
    # Check for refunds first (highest priority)
    if match_keywords(normalized_desc, REFUND_KEYWORDS):
        return Category.EXPENSE_REFUND, Confidence.HIGH
    
    # Check for income (positive amount + income keywords)
    if amount > 0 and match_keywords(normalized_desc, INCOME_KEYWORDS):
        return Category.CLIENT_INCOME, Confidence.HIGH
    
    return None, None


def categorize_by_expense_type(description: str) -> Tuple[Category, Confidence]:
    """Categorize expenses by type using keyword matching."""
    normalized_desc = normalize_text(description)
    
    for category, keywords in CATEGORY_RULES.items():
        if match_keywords(normalized_desc, keywords):
            return category, Confidence.HIGH
    
    return None, None


def categorize_transaction(description: str, amount: float) -> Dict[str, str]:
    """
    Main categorization function - the brain of the system.
    
    Args:
        description: Transaction description from bank statement
        amount: Transaction amount (positive = credit/income, negative = debit/expense)
    
    Returns:
        Dictionary with 'category' and 'confidence' keys
    
    Rules:
    1. Check if description is too ambiguous -> Needs Review
    2. Check for refund/income patterns (amount-aware)
    3. Check for expense category patterns
    4. Default to Needs Review if no match
    """
    # Validate inputs
    if not description or description.strip() == "":
        return {
            "category": Category.NEEDS_REVIEW,
            "confidence": Confidence.LOW
        }
    
    try:
        amount = float(amount)
    except (ValueError, TypeError):
        return {
            "category": Category.NEEDS_REVIEW,
            "confidence": Confidence.LOW
        }
    
    # Check for ambiguous descriptions first
    if is_ambiguous_description(description):
        return {
            "category": Category.NEEDS_REVIEW,
            "confidence": Confidence.LOW
        }
    
    # Try amount-based categorization (income/refunds)
    category, confidence = categorize_by_amount_and_keywords(description, amount)
    if category:
        return {
            "category": category,
            "confidence": confidence
        }
    
    # Try expense categorization
    category, confidence = categorize_by_expense_type(description)
    if category:
        return {
            "category": category,
            "confidence": confidence
        }
    
    # Default: needs manual review
    return {
        "category": Category.NEEDS_REVIEW,
        "confidence": Confidence.LOW
    }


def get_category_summary(transactions: list) -> Dict[str, int]:
    """
    Generate summary counts for each category.
    
    Args:
        transactions: List of categorized transactions
    
    Returns:
        Dictionary with category counts
    """
    summary = {category.value: 0 for category in Category}
    
    for transaction in transactions:
        category = transaction.get("category", Category.NEEDS_REVIEW)
        summary[category] = summary.get(category, 0) + 1
    
    return summary
