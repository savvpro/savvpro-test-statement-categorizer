# WORKING.md — How the Statement Categorizer Works

This document explains the complete working of the Statement Categorizer project,
from file upload to category assignment, for a technical reviewer.

---

## 1. Project Overview

The Statement Categorizer is a freelance-focused web application that reads a
business credit card statement (CSV), automatically categorizes each transaction
for tax time, and lets the user review and correct any uncertain rows. Totals
per category are shown at the end.

**Use case:** A freelance developer/designer uploads their business credit card
statement and needs every transaction sorted into tax categories (Software,
Travel, Meals, Office Supplies, Marketing, Utilities, Subscriptions, Income,
Refund, Transfer, Needs Review).


## 2. Repository Structure

```
statement-categorizer/
├── .env.example                # Template for environment variables
├── .gitignore                  # Git ignore rules
├── AI_USAGE.md                 # Template for AI tool usage disclosure
├── DESIGN.md                   # Design decisions, limitations, tech stack
├── README.md                   # Setup and run instructions
├── TASK.md                     # Original task requirements
├── WORKING.md                  # This document — full working explanation
│
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── main.py             # FastAPI app + CORS middleware
│   │   ├── api/routes.py       # All 4 API endpoints
│   │   ├── models.py           # Pydantic v2 data models
│   │   ├── parsing/csv_parser.py   # CSV parsing logic
│   │   ├── brain/constants.py      # All thresholds/weights in one place
│   │   ├── brain/normalizer.py     # Description normalization
│   │   ├── brain/overrides.py      # In-memory user override store
│   │   ├── brain/classifier.py     # 5-step categorization pipeline
│   │   └── store.py            # In-memory transaction store
│   ├── tests/
│   │   ├── test_csv_parser.py  # 34 parser tests
│   │   ├── test_classifier.py  # 43 brain tests
│   │   ├── test_overrides.py   # 5 override store tests
│   │   └── test_normalizer.py  # 10 normalizer tests
│   ├── config/rules.yaml          # 52 merchants across 10 categories
│   ├── pyproject.toml          # Ruff + pytest + project config
│   └── requirements.txt        # Python dependencies
│
├── frontend/                   # Vite + React + TypeScript frontend
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── src/
│       ├── main.tsx            # App entry point
│       ├── App.tsx             # Main React component
│       ├── index.css           # Plain CSS (no UI library)
│       ├── services/api.ts     # Fetch wrapper for all endpoints
│       └── types/
│           ├── index.ts        # TypeScript interfaces
│           └── css.d.ts        # CSS module type declarations

## 3. Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+, FastAPI, Pydantic v2, PyYAML |
| Backend testing | pytest, httpx, FastAPI TestClient |
| Backend linting | ruff |
| Frontend | React 18, TypeScript, Vite 5, plain CSS |
| State | In-memory (no database) — Postgres noted as production choice |

## 4. Brain Pipeline (Most Important Part)

Each transaction is classified through a **deterministic 5-step pipeline**.
The pipeline runs in this exact order, and the first matching step wins.

### Step 1: Normalize Description

The raw description string is cleaned:

1. Convert to uppercase
2. Strip noisy prefixes: `SQ *`, `TST*`, `AMZN MKTP US*`, `POS`, `PURCHASE`, `PAYPAL *`
3. Strip trailing store/reference numbers (e.g. `#1234`, 6+ digit runs)
4. Collapse internal whitespace

**Example:** `"SQ *Joes Cafe #9921"` → `"JOES CAFE"`

### Step 2: User Overrides

If the normalized merchant name has a saved override (from a previous user
correction), that category is applied immediately with **confidence 1.0** and
reason `"user correction"`.

### Step 3: Structural Rules

These rules fire before any merchant matching:

