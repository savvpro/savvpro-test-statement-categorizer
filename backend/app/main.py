"""
FastAPI Application for Statement Categorizer.
Provides endpoints for statement ingestion, Brain categorization, custom rule overrides, and tax summaries.
"""

import os
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse

from app.brain.taxonomy import Category, TAX_METADATA, ALL_CATEGORIES
from app.brain.normalizer import normalize_description
from app.brain.categorizer import categorize_transaction, CategorizationResult
from app.brain.parser import parse_statement_csv
from app.models import (
    TransactionItem,
    CategoryBreakdownItem,
    TaxSummary,
    CategorizationResponse,
    UpdateTransactionRequest,
    AddCustomRuleRequest,
    SampleDatasetMeta,
)

app = FastAPI(
    title="Statement Categorizer API - Tax Brain",
    description="Deterministic Brain for Freelance & Sole-Proprietor Statement Categorization (IRS Schedule C).",
    version="1.0.0",
)

# Enable CORS for local dev server (React Vite typically on 5173 or 3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store for active session custom rules & sample definitions
SESSION_CUSTOM_RULES: Dict[str, str] = {}

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))

SAMPLE_DATASETS: List[SampleDatasetMeta] = [
    SampleDatasetMeta(
        id="freelance-cc",
        title="Freelance Designer - Credit Card",
        subtitle="Messy Amex/Chase statement",
        description="Features Adobe, Figma, Uber, equipment, coffee, autopay, Amazon refund, and Joe's Cafe (ambiguous vendor).",
        transaction_count=19,
        tags=["Credit Card", "Refunds", "Ambiguous Cafe", "Autopay"],
    ),
    SampleDatasetMeta(
        id="sole-prop-checking",
        title="Sole Proprietor - Mixed Checking",
        subtitle="Business & Personal Checking Account",
        description="Features client ACH deposits, Stripe payouts, AWS, owner draws, Walmart grocery mix, and travel lodging.",
        transaction_count=12,
        tags=["Checking", "Client Income", "Owner's Draw", "Travel"],
    ),
    SampleDatasetMeta(
        id="tech-contractor-q4",
        title="Tech Contractor - Q4 Year End",
        subtitle="Q4 Tax Filing Prep Statement",
        description="Features AI APIs (OpenAI/Claude), hardware setup, contractor tools, advertising, and quarterly client wire.",
        transaction_count=12,
        tags=["Tech Contractor", "Hardware Expensing", "SaaS Subscriptions"],
    ),
]


def _build_tax_summary(transactions: List[TransactionItem]) -> TaxSummary:
    """
    Computes IRS Schedule C aggregated tax summary from transactions.
    Accurately handles:
    - 50% statutory deduction limit on Business Meals
    - Refunds reducing expense total rather than counting as revenue
    - Separation of Non-Expense transfers / credit card payments
    """
    gross_income = 0.0
    total_raw_expenses = 0.0
    total_deductible_expenses = 0.0
    total_refunds_offset = 0.0
    total_non_expense = 0.0
    needs_review_count = 0
    review_required_amt = 0.0

    breakdown_map: Dict[str, Dict[str, Any]] = {}
    for cat in ALL_CATEGORIES:
        meta = TAX_METADATA.get(cat, TAX_METADATA[Category.NEEDS_REVIEW])
        breakdown_map[cat] = {
            "category": cat,
            "schedule_c_line": meta["schedule_c_line"],
            "total_amount": 0.0,
            "deductible_amount": 0.0,
            "transaction_count": 0,
            "deductibility_pct": meta["deductibility_pct"],
            "color": meta["color"],
            "tax_note": meta["tax_note"],
        }

    for tx in transactions:
        abs_amt = abs(tx.amount)
        cat = tx.category
        if cat not in breakdown_map:
            cat = Category.NEEDS_REVIEW

        breakdown_map[cat]["transaction_count"] += 1
        breakdown_map[cat]["total_amount"] += abs_amt
        breakdown_map[cat]["deductible_amount"] += tx.deductible_amount

        if tx.needs_review:
            needs_review_count += 1
            review_required_amt += abs_amt

        if cat == Category.GROSS_INCOME:
            gross_income += abs_amt
        elif cat == Category.REFUND_REVERSAL:
            total_refunds_offset += abs_amt
        elif cat == Category.TRANSFER_OWNER_DRAW:
            total_non_expense += abs_amt
        elif tx.is_expense:
            total_raw_expenses += abs_amt
            total_deductible_expenses += tx.deductible_amount

    # Net taxable profit = Gross Income - (Deductible Expenses - Refunds Offset)
    net_profit = gross_income - max(0.0, (total_deductible_expenses - total_refunds_offset))

    categories_list = [
        CategoryBreakdownItem(**data)
        for data in breakdown_map.values()
        if data["transaction_count"] > 0
    ]
    # Sort categories by total_amount descending
    categories_list.sort(key=lambda x: x.total_amount, reverse=True)

    return TaxSummary(
        gross_income=round(gross_income, 2),
        total_raw_expenses=round(total_raw_expenses, 2),
        total_deductible_expenses=round(total_deductible_expenses, 2),
        total_refunds_offset=round(total_refunds_offset, 2),
        total_non_expense_transfers=round(total_non_expense, 2),
        net_taxable_profit=round(net_profit, 2),
        total_transactions=len(transactions),
        needs_review_count=needs_review_count,
        review_required_amount=round(review_required_amt, 2),
        categories=categories_list,
    )


