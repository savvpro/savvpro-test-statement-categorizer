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

### Pydantic v2

All request/response validation uses Pydantic v2 models for type safety and
automatic API documentation (Swagger UI at `/docs`).

### ruff

Python linting with ruff (E, F, I, N, S, W rules, S101 ignored for test
asserts).

### Plain CSS Frontend

No heavy UI library (no Bootstrap, Material UI, etc.). Custom CSS keeps the
bundle small (~150 KB gzipped) and dependencies minimal.

### Deterministic Brain

No randomness, no ML, no LLM. Same input always produces same output. All
thresholds and weights are constants in `constants.py` — no magic numbers
scattered in the code.


Downloads the final categorized result as a CSV file.

## 7. CSV Parser Capabilities

The parser handles real-world statement messiness:

| Feature | Implementation |
|---------|---------------|
| Single `Amount` column | Auto-detected from headers |
| Separate `Debit`/`Credit` columns | Auto-detected, debit=negative, credit=positive |
| Date formats | `YYYY-MM-DD` and `MM/DD/YYYY` |
| Amount formats | `$1,234.50`, `(45.00)`, `-45.00`, empty cells |
| Header variants | Date/Posting Date/Transaction Date, Description/Details/Memo |
| Duplicate rows | Flagged with `is_duplicate=true`, not silently dropped |
| Blank descriptions | Warned, categorized as Needs Review |
| Foreign currency lines | Warned |
| Malformed rows | Skipped with warning, app does not crash |
| Empty file / missing columns | Clear HTTP 400 error messages |

Sign convention: **spending is negative, money in is positive.**

52 merchants are defined across 10 categories. Two match types:

| Match Type | Confidence | Description |
|------------|-----------|-------------|
| Exact | 0.95 | Normalized description equals merchant name exactly |
| Keyword/contains | 0.80 | Merchant name appears as substring in normalized description |

### Step 5: Ambiguity → "Needs Review"

If none of the above steps produce a confident result, the transaction goes to
"Needs Review" with confidence 0.0. This happens when:

- Best confidence < 0.70
- Top-2 confidence gap < 0.10 (two categories too close to call)
- No merchant rule matches
- Description is blank
- Description contains an inherently ambiguous merchant: `AMAZON`, `AMZN`,
  `PAYPAL` (unless a user override exists)

**Why?** A wrong guess is worse than asking. If the brain is not sure, it must
say "Needs Review."

│
└── sample_data/                # Sample CSV files for testing
    ├── generate.py             # Stdlib-only CSV generator (fixed seed=42)
    ├── amount_single.csv       # Single Amount column, ISO dates (70 rows)
    └── debit_credit.csv        # Debit/Credit columns, $ signs, MM/DD/YYYY (70 rows)
```

**Core rule:** The categorization "brain" is 100% deterministic Python code — no
LLM or AI API is used for category decisions.
