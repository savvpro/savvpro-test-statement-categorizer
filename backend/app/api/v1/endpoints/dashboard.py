from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.category import Category
from app.models.statement import Statement
from app.models.transaction import Transaction

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
Db = Annotated[AsyncSession, Depends(get_db)]


@router.get("")
async def get_dashboard(db: Db, year: int | None = None) -> dict[str, Any]:
    """Summary KPIs for the dashboard."""
    base_filter = [Transaction.status != "needs_review"]
    if year:
        base_filter += [
            Transaction.posted_date >= f"{year}-01-01",
            Transaction.posted_date <= f"{year}-12-31",
        ]

    # Income
    income_cats_result = await db.execute(
        select(Category.id).where(Category.group == "income")
    )
    income_slugs = [r[0] for r in income_cats_result]
    income = 0
    if income_slugs:
        income = await db.scalar(
            select(func.sum(Transaction.amount_cents)).where(
                Transaction.category_id.in_(income_slugs),
                *base_filter,
            )
        ) or 0

    # Expenses (only expense group, P&L)
    expense_cats_result = await db.execute(
        select(Category.id).where(Category.group == "expense")
    )
    expense_slugs = [r[0] for r in expense_cats_result]
    total_expenses = 0
    deductible_expenses = 0
    if expense_slugs:
        total_expenses = await db.scalar(
            select(func.sum(Transaction.amount_cents)).where(
                Transaction.category_id.in_(expense_slugs),
                *base_filter,
            )
        ) or 0
        # Deductible: factor in deductible_pct
        exp_cats = await db.execute(
            select(Category).where(Category.group == "expense")
        )
        for cat in exp_cats.scalars():
            cat_total = await db.scalar(
                select(func.sum(Transaction.amount_cents)).where(
                    Transaction.category_id == cat.id,
                    *base_filter,
                )
            ) or 0
            pct = (cat.deductible_pct or 100) / 100
            deductible_expenses += int(cat_total * pct)

    # Needs review
    needs_review = await db.scalar(
        select(func.count(Transaction.id)).where(Transaction.status == "needs_review")
    ) or 0

    # Category breakdown
    breakdown = []
    all_cats = await db.execute(select(Category))
    for cat in all_cats.scalars():
        total = await db.scalar(
            select(func.sum(Transaction.amount_cents)).where(
                Transaction.category_id == cat.id,
                *base_filter,
            )
        ) or 0
        if total != 0:
            breakdown.append({
                "slug": cat.id,
                "name": cat.name,
                "group": cat.group,
                "color": cat.color,
                "total_cents": total,
            })

    # Monthly trend (last 12 months)
    monthly = {}
    monthly_result = await db.execute(
        select(
            func.strftime("%Y-%m", Transaction.posted_date).label("month"),
            func.sum(Transaction.amount_cents).label("total"),
            Transaction.category_id,
        ).where(
            Transaction.status != "needs_review",
        ).group_by("month", Transaction.category_id)
    )
    income_set = set(income_slugs)
    expense_set = set(expense_slugs)
    for row in monthly_result:
        month = row[0]
        total = row[1] or 0
        cat_id = row[2]
        if month not in monthly:
            monthly[month] = {"month": month, "income": 0, "expenses": 0}
        if cat_id in income_set:
            monthly[month]["income"] += total
        elif cat_id in expense_set:
            monthly[month]["expenses"] += abs(total)

    # Recent imports
    recent_result = await db.execute(
        select(Statement).order_by(Statement.created_at.desc()).limit(5)
    )
    recent = [
        {
            "id": s.id,
            "filename": s.filename,
            "row_count": s.row_count,
            "created_at": s.created_at.isoformat(),
        }
        for s in recent_result.scalars()
    ]

    net_profit = income + total_expenses  # expenses are negative

    return {
        "income_cents": income,
        "total_expenses_cents": abs(total_expenses),
        "deductible_expenses_cents": abs(deductible_expenses),
        "net_profit_cents": net_profit,
        "needs_review_count": needs_review,
        "category_breakdown": sorted(breakdown, key=lambda x: abs(x["total_cents"]), reverse=True),
        "monthly_trend": sorted(monthly.values(), key=lambda x: x["month"]),
        "recent_imports": recent,
    }
