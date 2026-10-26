"""Normalize every amount to the canonical rule: > 0 is money in, < 0 is money out."""

import re
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from app.brain.models import AccountType

_PAYMENT_RE = re.compile(r"\b(PAYMENT|THANK YOU|AUTOPAY|AUTO PAY)\b", re.IGNORECASE)
DEBIT_TYPES = {"DR", "DEBIT"}
CREDIT_TYPES = {"CR", "CREDIT"}


class SignConvention(StrEnum):
    debit_credit_columns = "debit_credit_columns"  # amount = |credit| - |debit|
    type_column = "type_column"  # sign taken from a DR/CR type column
    cr_dr_markers = "cr_dr_markers"  # "45.00 CR" style values in a single column
    as_is = "as_is"  # checking: already money-in positive
    charges_positive = "charges_positive"  # card export with charges > 0: flip
    charges_negative = "charges_negative"  # card export with charges < 0: keep


@dataclass(frozen=True, slots=True)
class AmountFields:
    """A row's amount cells after parsing, before sign normalization."""

    amount: Decimal | None = None
    marker: str | None = None
    debit: Decimal | None = None
    credit: Decimal | None = None
    type_value: str | None = None


@dataclass(frozen=True, slots=True)
class SignDecision:
    convention: SignConvention
    reason: str
    warning: str | None = None


def normalize_type(value: str) -> str:
    return re.sub(r"[^A-Z]", "", value.upper())


def is_type_column(values: list[str]) -> bool:
    """A type column decides signs only if every non-blank value is DR/CR/DEBIT/CREDIT."""
    known = DEBIT_TYPES | CREDIT_TYPES
    present = [normalize_type(v) for v in values if v.strip()]
    return bool(present) and all(v in known for v in present)


def decide(
    rows: list[tuple[str, AmountFields]],
    *,
    account_type: AccountType,
    split_amounts: bool,
    type_column: bool,
    charges_positive: bool | None,
) -> SignDecision:
    if split_amounts:
        return SignDecision(
            SignConvention.debit_credit_columns, "separate debit and credit columns"
        )
    if type_column:
        return SignDecision(SignConvention.type_column, "DR/CR type column")
    if any(fields.marker for _, fields in rows):
        return SignDecision(SignConvention.cr_dr_markers, "amounts carry CR/DR markers")
    if account_type is AccountType.checking:
        return SignDecision(SignConvention.as_is, "checking statements list money out as negative")
    return _decide_card(rows, charges_positive)


def _decide_card(
    rows: list[tuple[str, AmountFields]], charges_positive: bool | None
) -> SignDecision:
    if charges_positive is not None:
        convention = (
            SignConvention.charges_positive if charges_positive else SignConvention.charges_negative
        )
        return SignDecision(convention, "set explicitly by the uploader")

    amounts = [(d, f.amount) for d, f in rows if f.amount]
    payments = [a for d, a in amounts if _PAYMENT_RE.search(d)]
    neg = sum(1 for a in payments if a < 0)
    pos = len(payments) - neg
    if neg != pos:
        convention = (
            SignConvention.charges_positive if neg > pos else SignConvention.charges_negative
        )
        side = "negative" if neg > pos else "positive"
        return SignDecision(
            convention, f"{max(neg, pos)} of {len(payments)} card payment rows are {side}"
        )

    pos = sum(1 for _, a in amounts if a > 0)
    neg = len(amounts) - pos
    convention = SignConvention.charges_positive if pos > neg else SignConvention.charges_negative
    return SignDecision(
        convention,
        f"majority vote: {pos} positive vs {neg} negative rows",
        warning=(
            "Could not find card payment rows to confirm the sign convention; guessed "
            f"{convention.value} by majority vote. Set it explicitly if totals look inverted."
        ),
    )


def apply(fields: AmountFields, convention: SignConvention, account_type: AccountType) -> Decimal:
    if convention is SignConvention.debit_credit_columns:
        return abs(fields.credit or Decimal(0)) - abs(fields.debit or Decimal(0))

    if fields.amount is None:
        raise ValueError("single-column convention needs an amount")
    if convention is SignConvention.type_column:
        magnitude = abs(fields.amount)
        return magnitude if fields.type_value in CREDIT_TYPES else -magnitude
    if convention is SignConvention.cr_dr_markers:
        # Marked values are already signed by the parser. Unmarked card values are charges.
        if fields.marker or account_type is AccountType.checking:
            return fields.amount
        return -fields.amount
    if convention is SignConvention.charges_positive:
        return -fields.amount
    return fields.amount
