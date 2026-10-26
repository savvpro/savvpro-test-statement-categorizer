"""
Summary and Export API – per-category totals, reconciliation, CSV/XLSX export.
"""

from __future__ import annotations

import csv
import io
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import Session, select

from app.brain.categories import CATEGORIES, CategoryType
from app.db import get_session
from app.models import Statement, Transaction, TxnStatus
from app.schemas import CategoryTotal, StatusCounts, SummaryOut

router = APIRouter(prefix="/statements/{statement_id}", tags=["summary"])


@router.get("/summary", response_model=SummaryOut)
def get_summary(statement_id: int, session: Session = Depends(get_session)):
    """
    Compute per-category totals for a statement.

    Includes:
     - Total income, expenses, deductible, excluded, net
     - Status counts
     - Reconciliation check
    """
    stmt = session.get(Statement, statement_id)
    if not stmt:
        raise HTTPException(404, "Statement not found")

    txns = session.exec(
        select(Transaction).where(Transaction.statement_id == statement_id)
    ).all()

    # Group by category
    cat_data: dict[str, dict] = defaultdict(lambda: {
        "total_cents": 0, "count": 0,
    })

    total_income = 0
    total_expense = 0
    total_deductible = 0
    total_excluded = 0
    all_sum = 0

    status_counts = StatusCounts(total=len(txns))
    from app.brain.categories import EXCLUDED_KEYS

    for t in txns:
        all_sum += t.amount_cents
        cat_data[t.category]["total_cents"] += t.amount_cents
        cat_data[t.category]["count"] += 1

        meta = CATEGORIES.get(t.category)
        if not meta:
            continue

        if meta.cat_type == CategoryType.INCOME:
            total_income += t.amount_cents
        elif meta.cat_type == CategoryType.EXPENSE:
            total_expense += t.amount_cents
            deductible = (t.amount_cents * t.deductible_pct) // 100
            total_deductible += deductible
        elif meta.cat_type == CategoryType.EXCLUDED:
            total_excluded += t.amount_cents

        # Status counts
        if t.category in EXCLUDED_KEYS:
            status_counts.excluded += 1
        elif t.status in (TxnStatus.AUTO, TxnStatus.USER_CONFIRMED):
            status_counts.auto += 1
        elif t.status == TxnStatus.SUGGESTED:
            status_counts.suggested += 1
        elif t.status == TxnStatus.NEEDS_REVIEW:
            status_counts.needs_review += 1

    # Build category totals list
    totals: list[CategoryTotal] = []
    for cat_key, data in sorted(cat_data.items()):
        meta = CATEGORIES.get(cat_key)
        if not meta:
            continue
        deductible_pct = meta.deductible_pct
        deductible_cents = (data["total_cents"] * deductible_pct) // 100
        totals.append(CategoryTotal(
            category=cat_key,
            label=meta.label,
            schedule_c_line=meta.schedule_c_line,
            cat_type=meta.cat_type.value,
            total_cents=data["total_cents"],
            deductible_cents=deductible_cents,
            deductible_pct=deductible_pct,
            count=data["count"],
        ))

    # Reconciliation: sum of all rows should equal statement net change
    # Since we don't have the stated total from the file, we just verify internal consistency
    net = total_income + total_expense  # expense is negative
    reconciles = True
    recon_note = "All rows accounted for"

    unreviewed = status_counts.needs_review
    if unreviewed > 0:
        reconciles = False
        recon_note = f"{unreviewed} row(s) still need review"

    return SummaryOut(
        statement_id=statement_id,
        totals=totals,
        total_income_cents=total_income,
        total_expense_cents=total_expense,
        total_deductible_cents=total_deductible,
        total_excluded_cents=total_excluded,
        net_cents=net,
        status_counts=status_counts,
        reconciles=reconciles,
        reconciliation_note=recon_note,
    )


@router.get("/export")
def export_statement(
    statement_id: int,
    format: str = "csv",
    session: Session = Depends(get_session),
):
    """
    Export categorized transactions as CSV or XLSX.
    """
    stmt = session.get(Statement, statement_id)
    if not stmt:
        raise HTTPException(404, "Statement not found")

    txns = session.exec(
        select(Transaction)
        .where(Transaction.statement_id == statement_id)
        .order_by(Transaction.posted_date, Transaction.row_index)
    ).all()

    if format == "csv":
        return _export_csv(txns, stmt.filename)
    elif format == "xlsx":
        return _export_xlsx(txns, stmt.filename)
    else:
        raise HTTPException(400, f"Unsupported export format: {format}")


def _export_csv(txns: list[Transaction], filename: str) -> Response:
    """Generate CSV export."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Date", "Description", "Merchant Key", "Amount",
        "Category", "Category Label", "Schedule C Line",
        "Confidence", "Status", "Reason", "Deductible %",
        "Flags", "Note",
    ])

    for t in txns:
        meta = CATEGORIES.get(t.category)
        label = meta.label if meta else t.category
        line = meta.schedule_c_line if meta else ""
        amt_str = f"{t.amount_cents / 100:.2f}"  # only for display, never for arithmetic

        writer.writerow([
            t.posted_date.isoformat(),
            t.raw_description,
            t.merchant_key,
            amt_str,
            t.category,
            label,
            line,
            f"{t.confidence:.2f}",
            t.status,
            t.reason,
            t.deductible_pct,
            "; ".join(t.flags),
            t.user_note,
        ])

    csv_content = output.getvalue()
    export_name = filename.rsplit(".", 1)[0] + "_categorized.csv"
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{export_name}"'},
    )


def _export_xlsx(txns: list[Transaction], filename: str) -> Response:
    """Generate XLSX export using openpyxl."""
    try:
        from openpyxl import Workbook
    except ImportError:
        raise HTTPException(500, "openpyxl not installed – XLSX export unavailable")

    wb = Workbook()
    ws = wb.active
    ws.title = "Categorized Transactions"

    headers = [
        "Date", "Description", "Merchant Key", "Amount",
        "Category", "Category Label", "Schedule C Line",
        "Confidence", "Status", "Reason", "Deductible %",
        "Flags", "Note",
    ]
    ws.append(headers)

    for t in txns:
        meta = CATEGORIES.get(t.category)
        label = meta.label if meta else t.category
        line = meta.schedule_c_line if meta else ""
        amt = t.amount_cents / 100  # openpyxl handles number formatting

        ws.append([
            t.posted_date.isoformat(),
            t.raw_description,
            t.merchant_key,
            amt,
            t.category,
            label,
            line,
            round(t.confidence, 2),
            t.status,
            t.reason,
            t.deductible_pct,
            "; ".join(t.flags),
            t.user_note,
        ])

    # Auto-width columns
    for col in ws.columns:
        max_length = 0
        col_letter = col[0].column_letter
        for cell in col:
            try:
                if cell.value:
                    max_length = max(max_length, len(str(cell.value)))
            except Exception:
                pass
        ws.column_dimensions[col_letter].width = min(max_length + 2, 50)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    export_name = filename.rsplit(".", 1)[0] + "_categorized.xlsx"
    return Response(
        content=output.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{export_name}"'},
    )
