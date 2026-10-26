from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import uuid4

RuleScope = Literal["shared", "user"]
Category = Literal[
    "Client Income",
    "Software",
    "Advertising & Marketing",
    "Internet & Phone",
    "Equipment",
    "Payment Processing Fees",
    "Travel & Transport",
    "Travel",
    "Meals",
    "Food & Dining",
    "Transport",
    "Shopping",
    "Utilities",
    "Health",
    "Entertainment",
    "Education",
    "Personal Care",
    "Electronics",
    "Other",
    "Office Expenses",
    "Taxes",
    "Transfer",
    "Refund",
    "Personal Expense",
    "Needs Review",
]


@dataclass
class Transaction:
    id: str
    date: date | None
    description: str
    amount: Decimal
    currency: str
    direction: Literal["income", "expense"]
    category: Category = "Needs Review"
    confidence: int = 0
    explanation: str = "No reliable rule matched this transaction."
    rule_id: str | None = None
    rule_scope: RuleScope | None = None
    needs_review: bool = True


@dataclass
class CategorizationRule:
    pattern: str
    category: Category
    scope: RuleScope
    source: Literal["built_in", "user_correction"]
    user_id: str | None = None
    exact: bool = False
    id: str = field(default_factory=lambda: str(uuid4()))


@dataclass
class Statement:
    id: str
    filename: str
    transactions: list[Transaction]
