"""
Tax categories and IRS Schedule C mapping configuration.
"""

from typing import Any, Dict

TAX_CATEGORIES: Dict[str, Dict[str, Any]] = {
    "Software & Subscriptions": {
        "schedule_c_line": "Part V (Other - Software)",
        "deductible_percentage": 1.0,
        "tax_deductible": True,
        "color": "#3B82F6",  # blue
        "description": "Cloud hosting, SaaS subscriptions, developer tooling, and APIs",
        "example": "GitHub, AWS, Vercel, Datadog",
    },
    "Hardware & Equipment": {
        "schedule_c_line": "Line 13 (Depreciation)",
        "deductible_percentage": 1.0,
        "tax_deductible": True,
        "color": "#8B5CF6",  # purple
        "description": "Computers, monitors, peripherals, and office electronics",
        "example": "Laptops, monitors, Micro Center",
    },
    "Meals & Client Entertainment": {
        "schedule_c_line": "Line 24b",
        "deductible_percentage": 0.5,  # 50% IRS rule
        "tax_deductible": True,
        "color": "#F59E0B",  # amber
        "description": "Business meals with clients or while traveling for business (IRS 50% deduction)",
        "example": "Business dinners, working lunches, coffee meetings",
    },
    "Travel & Transportation": {
        "schedule_c_line": "Line 24a / Line 9",
        "deductible_percentage": 1.0,
        "tax_deductible": True,
        "color": "#10B981",  # emerald
        "description": "Rideshare, flights, trains, lodging, and public transport for business trips",
        "example": "Uber, Lyft, Delta, Amtrak, Airbnb",
    },
    "Internet & Utilities": {
        "schedule_c_line": "Line 25",
        "deductible_percentage": 0.8,  # 80% home office ratio
        "tax_deductible": True,
        "color": "#06B6D4",  # cyan
        "description": "Home office internet and mobile phone business allocation (standard 80%)",
        "example": "Comcast, Verizon, AT&T, T-Mobile",
    },
    "Professional & Legal Services": {
        "schedule_c_line": "Line 17",
        "deductible_percentage": 1.0,
        "tax_deductible": True,
        "color": "#EC4899",  # pink
        "description": "Accounting, CPA, legal counsel, business registration, and payment processing fees",
        "example": "CPA, Stripe fees, LegalZoom, Gusto",
    },
    "Advertising & Marketing": {
        "schedule_c_line": "Line 8",
        "deductible_percentage": 1.0,
        "tax_deductible": True,
        "color": "#F97316",  # orange
        "description": "Online ads, domain registrations, marketing tools, branding",
        "example": "Google Ads, Meta Ads, Namecheap, GoDaddy",
    },
    "Office Supplies & Books": {
        "schedule_c_line": "Line 22",
        "deductible_percentage": 1.0,
        "tax_deductible": True,
        "color": "#14B8A6",  # teal
        "description": "Desk accessories, stationery, technical reference books, courses",
        "example": "Notebooks, technical books, desk supplies",
    },
    "Gross Business Income": {
        "schedule_c_line": "Line 1",
        "deductible_percentage": 0.0,
        "tax_deductible": False,
        "color": "#22C55E",  # green
        "description": "Revenue from freelance clients, consulting fees, and platform payouts",
        "example": "Stripe payouts, Upwork, client wire transfers",
    },
    "Refund / Expense Reduction": {
        "schedule_c_line": "Adjustment",
        "deductible_percentage": 1.0,
        "tax_deductible": True,
        "color": "#64748B",  # slate
        "description": "Vendor refunds or expense credits reducing deductible expenses",
        "example": "Amazon return, AWS billing adjustment",
    },
    "Transfers & Non-Taxable": {
        "schedule_c_line": "N/A",
        "deductible_percentage": 0.0,
        "tax_deductible": False,
        "color": "#94A3B8",  # light slate
        "description": "Internal account transfers, credit card autopayments, owner draws",
        "example": "Credit card autopay, transfer to savings",
    },
    "Personal / Non-Deductible": {
        "schedule_c_line": "N/A",
        "deductible_percentage": 0.0,
        "tax_deductible": False,
        "color": "#EF4444",  # red
        "description": "Personal expenses charged on a business card or non-deductible items",
        "example": "Groceries, personal clothing, movie streaming",
    },
    "Needs Review": {
        "schedule_c_line": "Pending",
        "deductible_percentage": 0.0,
        "tax_deductible": False,
        "color": "#EAB308",  # yellow
        "description": "Unclassified, mixed-use, or ambiguous transactions requiring manual review",
        "example": "Amazon purchases, unverified bank codes",
    },
}

DEFAULT_CATEGORY = "Needs Review"


def get_category_info(category_name: str) -> Dict[str, Any]:
    """Retrieve metadata for a category with fallback to Needs Review."""
    return TAX_CATEGORIES.get(category_name, TAX_CATEGORIES[DEFAULT_CATEGORY])
