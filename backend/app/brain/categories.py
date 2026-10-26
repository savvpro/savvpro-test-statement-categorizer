"""Category catalogue for a rideshare / delivery driver filing a US Schedule C.

Every category has a *kind* that decides how it is counted in the tax summary:

* ``income``   - business income (Schedule C, Part I)
* ``expense``  - deductible business expense (Schedule C, Part II)
* ``personal`` - real spending, but not deductible
* ``transfer`` - money moving between the user's own accounts; not income or spending
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Kind(StrEnum):
    INCOME = "income"
    EXPENSE = "expense"
    PERSONAL = "personal"
    TRANSFER = "transfer"


@dataclass(frozen=True, slots=True)
class Category:
    id: str
    label: str
    kind: Kind
    schedule_c_line: str | None
    description: str
    # Largest single purchase we consider normal. Anything above is sent to review.
    max_typical_amount: int | None = None


CATEGORIES: tuple[Category, ...] = (
    Category(
        "platform_income",
        "Gig Platform Income",
        Kind.INCOME,
        "Line 1",
        "Payouts from Uber, Lyft, DoorDash, Instacart, Grubhub and similar platforms.",
    ),
    Category(
        "other_income",
        "Other Business Income",
        Kind.INCOME,
        "Line 6",
        "Other business income such as referral bonuses paid outside a platform.",
    ),
    Category(
        "fuel",
        "Fuel & EV Charging",
        Kind.EXPENSE,
        "Line 9",
        "Gas and EV charging. Only deductible with the actual-expense method.",
        max_typical_amount=200,
    ),
    Category(
        "vehicle_maintenance",
        "Vehicle Maintenance & Car Wash",
        Kind.EXPENSE,
        "Line 9",
        "Oil changes, tires, repairs, parts and car washes.",
        max_typical_amount=2500,
    ),
    Category(
        "tolls_parking",
        "Tolls & Parking",
        Kind.EXPENSE,
        "Line 9",
        "Business tolls and parking. Deductible even with the standard mileage rate.",
        max_typical_amount=150,
    ),
    Category(
        "vehicle_insurance",
        "Vehicle Insurance",
        Kind.EXPENSE,
        "Line 15",
        "Auto and rideshare insurance (business-use share).",
        max_typical_amount=1500,
    ),
    Category(
        "vehicle_lease_loan",
        "Car Lease / Loan Payment",
        Kind.EXPENSE,
        "Line 20a",
        "Lease payments are deductible; for a loan only the interest is.",
    ),
    Category(
        "phone_data",
        "Phone & Data",
        Kind.EXPENSE,
        "Line 25",
        "Mobile phone and data plan (business-use share).",
        max_typical_amount=400,
    ),
    Category(
        "software_services",
        "Apps, Software & Tax Prep",
        Kind.EXPENSE,
        "Line 27a",
        "Mileage trackers, driver apps, bookkeeping and tax-prep software.",
        max_typical_amount=500,
    ),
    Category(
        "supplies",
        "Driver Supplies",
        Kind.EXPENSE,
        "Line 22",
        "Phone mounts, chargers, insulated delivery bags, passenger water.",
        max_typical_amount=500,
    ),
    Category(
        "licenses_fees",
        "Licenses, Registration & Checks",
        Kind.EXPENSE,
        "Line 23",
        "Vehicle registration, driver licence fees, background checks, inspections.",
        max_typical_amount=600,
    ),
    Category(
        "bank_fees",
        "Bank Fees & Interest",
        Kind.EXPENSE,
        "Line 27a",
        "Account fees, foreign transaction fees and card interest on the business account.",
        max_typical_amount=300,
    ),
    Category(
        "personal",
        "Personal (not deductible)",
        Kind.PERSONAL,
        None,
        "Groceries, restaurants, entertainment and other personal spending.",
    ),
    Category(
        "transfer",
        "Transfers & Card Payments",
        Kind.TRANSFER,
        None,
        "Moving money between your own accounts, card payments and ATM cash.",
    ),
)

BY_ID: dict[str, Category] = {c.id: c for c in CATEGORIES}


def get(category_id: str) -> Category:
    try:
        return BY_ID[category_id]
    except KeyError:
        raise ValueError(f"Unknown category: {category_id!r}") from None


def is_valid(category_id: str) -> bool:
    return category_id in BY_ID
