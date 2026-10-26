from dataclasses import dataclass
from typing import Literal

from app.core.domain import AccountType


class IngestError(ValueError):
    """The whole file cannot be read."""


class UnsupportedFormatError(IngestError):
    """The header row matches no known bank layout."""


@dataclass(frozen=True)
class FormatProfile:
    name: str
    headers: tuple[str, ...]
    date_column: str
    description_column: str
    date_format: str
    amount_mode: Literal["signed", "debit_credit"]
    account_type: AccountType
    amount_column: str | None = None
    debit_column: str | None = None
    credit_column: str | None = None
    currency: str | None = None  # fixed currency, if the file has no currency column
    currency_column: str | None = None

    @property
    def header_set(self) -> frozenset[str]:
        return frozenset(self.headers)


BANK_A_CARD = FormatProfile(
    name="bank_a_card",
    headers=("Date", "Description", "Amount", "Currency"),
    date_column="Date",
    description_column="Description",
    date_format="%Y-%m-%d",
    amount_mode="signed",
    account_type="card",
    amount_column="Amount",
    currency_column="Currency",
)

BANK_B_CHECKING = FormatProfile(
    name="bank_b_checking",
    headers=("Txn Date", "Details", "Debit", "Credit", "Balance"),
    date_column="Txn Date",
    description_column="Details",
    date_format="%d/%m/%Y",
    amount_mode="debit_credit",
    account_type="bank",
    debit_column="Debit",
    credit_column="Credit",
    currency="PKR",
)

PROFILES: tuple[FormatProfile, ...] = (BANK_A_CARD, BANK_B_CHECKING)


def detect_profile(header: list[str]) -> FormatProfile:
    names = [cell.strip() for cell in header]
    for profile in PROFILES:
        if len(names) == len(profile.headers) and frozenset(names) == profile.header_set:
            return profile
    supported = "; ".join(f"{p.name}: {','.join(p.headers)}" for p in PROFILES)
    raise UnsupportedFormatError(
        f"Unrecognised header row: {','.join(names)!r}. Supported formats: {supported}"
    )

PROFILES_BY_NAME: dict[str, FormatProfile] = {p.name: p for p in PROFILES}
