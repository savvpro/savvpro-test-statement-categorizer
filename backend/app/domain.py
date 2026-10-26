"""Shared vocabulary. All persisted and aggregated amounts are integer minor units."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Kind = Literal["expense", "refund", "income", "transfer", "personal", "unknown"]
EXPENSE_CATEGORIES = {
    "software": "Software & subscriptions",
    "office": "Office & equipment",
    "services": "Professional services",
    "marketing": "Marketing",
    "travel": "Travel",
    "meals": "Meals",
    "fees": "Bank fees",
    "other": "Other business expense",
}
CATEGORIES = {
    **EXPENSE_CATEGORIES,
    "personal": "Personal",
    "income": "Income",
    "transfers": "Transfers",
    "uncategorized": "Uncategorized",
}
KIND_CATEGORIES = {
    "expense": list(EXPENSE_CATEGORIES),
    "refund": list(EXPENSE_CATEGORIES),
    "income": ["income"],
    "transfer": ["transfers"],
    "personal": ["personal"],
    "unknown": ["uncategorized"],
}
CURRENCIES = ("PKR", "USD", "GBP", "EUR")
ENGINE_VERSION = "1.0.0"
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_ROWS = 5000
MAX_AMOUNT_MINOR = 10**12  # Bounds also keep aggregate values exact in JS integers.


class ImportOptions(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    date_column: str = Field(min_length=1)
    description_column: str = Field(min_length=1)
    amount_column: str | None = None
    debit_column: str | None = None
    credit_column: str | None = None
    mode: Literal["signed", "split"]
    date_format: Literal["iso", "dmy", "mdy"]
    sign_convention: Literal["negative_outgoing", "positive_outgoing"]
    currency: Literal["PKR", "USD", "GBP", "EUR"]

    @model_validator(mode="after")
    def validate_columns(self):
        selected = [self.date_column, self.description_column]
        if self.mode == "signed":
            if not self.amount_column:
                raise ValueError("Select an amount column.")
            selected.append(self.amount_column)
        else:
            if not self.debit_column or not self.credit_column:
                raise ValueError("Select both debit and credit columns.")
            selected += [self.debit_column, self.credit_column]
        if len(selected) != len(set(selected)):
            raise ValueError("Map each field to a different column.")
        return self


class ReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["save", "reset", "duplicate"]
    kind: Kind | None = None
    category: str | None = None
    duplicate_action: Literal["keep", "exclude", "reset"] | None = None
    version: int = Field(ge=1)
