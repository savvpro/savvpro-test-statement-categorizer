"""Plain-English explanations shown next to every decision."""

from app.domain.enums import Category, Flag
from app.domain.taxonomy import info


def label(category: Category) -> str:
    return info(category).label


def structural(category: Category) -> str:
    return (
        f"Looks like a {label(category).lower()}, which is not counted on Schedule E."
        if (info(category).schedule_e_line is None)
        else f"Description matches a standard {label(category).lower()} pattern."
    )


def merchant(alias: str, category: Category) -> str:
    return f"Matched known merchant '{alias.title()}' → {label(category)}."


def keyword(token: str, category: Category) -> str:
    return f"Description contains '{token.lower()}' → {label(category)}."


def fuzzy(alias: str, ratio: float, category: Category) -> str:
    return f"Looks like '{alias.title()}' ({ratio:.0f}% similar) → {label(category)}."


def memory(merchant_key: str, category: Category) -> str:
    return f"You previously marked '{merchant_key.title()}' as {label(category)}."


def recurring(category: Category) -> str:
    return f"Same payer and amount repeat monthly, consistent with {label(category).lower()}."


FLAG_TEXT: dict[Flag, str] = {
    Flag.MIXED_USE_MERCHANT: "This store sells both business and personal items. Please confirm.",
    Flag.POSSIBLE_CAPITAL_IMPROVEMENT: (
        "Over the de-minimis limit, so this may be a capital improvement (depreciated) "
        "rather than a repair."
    ),
    Flag.MORTGAGE_SPLIT_REQUIRED: (
        "Mortgage payments mix interest (deductible) and principal (not). "
        "Check your Form 1098 and confirm or split."
    ),
    Flag.PAYMENT_TO_INDIVIDUAL: (
        "Payment to a person. Could be a contractor or personal. Please choose."
    ),
    Flag.CHECK_NO_PAYEE: "A paper check doesn't say who it paid. Please choose a category.",
    Flag.DIRECTION_CONFLICT: (
        "Money came in from a merchant we'd expect you to pay, with no sign it's a refund."
    ),
    Flag.AMOUNT_OUTLIER: "The amount is unusual compared with other payments to this party.",
    Flag.UNKNOWN_MERCHANT: "We don't recognize this merchant.",
    Flag.LOW_INFORMATION: "The description is too short to tell what this is.",
    Flag.ZERO_AMOUNT: "Zero amount, probably a card authorization hold.",
    Flag.AMBIGUOUS_MATCH: "Two categories fit about equally well.",
    Flag.REFUND_EXCEEDS_PURCHASE: (
        "This refund is larger than the matching purchase in this statement. Please check it."
    ),
    Flag.RENT_REVERSAL: "A tenant payment was returned, so it reduces rent received.",
    Flag.POSSIBLE_1099: "Payments to this person total $600 or more. You may need to file a 1099.",
    Flag.RECURRING: "Recurring monthly payment.",
    Flag.DUPLICATE_PENDING: "Pending copy of a posted transaction, skipped.",
    Flag.DUPLICATE_FITID: "The bank sent this transaction twice (same transaction ID), skipped.",
    Flag.DUPLICATE_PRIOR_UPLOAD: "Already imported from an earlier statement, skipped.",
}


def low_confidence(category: Category, confidence: float) -> str:
    return f"Best guess is {label(category)}, but confidence is only {confidence:.0%}."
