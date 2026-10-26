"""Server-rendered HTML page routes for LedgerLens.

Renders Jinja2 templates for:
- Dashboard (/)
- Statements list (/statements)
- Statement upload (/statements/upload)
- Statement detail (/statements/{id})
- All transactions (/transactions)
- Transaction detail (/transactions/{id})
- Review queue (/review)
- Category list (/categories)
"""

import io
import math
from decimal import Decimal
from typing import Any, Dict, Optional
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.api.dependencies import get_db_session
from app.core.config import get_settings
from app.models.transaction import ReviewStatus, Transaction
from app.services.category_repository import CategoryRepository
from app.services.dashboard_service import DashboardService, parse_date_range
from app.services.rule_service import RuleService
from app.services.statement_repository import StatementRepository
from app.services.transaction_repository import TransactionRepository
from app.services.statement_persistence_service import StatementPersistenceService
from app.services.report_service import ReportService
from app.services.reconciliation_service import ReconciliationService
from app.services.csv_export_service import CsvExportService
from app.services.backup_service import BackupService
from fastapi import Response

router = APIRouter(include_in_schema=False)

# Module-level templates reference; set by app.main on startup
_templates: Optional[Jinja2Templates] = None


def set_templates(t: Jinja2Templates) -> None:
    """Inject Jinja2Templates instance from main.py."""
    global _templates
    _templates = t


def _t() -> Jinja2Templates:
    """Get active Jinja2Templates instance."""
    if _templates is None:
        raise RuntimeError("Templates not initialized; call set_templates first")
    return _templates


def _build_query_string(params: Dict[str, Any], **overrides: Any) -> str:
    """Helper to build URL query strings while preserving existing parameters."""
    merged = {k: v for k, v in params.items() if v is not None and v != ""}
    merged.update({k: v for k, v in overrides.items() if v is not None and v != ""})
    return urlencode(merged)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@router.get("/", response_class=HTMLResponse, summary="Dashboard")
def dashboard(
    request: Request,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db_session),
) -> HTMLResponse:
    """Render main application dashboard with metrics, chart, and recent items."""
    s_date, e_date, date_error = parse_date_range(start_date, end_date)

    svc = DashboardService(db)
    # If date validation fails, calculate overall stats without invalid date filter
    effective_start = s_date if not date_error else None
    effective_end = e_date if not date_error else None

    stats = svc.get_stats(start_date=effective_start, end_date=effective_end)
    breakdown = svc.get_category_breakdown(start_date=effective_start, end_date=effective_end)
    recent_txs = svc.get_recent_transactions(limit=8, start_date=effective_start, end_date=effective_end)
    recent_statements = svc.get_recent_statements(limit=5)

    # Prepare category spending dict for charts & progress bars
    spending_categories = {
        item.category_name: item.total_spending
        for item in breakdown
        if item.total_spending > 0 and item.category_name != "Internal Transfer"
    }

    return _t().TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "stats": stats,
            "breakdown": breakdown,
            "recent_transactions": recent_txs,
            "statements": recent_statements,
            "category_totals": spending_categories,
            "start_date": start_date or "",
            "end_date": end_date or "",
            "date_error": date_error,
            # Backwards-compatibility variables for any legacy template references
            "total_in": stats.total_income,
            "total_out": stats.total_expenses,
            "review_count": stats.review_count,
            "total_statements": stats.total_statements,
        },
    )


# ---------------------------------------------------------------------------
# Statements list
# ---------------------------------------------------------------------------

@router.get("/statements", response_class=HTMLResponse, summary="Statement list")
def statements_list(
    request: Request,
    page: int = 1,
    db: Session = Depends(get_db_session),
) -> HTMLResponse:
    """Render paginated statement list."""
    page_size = 20
    offset = (max(1, page) - 1) * page_size
    stmt_repo = StatementRepository(db)
    statements = stmt_repo.list_statements(limit=page_size, offset=offset)

    return _t().TemplateResponse(
        request=request,
        name="statements.html",
        context={
            "statements": statements,
            "page": page,
            "has_next": len(statements) == page_size,
        },
    )


