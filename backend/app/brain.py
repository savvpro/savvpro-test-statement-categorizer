import re
from dataclasses import dataclass
from decimal import Decimal

from .models import CategorizationRule, Category, Transaction


SHARED_RULES = [
    ("ADOBE", "Software", False),
    ("MICROSOFT", "Software", False),
    ("FIGMA", "Software", False),
    ("NOTION", "Software", False),
    ("GOOGLE ADS", "Advertising & Marketing", False),
    ("META ADS", "Advertising & Marketing", False),
    ("UBER", "Travel & Transport", False),
    ("CAREEM", "Travel & Transport", False),
    ("DELTA AIR", "Travel & Transport", False),
    ("AIRBNB", "Travel & Transport", False),
    ("STRIPE FEE", "Payment Processing Fees", False),
    ("PAYPAL FEE", "Payment Processing Fees", False),
    ("WISE FEE", "Payment Processing Fees", False),
    ("BANK FEE", "Payment Processing Fees", False),
    ("MOBILE", "Internet & Phone", False),
    ("VERIZON", "Internet & Phone", False),
    ("AT&T", "Internet & Phone", False),
    ("STAPLES", "Office Expenses", False),
    ("OFFICE DEPOT", "Office Expenses", False),
    ("WHOLE FOODS", "Meals", False),
    ("SWIGGY", "Food & Dining", False),
    ("ZOMATO", "Food & Dining", False),
    ("DMART", "Food & Dining", False),
    ("UBER", "Transport", False),
    ("OLA", "Transport", False),
    ("IRCTC", "Travel", False),
    ("OYO", "Travel", False),
    ("MAKEMYTRIP", "Travel", False),
    ("NYKAA", "Personal Care", False),
    ("SALON", "Personal Care", False),
    ("APOLLO", "Health", False),
    ("MEDPLUS", "Health", False),
    ("PVR", "Entertainment", False),
    ("SPOTIFY", "Entertainment", False),
    ("UDEMY", "Education", False),
    ("COLLEGE", "Education", False),
    ("RELIANCE DIGITAL", "Electronics", False),
    ("CROMA", "Electronics", False),
    ("AMAZON", "Shopping", False),
    ("MALL", "Shopping", False),
    ("JIO", "Utilities", False),
    ("AIRTEL", "Utilities", False),
    ("ELECTRICITY", "Utilities", False),
    ("BANK", "Other", False),
    ("ATM", "Other", False),
]

GENERIC_RULES = [
    ("INTERNET", "Internet & Phone"),
    ("PHONE", "Internet & Phone"),
    ("TAX", "Taxes"),
    ("CAFE", "Meals"),
    ("COFFEE", "Meals"),
    ("RESTAURANT", "Meals"),
    ("EQUIPMENT", "Equipment"),
    ("LAPTOP", "Equipment"),
    ("PRINTER", "Equipment"),
    ("GROCER", "Food & Dining"),
    ("FOOD", "Food & Dining"),
    ("ZARA", "Shopping"),
    ("CLOTHES", "Shopping"),
    ("SHOPPING", "Shopping"),
    ("WIFI", "Utilities"),
    ("GAS BILL", "Utilities"),
    ("ELECTRICITY", "Utilities"),
    ("PHARMACY", "Health"),
    ("MEDICINE", "Health"),
    ("DOCTOR", "Health"),
    ("MOVIE", "Entertainment"),
    ("COURSE", "Education"),
    ("BOOKS", "Education"),
    ("CAB", "Transport"),
    ("TRAIN", "Travel"),
    ("HOTEL", "Travel"),
    ("TRIP", "Travel"),
    ("SALON", "Personal Care"),
    ("LAPTOP", "Electronics"),
    ("PHONE", "Electronics"),
]


def normalize_description(description: str) -> str:
    normalized = re.sub(r"[^A-Z0-9& ]", " ", description.upper())
    return re.sub(r"\s+", " ", normalized).strip()


def _special_case(transaction: Transaction) -> tuple[Category, int, str] | None:
    text = normalize_description(transaction.description)
    if "REFUND" in text or "REVERSAL" in text or transaction.amount < 0:
        return "Refund", 98, "Detected a refund or reversal indicator."
    if any(token in text for token in ("TRANSFER", "SAVINGS", "CASH WITHDRAWAL")):
        return "Transfer", 98, "Detected a movement of money rather than a business expense."
    if transaction.direction == "income" and any(
        token in text
        for token in ("CLIENT", "INVOICE", "PAYMENT RECEIVED", "PAYPAL", "WISE", "STRIPE")
    ):
        return "Client Income", 92, "Income direction and client-payment wording indicate business income."
    return None


def _rule_match(
    transaction: Transaction, rules: list[CategorizationRule]
) -> CategorizationRule | None:
    text = normalize_description(transaction.description)
    exact_matches = [
        rule for rule in rules if rule.exact and text == normalize_description(rule.pattern)
    ]
    if exact_matches:
        return exact_matches[0]
    matches = [
        rule for rule in rules if not rule.exact and normalize_description(rule.pattern) in text
    ]
    return max(matches, key=lambda rule: len(normalize_description(rule.pattern)), default=None)


def categorize(
    transaction: Transaction,
    user_rules: list[CategorizationRule] | None = None,
) -> Transaction:
    user_rules = user_rules or []
    special = _special_case(transaction)
    if special:
        transaction.category, transaction.confidence, transaction.explanation = special
        transaction.rule_id = None
        transaction.rule_scope = None
        transaction.needs_review = transaction.category == "Needs Review"
        return transaction

    personal = _rule_match(transaction, user_rules)
    if personal:
        transaction.category = personal.category
        transaction.confidence = 99
        transaction.explanation = "Matched your personal correction rule."
        transaction.rule_id = personal.id
        transaction.rule_scope = "user"
        transaction.needs_review = False
        return transaction

    shared = _rule_match(
        transaction,
        [
            CategorizationRule(
                pattern=pattern,
                category=category,  # type: ignore[arg-type]
                scope="shared",
                source="built_in",
                exact=exact,
            )
            for pattern, category, exact in SHARED_RULES
        ],
    )
    if shared:
        transaction.category = shared.category
        transaction.confidence = 90
        transaction.explanation = "Matched a curated shared default rule."
        transaction.rule_id = shared.id
        transaction.rule_scope = "shared"
        transaction.needs_review = False
        return transaction

    text = normalize_description(transaction.description)
    generic = next(
        ((keyword, category) for keyword, category in GENERIC_RULES if keyword in text),
        None,
    )
    if generic:
        transaction.category = generic[1]  # type: ignore[assignment]
        transaction.confidence = 72
        transaction.explanation = f"Matched the generic keyword “{generic[0]}”; please verify."
        transaction.rule_id = None
        transaction.rule_scope = None
        transaction.needs_review = True
        return transaction

    transaction.category = "Needs Review"
    transaction.confidence = 0
    transaction.explanation = "No reliable rule matched this transaction."
    transaction.rule_id = None
    transaction.rule_scope = None
    transaction.needs_review = True
    return transaction
