from typing import Annotated

from fastapi import APIRouter, File, Form, Response, UploadFile, status
from sqlalchemy import select

from app.api.deps import AppSettings, DbSession
from app.brain.models import AccountType, TxnStatus
from app.db.models import Statement, Transaction
from app.schemas import StatementDetailOut, StatementOut, SummaryOut, TransactionOut, UploadOut
from app.services import export_service, ingest_service, summary_service
from app.services.errors import NotFound

router = APIRouter(prefix="/statements", tags=["statements"])


def _get(db: DbSession, statement_id: int) -> Statement:
    statement = db.get(Statement, statement_id)
    if statement is None:
        raise NotFound(f"statement {statement_id} not found")
    return statement


def _detail(statement: Statement) -> dict[str, object]:
    out = StatementOut.model_validate(statement).model_dump()
    return out | {
        "warnings": statement.warnings,
        "detected_format": statement.detected_format,
        "review_count": sum(t.status is TxnStatus.needs_review for t in statement.transactions),
    }


@router.post("", response_model=UploadOut, status_code=status.HTTP_201_CREATED)
async def upload_statement(
    db: DbSession,
    settings: AppSettings,
    file: Annotated[UploadFile, File()],
    account_type: Annotated[AccountType, Form()],
    charges_positive: Annotated[bool | None, Form()] = None,
) -> UploadOut:
    # Read one byte past the limit so an oversize file is rejected without buffering all of it.
    content = await file.read(settings.max_upload_bytes + 1)
    statement = ingest_service.ingest(
        db,
        file.filename or "upload",
        content,
        account_type,
        charges_positive,
        settings.max_upload_bytes,
    )
    return UploadOut.model_validate(
        _detail(statement)
        | {"transactions": [TransactionOut.model_validate(t) for t in statement.transactions]}
    )


@router.get("", response_model=list[StatementOut])
def list_statements(db: DbSession) -> list[Statement]:
    return list(
        db.scalars(select(Statement).order_by(Statement.uploaded_at.desc(), Statement.id.desc()))
    )


@router.get("/{statement_id}", response_model=StatementDetailOut)
def get_statement(db: DbSession, statement_id: int) -> StatementDetailOut:
    return StatementDetailOut.model_validate(_detail(_get(db, statement_id)))


@router.delete("/{statement_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_statement(db: DbSession, statement_id: int) -> Response:
    db.delete(_get(db, statement_id))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{statement_id}/transactions", response_model=list[TransactionOut])
def list_transactions(
    db: DbSession, statement_id: int, status: TxnStatus | None = None
) -> list[Transaction]:
    _get(db, statement_id)
    query = select(Transaction).where(Transaction.statement_id == statement_id)
    if status is not None:
        query = query.where(Transaction.status == status)
    return list(db.scalars(query.order_by(Transaction.row_index)))


@router.get("/{statement_id}/summary", response_model=SummaryOut)
def get_summary(db: DbSession, statement_id: int) -> SummaryOut:
    return summary_service.summarize(db, statement_id)


@router.get("/{statement_id}/export.csv")
def export_statement(db: DbSession, statement_id: int) -> Response:
    statement = _get(db, statement_id)
    stem = statement.filename.rsplit(".", 1)[0] or "statement"
    return Response(
        content=export_service.export_csv(statement),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{stem}-categorized.csv"'},
    )
