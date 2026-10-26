import datetime as dt
from decimal import Decimal

from app.brain.engine import categorize
from app.brain.models import AccountType, Decision, ParsedRow


def row(
    description: str, amount: str, day: int = 5, month: int = 1, pending: bool = False
) -> tuple[str, str, int, int, bool]:
    return (description, amount, day, month, pending)


def decide(
    *specs: tuple[str, str, int, int, bool] | tuple[str, str],
    account: AccountType = AccountType.checking,
    user_rules: dict[str, str] | None = None,
    **kwargs: object,
) -> list[Decision]:
    rows = []
    for index, spec in enumerate(specs):
        description, amount, day, month, pending = (*spec, 5, 1, False)[:5]
        rows.append(
            ParsedRow(index, dt.date(2026, month, day), description, Decimal(amount), pending)
        )
    return categorize(rows, account, user_rules, **kwargs)  # type: ignore[arg-type]


def one(description: str, amount: str, **kwargs: object) -> Decision:
    return decide((description, amount), **kwargs)[0]  # type: ignore[arg-type]
