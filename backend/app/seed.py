"""Seed categories and demo data (100% fake)."""
from __future__ import annotations

import json
import uuid
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.brain.taxonomy import ALL_CATEGORIES
from app.models.account import Account
from app.models.category import Category
from app.models.statement import Statement
from app.models.transaction import Transaction


async def seed_categories(db: AsyncSession) -> None:
    """Upsert all taxonomy categories."""
    for cat in ALL_CATEGORIES:
        existing = await db.get(Category, cat.slug)
        if not existing:
            db_cat = Category(
                id=cat.slug,
                name=cat.name,
                group=cat.group,
                schedule_c_line=cat.schedule_c_line,
                deductible_pct=cat.deductible_pct,
                color=cat.color,
                icon=cat.icon,
                description=cat.description,
                is_system=True,
            )
            db.add(db_cat)
    await db.commit()


# Fake transactions for a fictional freelance designer at "Apex Creative Studio"
_DEMO_TRANSACTIONS = [
    # Income
    ("2026-01-15", "STRIPE TRANSFER APEX CREATIVE STUDIO", 320000, "income", "client_income", "auto", 0.90),
    ("2026-01-28", "ACH CREDIT BLUE HORIZON MEDIA CO", 150000, "income", "client_income", "auto", 0.85),
    ("2026-02-10", "PAYPAL TRANSFER STARDUST DESIGN", 85000, "income", "client_income", "auto", 0.90),
    ("2026-02-25", "STRIPE TRANSFER VELVET AGENCY", 220000, "income", "client_income", "auto", 0.90),
    ("2026-03-05", "ACH CREDIT NEON BRANDS LLC", 175000, "income", "client_income", "auto", 0.88),
    ("2026-03-20", "STRIPE TRANSFER APEX CREATIVE STUDIO", 280000, "income", "client_income", "auto", 0.90),
    ("2026-04-12", "ACH CREDIT TERRA NOVA STARTUP", 95000, "income", "client_income", "auto", 0.85),
    # Software
    ("2026-01-02", "ADOBE CREATIVE CLOUD", -5499, "expense", "software", "auto", 0.95),
    ("2026-02-02", "ADOBE CREATIVE CLOUD", -5499, "expense", "software", "auto", 0.95),
    ("2026-03-02", "ADOBE CREATIVE CLOUD", -5499, "expense", "software", "auto", 0.95),
    ("2026-01-03", "FIGMA", -1500, "expense", "software", "auto", 0.95),
    ("2026-01-05", "GITHUB", -400, "expense", "software", "auto", 0.95),
    ("2026-01-10", "NOTION", -800, "expense", "software", "auto", 0.95),
    ("2026-02-10", "NOTION", -800, "expense", "software", "auto", 0.95),
    ("2026-01-15", "SLACK", -1250, "expense", "software", "auto", 0.95),
    ("2026-02-15", "VERCEL", -2000, "expense", "software", "auto", 0.95),
    ("2026-01-20", "ZOOM", -1499, "expense", "software", "auto", 0.95),
    # Meals
    ("2026-01-08", "SQ *JOES CAFE 9921 BROOKLYN NY", -2400, "expense", "meals", "auto", 0.85),
    ("2026-01-14", "STARBUCKS STORE 12345", -850, "expense", "meals", "auto", 0.95),
    ("2026-02-03", "TST* THE GRID BISTRO", -6800, "expense", "meals", "needs_review", 0.70),
    ("2026-02-20", "PANERA BREAD 0042", -1200, "expense", "meals", "auto", 0.95),
    # Travel
    ("2026-02-14", "DELTA AIR LINES DL1234", -38500, "expense", "travel", "auto", 0.95),
    ("2026-02-15", "MARRIOTT HOTEL NYC", -24000, "expense", "travel", "auto", 0.95),
    ("2026-03-10", "UBER TRIP 8X9K", -2200, "expense", "travel", "needs_review", 0.70),
    ("2026-03-15", "LYFT RIDE REQUEST", -1800, "expense", "travel", "needs_review", 0.70),
    # Equipment
    ("2026-01-25", "B&H PHOTO VIDEO", -89900, "expense", "equipment", "needs_review", 0.90),
    ("2026-02-28", "APPLE STORE MACBOOK PRO", -199900, "expense", "equipment", "needs_review", 0.60),
    # Needs review – mixed use
    ("2026-01-18", "AMAZON MARKETPLACE", -4500, "expense", "supplies", "needs_review", 0.80),
    ("2026-02-22", "AMAZON MARKETPLACE", -12000, "expense", "supplies", "needs_review", 0.80),
    ("2026-03-01", "AMAZON MARKETPLACE", -3200, "expense", "supplies", "needs_review", 0.80),
    # Utilities
    ("2026-01-12", "VERIZON WIRELESS", -8500, "expense", "utilities", "auto", 0.95),
    ("2026-02-12", "VERIZON WIRELESS", -8500, "expense", "utilities", "auto", 0.95),
    ("2026-01-20", "COMCAST BUSINESS", -12000, "expense", "utilities", "auto", 0.95),
    # Non-P&L
    ("2026-01-27", "TRANSFER TO SAVINGS", -100000, "transfer", "non_pl", "auto", 0.95),
    ("2026-02-05", "ONLINE PAYMENT THANK YOU", -89000, "cc_payment", "non_pl", "auto", 0.95),
    ("2026-03-15", "IRS USATAXPYMT", -25000, "tax_payment", "non_pl", "auto", 0.95),
    # Refund
    ("2026-02-18", "AMAZON REFUND", 4500, "refund", "supplies", "auto", 0.85),
    # Advertising
    ("2026-01-22", "GOOGLE ADS", -15000, "expense", "advertising", "auto", 0.95),
    ("2026-02-22", "GOOGLE ADS", -15000, "expense", "advertising", "auto", 0.95),
    ("2026-03-22", "FACEBOOK ADS", -8000, "expense", "advertising", "auto", 0.95),
    # Education
    ("2026-02-01", "SKILLSHARE ANNUAL", -9900, "expense", "education", "auto", 0.95),
    ("2026-03-05", "UDEMY COURSE DESIGN SYSTEMS", -1500, "expense", "education", "auto", 0.95),
    # Commissions / platform fees
    ("2026-01-15", "STRIPE FEE", -930, "expense", "commissions", "auto", 0.95),
    ("2026-01-28", "STRIPE FEE", -435, "expense", "commissions", "auto", 0.95),
    ("2026-02-25", "STRIPE FEE", -638, "expense", "commissions", "auto", 0.95),
    # Unknown income
    ("2026-03-25", "DEPOSIT 2839021", 50000, "unknown", None, "needs_review", 0.0),
    # Rent
    ("2026-01-01", "WEWORK MONTHLY MEMBERSHIP", -55000, "expense", "rent_cowork", "auto", 0.95),
    ("2026-02-01", "WEWORK MONTHLY MEMBERSHIP", -55000, "expense", "rent_cowork", "auto", 0.95),
    ("2026-03-01", "WEWORK MONTHLY MEMBERSHIP", -55000, "expense", "rent_cowork", "auto", 0.95),
    # Bank fees
    ("2026-01-31", "MONTHLY SERVICE FEE", -1500, "fee", "bank_fees", "auto", 0.85),
    ("2026-02-28", "MONTHLY SERVICE FEE", -1500, "fee", "bank_fees", "auto", 0.85),
]


