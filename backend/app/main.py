
import csv
import io
from fastapi.middleware.cors import CORSMiddleware

from fastapi import FastAPI, File, HTTPException, UploadFile

from app.categorizer import categorize_transaction

app = FastAPI(
    title="Statement Categorizer API",
    description="Rule-based transaction categorization for freelancers.",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {
        "message": "Statement Categorizer API is running!",
        "status": "healthy",
    }


@app.post("/api/transactions/upload")
async def upload_statement(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Please upload a CSV file.",
        )

    content = await file.read()

    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail="File is too large. Maximum size is 5 MB.",
        )

    try:
        text = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))

        if not reader.fieldnames:
            raise ValueError("CSV has no header row.")

        # Initially support these two columns.
        required_columns = {"description", "amount"}
        actual_columns = {
            column.strip().lower()
            for column in reader.fieldnames
            if column
        }

        if not required_columns.issubset(actual_columns):
            raise ValueError(
                "CSV must contain 'description' and 'amount' columns."
            )

        # Normalize column names, ignoring capitalization and spaces.
        normalized_rows = []
        for row in reader:
            normalized_rows.append({
                (key or "").strip().lower(): value
                for key, value in row.items()
            })

        transactions = []

        for row_number, row in enumerate(normalized_rows, start=2):
            description = (row.get("description") or "").strip()
            raw_amount = (row.get("amount") or "").strip()

            if not description or not raw_amount:
                raise ValueError(
                    f"Row {row_number}: description and amount are required."
                )

            try:
                amount = float(raw_amount.replace(",", ""))
            except ValueError:
                raise ValueError(
                    f"Row {row_number}: amount must be a valid number."
                )

            if not (-1e12 < amount < 1e12):
                raise ValueError(
                    f"Row {row_number}: amount is outside the supported range."
                )

            result = categorize_transaction(description, amount)

            transactions.append({
                "description": description,
                "amount": amount,
                **result,
            })

        return {
            "filename": file.filename,
            "transaction_count": len(transactions),
            "transactions": transactions,
        }

    except (UnicodeDecodeError, csv.Error, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    finally:
        await file.close()
