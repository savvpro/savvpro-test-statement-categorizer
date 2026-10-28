"""Category metadata: labels, Schedule E lines and which money directions are allowed."""

from dataclasses import dataclass

from app.domain.enums import Category, CategoryKind, Direction

IN = frozenset({Direction.INFLOW})
OUT = frozenset({Direction.OUTFLOW})
BOTH = frozenset({Direction.INFLOW, Direction.OUTFLOW})


@dataclass(frozen=True, slots=True)
class CategoryInfo:
    code: Category
    label: str
    kind: CategoryKind
    schedule_e_line: str | None
    allowed_directions: frozenset[Direction]


_C = Category
_K = CategoryKind

TAXONOMY: dict[Category, CategoryInfo] = {
    info.code: info
    for info in (
        CategoryInfo(_C.RENT, "Rents received", _K.INCOME, "3", IN),
        CategoryInfo(_C.ADVERTISING, "Advertising", _K.EXPENSE, "5", OUT),
        CategoryInfo(_C.AUTO_TRAVEL, "Auto and travel", _K.EXPENSE, "6", OUT),
        CategoryInfo(_C.CLEANING_MAINTENANCE, "Cleaning and maintenance", _K.EXPENSE, "7", OUT),
        CategoryInfo(_C.COMMISSIONS, "Commissions", _K.EXPENSE, "8", OUT),
        CategoryInfo(_C.INSURANCE, "Insurance", _K.EXPENSE, "9", OUT),
        CategoryInfo(
            _C.LEGAL_PROFESSIONAL, "Legal and other professional fees", _K.EXPENSE, "10", OUT
        ),
        CategoryInfo(_C.MANAGEMENT_FEES, "Management fees", _K.EXPENSE, "11", OUT),
        CategoryInfo(
            _C.MORTGAGE_INTEREST, "Mortgage interest paid to banks", _K.EXPENSE, "12", OUT
        ),
        CategoryInfo(_C.OTHER_INTEREST, "Other interest", _K.EXPENSE, "13", OUT),
        CategoryInfo(_C.REPAIRS, "Repairs", _K.EXPENSE, "14", OUT),
        CategoryInfo(_C.SUPPLIES, "Supplies", _K.EXPENSE, "15", OUT),
        CategoryInfo(_C.TAXES, "Taxes", _K.EXPENSE, "16", OUT),
        CategoryInfo(_C.UTILITIES, "Utilities", _K.EXPENSE, "17", OUT),
        CategoryInfo(_C.OTHER_EXPENSE, "Other", _K.EXPENSE, "19", OUT),
        CategoryInfo(
            _C.SECURITY_DEPOSIT_RECEIVED, "Security deposit received", _K.NON_PNL, None, IN
        ),
        CategoryInfo(
            _C.SECURITY_DEPOSIT_RETURNED, "Security deposit returned", _K.NON_PNL, None, OUT
        ),
        CategoryInfo(_C.LOAN_PRINCIPAL, "Loan principal", _K.NON_PNL, None, OUT),
        CategoryInfo(_C.CAPITAL_IMPROVEMENT, "Capital improvement", _K.NON_PNL, None, OUT),
        CategoryInfo(_C.TRANSFER, "Transfer between accounts", _K.NON_PNL, None, BOTH),
        CategoryInfo(_C.CARD_PAYMENT, "Credit card payment", _K.NON_PNL, None, BOTH),
        CategoryInfo(_C.OWNER_CONTRIBUTION, "Owner contribution", _K.NON_PNL, None, IN),
        CategoryInfo(_C.OWNER_DRAW, "Owner draw", _K.NON_PNL, None, OUT),
        CategoryInfo(_C.PERSONAL, "Personal (not deductible)", _K.NON_PNL, None, BOTH),
        CategoryInfo(_C.INTEREST_EARNED, "Interest earned", _K.NON_PNL, None, IN),
    )
}


def info(category: Category) -> CategoryInfo:
    return TAXONOMY[category]


def is_allowed(category: Category, direction: Direction, *, is_refund: bool = False) -> bool:
    """Whether a category may be applied to money moving in `direction`.

    Refunds keep their expense category on an inflow; rent reversals keep RENT on an outflow.
    """
    meta = TAXONOMY[category]
    if direction in meta.allowed_directions:
        return True
    if is_refund and meta.kind is CategoryKind.EXPENSE and direction is Direction.INFLOW:
        return True
    return is_refund and category is Category.RENT and direction is Direction.OUTFLOW
