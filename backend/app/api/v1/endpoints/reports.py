from __future__ import annotations

import csv
import io
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.category import Category
from app.models.transaction import Transaction

router = APIRouter(prefix="/reports", tags=["reports"])
Db = Annotated[AsyncSession, Depends(get_db)]


@router.get("/summary")
async def get_summary(db: Db, year: int | None = None) -> dict[str, Any]:
    """Schedule C summary by line."""
    filters = [Transaction.status != "needs_review"]
    if year:
        filters += [
            Transaction.posted_date >= f"{year}-01-01",
            Transaction.posted_date <= f"{year}-12-31",
        ]

    cats_result = await db.execute(select(Category))
    cats = {c.id: c for c in cats_result.scalars()}

    lines: dict[str, dict[str, Any]] = {}
    for cat in cats.values():
        total = await db.scalar(
            select(func.sum(Transaction.amount_cents)).where(
                Transaction.category_id == cat.id,
                *filters,
            )
        ) or 0
        if total == 0:
            continue
        deductible_pct = cat.deductible_pct or 100
        deductible = int(abs(total) * deductible_pct / 100)
        line = cat.schedule_c_line or "Non-P&L"
        if line not in lines:
            lines[line] = {
                "line": line,
                "categories": [],
                "total_cents": 0,
                "deductible_cents": 0,
            }
        lines[line]["categories"].append({
            "slug": cat.id,
            "name": cat.name,
            "group": cat.group,
            "total_cents": total,
            "deductible_cents": deductible,
            "deductible_pct": deductible_pct,
        })
        lines[line]["total_cents"] += total
        lines[line]["deductible_cents"] += deductible

    # Non-P&L summary
    non_pl_result = await db.execute(
        select(
            func.count(Transaction.id).label("count"),
            func.sum(Transaction.amount_cents).label("total"),
        ).where(Transaction.kind.in_([
            "transfer", "cc_payment", "owner_draw", "tax_payment", "loan_payment"
        ]))
    )
    non_pl_row = non_pl_result.one_or_none()

    return {
        "year": year,
        "schedule_c_lines": sorted(lines.values(), key=lambda x: x["line"]),
        "non_pl_summary": {
            "count": non_pl_row[0] if non_pl_row else 0,
            "total_cents": non_pl_row[1] if non_pl_row else 0,
        },
    }


@router.get("/schedule-c.csv")
async def export_schedule_c(db: Db, year: int | None = None) -> Response:
    summary = await get_summary(db, year=year)

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Schedule C Line", "Category", "Total", "Deductible %", "Deductible Amount"])
    for line_data in summary["schedule_c_lines"]:
        for cat in line_data["categories"]:
            def fmt(c: int) -> str:
                return f"${abs(c) / 100:.2f}"
            writer.writerow([
                line_data["line"],
                cat["name"],
                fmt(cat["total_cents"]),
                f"{cat['deductible_pct']}%",
                fmt(cat["deductible_cents"]),
            ])

    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=schedule-c.csv"},
    )
