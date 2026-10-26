"""Deterministic, conservative classification. No network or model dependencies."""

import re
from dataclasses import asdict, dataclass

VERSION = "rules-1.0"
CATEGORIES = [
    "AI & developer tools",
    "Software subscriptions",
    "Cloud & hosting",
    "Domains & websites",
    "Professional education",
    "Education",
    "Entertainment",
    "Groceries",
    "Food & dining",
    "Shopping & household",
    "Internet & mobile",
    "Utilities",
    "Transport",
    "Equipment",
    "Healthcare",
    "Donations",
    "Bank fees",
    "Taxes & levies",
    "Freelance income",
    "Own-account transfer",
    "Family support",
    "Transfer",
    "Card payment",
    "Cash withdrawal",
    "Uncategorized",
]
TYPES = ["expense", "income", "refund", "transfer", "card_payment", "cash", "unresolved"]
PURPOSES = ["business", "personal", "mixed", "unknown", "excluded"]


def normalize(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", " ", value.upper()).strip()


@dataclass(frozen=True)
class Decision:
    kind: str
    category: str
    purpose: str
    category_confidence: str
    needs_review: bool
    reason: str
    rule_id: str
    business_percent: int = 0

    def dict(self):
        return asdict(self) | {"rule_version": VERSION}


# Bounded patterns, not loose substring matches (e.g. AWS must not match PAWS).
MERCHANTS = [
    (
        r"OPENAI|CHATGPT|ANTHROPIC|CLAUDE AI|GITHUB COPILOT|CURSOR|MIDJOURNEY|PERPLEXITY",
        "AI & developer tools",
        "unknown",
    ),
    (
        r"JETBRAINS|FIGMA|ADOBE|POSTMAN|NOTION|MICROSOFT 365|GOOGLE WORKSPACE|GITHUB(?! COPILOT)",
        "Software subscriptions",
        "unknown",
    ),
    (
        r"AMAZON WEB SERVICES|AWS|DIGITALOCEAN|VERCEL|NETLIFY|CLOUDFLARE|HETZNER|SUPABASE|RENDER",
        "Cloud & hosting",
        "unknown",
    ),
    (r"NAMECHEAP|GODADDY|PORKBUN", "Domains & websites", "unknown"),
    (r"UDEMY|COURSERA|PLURALSIGHT|EDX|FRONTEND MASTERS", "Professional education", "unknown"),
    (r"SCHOOL|UNIVERSITY|TUITION|EDUCATION FEE", "Education", "unknown"),
    (r"NETFLIX|SPOTIFY|YOUTUBE PREMIUM|STEAM|PLAYSTATION|PRIME VIDEO", "Entertainment", "personal"),
    (r"IMTIAZ|CARREFOUR|GROCERY|GROCERIES|METRO CASH", "Groceries", "personal"),
    (r"FOODPANDA|CAFE|RESTAURANT|KFC|MCDONALD S", "Food & dining", "unknown"),
    (r"DARAZ|IKEA|HOUSEHOLD|CLOTHING", "Shopping & household", "unknown"),
    (r"NAYATEL|PTCL|STORMFIBER|JAZZ|ZONG|UFONE|TELENOR|TRANSWORLD", "Internet & mobile", "unknown"),
    (r"ELECTRICITY|GAS BILL|K ELECTRIC|LESCO|IESCO|SSGC|SNGPL|WATER BILL", "Utilities", "unknown"),
    (r"CAREEM|INDRIVE|UBER|PSO|SHELL|TOTAL PARCO|TOLL", "Transport", "unknown"),
    (r"COMPUTER SHOP|LAPTOP|MONITOR|PAK LAP|PAKLAP|CZONE", "Equipment", "unknown"),
    (r"PHARMACY|HOSPITAL|CLINIC|LABORATORY", "Healthcare", "personal"),
    (r"CHARITY|DONATION|EDHI|CHHIPA", "Donations", "unknown"),
]
PATTERNS = [
    (re.compile(r"\b(?:" + pattern + r")\b"), category, purpose) for pattern, category, purpose in MERCHANTS
]


def classify(description: str, amount_minor: int, rules: list[dict] | None = None) -> dict:
    """Positive = money out; negative = money in, in every normalized account."""
    text = normalize(description)

    def result(kind, category, purpose, confidence, review, reason, rule_id):
        return Decision(kind, category, purpose, confidence, review, reason, rule_id).dict()

    if re.search(r"\b(PAYMENT THANK YOU|PAYMENT RECEIVED|CREDIT CARD PAYMENT|CARD REPAYMENT)\b", text):
        return result(
            "card_payment",
            "Card payment",
            "excluded",
            "high",
            False,
            "Card settlement is excluded to avoid counting the purchase twice.",
            "type.card-payment",
        )
    if re.search(r"\b(TRANSFER TO OWN SAVINGS|OWN ACCOUNT TRANSFER)\b", text):
        return result(
            "transfer",
            "Own-account transfer",
            "excluded",
            "high",
            False,
            "Description explicitly identifies an own-account movement.",
            "type.own-transfer",
        )
    if re.search(r"\b(ATM|CASH WITHDRAWAL)\b", text):
        return result(
            "cash",
            "Cash withdrawal",
            "unknown",
            "high",
            True,
            "Cash movement recognized; the statement cannot explain how cash was spent.",
            "type.cash",
        )

    matches = [(category, purpose) for pattern, category, purpose in PATTERNS if pattern.search(text)]
    categories = {category for category, _ in matches}
    refund_word = bool(re.search(r"\b(REFUND|REVERSAL|REVERSED)\b", text))
    if amount_minor < 0 and refund_word:
        category = matches[0][0] if len(categories) == 1 else "Uncategorized"
        return result(
            "refund",
            category,
            "unknown",
            "high" if category != "Uncategorized" else "unknown",
            True,
            "Credit explicitly says refund/reversal. Confirm the original expense and its purpose.",
            "type.refund",
        )
    if refund_word:
        return result(
            "unresolved",
            "Uncategorized",
            "unknown",
            "unknown",
            True,
            "Refund/reversal wording conflicts with an outgoing amount. Check the source.",
            "conflict.refund-direction",
        )
    if re.search(r"\b(IBFT|RAAST|TRANSFER|EASYPAISA|JAZZCASH|WALLET TOP UP)\b", text):
        decision = result(
            "transfer",
            "Transfer",
            "unknown",
            "suggested",
            True,
            "Transfer detected. Identify whether this is your account, family support, or another payment.",
            "type.transfer",
        )
        # Only exact, account-scoped user rules may identify a transfer's purpose.
        for rule in rules or []:
            if rule["match_text"] == text and (
                rule["kind"] == "transfer" or (rule["kind"] == "expense" and amount_minor > 0)
            ):
                return (
                    decision
                    | {k: rule[k] for k in ("kind", "category", "purpose", "business_percent")}
                    | {
                        "needs_review": False,
                        "category_confidence": "high",
                        "rule_id": "user.exact",
                        "reason": "Your exact-description rule for this account was applied.",
                    }
                )
        return decision
    if amount_minor < 0:
        if re.search(
            r"\b(CLIENT PAYMENT|FREELANCE PAYOUT|UPWORK PAYOUT|FIVERR PAYOUT|INWARD REMITTANCE)\b", text
        ):
            return result(
                "income",
                "Freelance income",
                "unknown",
                "suggested",
                True,
                "Possible freelance receipt. Confirm its source; no gross revenue or fees are inferred.",
                "type.income",
            )
        return result(
            "unresolved",
            "Uncategorized",
            "unknown",
            "unknown",
            True,
            "Incoming funds may be a refund, transfer, or income. Confirm the transaction type.",
            "unknown.credit",
        )
    if re.search(r"\b(TAX|LEVY|WITHHOLDING|FED)\b", text):
        return result(
            "expense",
            "Taxes & levies",
            "unknown",
            "high",
            True,
            "Separately posted tax/levy. Confirm purpose; no deductibility is inferred.",
            "type.levy",
        )
    if re.search(r"\b(FEE|CHARGES|MARKUP|INTEREST)\b", text) and not matches:
        return result(
            "expense",
            "Bank fees",
            "unknown",
            "high",
            True,
            "Explicit fee or financing charge. Confirm whether it relates to business use.",
            "type.fee",
        )
    for rule in rules or []:
        if rule["match_text"] == text and rule["kind"] == "expense":
            return result(
                "expense",
                rule["category"],
                rule["purpose"],
                "high",
                False,
                "Your exact-description rule for this account was applied.",
                "user.exact",
            ) | {"business_percent": rule["business_percent"]}
    if len(categories) > 1:
        return result(
            "expense",
            "Uncategorized",
            "unknown",
            "unknown",
            True,
            "Multiple category rules matched. A person must resolve the conflict.",
            "conflict.merchant",
        )
    if matches:
        category, purpose = matches[0]
        return result(
            "expense",
            category,
            purpose,
            "high",
            purpose == "unknown",
            f"Recognized {category.lower()} merchant. "
            + (
                "Business purpose cannot be determined from a merchant name."
                if purpose == "unknown"
                else "Personal-use default; you can correct it."
            ),
            "merchant." + category.lower().replace(" ", "-"),
        )
    return result(
        "expense",
        "Uncategorized",
        "unknown",
        "unknown",
        True,
        "No reliable merchant rule matched. Choose a category and purpose.",
        "unknown.merchant",
    )