def _process_parsed_transactions(
    parsed_rows: List[Dict[str, Any]],
    custom_rules: Optional[Dict[str, str]] = None,
) -> List[TransactionItem]:
    active_rules = dict(SESSION_CUSTOM_RULES)
    if custom_rules:
        active_rules.update(custom_rules)

    items: List[TransactionItem] = []
    for row in parsed_rows:
        raw_desc = row.get("raw_description", "")
        amt = float(row.get("amount", 0.0))
        tx_type = row.get("transaction_type", "DEBIT")

        decision: CategorizationResult = categorize_transaction(
            raw_description=raw_desc,
            amount=amt,
            transaction_type=tx_type,
            user_rules=active_rules,
        )

        # Calculate deductible amount based on statutory deductibility_pct
        abs_amt = abs(amt)
        deductible_amt = 0.0
        if decision.is_expense:
            deductible_amt = round(abs_amt * decision.deductibility_pct, 2)

        items.append(
            TransactionItem(
                id=row["id"],
                date=row.get("date", ""),
                raw_description=raw_desc,
                amount=amt,
                transaction_type=tx_type,
                cleaned_merchant=decision.cleaned_merchant,
                category=decision.category,
                confidence=decision.confidence,
                reason=decision.reason,
                needs_review=decision.needs_review,
                suggested_category=decision.suggested_category,
                schedule_c_line=decision.schedule_c_line,
                deductibility_pct=decision.deductibility_pct,
                deductible_amount=deductible_amt,
                is_expense=decision.is_expense,
                is_income=decision.is_income,
                tax_note=decision.tax_note,
                color=decision.color,
                user_overridden=False,
                notes=None,
            )
        )
    return items


@app.get("/api/health")
def health_check():
    return {"status": "ok", "app": "Statement Categorizer Brain", "version": "1.0.0"}


@app.get("/api/categories")
def get_categories():
    return {
        "categories": [
            {
                "name": cat,
                "schedule_c_line": meta["schedule_c_line"],
                "deductibility_pct": meta["deductibility_pct"],
                "is_expense": meta["is_expense"],
                "is_income": meta["is_income"],
                "tax_note": meta["tax_note"],
                "color": meta["color"],
            }
            for cat, meta in TAX_METADATA.items()
        ]
    }


@app.get("/api/sample-statements", response_model=List[SampleDatasetMeta])
def list_sample_statements():
    return SAMPLE_DATASETS


@app.get("/api/sample-statements/{sample_id}", response_model=CategorizationResponse)
def load_sample_statement(sample_id: str):
    file_map = {
        "freelance-cc": "freelance_designer_messy_cc.csv",
        "sole-prop-checking": "sole_prop_checking_mixed.csv",
        "tech-contractor-q4": "tech_contractor_q4.csv",
    }
    if sample_id not in file_map:
        raise HTTPException(status_code=404, detail="Sample dataset not found.")

    filepath = os.path.join(DATA_DIR, file_map[sample_id])
    if not os.path.exists(filepath):
        raise HTTPException(status_code=500, detail=f"Sample file {file_map[sample_id]} missing.")

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    parsed = parse_statement_csv(content)
    transactions = _process_parsed_transactions(parsed)
    tax_summary = _build_tax_summary(transactions)

    return CategorizationResponse(
        transactions=transactions,
        tax_summary=tax_summary,
        applied_rules_count=len(SESSION_CUSTOM_RULES),
    )


@app.post("/api/upload", response_model=CategorizationResponse)
async def upload_statement(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".csv"):
        # We can still attempt to read text CSV format
        pass
    contents = await file.read()
    try:
        decoded = contents.decode("utf-8")
    except UnicodeDecodeError:
        decoded = contents.decode("latin-1")

    parsed = parse_statement_csv(decoded)
    if not parsed:
        raise HTTPException(status_code=400, detail="Could not parse any transactions from CSV.")

    transactions = _process_parsed_transactions(parsed)
    tax_summary = _build_tax_summary(transactions)

    return CategorizationResponse(
        transactions=transactions,
        tax_summary=tax_summary,
        applied_rules_count=len(SESSION_CUSTOM_RULES),
    )


@app.post("/api/custom-rule")
def add_custom_rule(payload: AddCustomRuleRequest):
    pattern = payload.merchant_pattern.strip().upper()
    cat = payload.category.strip()
    if cat not in TAX_METADATA:
        raise HTTPException(status_code=400, detail=f"Invalid category '{cat}'.")
    SESSION_CUSTOM_RULES[pattern] = cat
    return {"message": f"Saved rule for '{pattern}' -> '{cat}'.", "total_rules": len(SESSION_CUSTOM_RULES)}


@app.post("/api/recalculate", response_model=CategorizationResponse)
def recalculate(transactions: List[TransactionItem]):
    tax_summary = _build_tax_summary(transactions)
    return CategorizationResponse(
        transactions=transactions,
        tax_summary=tax_summary,
        applied_rules_count=len(SESSION_CUSTOM_RULES),
    )