| Pattern | Category | Notes |
|---------|----------|-------|
| `TRANSFER TO`, `TRANSFER FROM`, `PAYMENT THANK YOU`, `AUTOPAY`, `CARD PAYMENT` | Transfer | Excluded from spending totals |
| Positive amount + `REFUND` or `REVERSAL` keyword | Refund | Money back, NOT income |
| Positive amount + known merchant name | Refund | Money back from that merchant |
| Positive amount + `INVOICE`, `PAYROLL`, `DEPOSIT`, `CLIENT` | Income | Money coming in |

**Confidence:** 0.98 for all structural rules.

### Step 4: Merchant Rules (from `config/rules.yaml`)


## 5. Categories

| Category | Description |
|----------|-------------|
| Software | SaaS, dev tools, cloud services |
| Travel | Airlines, hotels, rideshare |
| Meals | Restaurants, cafes |
| Office Supplies | Stationery, office equipment |
| Marketing | Ad platforms, advertising |
| Utilities | Internet, phone, power |
| Subscriptions | Streaming, media services |
| Income | Money coming in (invoices, payroll) |
| Refund | Money back from a merchant (not income) |
| Transfer | Internal transfers, card payments (excluded from spending) |
| Needs Review | Could not confidently categorize |

## 6. API Endpoints

All backend endpoints are under `/api`.

### POST `/api/upload`

Upload a multipart CSV file. Returns categorized transactions, summary, and
parse warnings.

**Request:** `file` (multipart/form-data, `.csv`, max 10 MB)

**Response:**
```json
{
  "transactions": [...],
  "summary": {"Meals": -45.50, "Software": -120.00, ...},
  "warnings": ["Row 5: blank description", ...]
}
```

### PATCH `/api/transactions/{id}`

Update a transaction's category. Also saves a merchant override so future
uploads of the same merchant are auto-categorized.

**Request body:** `{"category": "Meals"}`

**Response:** Updated transaction + new summary.

### GET `/api/summary`

Returns per-category totals. Transfer is excluded from spending_total.
Refunds are shown as negative spend. Needs Review is shown separately.

**Response:**
```json
{
  "totals": {"Meals": -45.50, "Transfer": -500.00, ...},
  "needs_review_total": 0.0,
  "spending_total": -45.50
}
```

### GET `/api/export`

## 8. Test Coverage

**88 total tests**, all passing:

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `test_csv_parser.py` | 34 | Both formats, header variants, dates, amounts, duplicates, edge cases |
| `test_classifier.py` | 43 | Every pipeline step, all tricky sample-data rows, override priority, ambiguity, **no-AI-SDK guarantee** |
| `test_overrides.py` | 5 | Get, set, remove, clear, copy-on-read |
| `test_normalizer.py` | 10 | Uppercase, prefix stripping, trailing numbers, whitespace collapse |
| `test_api.py` | 11 | Upload (both formats), invalid file type, empty file, duplicates, tricky rows, PATCH, summary, export |

**No-AI-SDK guarantee:** `test_brain_imports_no_ai_sdk` asserts that no AI packages
(openai, anthropic, gemini, cohere, llama_index) are imported anywhere in the
brain code.

## 9. Sample Data

Two CSVs generated by `sample_data/generate.py` (stdlib only, fixed seed = 42):

- **`amount_single.csv`** — `Date, Description, Amount` with ISO dates
- **`debit_credit.csv`** — `Transaction Date, Details, Debit, Credit` with `$`
  signs, commas, MM/DD/YYYY dates

Each has 70 rows including deliberate tricky rows:

| Tricky Row | Expected Category | Expected needs_review |
|------------|------------------|----------------------|
| Duplicate Adobe charge | Software | False |
| REFUND UBER *TRIP | Refund | False |
| TRANSFER TO SAVINGS 1234 | Transfer | False |
| PAYMENT THANK YOU | Transfer | False |
| INVOICE DEPOSIT CLIENT ACME | Income | False |
| Blank description | Needs Review | True |
| FOREIGN CURRENCY FEE EUR | Needs Review | True |
| AMZN Mktp US*BOOKS | Needs Review | True |
| PAYPAL *EBAY SELLER | Needs Review | True |