# ---------------------------------------------------------------------------
# Upload page (GET) and processing (POST)
# ---------------------------------------------------------------------------

@router.get("/statements/upload", response_class=HTMLResponse, summary="Upload form")
def upload_form(request: Request) -> HTMLResponse:
    """Render the CSV upload form."""
    settings = get_settings()
    return _t().TemplateResponse(
        request=request,
        name="upload.html",
        context={
            "max_upload_size_mb": settings.max_upload_size_mb,
        },
    )


@router.post("/statements/upload", response_class=HTMLResponse, summary="Process uploaded CSV")
async def upload_statement(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db_session),
) -> HTMLResponse:
    """Receive a CSV file, parse it, categorize transactions, and persist results."""
    settings = get_settings()
    max_bytes = settings.max_upload_size_mb * 1024 * 1024

    # Validate file type
    filename = file.filename or "upload.csv"
    if not filename.lower().endswith(".csv"):
        return _t().TemplateResponse(
            request=request,
            name="upload.html",
            context={
                "error": "Only CSV files are supported. Please upload a .csv file.",
                "max_upload_size_mb": settings.max_upload_size_mb,
            },
            status_code=422,
        )

    # Read and size-check file content
    content = await file.read()
    if len(content) == 0:
        return _t().TemplateResponse(
            request=request,
            name="upload.html",
            context={
                "error": "The uploaded file is empty. Please upload a valid CSV statement.",
                "max_upload_size_mb": settings.max_upload_size_mb,
            },
            status_code=422,
        )

    if len(content) > max_bytes:
        return _t().TemplateResponse(
            request=request,
            name="upload.html",
            context={
                "error": (
                    f"File is too large ({len(content) / 1024 / 1024:.1f} MB). "
                    f"Maximum allowed size is {settings.max_upload_size_mb} MB."
                ),
                "max_upload_size_mb": settings.max_upload_size_mb,
            },
            status_code=422,
        )

    # Parse, categorize, and persist
    try:
        svc = StatementPersistenceService(session=db)
        result = svc.process_and_persist(
            file_input=io.BytesIO(content),
            filename=filename,
        )
    except Exception as exc:
        return _t().TemplateResponse(
            request=request,
            name="upload.html",
            context={
                "error": f"Processing failed: {exc}",
                "max_upload_size_mb": settings.max_upload_size_mb,
            },
            status_code=500,
        )

    # Redirect to statement detail on success, or render error summary
    if result.statement_id is not None:
        return RedirectResponse(
            url=f"/statements/{result.statement_id}?imported=1",
            status_code=303,
        )

    return _t().TemplateResponse(
        request=request,
        name="upload.html",
        context={
            "error": "Import failed: no valid transactions were found in the file.",
            "import_result": result.import_result,
            "max_upload_size_mb": settings.max_upload_size_mb,
        },
        status_code=422,
    )


# ---------------------------------------------------------------------------
# Statement detail
# ---------------------------------------------------------------------------

@router.get("/statements/{statement_id}", response_class=HTMLResponse, summary="Statement detail")
def statement_detail(
    request: Request,
    statement_id: int,
    imported: Optional[int] = None,
    db: Session = Depends(get_db_session),
) -> HTMLResponse:
    """Render statement detail page with transaction listing."""
    stmt_repo = StatementRepository(db)
    statement = stmt_repo.get_by_id(statement_id)
    if not statement:
        raise HTTPException(status_code=404, detail="Statement not found")

    tx_repo = TransactionRepository(db)
    transactions = tx_repo.list_by_statement(statement_id, limit=200)

    # Build summary
    total_in = Decimal("0")
    total_out = Decimal("0")
    review_count = 0
    category_totals: dict = {}

    for t in transactions:
        cat_name = t.category.name if t.category else "Needs Review"
        if cat_name == "Internal Transfer":
            continue
        if t.amount > 0:
            total_in += t.amount
        else:
            total_out += abs(t.amount)
        if t.review_status == ReviewStatus.PENDING:
            review_count += 1
        category_totals[cat_name] = category_totals.get(cat_name, Decimal("0")) + abs(t.amount)

    return _t().TemplateResponse(
        request=request,
        name="statement_detail.html",
        context={
            "statement": statement,
            "transactions": transactions,
            "total_in": total_in,
            "total_out": total_out,
            "review_count": review_count,
            "category_totals": dict(
                sorted(category_totals.items(), key=lambda x: x[1], reverse=True)
            ),
            "just_imported": bool(imported),
        },
    )


