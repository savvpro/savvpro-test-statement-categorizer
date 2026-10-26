# Statement Categorizer

A production-grade, deterministic bank and credit card statement categorizer tailored for freelance software engineers and tech small business owners preparing for tax time.

Built with a **100% deterministic rule-based brain** (strictly zero external AI/LLM API calls) and calibrated confidence scoring.

---

## Features

- **The Brain (Deterministic Categorization Engine):**
  - Multi-tier rule hierarchy: User corrections $\rightarrow$ Internal transfers $\rightarrow$ Refund offsets $\rightarrow$ Personal ambiguity gates $\rightarrow$ Exact merchant dictionary $\rightarrow$ Regex pattern rules $\rightarrow$ Rapidfuzz fuzzy matching $\rightarrow$ Threshold fallback.
  - Transparent confidence scores ($0.0 - 1.0$) and human-readable decision reasons for every row.
  - "Needs Review" threshold gating: when confidence is $< 0.75$ or a vendor has mixed personal/business usage, the transaction is flagged for user confirmation.
- **Messy Real-World Edge Cases Handled:**
  - **Refunds & Reversals:** Money back is treated as an expense offset and linked to original charges—never counted as taxable income.
  - **Internal Transfers & Card Payments:** `TRANSFER TO SAVINGS` and credit card autopay payments are isolated as non-spending, preventing double deductions.
  - **Duplicate Detection:** Automatic flags for identical charges on the same date for the same amount.
  - **Personal vs. Business Ambiguity:** Mixed retailers (Amazon, Target, Costco, local cafes) are flagged for tax review.
  - **Foreign Currency & Merchant Fees:** Foreign transaction fees, international wire fees, and bank service charges are isolated under `Bank & Merchant Fees`.
  - **Robust Parser:** Handles multiple encodings (`utf-8`, `utf-8-sig`, `cp1252`, `latin-1`), auto-detects delimiters (`,`, `;`, `\t`, `|`), skips preamble bank headers and footers, and supports single or split debit/credit columns.
  - **Active Rule Learning:** User category corrections can be saved as persistent rules for future statement uploads.
- **Modern Interactive Dashboard:**
  - Single-page React (Vite + TypeScript) dashboard with real-time financial KPI cards.
  - Quick filter buttons (`All`, `Needs Review`, `Duplicates`, `Refunds`, `Transfers`, and by Category).
  - Inline category dropdown with instant recalculation.
  - One-click export to accountant-ready CSV with categorized transactions and tax summary breakdown.

---

## Project Structure

```
statement-categorizer/
├── backend/
│   ├── app/
│   │   ├── api/routes.py            # FastAPI endpoints (/upload, /recalculate, /correct, /export)
│   │   ├── engine/
│   │   │   ├── brain.py             # Multi-layer deterministic categorization engine
│   │   │   ├── normalizer.py        # Description sanitizer (removes POS prefixes, store IDs, codes)
│   │   │   ├── rules.py             # Exact merchants, regex patterns, canonical fuzzy targets
│   │   │   └── edge_cases.py        # Refund linking, transfers, duplicates, ambiguity detection
│   │   ├── services/
│   │   │   ├── parser.py            # Robust CSV parser with encoding & delimiter autodetection
│   │   │   ├── rule_store.py        # Thread-safe persistent JSON rule store
│   │   │   └── exporter.py          # Accountant-ready CSV export formatter
│   │   ├── models/                  # Pydantic v2 schemas
│   │   ├── config.py                # Environment and threshold configuration
│   │   └── main.py                  # FastAPI application entrypoint
│   ├── data/
│   │   └── user_rules.json          # Persistent storage for user-saved rules
│   ├── tests/                       # 28 pytest tests (parser, brain, edge cases, API, rules)
│   ├── requirements.txt             # Python dependencies
│   └── pyproject.toml               # Ruff and Pytest configuration
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Header.tsx           # Navigation bar with export & reset actions
│   │   │   ├── FileUpload.tsx       # Drag-and-drop zone with quick sample buttons
│   │   │   ├── SummaryCards.tsx     # Financial KPIs & review progress bar
│   │   │   ├── CategoryTotals.tsx   # Tax breakdown card with expense percentage bars
│   │   │   └── TransactionTable.tsx # Filterable table with inline category selector & badges
│   │   ├── services/api.ts          # Fetch client connecting to FastAPI backend
│   │   ├── types/index.ts           # TypeScript interfaces matching backend models
│   │   ├── test/App.test.tsx        # Vitest & React Testing Library tests
│   │   ├── App.tsx                  # Main dashboard layout & state management
│   │   └── App.css                  # Modern UI stylesheet
│   ├── package.json                 # Node dependencies & test scripts
│   └── vite.config.ts               # Vite & Vitest configuration
├── sample_data/                     # Realistic sample statements
│   ├── clean_business_credit_card.csv
│   ├── messy_checking_statement.csv
│   ├── edge_cases_and_refunds.csv
│   └── malformed_statement.csv
├── .github/workflows/ci.yml         # GitHub Actions automated test & lint workflow
├── Makefile                         # Unified commands for test, lint, and run
├── DESIGN.md                        # Architectural design & decision-making specification
├── AI_USAGE.md                      # AI tools used, mistakes resolved, and token usage section
├── TASK.md                          # Original assessment task specification (untouched)
└── README.md
```

