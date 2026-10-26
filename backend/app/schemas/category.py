"""Category definitions and single source of truth for default categories.

LedgerLens uses these 16 system categories to classify business and financial transactions.
Database models and seeding in later phases will reference this source of truth.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional


class DefaultCategory(str, Enum):
    """The 16 core categories supported by LedgerLens."""

    SOFTWARE = "Software"
    CLOUD_HOSTING = "Cloud Hosting"
    OFFICE_SUPPLIES = "Office Supplies"
    HARDWARE_AND_EQUIPMENT = "Hardware and Equipment"
    INTERNET_AND_TELECOM = "Internet and Telecommunications"
    ADVERTISING_AND_MARKETING = "Advertising and Marketing"
    PROFESSIONAL_SERVICES = "Professional Services"
    TRAVEL = "Travel"
    MEALS = "Meals"
    BANK_FEES = "Bank Fees"
    BUSINESS_INCOME = "Business Income"
    REFUND = "Refund"
    REVERSAL = "Reversal"
    INTERNAL_TRANSFER = "Internal Transfer"
    PERSONAL_EXPENSE = "Personal Expense"
    NEEDS_REVIEW = "Needs Review"


@dataclass(frozen=True)
class CategoryMetadata:
    """Metadata describing a category's intended purpose and examples."""

    name: str
    description: str
    example: str
    is_system_category: bool = True


DEFAULT_CATEGORIES: Dict[DefaultCategory, CategoryMetadata] = {
    DefaultCategory.SOFTWARE: CategoryMetadata(
        name=DefaultCategory.SOFTWARE.value,
        description="IDE licenses, developer tools, SaaS subscriptions, and digital productivity tools.",
        example="JetBrains, GitHub Copilot, Docker, Figma, Slack",
    ),
    DefaultCategory.CLOUD_HOSTING: CategoryMetadata(
        name=DefaultCategory.CLOUD_HOSTING.value,
        description="VPS, cloud compute, object storage, serverless platforms, and DNS infrastructure.",
        example="AWS, DigitalOcean, Heroku, Vercel, Cloudflare, Google Cloud",
    ),
    DefaultCategory.OFFICE_SUPPLIES: CategoryMetadata(
        name=DefaultCategory.OFFICE_SUPPLIES.value,
        description="Stationery, printer supplies, desk accessories, and physical office consumables.",
        example="Staples, Office Depot",
    ),
    DefaultCategory.HARDWARE_AND_EQUIPMENT: CategoryMetadata(
        name=DefaultCategory.HARDWARE_AND_EQUIPMENT.value,
        description="Computers, monitors, keyboards, test devices, and IT hardware equipment.",
        example="Apple Store, Dell, Micro Center, Lenovo",
    ),
    DefaultCategory.INTERNET_AND_TELECOM: CategoryMetadata(
        name=DefaultCategory.INTERNET_AND_TELECOM.value,
        description="Broadband internet, fiber service, mobile phone, and telecommunication services.",
        example="Comcast, AT&T, Verizon, Spectrum, Starlink",
    ),
    DefaultCategory.ADVERTISING_AND_MARKETING: CategoryMetadata(
        name=DefaultCategory.ADVERTISING_AND_MARKETING.value,
        description="Online advertising, sponsored posts, marketing tools, and promotion costs.",
        example="Google Ads, Meta Ads, LinkedIn Ads, Twitter Ads",
    ),
    DefaultCategory.PROFESSIONAL_SERVICES: CategoryMetadata(
        name=DefaultCategory.PROFESSIONAL_SERVICES.value,
        description="Legal fees, accounting and bookkeeping services, and specialized business consultations.",
        example="CPA Accounting, LegalZoom, Tax Consulting",
    ),
    DefaultCategory.TRAVEL: CategoryMetadata(
        name=DefaultCategory.TRAVEL.value,
        description="Business transport, airline tickets, trains, taxis, and lodging.",
        example="Uber, Lyft, Delta Air Lines, United Airlines, Amtrak",
    ),
    DefaultCategory.MEALS: CategoryMetadata(
        name=DefaultCategory.MEALS.value,
        description="Client dining, business meals during work travel, and food delivery.",
        example="Starbucks, Joe's Cafe, DoorDash, Uber Eats",
    ),
    DefaultCategory.BANK_FEES: CategoryMetadata(
        name=DefaultCategory.BANK_FEES.value,
        description="Account maintenance fees, wire charges, foreign transaction fees, and banking surcharges.",
        example="Monthly Maintenance Fee, Wire Transfer Fee, Overdraft Fee",
    ),
    DefaultCategory.BUSINESS_INCOME: CategoryMetadata(
        name=DefaultCategory.BUSINESS_INCOME.value,
        description="Freelance client payments, consulting retainers, and business revenues.",
        example="Client Payment, Invoice #1024, Retainer Deposit",
    ),
    DefaultCategory.REFUND: CategoryMetadata(
        name=DefaultCategory.REFUND.value,
        description="Credits or returned funds for previously purchased goods or cancelled services.",
        example="Refund Cloudhost, Return Credit, Merchant Refund",
    ),
    DefaultCategory.REVERSAL: CategoryMetadata(
        name=DefaultCategory.REVERSAL.value,
        description="Cancelled, reversed, or chargeback-adjusted bank transactions.",
        example="Transaction Reversal, Chargeback Adjustment, Reversed Fee",
    ),
    DefaultCategory.INTERNAL_TRANSFER: CategoryMetadata(
        name=DefaultCategory.INTERNAL_TRANSFER.value,
        description="Funds transferred between the user's own accounts (not income or expense).",
        example="Transfer to Savings, Transfer from Checking, Internal Transfer",
    ),
    DefaultCategory.PERSONAL_EXPENSE: CategoryMetadata(
        name=DefaultCategory.PERSONAL_EXPENSE.value,
        description="Non-business spending identified on a shared or personal statement.",
        example="Personal Grocery, Cinema, Family Shopping",
    ),
    DefaultCategory.NEEDS_REVIEW: CategoryMetadata(
        name=DefaultCategory.NEEDS_REVIEW.value,
        description="Ambiguous or unrecognized transactions requiring manual user review.",
        example="Unknown Merchant, Ambiguous Store Pattern",
    ),
}


def is_valid_category(category_name: str) -> bool:
    """Check if the given category name matches a recognized default category."""
    return any(c.value == category_name for c in DefaultCategory)


def get_category_metadata(category: DefaultCategory | str) -> Optional[CategoryMetadata]:
    """Retrieve metadata for a category if known."""
    if isinstance(category, DefaultCategory):
        return DEFAULT_CATEGORIES.get(category)
    for cat, meta in DEFAULT_CATEGORIES.items():
        if cat.value == category:
            return meta
    return None


def get_all_category_names() -> List[str]:
    """Return all 16 category names in order."""
    return [c.value for c in DefaultCategory]
