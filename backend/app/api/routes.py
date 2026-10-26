import logging
from collections import defaultdict

from fastapi import APIRouter, File, HTTPException, Response, UploadFile, status

from app.config import settings
from app.engine.brain import CategorizationBrain
from app.engine.rules import CATEGORIES
from app.models.response import (
    CategorizationResponse,
    CategoryTotal,
    StatementSummary,
    UpdateCategoryRequest,
)
from app.models.rule import CustomRule, RuleCreateRequest
from app.models.transaction import CategorizedTransaction, TransactionType
from app.services.exporter import ExporterService
from app.services.parser import StatementParseError, StatementParser
from app.services.rule_store import rule_store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


def calculate_metrics(transactions: list[CategorizedTransaction]) -> tuple[list[CategoryTotal], StatementSummary]:
    category_counts: dict[str, int] = defaultdict(int)
    category_sums: dict[str, float] = defaultdict(float)

    total_income = 0.0
    total_expenses = 0.0
    total_transfers = 0.0
    total_refunds = 0.0
    needs_review_count = 0
    duplicate_count = 0

    for tx in transactions:
        category_counts[tx.category] += 1
        category_sums[tx.category] += tx.amount

        if tx.needs_review:
            needs_review_count += 1
        if tx.is_duplicate:
            duplicate_count += 1

        if tx.is_transfer:
            total_transfers += tx.amount
        elif tx.is_refund:
            total_refunds += tx.amount
        elif tx.transaction_type == TransactionType.CREDIT:
            if tx.category == "Client Income & Revenue":
                total_income += tx.amount
        else:
            # Debit transaction
            if tx.category not in ["Transfers & Card Payments", "Needs Review"]:
                total_expenses += tx.amount

    # Net expense calculation: deduct refund offsets
    net_expenses = max(0.0, total_expenses - total_refunds)

    category_totals: list[CategoryTotal] = []
    # Include all known categories plus any custom user ones present
    all_cat_keys = sorted(
        list(set(CATEGORIES) | set(category_counts.keys()))
    )

    for cat in all_cat_keys:
        cnt = category_counts[cat]
        amt = category_sums[cat]
        pct = (amt / net_expenses * 100.0) if net_expenses > 0 and amt > 0 else 0.0
        category_totals.append(
            CategoryTotal(
                category=cat,
                count=cnt,
                total_amount=round(amt, 2),
                percentage_of_expenses=round(pct, 1),
            )
        )

    # Sort categories by total amount descending
    category_totals.sort(key=lambda c: c.total_amount, reverse=True)

    total_tx = len(transactions)
    reviewed_tx = total_tx - needs_review_count
    progress = (reviewed_tx / total_tx * 100.0) if total_tx > 0 else 100.0

    summary = StatementSummary(
        total_transactions=total_tx,
        total_income=round(total_income, 2),
        total_expenses=round(net_expenses, 2),
        total_transfers=round(total_transfers, 2),
        total_refunds=round(total_refunds, 2),
        needs_review_count=needs_review_count,
        duplicate_count=duplicate_count,
        review_progress_percent=round(progress, 1),
    )

    return category_totals, summary


@router.get("/categories", response_model=list[str])
def get_categories():
    """Returns the list of tax categories available for categorization."""
    return CATEGORIES


@router.post("/upload", response_model=CategorizationResponse)
async def upload_statement(file: UploadFile = File(...)):
    """
    Upload and categorize a bank/credit card statement:
    - Enforces file type and size constraints
    - Parses statement with robust encoding/delimiter discovery
    - Runs multi-layer deterministic engine
    - Returns rows with confidence and explanation
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must have a valid filename.",
        )

    ext = "." + file.filename.split(".")[-1].lower() if "." in file.filename else ""
    if ext not in settings.allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Allowed formats: {', '.join(settings.allowed_extensions)}",
        )

    content = await file.read()
    max_bytes = settings.max_file_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {settings.max_file_size_mb}MB.",
        )

    # Parse transactions
    try:
        raw_txs = StatementParser.parse_csv(content, filename=file.filename)
    except StatementParseError as spe:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=spe.message,
        ) from spe
    except Exception as e:
        logger.exception("Unexpected error while parsing statement")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unable to process statement: {str(e)}",
        ) from e

    # Load custom learned rules
    custom_rules = rule_store.get_all()

    # Run categorization engine
    brain = CategorizationBrain(custom_rules=custom_rules)
    categorized_txs = brain.categorize_batch(raw_txs)

    # Compute metrics & summary
    cat_totals, summary = calculate_metrics(categorized_txs)

    return CategorizationResponse(
        filename=file.filename,
        transactions=categorized_txs,
        category_totals=cat_totals,
        summary=summary,
    )


@router.post("/recalculate", response_model=CategorizationResponse)
def recalculate(payload: dict):
    """Recalculates totals and review status after frontend row adjustments."""
    transactions = [CategorizedTransaction(**t) for t in payload.get("transactions", [])]
    filename = payload.get("filename", "statement.csv")
    cat_totals, summary = calculate_metrics(transactions)

    return CategorizationResponse(
        filename=filename,
        transactions=transactions,
        category_totals=cat_totals,
        summary=summary,
    )


@router.post("/correct", response_model=CustomRule)
def submit_correction(req: UpdateCategoryRequest):
    """
    Records a user correction and optionally saves it as a persistent rule
    for subsequent statements.
    """
    if not req.save_as_rule:
        return CustomRule(
            id="temp",
            pattern=req.rule_pattern or "",
            category=req.new_category,
            is_active=False,
        )

    pattern = req.rule_pattern or req.transaction_id
    new_rule = rule_store.add_rule(
        RuleCreateRequest(
            pattern=pattern,
            category=req.new_category,
            notes=f"Created via user correction for tx {req.transaction_id}",
        )
    )
    return new_rule


@router.get("/rules", response_model=list[CustomRule])
def list_rules():
    """List all user-defined custom rules."""
    return rule_store.get_all()


@router.post("/rules", response_model=CustomRule)
def create_rule(req: RuleCreateRequest):
    """Add or update a custom categorization rule."""
    return rule_store.add_rule(req)


@router.delete("/rules/{rule_id}")
def delete_rule(rule_id: str):
    """Delete a user-defined rule."""
    success = rule_store.delete_rule(rule_id)
    if not success:
        raise HTTPException(status_code=404, detail="Rule not found.")
    return {"status": "success", "message": "Rule removed."}


@router.post("/export")
def export_csv(payload: CategorizationResponse):
    """Generates an accountant-ready CSV export with transaction details and tax totals."""
    csv_content = ExporterService.export_to_csv(payload)
    safe_name = payload.filename.replace(".csv", "") + "_categorized.csv"

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
    )