# ---------------------------------------------------------------------------
# Transactions list (all) with search, filters, sorting, and pagination
# ---------------------------------------------------------------------------

@router.get("/transactions", response_class=HTMLResponse, summary="All transactions")
def transactions_list(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    q: Optional[str] = None,
    category_id: Optional[int] = None,
    status: Optional[str] = None,
    review: Optional[str] = None,
    tx_type: Optional[str] = None,
    statement_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    sort_by: str = Query("date"),
    sort_dir: str = Query("desc"),
    db: Session = Depends(get_db_session),
) -> HTMLResponse:
    """Render paginated, searchable, and filterable transaction table."""
    # Backwards compatibility: review=pending maps to status=PENDING
    effective_status = status
    if review and review.lower() == "pending" and not status:
        effective_status = "PENDING"

    s_date, e_date, date_error = parse_date_range(start_date, end_date)

    # Fetch filter reference data
    cat_repo = CategoryRepository(db)
    all_categories = cat_repo.list_categories()

    stmt_repo = StatementRepository(db)
    all_statements = stmt_repo.list_statements(limit=100)

    tx_repo = TransactionRepository(db)
    transactions, total_count = tx_repo.search_and_filter(
        q=q,
        category_id=category_id,
        status=effective_status,
        tx_type=tx_type,
        statement_id=statement_id,
        start_date=s_date if not date_error else None,
        end_date=e_date if not date_error else None,
        sort_by=sort_by,
        sort_dir=sort_dir,
        page=page,
        page_size=page_size,
    )

    total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1
    safe_page = min(max(1, page), total_pages)
    start_item = (safe_page - 1) * page_size + 1 if total_count > 0 else 0
    end_item = min(safe_page * page_size, total_count)

    # Active filter dictionary for preserving query parameters in links
    current_params = {
        "q": q,
        "category_id": category_id,
        "status": effective_status,
        "tx_type": tx_type,
        "statement_id": statement_id,
        "start_date": start_date,
        "end_date": end_date,
        "sort_by": sort_by,
        "sort_dir": sort_dir,
        "page_size": page_size if page_size != 25 else None,
    }

    def url_for_page(p: int) -> str:
        qs = _build_query_string(current_params, page=p)
        return f"/transactions?{qs}" if qs else "/transactions"

    def url_for_sort(col: str) -> str:
        new_dir = "asc" if (sort_by == col and sort_dir == "desc") else "desc"
        qs = _build_query_string(current_params, sort_by=col, sort_dir=new_dir, page=1)
        return f"/transactions?{qs}" if qs else "/transactions"

    return _t().TemplateResponse(
        request=request,
        name="transactions.html",
        context={
            "transactions": transactions,
            "total_count": total_count,
            "page": safe_page,
            "page_size": page_size,
            "total_pages": total_pages,
            "has_prev": safe_page > 1,
            "has_next": safe_page < total_pages,
            "start_item": start_item,
            "end_item": end_item,
            "q": q or "",
            "category_id": category_id,
            "status": effective_status or "",
            "review_filter": review,
            "tx_type": tx_type or "",
            "statement_id": statement_id,
            "start_date": start_date or "",
            "end_date": end_date or "",
            "date_error": date_error,
            "sort_by": sort_by,
            "sort_dir": sort_dir,
            "categories": all_categories,
            "statements": all_statements,
            "url_for_page": url_for_page,
            "url_for_sort": url_for_sort,
        },
    )


# ---------------------------------------------------------------------------
# Transaction detail
# ---------------------------------------------------------------------------

