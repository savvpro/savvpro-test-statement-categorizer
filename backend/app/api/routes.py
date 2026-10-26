"""HTTP endpoints. Thin: validation and error mapping only; logic lives in services."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile
from sqlmodel import Session, func, select

from app import services
from app.config import SAMPLE_DATA_DIR, get_settings
from app.db import get_session
from app.engine.categories import CATEGORIES
from app.models import (
    CategoryUpdate,
    LearnedRule,
    LearnedRuleOut,
    Statement,
    StatementListItem,
    StatementOut,
    Summary,
    Transaction,
    TransactionOut,
    TransactionUpdateResult,
)
from app.parsing.csv_parser import CSVParseError

router = APIRouter(prefix="/api")

SAMPLES = ("bank_a", "bank_b", "messy")


def _statement_out(session: Session, statement: Statement) -> StatementOut:
    rows = services.statement_transactions(session, statement.id)
    return StatementOut(
        id=statement.id,
        filename=statement.filename,
        uploaded_at=statement.uploaded_at,
        row_count=statement.row_count,
        warnings=statement.warnings,
        transactions=[TransactionOut.from_row(r) for r in rows],
    )


def _load_statement(session: Session, statement_id: int) -> Statement:
    try:
        return services.get_statement(session, statement_id)
    except services.NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _ingest(session: Session, filename: str, content: bytes) -> StatementOut:
    try:
        statement = services.ingest_statement(session, filename, content)
    except CSVParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _statement_out(session, statement)


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/categories")
def categories() -> list[str]:
    return list(CATEGORIES)


@router.post("/statements", status_code=201, response_model=StatementOut)
async def upload_statement(
    file: UploadFile = File(...), session: Session = Depends(get_session)
) -> StatementOut:
    filename = file.filename or "statement.csv"
    if not filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are supported")
    limit = get_settings().max_upload_bytes
    content = await file.read(limit + 1)
    if len(content) > limit:
        raise HTTPException(
            status_code=400, detail=f"File is larger than {limit // (1024 * 1024)} MB"
        )
    if b"\x00" in content[:4096]:
        raise HTTPException(status_code=400, detail="This does not look like a text CSV file")
    return _ingest(session, filename, content)


@router.post("/statements/sample", status_code=201, response_model=StatementOut)
def load_sample(
    name: str = Query("messy"), session: Session = Depends(get_session)
) -> StatementOut:
    if name not in SAMPLES:
        raise HTTPException(status_code=400, detail=f"Unknown sample. Choose one of {SAMPLES}")
    path = SAMPLE_DATA_DIR / f"{name}.csv"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Sample files are not available")
    return _ingest(session, path.name, path.read_bytes())


@router.get("/statements", response_model=list[StatementListItem])
def list_statements(session: Session = Depends(get_session)) -> list[StatementListItem]:
    review_counts = dict(
        session.exec(
            select(Transaction.statement_id, func.count())
            .where(Transaction.needs_review == True)  # noqa: E712 - SQL expression
            .group_by(Transaction.statement_id)
        ).all()
    )
    statements = session.exec(
        select(Statement).order_by(Statement.uploaded_at.desc(), Statement.id.desc())
    )
    return [
        StatementListItem(
            id=s.id,
            filename=s.filename,
            uploaded_at=s.uploaded_at,
            row_count=s.row_count,
            needs_review_count=review_counts.get(s.id, 0),
        )
        for s in statements
    ]


@router.get("/statements/{statement_id}", response_model=StatementOut)
def read_statement(statement_id: int, session: Session = Depends(get_session)) -> StatementOut:
    return _statement_out(session, _load_statement(session, statement_id))


@router.get("/statements/{statement_id}/summary", response_model=Summary)
def statement_summary(statement_id: int, session: Session = Depends(get_session)) -> Summary:
    _load_statement(session, statement_id)
    return services.summarize(statement_id, services.statement_transactions(session, statement_id))


@router.get("/statements/{statement_id}/export")
def export_statement(statement_id: int, session: Session = Depends(get_session)) -> Response:
    statement = _load_statement(session, statement_id)
    body = services.export_csv(services.statement_transactions(session, statement_id))
    filename = f"categorized_{statement.filename}"
    return Response(
        content=body,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.patch("/transactions/{transaction_id}", response_model=TransactionUpdateResult)
def update_transaction(
    transaction_id: int, body: CategoryUpdate, session: Session = Depends(get_session)
) -> TransactionUpdateResult:
    try:
        txn, rule, also = services.update_category(session, transaction_id, body.category)
    except services.NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return TransactionUpdateResult(
        transaction=TransactionOut.from_row(txn),
        learned_rule=LearnedRuleOut.model_validate(rule, from_attributes=True) if rule else None,
        also_updated=also,
    )


@router.get("/rules/learned", response_model=list[LearnedRuleOut])
def learned_rules(session: Session = Depends(get_session)) -> list[LearnedRuleOut]:
    rules = session.exec(select(LearnedRule).order_by(LearnedRule.created_at.desc()))
    return [LearnedRuleOut.model_validate(r, from_attributes=True) for r in rules]


@router.delete("/rules/learned/{rule_id}", status_code=204)
def delete_learned_rule(rule_id: int, session: Session = Depends(get_session)) -> Response:
    rule = session.get(LearnedRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail=f"Learned rule {rule_id} not found")
    session.delete(rule)
    session.commit()
    return Response(status_code=204)