def _demo_review_reason(desc: str, cat: str | None, amount_cents: int) -> str:
    """Human-readable reason a demo transaction is flagged for review."""
    upper = desc.upper()
    if "AMAZON" in upper:
        return "Amazon sells both business and personal items, please confirm this purchase"
    if cat == "equipment" or abs(amount_cents) > 250000:
        return "Equipment over the $2,500 de-minimis limit, verify whether to expense or depreciate"
    if "UBER" in upper or "LYFT" in upper:
        return "Rideshare can be personal, please confirm this was business travel"
    if cat is None:
        return "Unknown credit, please classify (income, refund, transfer, or personal)"
    if cat == "meals":
        return "Larger meal amount, possible catering or a personal event, please confirm"
    return "Low confidence, please review the suggested category"


async def seed_demo_data(db: AsyncSession) -> dict[str, Any]:
    """Insert one demo checking account + statement + transactions."""
    # Check if already seeded
    existing = await db.scalar(select(Account))
    if existing:
        return {"status": "already seeded", "account_id": existing.id}

    await seed_categories(db)

    account = Account(
        id=str(uuid.uuid4()),
        name="Northwind Bank Business Checking",
        type="checking",
        institution="Northwind Bank",
        mask="4892",
    )
    db.add(account)
    await db.flush()

    stmt = Statement(
        id=str(uuid.uuid4()),
        account_id=account.id,
        filename="northwind_bank_2026_q1.csv",
        file_sha256="demo-" + uuid.uuid4().hex,
        format="csv",
        period_start=date(2026, 1, 1),
        period_end=date(2026, 4, 30),
        row_count=len(_DEMO_TRANSACTIONS),
        skipped_rows="[]",
        warnings='["Demo data, not real bank statements"]',
    )
    db.add(stmt)
    await db.flush()

    for i, (dt, desc, amt, kind, cat, status, conf) in enumerate(_DEMO_TRANSACTIONS):
        from app.brain.normalize import normalize_merchant
        merchant = normalize_merchant(desc)
        fp = f"demo-{account.id}-{i}"
        t = Transaction(
            id=str(uuid.uuid4()),
            statement_id=stmt.id,
            account_id=account.id,
            posted_date=date.fromisoformat(dt),
            description_raw=desc,
            merchant=merchant,
            amount_cents=amt,
            kind=kind,
            category_id=cat,
            status=status,
            confidence=conf,
            reasons=json.dumps([f"Demo seed: {desc}"]),
            review_reason=(_demo_review_reason(desc, cat, amt) if status == "needs_review" else None),
            fingerprint=fp,
        )
        db.add(t)

    await db.commit()
    return {"status": "seeded", "account_id": account.id, "statement_id": stmt.id,
            "transaction_count": len(_DEMO_TRANSACTIONS)}
