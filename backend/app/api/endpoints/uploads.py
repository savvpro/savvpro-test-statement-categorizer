
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Statement, Transaction
from app.services.file_parser import parse_statement
from app.services.categorization_engine import CategorizationEngine

router = APIRouter(prefix="/uploads", tags=["Uploads"])

ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}
MAX_FILE_SIZE = 10 * 1024 * 1024


@router.post("/")
async def upload_statement(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload, parse, categorize, and save a bank statement."""
    filename = file.filename or ""
    suffix = Path(filename).suffix.lower()

    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Upload CSV, XLSX, or XLS.",
        )

    content = await file.read(MAX_FILE_SIZE + 1)

    if not content:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File exceeds the 10 MB limit.")

    temporary_path = None

    try:
        with NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
            temp_file.write(content)
            temporary_path = Path(temp_file.name)

        result = parse_statement(temporary_path)

        if not result["valid"]:
            return {
                "success": False,
                "filename": filename,
                "message": "Statement is missing required columns.",
                "missing_columns": result["missing_columns"],
                "identified_columns": result["identified_columns"],
                "errors": result["errors"],
                "transactions": [],
            }

        engine = CategorizationEngine()
        statement = Statement(
            filename=filename,
            transaction_count=len(result["transactions"]),
        )

        for item in result["transactions"]:
            category = engine.categorize(
                item["description"],
                item["amount"],
            )

            statement.transactions.append(
                Transaction(
                    date=item["date"],
                    description=item["description"],
                    amount=item["amount"],
                    currency=item["currency"],
                    balance=item["balance"],
                    source_row=item["source_row"],
                    category=category["category"],
                    status=category["status"],
                    reason=category["reason"],
                    confidence=category["confidence"],
                    source=category["source"],
                    exclude_from_spending=category["exclude_from_spending"],
                )
            )

        db.add(statement)
        db.commit()
        db.refresh(statement)

        transactions = [
            {
                "id": transaction.id,
                "date": transaction.date,
                "description": transaction.description,
                "amount": transaction.amount,
                "currency": transaction.currency,
                "balance": transaction.balance,
                "source_row": transaction.source_row,
                "category": transaction.category,
                "status": transaction.status,
                "reason": transaction.reason,
                "confidence": transaction.confidence,
                "source": transaction.source,
                "exclude_from_spending": transaction.exclude_from_spending,
            }
            for transaction in statement.transactions
        ]

        return {
            "success": True,
            "statement_id": statement.id,
            "filename": filename,
            "message": "Statement parsed, categorized, and saved.",
            "transaction_count": len(transactions),
            "review_count": sum(
                item["status"] == "needs_review" for item in transactions
            ),
            "identified_columns": result["identified_columns"],
            "transactions": transactions,
        }

    except (ValueError, OSError) as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
