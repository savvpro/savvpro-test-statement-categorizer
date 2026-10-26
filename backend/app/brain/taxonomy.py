"""
Taxonomy and Tax Classification Metadata for Freelance & Sole-Proprietor
Statement Categorization (aligned with IRS Schedule C / Form 1040).
"""

from typing import Dict, Any

class Category:
    SOFTWARE_SAAS = "Software & SaaS Subscriptions"
    OFFICE_SUPPLIES = "Office Supplies & Stationery"
    EQUIPMENT_HARDWARE = "Equipment & Tech Hardware"
    TRAVEL_TRANSIT = "Travel & Transit"
    BUSINESS_MEALS = "Business Meals & Dining"
    ADVERTISING_MARKETING = "Advertising & Marketing"
    PROFESSIONAL_SERVICES = "Legal & Professional Services"
    BANKING_FEES = "Bank & Merchant Processing Fees"
    UTILITIES_INTERNET = "Utilities & Communications"
    GROSS_INCOME = "Gross Business Income"
    REFUND_REVERSAL = "Refund / Expense Offset"
    TRANSFER_OWNER_DRAW = "Transfer / Owner's Draw (Non-Expense)"
    NEEDS_REVIEW = "Needs Review"


TAX_METADATA: Dict[str, Dict[str, Any]] = {
    Category.SOFTWARE_SAAS: {
        "schedule_c_line": "Part V / Other Expenses (Software & Cloud Services)",
        "deductibility_pct": 1.0,
        "is_expense": True,
        "is_income": False,
        "tax_note": "100% deductible ordinary and necessary software & digital tooling used in freelance trade.",
        "color": "#6366f1",  # indigo
    },
    Category.OFFICE_SUPPLIES: {
        "schedule_c_line": "Line 18 (Office Expense)",
        "deductibility_pct": 1.0,
        "is_expense": True,
        "is_income": False,
        "tax_note": "100% deductible office stationery, desk accessories, packaging, and printing supplies.",
        "color": "#0ea5e9",  # sky
    },
    Category.EQUIPMENT_HARDWARE: {
        "schedule_c_line": "Line 13 (Depreciation / De Minimis Safe Harbor Election)",
        "deductibility_pct": 1.0,
        "is_expense": True,
        "is_income": False,
        "tax_note": "Eligible for 100% expensing under Section 179 or Tangible Property Safe Harbor (< $2,500/item).",
        "color": "#8b5cf6",  # purple
    },
    Category.TRAVEL_TRANSIT: {
        "schedule_c_line": "Line 24a (Travel)",
        "deductibility_pct": 1.0,
        "is_expense": True,
        "is_income": False,
        "tax_note": "100% deductible business flights, hotels, car rentals, tolls, and rideshares away from tax home.",
        "color": "#14b8a6",  # teal
    },
    Category.BUSINESS_MEALS: {
        "schedule_c_line": "Line 24b (Deductible Meals - 50% Limit)",
        "deductibility_pct": 0.5,
        "is_expense": True,
        "is_income": False,
        "tax_note": "IRS statutory 50% limit applies to client dining or meals during overnight business travel. Requires business purpose record.",
        "color": "#f59e0b",  # amber
    },
    Category.ADVERTISING_MARKETING: {
        "schedule_c_line": "Line 8 (Advertising)",
        "deductibility_pct": 1.0,
        "is_expense": True,
        "is_income": False,
        "tax_note": "100% deductible marketing, domain registrations, pay-per-click ads, and lead generation.",
        "color": "#ec4899",  # pink
    },
    Category.PROFESSIONAL_SERVICES: {
        "schedule_c_line": "Line 17 (Legal and Professional Services)",
        "deductibility_pct": 1.0,
        "is_expense": True,
        "is_income": False,
        "tax_note": "100% deductible subcontractor fees (1099-NEC required if >$600), accountants, and legal fees.",
        "color": "#3b82f6",  # blue
    },
    Category.BANKING_FEES: {
        "schedule_c_line": "Line 10 (Commissions and Fees)",
        "deductibility_pct": 1.0,
        "is_expense": True,
        "is_income": False,
        "tax_note": "100% deductible account maintenance fees, wire charges, and merchant gateway processing fees (e.g. Stripe/PayPal).",
        "color": "#64748b",  # slate
    },
    Category.UTILITIES_INTERNET: {
        "schedule_c_line": "Line 25 (Utilities)",
        "deductibility_pct": 1.0,
        "is_expense": True,
        "is_income": False,
        "tax_note": "Deductible business portion of mobile communications and high-speed internet service.",
        "color": "#10b981",  # emerald
    },
    Category.GROSS_INCOME: {
        "schedule_c_line": "Line 1 (Gross Receipts or Sales)",
        "deductibility_pct": 0.0,
        "is_expense": False,
        "is_income": True,
        "tax_note": "Taxable gross business revenue from client payments, invoices, and sales receipts.",
        "color": "#22c55e",  # green
    },
    Category.REFUND_REVERSAL: {
        "schedule_c_line": "Expense Offset / Line 2 (Returns & Allowances)",
        "deductibility_pct": 0.0,
        "is_expense": False,
        "is_income": False,
        "tax_note": "Purchase return or credit reversal. Directly reduces deductible expenses rather than inflating gross revenue.",
        "color": "#06b6d4",  # cyan
    },
    Category.TRANSFER_OWNER_DRAW: {
        "schedule_c_line": "Excluded from Schedule C (Balance Sheet / Equity)",
        "deductibility_pct": 0.0,
        "is_expense": False,
        "is_income": False,
        "tax_note": "Inter-account transfers, owner withdrawals, or credit card debt repayments are non-deductible balance sheet adjustments.",
        "color": "#94a3b8",  # slate light
    },
    Category.NEEDS_REVIEW: {
        "schedule_c_line": "Unassigned - Pending Clarification",
        "deductibility_pct": 0.0,
        "is_expense": None,
        "is_income": None,
        "tax_note": "Ambiguous merchant or low confidence score. A wrong guess is worse than asking. Requires user confirmation.",
        "color": "#ef4444",  # red
    },
}

ALL_CATEGORIES = list(TAX_METADATA.keys())
