"""Stage 2: who is on the other side. Tenants paying rent, deposits, people, paper checks."""

import re

from app.brain.state import RowState
from app.domain.enums import AccountType, Category, Direction, Flag

DEPOSIT_RE = re.compile(r"\b(SECURITY|SEC DEP|DEPOSIT)\b")
DEPOSIT_RETURN_RE = re.compile(
    r"\b(DEPOSIT|SEC DEP)\b.*\b(RETURN|REFUND)|\b(RETURN|REFUND)\b.*\bDEPOSIT\b"
)
RENT_RE = re.compile(r"\bRENT\b")
NOT_RENT_RE = re.compile(
    r"(HELP|GIFT|LOAN|PARENT|PARENTS|FAMILY|REIMBURSEMENT|REFUND|PERSONAL|INVEST(MENT)?)"
)
RENT_EXTRA_RE = re.compile(r"\b(LATE FEE|PET (FEE|RENT)|PARKING FEE)\b")
BUSINESS_TOKENS = frozenset(
    {
        "LLC",
        "INC",
        "CO",
        "CORP",
        "LTD",
        "LP",
        "COMPANY",
        "SERVICES",
        "SERVICE",
        "GROUP",
        "PLUMBING",
        "ROOFING",
        "HVAC",
        "ELECTRIC",
        "CLEANING",
        "LANDSCAPING",
        "MGMT",
        "MANAGEMENT",
        "REALTY",
        "PROPERTIES",
        "HOA",
        "ASSOCIATION",
        "BANK",
        "INSURANCE",
        "CONSTRUCTION",
        "CONTRACTORS",
        "REPAIR",
        "REPAIRS",
        "LAW",
        "CPA",
    }
)


def looks_like_person(name: str | None) -> bool:
    if not name:
        return False
    tokens = name.split()
    return (
        2 <= len(tokens) <= 4
        and all(t.isalpha() for t in tokens)
        and not any(t in BUSINESS_TOKENS for t in tokens)
    )


def apply(state: RowState) -> None:
    txn = state.txn
    text = state.text

    if txn.channel == "CHECK" and txn.direction is Direction.OUTFLOW:
        state.flags.add(Flag.CHECK_NO_PAYEE)
        return

    if not state.is_p2p:
        _rent_word_inflow(state)
        return
    if not looks_like_person(txn.counterparty):
        _rent_word_inflow(state)
        return

    who = (txn.counterparty or "").title()
    if txn.direction is Direction.INFLOW and txn.account_type is AccountType.CHECKING:
        if DEPOSIT_RE.search(text) and not RENT_RE.search(text):
            state.add(
                Category.SECURITY_DEPOSIT_RECEIVED,
                0.92,
                "channel",
                "ch.deposit_in",
                f"Payment from {who} mentions a deposit. Deposits are held for the tenant, "
                "not income.",
            )
            state.add(Category.RENT, 0.30, "channel", "ch.rent_weak", f"Payment from {who}.")
        elif RENT_RE.search(text) or RENT_EXTRA_RE.search(text):
            state.add(
                Category.RENT,
                0.92,
                "channel",
                "ch.rent_memo",
                f"Payment from {who} with a rent-related memo.",
            )
        else:
            state.add(
                Category.RENT,
                0.70,
                "channel",
                "ch.rent_person",
                f"Payment from a person ({who}). Often rent, but there's no memo.",
            )
    elif txn.direction is Direction.OUTFLOW:
        if DEPOSIT_RETURN_RE.search(text):
            state.add(
                Category.SECURITY_DEPOSIT_RETURNED,
                0.92,
                "channel",
                "ch.deposit_out",
                f"Deposit returned to {who}. Not an expense.",
            )
        else:
            state.flags.add(Flag.PAYMENT_TO_INDIVIDUAL)


def _is_checking_inflow(state: RowState) -> bool:
    txn = state.txn
    return txn.direction is Direction.INFLOW and txn.account_type is AccountType.CHECKING


def _rent_word_inflow(state: RowState) -> None:
    """Rent can also arrive as an ACH/OFX credit, or a P2P memo we couldn't split from the name."""
    if (
        _is_checking_inflow(state)
        and RENT_RE.search(state.text)
        and not DEPOSIT_RE.search(state.text)
        and not NOT_RENT_RE.search(state.text)
    ):
        state.add(Category.RENT, 0.90, "channel", "ch.rent_word", "Deposit mentions rent.")


def person_inflow_fallback(state: RowState) -> None:
    """Runs after merchant/keyword matching: an unexplained credit naming a person is often rent."""
    txn = state.txn
    if state.candidates or state.is_p2p or not _is_checking_inflow(state):
        return
    if looks_like_person(txn.merchant_key):
        state.add(
            Category.RENT,
            0.70,
            "channel",
            "ch.rent_person",
            f"Payment from a person ({txn.merchant_key.title()}). Often rent, but there's no memo.",
        )
