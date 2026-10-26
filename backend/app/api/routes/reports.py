"""JSON API routes for financial reports and analytics."""

from datetime import date
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_db_session
from app.services.dashboard_service import parse_date_range
from app.services.report_service import ReportService

router = APIRouter(prefix="/api/reports", tags=["reports-api"])


@router.get("/summary", summary="Financial summary report")
def api_report_summary(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    category_id: Optional[int] = Query(None, description="Category ID filter"),
    tx_type: Optional[str] = Query(None, description="'income' or 'expense'"),
    statement_id: Optional[int] = Query(None, description="Statement ID filter"),
    db: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """Return aggregated financial summary metrics."""
    s_date, e_date, date_err = parse_date_range(start_date, end_date)
    svc = ReportService(db)
    summary = svc.get_financial_summary(
        start_date=s_date,
        end_date=e_date,
        category_id=category_id,
        tx_type=tx_type,
        statement_id=statement_id,
    )

    return {
        "total_transactions": summary.total_transactions,
        "total_income": float(summary.total_income),
        "total_expenses": float(summary.total_expenses),
        "net_movement": float(summary.net_movement),
        "categorized_count": summary.categorized_count,
        "uncategorized_count": summary.uncategorized_count,
        "review_required_count": summary.review_required_count,
        "total_transfers": float(summary.total_transfers),
        "total_refunds": float(summary.total_refunds),
        "start_date": summary.start_date.isoformat() if summary.start_date else None,
        "end_date": summary.end_date.isoformat() if summary.end_date else None,
        "date_error": date_err,
    }


@router.get("/categories", summary="Category-wise financial report")
def api_report_categories(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    category_id: Optional[int] = Query(None, description="Category ID filter"),
    tx_type: Optional[str] = Query(None, description="'income' or 'expense'"),
    statement_id: Optional[int] = Query(None, description="Statement ID filter"),
    db: Session = Depends(get_db_session),
) -> List[Dict[str, Any]]:
    """Return category distribution and financial breakdown."""
    s_date, e_date, _ = parse_date_range(start_date, end_date)
    svc = ReportService(db)
    items = svc.get_category_report(
        start_date=s_date,
        end_date=e_date,
        category_id=category_id,
        tx_type=tx_type,
        statement_id=statement_id,
    )

    return [
        {
            "category_id": item.category_id,
            "category_name": item.category_name,
            "transaction_count": item.transaction_count,
            "total_expenses": float(item.total_expenses),
            "total_income": float(item.total_income),
            "net_amount": float(item.net_amount),
            "review_required_count": item.review_required_count,
            "percentage_of_expenses": item.percentage_of_expenses,
        }
        for item in items
    ]


@router.get("/monthly", summary="Monthly trend report")
def api_report_monthly(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    category_id: Optional[int] = Query(None, description="Category ID filter"),
    tx_type: Optional[str] = Query(None, description="'income' or 'expense'"),
    statement_id: Optional[int] = Query(None, description="Statement ID filter"),
    db: Session = Depends(get_db_session),
) -> List[Dict[str, Any]]:
    """Return monthly income, expenses, and net cash flow."""
    s_date, e_date, _ = parse_date_range(start_date, end_date)
    svc = ReportService(db)
    trends = svc.get_monthly_trends(
        start_date=s_date,
        end_date=e_date,
        category_id=category_id,
        tx_type=tx_type,
        statement_id=statement_id,
    )

    return [
        {
            "month_key": t.month_key,
            "month_label": t.month_label,
            "transaction_count": t.transaction_count,
            "income": float(t.income),
            "expenses": float(t.expenses),
            "net": float(t.net),
        }
        for t in trends
    ]