---

## Quick Start & Setup

### Prerequisites
- **Python 3.11+**
- **Node.js 18+** and **npm**

---

### 1. Backend Setup

```bash
# 1. Create and activate a virtual environment
python -m venv .venv

# On Windows (PowerShell):
.\.venv\Scripts\Activate.ps1

# On macOS/Linux:
source .venv/bin/activate

# 2. Install dependencies
pip install -r backend/requirements.txt

# 3. Start the FastAPI backend server (runs on http://localhost:8000)
# (Ensure PYTHONPATH includes backend)
# On Windows PowerShell:
$env:PYTHONPATH="backend"
uvicorn app.main:app --app-dir backend --reload --port 8000

# On macOS/Linux:
PYTHONPATH=backend uvicorn app.main:app --app-dir backend --reload --port 8000
```

The interactive Swagger API documentation is available at `http://localhost:8000/docs`.

---

### 2. Frontend Setup

In a new terminal:

```bash
cd frontend

# 1. Install dependencies
npm install

# 2. Start the Vite dev server (runs on http://localhost:5173)
npm run dev
```

Open `http://localhost:5173` in your browser.

---

## Running Tests & Linters

### Backend Tests (`pytest`)
All 28 unit and integration tests cover description normalization, encoding/delimiter discovery, brain layers, refund linking, duplicate flags, persistent learning, and API endpoints:

```bash
# Run backend tests
# On Windows PowerShell:
$env:PYTHONPATH="backend"
pytest backend/tests -v

# On macOS/Linux:
PYTHONPATH=backend pytest backend/tests -v
```

### Backend Linter (`ruff`)
```bash
ruff check backend
```

### Frontend Tests (`vitest`)
```bash
cd frontend
npm test
```

### Frontend Production Build
```bash
cd frontend
npm run build
```

---

## Using the Sample Statements

The `sample_data/` directory includes four statements designed to demonstrate the engine's capabilities:

1. **`clean_business_credit_card.csv`**: A clean freelance tech developer statement with recurring SaaS, hardware, and travel expenses.
2. **`messy_checking_statement.csv`**: Realistic bank statement with multi-line preamble metadata headers, semicolon delimiters, currency symbols, thousand commas, POS prefixes, payment aggregators (`SQ *`, `TST*`), foreign transaction fees, and footers.
3. **`edge_cases_and_refunds.csv`**: Demonstrates refund linking (AWS expense offset), duplicate charge detection (same day/amount), non-spending transfers to savings, and personal vs. business ambiguity routing (Target, Amazon, Cafe $\rightarrow$ Needs Review).
4. **`malformed_statement.csv`**: Used to verify clear, friendly error handling when an unparseable file is uploaded.

You can upload these directly through the drag-and-drop zone or click the sample test buttons on the upload screen.
