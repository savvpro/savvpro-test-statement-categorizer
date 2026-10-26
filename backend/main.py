from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from parser import parse_csv
from categorizer import categorize_transaction


app = FastAPI(
    title="Freelancer Statement Categorizer",
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {
        "message": "Statement Categorizer API is running"
    }


@app.post("/api/categorize")
async def categorize_statement(file: UploadFile = File(...)):

    if not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Only CSV files are supported."
        )

    try:
        contents = await file.read()

        transactions = parse_csv(contents)

        results = []

        for transaction in transactions:

            decision = categorize_transaction(
                transaction["description"],
                float(transaction["amount"]),
            )

            results.append({
                **transaction,
                **decision,
            })

        totals = {}

        for row in results:
            category = row["category"]

            totals[category] = (
                totals.get(category, 0)
                + abs(float(row["amount"]))
            )

        return {
            "transactions": results,
            "totals": totals,
        }

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Unable to process statement.",
        )