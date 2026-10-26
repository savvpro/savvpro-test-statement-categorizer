"""JSON API routes for dashboard metrics."""

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_db_session
from app.services.dashboard_service import DashboardService, parse_date_range

router = APIRouter(prefix="/api/dashboard", tags=["dashboard-api"])


@router.get("/stats", summary="Get dashboard summary and category breakdown")
def get_dashboard_stats(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """Retrieve summary metrics and category distributions for a date range."""
    s_date, e_date, date_err = parse_date_range(start_date, end_date)
    if date_err:
        raise HTTPException(status_code=400, detail=date_err)

    svc = DashboardService(db)
    stats = svc.get_stats(start_date=s_date, end_date=e_date)
    breakdown = svc.get_category_breakdown(start_date=s_date, end_date=e_date)

    return {
        "stats": {
            "total_transactions": stats.total_transactions,
            "categorized_count": stats.categorized_count,
            "review_count": stats.review_count,
            "unknown_count": stats.unknown_count,
            "total_income": float(stats.total_income),
            "total_expenses": float(stats.total_expenses),
            "net_cash_flow": float(stats.net_cash_flow),
            "total_statements": stats.total_statements,
            "start_date": stats.start_date.isoformat() if stats.start_date else None,
            "end_date": stats.end_date.isoformat() if stats.end_date else None,
        },
        "category_breakdown": [
            {
                "category_id": item.category_id,
                "category_name": item.category_name,
                "transaction_count": item.transaction_count,
                "total_spending": float(item.total_spending),
                "total_income": float(item.total_income),
                "percentage_of_spending": item.percentage_of_spending,
            }
            for item in breakdown
        ],
    }