## 10. Design Decisions

### In-Memory State (No Database)

Transactions and overrides live in Python dicts. This is suitable for a
single-user take-home app. **Production choice: PostgreSQL** — documented in
DESIGN.md with rationale (persistence across restarts, concurrent access, ACID,
query performance).


## 11. How to Run

### Backend

```powershell
cd backend
pip install -r requirements.txt
pip install pytest httpx python-multipart ruff
python -m uvicorn app.main:app --port 8000 --host 127.0.0.1
pytest -v
ruff check .
```

### Frontend

```powershell
cd frontend
npm install
npm run dev          # http://localhost:5173
npm run build        # production build
npx tsc --noEmit     # type check
```

### Full Flow

1. Start backend (Terminal 1)
2. Start frontend (Terminal 2)
3. Open http://localhost:5173
4. Upload a sample CSV from `sample_data/`
5. Review categorized transactions
6. Fix "Needs Review" rows using the dropdown
7. Click "Export CSV" to download final results

## 12. Limitations

1. **In-memory state** is lost on server restart. Use Postgres in production.
2. **Override store is thread-unsafe** — single-user app assumption.
3. **Each upload replaces previous data** — no upload history.
4. **Date parsing** limited to ISO and US formats; DD/MM/YYYY not supported.
5. **Merchant rules are static YAML** — no learning from user corrections
   beyond the override store.

## 13. HARD RULEs Compliance

| Rule | Status |
|------|--------|
| No LLM/AI API for categorization | ✅ Verified by test |
| Uncertain → "Needs Review" | ✅ Pipeline step 5 |
| No secrets committed | ✅ .env.example only, .env ignored |
| Fake data only | ✅ Sample data is fictional |
| Tests included | ✅ 88 tests, all passing |

## 14. File Summary

| File | Purpose |
|------|---------|
| `README.md` | Setup and run instructions |
| `DESIGN.md` | Design decisions, pipeline, limitations |
| `AI_USAGE.md` | Template for AI tool usage disclosure |
| `WORKING.md` | This document — full working explanation |
| `backend/app/brain/classifier.py` | 5-step categorization pipeline |
| `backend/app/brain/constants.py` | All thresholds and weights |
| `backend/app/brain/normalizer.py` | Description normalization |
| `backend/app/brain/overrides.py` | User override store |
| `backend/app/parsing/csv_parser.py` | CSV parsing with edge case handling |
| `backend/app/api/routes.py` | FastAPI endpoints |
| `backend/app/store.py` | In-memory transaction store |
| `backend/app/models.py` | Pydantic v2 models |
| `backend/config/rules.yaml` | 52 merchant categorization rules |
| `frontend/src/App.tsx` | Main React component |
| `frontend/src/services/api.ts` | API fetch wrapper |
| `sample_data/generate.py` | Sample CSV generator |

## 15. Project Summary

### Title

**Statement Categorizer** — A deterministic, rule-based transaction categorization web application for freelancers and small business owners.

### Description

The Statement Categorizer helps freelance developers and designers organize their business credit card transactions for tax time. Users upload a CSV statement, and the app automatically categorizes each transaction using a 100% deterministic Python brain (no LLM or AI API). Transactions are sorted into categories like Software, Travel, Meals, Office Supplies, Marketing, Utilities, Subscriptions, Income, Refund, and Transfer. Uncertain transactions are flagged as "Needs Review" so users can correct them — a wrong guess is intentionally worse than asking. The app displays per-category totals, lets users fix categories through a React frontend, and exports the final result as CSV.

**Key features:**
- Handles messy real-world CSV formats (Amount or Debit/Credit columns, multiple date formats, various amount formats)
- 52 pre-configured merchant rules across 10 categories
- User overrides persist across uploads
- Duplicate detection and warning system
- No database — in-memory state with PostgreSQL noted as the production choice
- 88 tests covering parser, brain, overrides, and API endpoints
- No AI/LLM used for categorization decisions (verified by test)
