import re
from dataclasses import dataclass
from decimal import Decimal

from .models import Category


@dataclass(frozen=True)
class Decision:
    category: Category
    explanation: str


MERCHANT_RULES = (
    (r"ADOBE(?: CREATIVE CLOUD)?", Category.SOFTWARE, "Adobe subscription"),
    (r"GITHUB(?: COPILOT)?", Category.SOFTWARE, "GitHub subscription"),
    (r"JETBRAINS", Category.SOFTWARE, "JetBrains subscription"),
    (r"FIGMA", Category.SOFTWARE, "Figma subscription"),
    (r"AWS(?: BILLING)?", Category.CLOUD, "AWS hosting"),
    (r"DIGITALOCEAN", Category.CLOUD, "DigitalOcean hosting"),
    (r"VERCEL", Category.CLOUD, "Vercel hosting"),
    (r"UBER TRIP", Category.TRAVEL, "Uber trip"),
    (r"TRAIN TICKET", Category.TRAVEL, "train ticket"),
    (r"(?:NAYATEL|PTCL) INTERNET(?: BILL)?", Category.TELECOM, "internet service bill"),
    (r"BANK (?:FEE|FEES|CHARGES)|MONTHLY ACCOUNT FEE", Category.FEES, "bank fee"),
)


def normalize_description(description: str) -> str:
    return " ".join(re.sub(r"[^A-Z0-9]+", " ", description.upper()).split())


def categorize(
    description: str, amount: Decimal, transaction_type: str = ""
) -> Decision:
    description = normalize_description(description)
    transaction_type = normalize_description(transaction_type)
    if amount == 0:
        return Decision(
            Category.REVIEW,
            "Zero amount. Check this entry against the original statement.",
        )

    is_transfer = transaction_type == "INTERNAL TRANSFER" or bool(
        re.fullmatch(
            r"(?:INTERNAL TRANSFER(?: (?:TO|FROM) (?:OWN )?SAVINGS(?: ACCOUNT)?)?"
            r"|TRANSFER (?:TO|FROM) (?:OWN )?SAVINGS(?: ACCOUNT)?"
            r"|TRANSFER BETWEEN OWN ACCOUNTS)",
            description,
        )
    )
    is_refund = transaction_type == "REFUND" or bool(
        re.match(r"^REFUND\b", description) or re.search(r"\bREFUND$", description)
    )
    is_client_payment = transaction_type == "CLIENT PAYMENT" or bool(
        re.match(r"^CLIENT PAYMENT\b", description)
    )
    if is_refund and (is_transfer or is_client_payment):
        return Decision(
            Category.REVIEW,
            "Conflicting refund and payment-type indicators. Please check the payment.",
        )
    if is_transfer:
        return Decision(
            Category.TRANSFER,
            "Explicit movement between own accounts. Excluded from income and expenses.",
        )
    if is_refund:
        if amount > 0:
            return Decision(
                Category.REFUND, "Incoming refund. Kept separate from client income."
            )
        return Decision(
            Category.REVIEW,
            "Refund indicator on an outgoing payment. Check its purpose.",
        )

    if amount > 0:
        if is_client_payment:
            return Decision(
                Category.INCOME,
                "Incoming payment explicitly identified as a client payment.",
            )
        return Decision(
            Category.REVIEW,
            "Incoming money without a clear client payment or refund indicator.",
        )

    if transaction_type in {"TRANSFER", "IBFT", "RAAST"} or re.match(
        r"^(?:TRANSFER|IBFT|RAAST)\b", description
    ):
        return Decision(
            Category.REVIEW,
            "Bank payment without clear internal-account or business-purpose details.",
        )

    for pattern, category, merchant in MERCHANT_RULES:
        if re.fullmatch(rf"(?:{pattern})(?: \d{{3,}})?", description):
            return Decision(category, f"Outgoing payment matched {merchant}.")
    return Decision(
        Category.REVIEW, "The description does not establish a clear business category."
    )
