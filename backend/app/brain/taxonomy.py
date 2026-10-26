"""Schedule C taxonomy: single source of truth for categories and kinds."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class TxKind(StrEnum):
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"
    CC_PAYMENT = "cc_payment"
    OWNER_DRAW = "owner_draw"
    OWNER_CONTRIB = "owner_contrib"
    TAX_PAYMENT = "tax_payment"
    LOAN_PAYMENT = "loan_payment"
    REFUND = "refund"
    INTEREST_INCOME = "interest_income"
    INTEREST_EXPENSE = "interest_expense"
    FEE = "fee"
    PERSONAL = "personal"
    UNKNOWN = "unknown"

    @property
    def is_pl(self) -> bool:
        """Does this kind affect P&L?"""
        return self in {TxKind.INCOME, TxKind.EXPENSE, TxKind.REFUND,
                        TxKind.INTEREST_INCOME, TxKind.FEE}


class CategoryGroup(StrEnum):
    INCOME = "income"
    EXPENSE = "expense"
    NON_PL = "non_pl"


@dataclass(frozen=True)
class Category:
    slug: str
    name: str
    group: CategoryGroup
    schedule_c_line: str | None
    deductible_pct: int = 100  # percentage 0-100
    color: str = "#64748b"
    icon: str = "circle"
    description: str = ""
    always_review: bool = False  # flag even if confident
    mixed_use: bool = False  # Amazon, etc.


# ── Income categories ──────────────────────────────────────────────────────────
CAT_CLIENT_INCOME = Category(
    slug="client_income", name="Client Income", group=CategoryGroup.INCOME,
    schedule_c_line="L1", color="#1D6B48", icon="briefcase",
    description="Revenue from clients and customers",
)
CAT_OTHER_INCOME = Category(
    slug="other_income", name="Other Income", group=CategoryGroup.INCOME,
    schedule_c_line="L6", color="#2D9D6E", icon="plus-circle",
    description="Other business income",
)
CAT_INTEREST_INCOME = Category(
    slug="interest_income", name="Interest Income", group=CategoryGroup.INCOME,
    schedule_c_line="Sch B", color="#4ade80", icon="trending-up",
    description="Interest earned (informational, reported on Schedule B)",
)

# ── Expense categories ─────────────────────────────────────────────────────────
CAT_ADVERTISING = Category(
    slug="advertising", name="Advertising", group=CategoryGroup.EXPENSE,
    schedule_c_line="L8", color="#7c3aed", icon="megaphone",
    description="Ads, promotions, marketing spend",
)
CAT_CAR_TRUCK = Category(
    slug="car_truck", name="Car & Truck", group=CategoryGroup.EXPENSE,
    schedule_c_line="L9", color="#6d28d9", icon="car",
    description="Business vehicle expenses",
    always_review=True,
)
CAT_COMMISSIONS = Category(
    slug="commissions", name="Commissions & Fees", group=CategoryGroup.EXPENSE,
    schedule_c_line="L10", color="#8b5cf6", icon="percent",
    description="Payment processing fees (Stripe, PayPal), platform commissions",
)
CAT_CONTRACT_LABOR = Category(
    slug="contract_labor", name="Contract Labor", group=CategoryGroup.EXPENSE,
    schedule_c_line="L11", color="#a78bfa", icon="users",
    description="Payments to contractors/freelancers",
)
CAT_INSURANCE = Category(
    slug="insurance", name="Insurance", group=CategoryGroup.EXPENSE,
    schedule_c_line="L15", color="#0ea5e9", icon="shield",
    description="Business insurance premiums",
)
CAT_INTEREST_EXP = Category(
    slug="interest_expense", name="Interest (Business Loan)", group=CategoryGroup.EXPENSE,
    schedule_c_line="L16b", color="#38bdf8", icon="credit-card",
    description="Interest on business loans",
)
CAT_LEGAL_PROF = Category(
    slug="legal_professional", name="Legal & Professional", group=CategoryGroup.EXPENSE,
    schedule_c_line="L17", color="#0284c7", icon="scale",
    description="Attorneys, CPAs, consultants",
)
CAT_OFFICE_EXPENSE = Category(
    slug="office_expense", name="Office Expense", group=CategoryGroup.EXPENSE,
    schedule_c_line="L18", color="#0369a1", icon="printer",
    description="Office supplies, postage, small office items",
)
CAT_RENT_COWORK = Category(
    slug="rent_cowork", name="Rent (Coworking / Office)", group=CategoryGroup.EXPENSE,
    schedule_c_line="L20b", color="#1e40af", icon="building-2",
    description="Coworking memberships, office rent",
)
CAT_REPAIRS = Category(
    slug="repairs", name="Repairs & Maintenance", group=CategoryGroup.EXPENSE,
    schedule_c_line="L21", color="#1e3a8a", icon="wrench",
    description="Repairs on business assets",
)
CAT_SUPPLIES = Category(
    slug="supplies", name="Supplies", group=CategoryGroup.EXPENSE,
    schedule_c_line="L22", color="#3730a3", icon="package",
    description="Office and business supplies",
)
CAT_TAXES_LICENSES = Category(
    slug="taxes_licenses", name="Taxes & Licenses", group=CategoryGroup.EXPENSE,
    schedule_c_line="L23", color="#4338ca", icon="file-text",
    description="Business licenses, state taxes paid",
)
CAT_TRAVEL = Category(
    slug="travel", name="Travel", group=CategoryGroup.EXPENSE,
    schedule_c_line="L24a", color="#b45309", icon="plane",
    description="Flights, hotels, ground transport for business travel",
)
CAT_MEALS = Category(
    slug="meals", name="Meals (50%)", group=CategoryGroup.EXPENSE,
    schedule_c_line="L24b", deductible_pct=50, color="#d97706", icon="utensils",
    description="Business meals, 50% deductible",
)
CAT_UTILITIES = Category(
    slug="utilities", name="Utilities (Phone / Internet)", group=CategoryGroup.EXPENSE,
    schedule_c_line="L25", color="#dc2626", icon="wifi",
    description="Business phone, internet, utilities",
)
CAT_SOFTWARE = Category(
    slug="software", name="Software & Subscriptions", group=CategoryGroup.EXPENSE,
    schedule_c_line="L27a", color="#059669", icon="monitor",
    description="SaaS tools, subscriptions, cloud services",
)
CAT_EDUCATION = Category(
    slug="education", name="Education & Training", group=CategoryGroup.EXPENSE,
    schedule_c_line="L27a", color="#0d9488", icon="book-open",
    description="Courses, books, conferences",
)
CAT_BANK_FEES = Category(
    slug="bank_fees", name="Bank & Service Fees", group=CategoryGroup.EXPENSE,
    schedule_c_line="L27a", color="#64748b", icon="landmark",
    description="Monthly service fees, wire fees, ATM fees",
)
CAT_EQUIPMENT = Category(
    slug="equipment", name="Equipment & Assets", group=CategoryGroup.EXPENSE,
    schedule_c_line="L13", color="#7f1d1d", icon="cpu",
    description="Business equipment, always review if > $2,500 (de minimis safe harbor)",
    always_review=True,
)

# ── Non-P&L categories (tracked but excluded from profit calc) ─────────────────
CAT_NON_PL = Category(
    slug="non_pl", name="Non-P&L Movement", group=CategoryGroup.NON_PL,
    schedule_c_line=None, color="#94a3b8", icon="arrow-right-left",
    description="Transfers, card payments, owner draws, tax payments",
)

# ── Lookup helpers ─────────────────────────────────────────────────────────────
ALL_CATEGORIES: list[Category] = [
    CAT_CLIENT_INCOME, CAT_OTHER_INCOME, CAT_INTEREST_INCOME,
    CAT_ADVERTISING, CAT_CAR_TRUCK, CAT_COMMISSIONS, CAT_CONTRACT_LABOR,
    CAT_INSURANCE, CAT_INTEREST_EXP, CAT_LEGAL_PROF, CAT_OFFICE_EXPENSE,
    CAT_RENT_COWORK, CAT_REPAIRS, CAT_SUPPLIES, CAT_TAXES_LICENSES,
    CAT_TRAVEL, CAT_MEALS, CAT_UTILITIES, CAT_SOFTWARE, CAT_EDUCATION,
    CAT_BANK_FEES, CAT_EQUIPMENT, CAT_NON_PL,
]

CATEGORY_BY_SLUG: dict[str, Category] = {c.slug: c for c in ALL_CATEGORIES}


def get_category(slug: str) -> Category:
    if slug not in CATEGORY_BY_SLUG:
        raise KeyError(f"Unknown category slug {slug!r}")
    return CATEGORY_BY_SLUG[slug]