@router.get(
    "/transactions/{transaction_id}",
    response_class=HTMLResponse,
    summary="Transaction detail view",
)
def transaction_detail(
    request: Request,
    transaction_id: int,
    db: Session = Depends(get_db_session),
) -> HTMLResponse:
    """Render comprehensive detail view for a specific transaction."""
    if transaction_id <= 0:
        raise HTTPException(status_code=404, detail="Invalid transaction ID")

    tx_repo = TransactionRepository(db)
    tx = tx_repo.get_by_id(transaction_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    cat_repo = CategoryRepository(db)
    categories = cat_repo.list_categories()

    return _t().TemplateResponse(
        request=request,
        name="transaction_detail.html",
        context={
            "transaction": tx,
            "categories": categories,
        },
    )


# ---------------------------------------------------------------------------
# Review queue
# ---------------------------------------------------------------------------

@router.get("/review", response_class=HTMLResponse, summary="Review queue")
def review_queue(request: Request, db: Session = Depends(get_db_session)) -> HTMLResponse:
    """Display all transactions requiring manual review."""
    cat_repo = CategoryRepository(db)
    categories = cat_repo.list_categories()

    query = (
        from_sqlalchemy_select := None
    )
    from sqlalchemy import select
    query = (
        select(Transaction)
        .where(Transaction.review_status == ReviewStatus.PENDING)
        .order_by(Transaction.transaction_date, Transaction.id)
    )
    transactions = db.execute(query).scalars().all()

    return _t().TemplateResponse(
        request=request,
        name="review.html",
        context={
            "transactions": transactions,
            "categories": categories,
        },
    )


# ---------------------------------------------------------------------------
# Categories page
# ---------------------------------------------------------------------------

@router.get("/categories", response_class=HTMLResponse, summary="Category management")
def categories_page(request: Request, db: Session = Depends(get_db_session)) -> HTMLResponse:
    """Display all categories with transaction counts."""
    from sqlalchemy import func, select
    from app.models.merchant_rule import MerchantRule

    cat_repo = CategoryRepository(db)
    categories = cat_repo.list_categories()

    # Count transactions and rules per category
    tx_counts = {}
    rule_counts = {}
    for cat in categories:
        tx_counts[cat.id] = db.execute(
            select(func.count(Transaction.id)).where(Transaction.category_id == cat.id)
        ).scalar_one()
        rule_counts[cat.id] = db.execute(
            select(func.count(MerchantRule.id)).where(MerchantRule.category_id == cat.id)
        ).scalar_one()

    return _t().TemplateResponse(
        request=request,
        name="categories.html",
        context={
            "categories": categories,
            "tx_counts": tx_counts,
            "rule_counts": rule_counts,
        },
    )



# ---------------------------------------------------------------------------
# Reusable merchant categorization rules
# ---------------------------------------------------------------------------

@router.get("/rules", response_class=HTMLResponse, summary="Rules management")
def rules_page(
    request: Request,
    prefill_pattern: Optional[str] = None,
    prefill_category_id: Optional[int] = None,
    success: Optional[str] = None,
    error: Optional[str] = None,
    db: Session = Depends(get_db_session),
) -> HTMLResponse:
    """Display rules management page with list, creation form, and guidance."""
    rule_svc = RuleService(db)
    rules = rule_svc.list_rules()

    cat_repo = CategoryRepository(db)
    categories = cat_repo.list_categories()

    return _t().TemplateResponse(
        request=request,
        name="rules.html",
        context={
            "rules": rules,
            "categories": categories,
            "prefill_pattern": prefill_pattern or "",
            "prefill_category_id": prefill_category_id,
            "success": success,
            "error": error,
        },
    )


@router.post("/rules", response_class=HTMLResponse, summary="Create rule via HTML form")
def create_rule_form(
    request: Request,
    merchant_pattern: str = Form(...),
    category_id: int = Form(...),
    match_type: str = Form("CONTAINS"),
    priority: int = Form(100),
    is_active: Optional[str] = Form(None),
    preview_first: Optional[str] = Form(None),
    db: Session = Depends(get_db_session),
) -> RedirectResponse:
    """Process rule creation form submission."""
    rule_svc = RuleService(db)
    try:
        rule = rule_svc.create_rule(
            merchant_pattern=merchant_pattern,
            category_id=category_id,
            match_type=match_type,
            priority=priority,
            is_active=bool(is_active),
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        qs = urlencode({"error": str(exc), "prefill_pattern": merchant_pattern, "prefill_category_id": category_id})
        return RedirectResponse(url=f"/rules?{qs}", status_code=303)

    if preview_first:
        return RedirectResponse(url=f"/rules/{rule.id}/preview", status_code=303)

    qs = urlencode({"success": f"Rule for '{rule.merchant_pattern}' created successfully!"})
    return RedirectResponse(url=f"/rules?{qs}", status_code=303)


@router.post("/rules/{rule_id}/toggle", summary="Toggle rule active state")
def toggle_rule_form(
    rule_id: int,
    db: Session = Depends(get_db_session),
) -> RedirectResponse:
    """Toggle active state of a rule."""
    rule_svc = RuleService(db)
    try:
        rule = rule_svc.toggle_rule(rule_id)
        db.commit()
        state_str = "activated" if rule.is_active else "disabled"
        qs = urlencode({"success": f"Rule #{rule.id} has been {state_str}."})
    except ValueError as exc:
        db.rollback()
        qs = urlencode({"error": str(exc)})

    return RedirectResponse(url=f"/rules?{qs}", status_code=303)


@router.post("/rules/{rule_id}/delete", summary="Delete rule")
def delete_rule_form(
    rule_id: int,
    db: Session = Depends(get_db_session),
) -> RedirectResponse:
    """Safely delete a rule without modifying past transactions."""
    rule_svc = RuleService(db)
    deleted = rule_svc.delete_rule(rule_id)
    if deleted:
        db.commit()
        qs = urlencode({"success": f"Rule #{rule_id} was deleted successfully."})
    else:
        qs = urlencode({"error": f"Rule #{rule_id} not found."})

    return RedirectResponse(url=f"/rules?{qs}", status_code=303)


@router.get("/rules/{rule_id}/preview", response_class=HTMLResponse, summary="Preview rule recategorization")
def preview_rule_page(
    request: Request,
    rule_id: int,
    applied: Optional[int] = None,
    updated: Optional[int] = None,
    protected: Optional[int] = None,
    db: Session = Depends(get_db_session),
) -> HTMLResponse:
    """Render preview of matching transactions for a rule."""
    rule_svc = RuleService(db)
    rule = rule_svc.get_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    preview = rule_svc.preview_recategorization(rule_id)

    return _t().TemplateResponse(
        request=request,
        name="rule_preview.html",
        context={
            "rule": rule,
            "preview": preview,
            "applied": bool(applied),
            "updated_count": updated or 0,
            "protected_count": protected or 0,
        },
    )


@router.post("/rules/{rule_id}/apply", summary="Apply rule to matching transactions")
def apply_rule_form(
    rule_id: int,
    override_manual: Optional[str] = Form(None),
    db: Session = Depends(get_db_session),
) -> RedirectResponse:
    """Apply rule recategorization to matching transactions in bulk."""
    rule_svc = RuleService(db)
    try:
        result = rule_svc.apply_recategorization(
            rule_id=rule_id,
            override_manual=bool(override_manual),
        )
        db.commit()
        qs = urlencode(
            {
                "applied": 1,
                "updated": result["updated_count"],
                "protected": result["protected_count"],
            }
        )
        return RedirectResponse(url=f"/rules/{rule_id}/preview?{qs}", status_code=303)
    except ValueError as exc:
        db.rollback()
        qs = urlencode({"error": str(exc)})
        return RedirectResponse(url=f"/rules?{qs}", status_code=303)


# ---------------------------------------------------------------------------
# Phase 7: Financial Reporting, Statement Reconciliation, and CSV Export
# ---------------------------------------------------------------------------

@router.get("/reports", response_class=HTMLResponse, summary="Financial reports page")
def reports_page(
    request: Request,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    category_id: Optional[int] = Query(None),
    tx_type: Optional[str] = Query(None),
    statement_id: Optional[int] = Query(None),
    db: Session = Depends(get_db_session),
) -> HTMLResponse:
    """Render financial reports page with summary metrics, category tables, and trends."""
    s_date, e_date, date_err = parse_date_range(start_date, end_date)
    report_svc = ReportService(db)
    cat_repo = CategoryRepository(db)
    stmt_repo = StatementRepository(db)

    summary = report_svc.get_financial_summary(
        start_date=s_date,
        end_date=e_date,
        category_id=category_id,
        tx_type=tx_type,
        statement_id=statement_id,
    )
    categories_breakdown = report_svc.get_category_report(
        start_date=s_date,
        end_date=e_date,
        category_id=category_id,
        tx_type=tx_type,
        statement_id=statement_id,
    )
    monthly_trends = report_svc.get_monthly_trends(
        start_date=s_date,
        end_date=e_date,
        category_id=category_id,
        tx_type=tx_type,
        statement_id=statement_id,
    )

    all_categories = cat_repo.list_categories()
    all_statements = stmt_repo.list_statements(limit=100)

    # Prepare Chart.js data
    trend_labels = [m.month_label for m in monthly_trends]
    trend_income = [float(m.income) for m in monthly_trends]
    trend_expenses = [float(m.expenses) for m in monthly_trends]
    trend_net = [float(m.net) for m in monthly_trends]

    cat_labels = [c.category_name for c in categories_breakdown if c.total_expenses > 0]
    cat_values = [float(c.total_expenses) for c in categories_breakdown if c.total_expenses > 0]

    return _t().TemplateResponse(
        request=request,
        name="reports.html",
        context={
            "summary": summary,
            "categories_breakdown": categories_breakdown,
            "monthly_trends": monthly_trends,
            "all_categories": all_categories,
            "all_statements": all_statements,
            "start_date": start_date or "",
            "end_date": end_date or "",
            "category_id": category_id,
            "tx_type": tx_type or "",
            "statement_id": statement_id,
            "date_error": date_err,
            "trend_labels": trend_labels,
            "trend_income": trend_income,
            "trend_expenses": trend_expenses,
            "trend_net": trend_net,
            "cat_labels": cat_labels,
            "cat_values": cat_values,
        },
    )


@router.get("/reconciliation", response_class=HTMLResponse, summary="Statement reconciliation page")
def reconciliation_page(
    request: Request,
    statement_id: Optional[int] = Query(None),
    opening_balance: Optional[float] = Query(None),
    closing_balance: Optional[float] = Query(None),
    db: Session = Depends(get_db_session),
) -> HTMLResponse:
    """Render statement reconciliation audit and balance checking page."""
    rec_svc = ReconciliationService(db)
    stmt_repo = StatementRepository(db)

    all_statements = stmt_repo.list_statements(limit=100)
    summaries = rec_svc.reconcile_all_statements()

    selected_rec = None
    if statement_id:
        open_dec = Decimal(str(opening_balance)) if opening_balance is not None else None
        close_dec = Decimal(str(closing_balance)) if closing_balance is not None else None
        selected_rec = rec_svc.reconcile_statement(
            statement_id, opening_balance=open_dec, closing_balance=close_dec
        )

    return _t().TemplateResponse(
        request=request,
        name="reconciliation.html",
        context={
            "summaries": summaries,
            "all_statements": all_statements,
            "selected_rec": selected_rec,
            "statement_id": statement_id,
            "opening_balance": opening_balance,
            "closing_balance": closing_balance,
        },
    )


@router.get("/export/transactions", summary="Download transactions CSV")
def export_transactions_web(
    q: Optional[str] = Query(None),
    category_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    tx_type: Optional[str] = Query(None),
    statement_id: Optional[int] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    sort_by: str = Query("date"),
    sort_dir: str = Query("desc"),
    db: Session = Depends(get_db_session),
) -> Response:
    """Download CSV file of all matching transactions with formula-injection protection."""
    from datetime import datetime
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


# ---------------------------------------------------------------------------
# Phase 8: Backup and Restore Management
# ---------------------------------------------------------------------------

@router.get("/backups", response_class=HTMLResponse, summary="Backup and Restore Management")
def backups_page(
    request: Request,
    success: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
) -> HTMLResponse:
    """Render Backup and Restore interface with diagnostics and available backups."""
    service = BackupService()
    backups = service.list_backups()
    diagnostics = service.get_diagnostics()

    return _t().TemplateResponse(
        request=request,
        name="backups.html",
        context={
            "backups": backups,
            "diagnostics": diagnostics,
            "success": success,
            "error": error,
        },
    )


@router.post("/backups/create", response_class=RedirectResponse, summary="Create Manual Backup")
def create_backup_web(request: Request) -> RedirectResponse:
    """Handle form submission to create a manual database backup."""
    service = BackupService()
    try:
        meta = service.create_backup(backup_type="manual")
        msg = f"Backup '{meta.backup_id}' created successfully ({meta.file_size_bytes} bytes)."
        return RedirectResponse(url=f"/backups?success={msg}", status_code=303)
    except Exception as exc:
        err = f"Failed to create backup: {exc}"
        return RedirectResponse(url=f"/backups?error={err}", status_code=303)


@router.post("/backups/{backup_id}/verify", response_class=RedirectResponse, summary="Verify Backup")
def verify_backup_web(backup_id: str) -> RedirectResponse:
    """Handle form submission to verify backup integrity."""
    service = BackupService()
    try:
        res = service.verify_backup(backup_id)
        if res.get("valid"):
            msg = f"Backup '{backup_id}' verified successfully (Checksum: {res.get('sha256_checksum')[:12]}...)."
            return RedirectResponse(url=f"/backups?success={msg}", status_code=303)
        else:
            err = f"Verification failed for '{backup_id}': {res.get('reason')}"
            return RedirectResponse(url=f"/backups?error={err}", status_code=303)
    except Exception as exc:
        err = f"Verification error: {exc}"
        return RedirectResponse(url=f"/backups?error={err}", status_code=303)


@router.post("/backups/{backup_id}/restore", response_class=RedirectResponse, summary="Restore Backup")
def restore_backup_web(
    backup_id: str,
    confirm_text: str = Form(...),
) -> RedirectResponse:
    """Handle form submission to restore database from backup.

    Requires explicit user typing 'RESTORE' to prevent accidental execution.
    """
    if confirm_text.strip().upper() != "RESTORE":
        err = "Restoration aborted: you must type 'RESTORE' exactly to confirm data replacement."
        return RedirectResponse(url=f"/backups?error={err}", status_code=303)

    service = BackupService()
    try:
        res = service.restore_backup(backup_id, confirmation=True)
        msg = (
            f"Successfully restored database from '{backup_id}' in {res.get('elapsed_seconds')}s. "
            f"Pre-restore safety backup created: '{res.get('safety_backup_id')}'."
        )
        return RedirectResponse(url=f"/backups?success={msg}", status_code=303)
    except Exception as exc:
        err = f"Restore failed: {exc}"
        return RedirectResponse(url=f"/backups?error={err}", status_code=303)


@router.post("/backups/{backup_id}/delete", response_class=RedirectResponse, summary="Delete Backup")
def delete_backup_web(backup_id: str) -> RedirectResponse:
    """Handle form submission to delete a backup."""
    service = BackupService()
    try:
        deleted = service.delete_backup(backup_id)
        if deleted:
            msg = f"Backup '{backup_id}' deleted successfully."
            return RedirectResponse(url=f"/backups?success={msg}", status_code=303)
        else:
            err = f"Backup '{backup_id}' not found."
            return RedirectResponse(url=f"/backups?error={err}", status_code=303)
    except Exception as exc:
        err = f"Delete failed: {exc}"
        return RedirectResponse(url=f"/backups?error={err}", status_code=303)


@router.post("/backups/prune", response_class=RedirectResponse, summary="Prune Old Backups")
def prune_backups_web() -> RedirectResponse:
    """Handle form submission to prune old backups according to retention policy."""
    service = BackupService()
    try:
        res = service.prune_backups()
        msg = f"Pruned {res.get('pruned_count')} old backup(s). {res.get('retained_count')} backup(s) retained."
        return RedirectResponse(url=f"/backups?success={msg}", status_code=303)
    except Exception as exc:
        err = f"Pruning failed: {exc}"
        return RedirectResponse(url=f"/backups?error={err}", status_code=303)

