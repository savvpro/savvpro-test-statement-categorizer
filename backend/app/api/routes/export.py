"""CSV export API routes for LedgerLens transactions."""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.api.dependencies import get_db_session
from app.services.csv_export_service import CsvExportService
from app.services.dashboard_service import parse_date_range
from app.services.transaction_repository import TransactionRepository

router = APIRouter(prefix="/api/export", tags=["export-api"])


@router.get("/transactions", summary="Export transactions to CSV")
def api_export_transactions(
    q: Optional[str] = Query(None, description="Search query"),
    category_id: Optional[int] = Query(None, description="Category ID filter"),
    status: Optional[str] = Query(None, description="Review status filter"),
    tx_type: Optional[str] = Query(None, description="Transaction type ('income' or 'expense')"),
    statement_id: Optional[int] = Query(None, description="Statement ID filter"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    sort_by: str = Query("date", description="Column to sort by"),
    sort_dir: str = Query("desc", description="Sort direction ('asc' or 'desc')"),
    db: Session = Depends(get_db_session),
) -> Response:
    """Stream or return a CSV file containing all matching transactions with formula-injection protection."""
    s_date, e_date, _ = parse_date_range(start_date, end_date)
    repo = TransactionRepository(db)

    transactions = repo.get_all_matching(
        q=q,
        category_id=category_id,
        status=status,
        tx_type=tx_type,
        statement_id=statement_id,
        start_date=s_date,
        end_date=e_date,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )

    csv_content = CsvExportService.export_transactions(transactions)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"ledgerlens_transactions_{timestamp}.csv"

    return Response(
        content=csv_content.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )
