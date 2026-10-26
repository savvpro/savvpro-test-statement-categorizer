import uuid
import io
import csv
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .models.schemas import (
    StatementAnalysisResponse,
    StatementSummary,
    Transaction,
    CategoryName,
    TaxDeductibility,
    UpdateCategoryRequest,
    CategorySummary
)
from .parser.csv_parser import StatementCSVParser
from .engine.brain import CategorizationBrain
from .engine.aggregator import StatementAggregator
from .engine.memory import user_rule_memory
from .engine.rules import CATEGORY_TAXONOMY


app = FastAPI(
    title="Statement Categorizer API",
    description="Deterministic rule & heuristic statement categorizer for Freelancers and Consultants.",
    version="1.0.0"
)

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session store for current statement
_current_statement: List[Transaction] = []
_current_filename: str = "statement.csv"


# Realistic Freelancer Test Statement Dataset with all edge cases
SAMPLE_CSV_DATA = """Date,Description,Amount,Type
2024-10-02,ADOBE *CREATIVE CLOUD 800-833-6687 CA,54.99,DEBIT
2024-10-03,CHECKCARD 1024 FIGMA.COM SAN FRANCISCO CA,15.00,DEBIT
2024-10-04,PAYPAL *GITHUB INC 402-935-7733 CA,21.00,DEBIT
2024-10-05,AMAZON WEB SERVICES AWS.AMAZON.CO WA,87.42,DEBIT
2024-10-06,UBER *TRIP HELP.UBER.COM,34.20,DEBIT
2024-10-07,DELTA AIR 006238192831 ATLANTA GA,412.80,DEBIT
2024-10-08,STARBUCKS STORE #19821 SEATTLE WA,6.75,DEBIT
2024-10-09,TST* BLUE BOTTLE COFFEE #12 SAN JOSE CA,9.25,DEBIT
2024-10-10,SQ *JOES CAFE 9921 SAN FRANCISCO CA,14.50,DEBIT
2024-10-12,CLIENT INVOICE #1042 WIRE TRANSFER INCOMING,-3500.00,CREDIT
2024-10-14,STRIPE PAYOUT ACC-910248,-1850.00,CREDIT
2024-10-15,TRANSFER TO SAVINGS ACC #4821,1000.00,DEBIT
2024-10-16,AUTOPAY CREDIT CARD PAYMENT - THANK YOU,500.00,DEBIT
2024-10-17,REFUND: APPLE STORE RETURN #9812,-129.00,CREDIT
2024-10-18,AMZN Mktp US*2J9K10931 Amzn.com/bill WA,64.20,DEBIT
2024-10-19,GOOGLE *ADS912841289 MOUNTAIN VIEW CA,150.00,DEBIT
2024-10-20,UPWORK SERVICE FEE REF#8491823,39.50,DEBIT
2024-10-21,COMCAST CABLE INTERNET AUTOPAY,89.99,DEBIT
2024-10-22,VERCEL INC 855-837-2354 CA,20.00,DEBIT
2024-10-23,OPENAI *CHATGPT SUBSCRIPTION CA,20.00,DEBIT
2024-10-24,SQ *CORNER MART 4402 AUSTIN TX,18.30,DEBIT
2024-10-25,NOTION LABS INC SAN FRANCISCO CA,10.00,DEBIT
2024-10-26,BEST BUY #0491 SAN FRANCISCO CA,189.99,DEBIT
"""


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "statement-categorizer-engine",
        "learned_rules_count": user_rule_memory.total_learned_rules
    }


@app.get("/api/categories")
def get_categories():
    categories_info = []
    for cat in CategoryName:
        meta = CATEGORY_TAXONOMY.get(cat, {})
        tax_status = meta.get("tax_status", TaxDeductibility.FULLY_DEDUCTIBLE)
        if cat == CategoryName.GROSS_INCOME:
            tax_status = TaxDeductibility.TAXABLE_INCOME
        elif cat == CategoryName.INTERNAL_TRANSFER:
            tax_status = TaxDeductibility.NON_DEDUCTIBLE
        elif cat == CategoryName.REFUND_CREDIT:
            tax_status = TaxDeductibility.EXPENSE_OFFSET
        elif cat == CategoryName.NEEDS_REVIEW:
            tax_status = TaxDeductibility.PENDING_REVIEW

        categories_info.append({
            "name": cat.value,
            "tax_status": tax_status.value,
            "description": meta.get("description", "")
        })
    return {"categories": categories_info}


@app.post("/api/statements/upload", response_model=StatementAnalysisResponse)
async def upload_statement(file: UploadFile = File(...)):
    global _current_statement, _current_filename
    if not file.filename.endswith((".csv", ".txt")):
        raise HTTPException(status_code=400, detail="Only CSV or TXT statement files are supported.")

    content = await file.read()
    try:
        decoded_content = content.decode("utf-8")
    except UnicodeDecodeError:
        decoded_content = content.decode("latin-1")

    raw_records = StatementCSVParser.parse_csv_content(decoded_content)
    if not raw_records:
        raise HTTPException(status_code=400, detail="No valid transaction rows found in the uploaded file.")

    transactions: List[Transaction] = []
    for i, rec in enumerate(raw_records):
        tx_id = f"tx-{i+1}-{uuid.uuid4().hex[:6]}"
        tx = CategorizationBrain.categorize_transaction(
            tx_id=tx_id,
            date=rec["date"],
            raw_description=rec["description"],
            amount=rec["amount"],
            tx_type=rec["type"]
        )
        transactions.append(tx)

    _current_statement = transactions
    _current_filename = file.filename
    summary = StatementAggregator.calculate_summary(transactions)

    return StatementAnalysisResponse(
        filename=file.filename,
        summary=summary,
        transactions=transactions
    )


@app.get("/api/statements/sample", response_model=StatementAnalysisResponse)
def load_sample_statement():
    global _current_statement, _current_filename
    raw_records = StatementCSVParser.parse_csv_content(SAMPLE_CSV_DATA)

    transactions: List[Transaction] = []
    for i, rec in enumerate(raw_records):
        tx_id = f"sample-tx-{i+1}"
        tx = CategorizationBrain.categorize_transaction(
            tx_id=tx_id,
            date=rec["date"],
            raw_description=rec["description"],
            amount=rec["amount"],
            tx_type=rec["type"]
        )
        transactions.append(tx)

    _current_statement = transactions
    _current_filename = "freelance_designer_statement_2024.csv"
    summary = StatementAggregator.calculate_summary(transactions)

    return StatementAnalysisResponse(
        filename=_current_filename,
        summary=summary,
        transactions=transactions
    )


@app.post("/api/transactions/update-category", response_model=StatementAnalysisResponse)
def update_transaction_category(payload: UpdateCategoryRequest):
    global _current_statement, _current_filename
    if not _current_statement:
        raise HTTPException(status_code=404, detail="No active statement loaded.")

    target_tx: Optional[Transaction] = None
    for tx in _current_statement:
        if tx.id == payload.transaction_id:
            target_tx = tx
            break

    if not target_tx:
        raise HTTPException(status_code=404, detail=f"Transaction {payload.transaction_id} not found.")

    # Determine tax deductibility based on new category
    new_tax_status = TaxDeductibility.FULLY_DEDUCTIBLE
    if payload.new_category == CategoryName.MEALS_ENTERTAINMENT:
        new_tax_status = TaxDeductibility.PARTIALLY_DEDUCTIBLE
    elif payload.new_category == CategoryName.GROSS_INCOME:
        new_tax_status = TaxDeductibility.TAXABLE_INCOME
    elif payload.new_category == CategoryName.INTERNAL_TRANSFER:
        new_tax_status = TaxDeductibility.NON_DEDUCTIBLE
    elif payload.new_category == CategoryName.REFUND_CREDIT:
        new_tax_status = TaxDeductibility.EXPENSE_OFFSET
    elif payload.new_category == CategoryName.NEEDS_REVIEW:
        new_tax_status = TaxDeductibility.PENDING_REVIEW

    # Update transaction
    target_tx.category = payload.new_category
    target_tx.tax_status = new_tax_status
    target_tx.needs_review = (payload.new_category == CategoryName.NEEDS_REVIEW)
    target_tx.confidence = 1.0
    target_tx.user_edited = True
    target_tx.review_reason = f"User explicitly verified category as {payload.new_category.value}"

    # If apply_to_future is True, teach the Brain for this merchant!
    if payload.apply_to_future:
        user_rule_memory.add_override(
            clean_merchant=target_tx.clean_merchant,
            category=payload.new_category,
            tax_status=new_tax_status
        )
        # Also auto-update any other transaction in the current statement with the same merchant!
        for other_tx in _current_statement:
            if other_tx.clean_merchant.lower() == target_tx.clean_merchant.lower() and other_tx.id != target_tx.id:
                other_tx.category = payload.new_category
                other_tx.tax_status = new_tax_status
                other_tx.needs_review = (payload.new_category == CategoryName.NEEDS_REVIEW)
                other_tx.confidence = 1.0
                other_tx.user_edited = True
                other_tx.review_reason = f"Auto-updated from user override on {target_tx.clean_merchant}"

    # Recalculate summary
    summary = StatementAggregator.calculate_summary(_current_statement)

    return StatementAnalysisResponse(
        filename=_current_filename,
        summary=summary,
        transactions=_current_statement
    )


@app.get("/api/statements/export")
def export_statement_csv():
    global _current_statement, _current_filename
    if not _current_statement:
        raise HTTPException(status_code=404, detail="No active statement to export.")

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Date",
        "Original Description",
        "Clean Merchant",
        "Amount ($)",
        "Type",
        "Category",
        "Tax Status",
        "Confidence",
        "Needs Review",
        "Notes"
    ])

    for tx in _current_statement:
        writer.writerow([
            tx.date,
            tx.raw_description,
            tx.clean_merchant,
            f"{tx.amount:.2f}",
            tx.transaction_type.value,
            tx.category.value,
            tx.tax_status.value,
            f"{int(tx.confidence * 100)}%",
            "Yes" if tx.needs_review else "No",
            tx.review_reason or ""
        ])

    output.seek(0)
    export_filename = f"categorized_{_current_filename.replace('.csv', '')}.csv"
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={export_filename}"}
    )
