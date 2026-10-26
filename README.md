# Statement Categorizer

An auditable, deterministic bank and credit card statement categorizer built for freelance designers and small business owners preparing for tax season.

The application reads messy bank statements, automatically validates and classifies transactions using an explicit rules hierarchy, detects potential duplicates, separates operating results from internal transfers, and provides an interactive dashboard for reviewing and correcting transactions before exporting to CSV.

---

## Key Features

- **The Brain (Zero-LLM Runtime):** 100% deterministic Python rules engine. Every categorization decision is backed by a specific `Rule ID`, confidence rating, and plain-English explanation.
- **Two-Axis Financial Model:** Separates *Financial Treatment* (`income`, `expense`, `refund`, `transfer`, `fee`) from *Business Category* (`Software`, `Travel`, `Office Supplies`, `Contractor Expense`, etc.).
- **Direction-Aware & Conflict-Free Rules:**
  - Enforces direction matching (`expected_sign`): vendor invoices (`-$50.00`) cannot be mistakenly classified as income.
  - Payment processing fee rule runs before general bank fees, ensuring Stripe/PayPal processing fees map to `Payment Processing`.
  - P2P contractor payments (`Venmo payment to contractor`) are classified as business expenses, while generic transfers route to `Needs Review`.
  - Word boundaries (`\baws\b`) prevent substring collisions with unrelated words like `lawson` or `flaws`.
- **Smart Refund & Transfer Precedence:**
  - Transfers between verified own accounts are excluded from operating P&L calculations.
  - Safe refund handling: only refunds matched to legitimate business expense categories reduce gross expenses; unmatched refunds and payouts are held in `Needs Review` and do **not** reduce expenses.
  - Software refunds automatically link to the corresponding original expense (e.g., `REFUND - ADOBE CREATIVE CLOUD` links to prior Adobe purchase).
- **Provisional vs. Reconciled Financial Summary:**
  - Explicitly flags summaries as **Provisional Operating Result** with unclassified dollar volumes (`$X.XX in review`) whenever unresolved items remain, ensuring unresolved transactions never silently distort profit/loss.
  - Labels as **Operating Result (Reconciled)** once all items are confirmed.
- **Normalized Duplicate Detection:** Identifies and flags potential duplicate charges (`Date`, normalized `Description`, and `Amount`) without deleting records.
- **Decimal-Exact Calculations & Finiteness Checks:** Built with Python's standard `Decimal` module to prevent IEEE-754 floating-point errors, validating finite amounts and rejecting `NaN`/`Infinity`.
- **Live Recalculation & Dedicated Correction Endpoint:** Live updates via `POST /api/transactions/recalculate` and dedicated `POST /api/transactions/correct` endpoint.
- **CSV Export:** Exports the complete corrected dataset with full audit trail attributes and linked purchase IDs.

---

## Tech Stack

- **Backend:** Python 3.11+, FastAPI, Pydantic v2, Uvicorn, Pytest, HTTPX
- **Frontend:** Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS
- **Data & Testing:** Pure in-memory processing (no database setup required), Pytest test suite (52 automated tests including the 9 release-gate checklist tests)

---

## Project Structure

```text
savvpro-test-statement-categorizer/
├── backend/
│   ├── __init__.py
│   ├── main.py          # FastAPI application, CORS & REST endpoints
│   ├── models.py        # Pydantic schemas, Enums, Decimal models
│   ├── parser.py        # CSV parsing, column validation, encoding & date safety
│   ├── rules.py         # Ordered rule hierarchy & word-boundary regexes
│   ├── categorizer.py   # Classification engine, duplicate detection & refund linking
│   └── summaries.py     # Decimal financial aggregation & provisional P&L math
├── tests/
│   ├── __init__.py
│   ├── test_checklist.py    # Dedicated 9-point Financial Correctness Checklist tests
│   ├── test_parser.py       # CSV validation, dates, encoding & NaN/Infinity rejection
│   ├── test_categorizer.py  # Rule precedence, direction checks & word boundaries
│   ├── test_summaries.py    # Decimal summary math & matched/unmatched refund safety
│   └── test_api.py          # HTTP integration tests & correction endpoint
├── data/
│   └── sample_statement.csv # Realistic fake bank statement
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx     # Interactive categorization dashboard
│   │   │   ├── layout.tsx   # Base layout & font configurations
│   │   │   └── globals.css
│   │   ├── lib/api.ts       # Backend API client & CSV exporter
│   │   └── types.ts         # TypeScript interfaces
│   └── package.json
├── requirements.txt
├── README.md
├── DESIGN.md
└── AI_USAGE.md
```

---

## Prerequisites & Installation

### 1. Prerequisites
- Python 3.10+ installed
- Node.js 18+ and npm installed
- Git

### 2. Backend Setup
From the repository root:

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS / Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Frontend Setup
From the repository root:

```bash
cd frontend
npm install
cd ..
```

---

## Running the Application

### 1. Start the Backend API
In your terminal (with the virtual environment activated):

```bash
uvicorn backend.main:app --reload --port 8000
```
- API Base: `http://localhost:8000`
- Interactive Swagger Documentation: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

### 2. Start the Frontend Dashboard
In a separate terminal window:

```bash
cd frontend
npm run dev
```
Open `http://localhost:3000` in your web browser.

> **Tip:** You can click the **"Load Sample Freelancer Statement"** button on the home page to immediately test the application with pre-loaded fake statement data without having to upload a file.

---

## Running Automated Tests

Run the full backend test suite covering parser edge cases, categorizer precedence, duplicate detection, summary math, and the 9-point financial checklist:

```bash
# Make sure .venv is activated
pytest -v
```

All 52 tests will execute:
```text
tests/test_api.py . . . . . .
tests/test_categorizer.py . . . . . . . . . . . . . . . . .
tests/test_checklist.py . . . . . . . . .
tests/test_parser.py . . . . . . . . . . . . . .
tests/test_summaries.py . . . . . .
============================= 52 passed in 3.25s ==============================
```

To run the frontend production build verification:

```bash
cd frontend
npm run build
```

---

## Supported CSV Format & Amount Conventions

### Required Header Columns
The CSV parser expects standard bank statement columns (case-insensitive):
- `Date`: Transaction date (accepts `YYYY-MM-DD`, `MM/DD/YYYY`, `DD/MM/YYYY`, warns on ambiguous dates)
- `Description`: Merchant name or transaction narrative
- `Amount`: Numerical amount (supports commas, currency signs like `$1,200.00`, rejects non-finite values)

### Amount Convention
- **Positive numbers (`+` or unsigned):** Money coming **into** the account (Client payments, refunds, incoming transfers).
- **Negative numbers (`-`):** Money going **out of** the account (Card purchases, software subscriptions, bank fees, outgoing transfers).

### Example CSV (`data/sample_statement.csv`)
```csv
Date,Description,Amount
2024-01-03,ACME CORP - INVOICE 1042,5000.00
2024-01-05,ADOBE CREATIVE CLOUD,-54.99
2024-01-06,UBER *TRIP 8812,-32.50
2024-01-07,STAPLES OFFICE SUPPLIES,-89.75
2024-01-08,TRANSFER TO SAVINGS,-500.00
2024-01-10,JOES CAFE 9921,-18.40
2024-01-10,JOES CAFE 9921,-18.40
2024-01-12,PAYPAL *FREELANDESIGN,3200.00
2024-01-14,AMAZON WEB SERVICES,-149.00
2024-01-15,GOOGLE ADS,-250.00
2024-01-16,REFUND - ADOBE CREATIVE CLOUD,54.99
2024-01-17,WIX PREMIUM PLAN,-16.00
2024-01-18,DELTA AIR LINES,-387.20
2024-01-19,MARRIOTT HOTELS,-212.00
2024-01-20,CLIENT PAYMENT - WEBFLOW PROJECT,1800.00
2024-01-21,STRIPE PROCESSING FEE,-45.00
2024-01-22,TRANSFER FROM CHECKING,300.00
2024-01-23,ATM WITHDRAWAL,-200.00
2024-01-24,CANVA PRO SUBSCRIPTION,-12.99
2024-01-25,INTEREST CHARGE,-3.42
2024-01-26,COSTCO WHOLESALE,-67.80
2024-01-27,PAYMENT RECEIVED - THANK YOU,2500.00
2024-01-28,REFUND - AMAZON MARKETPLACE,29.99
2024-01-29,VENMO TRANSFER,-150.00
2024-01-30,FIGMA PROFESSIONAL,-15.00
2024-01-31,LATE PAYMENT FEE,-35.00
```

---

## Known Limitations & Future Enhancements

1. **In-Memory Processing:** Current version processes statements in memory for rapid, zero-database setup during assessments. Future iterations can add SQLite/PostgreSQL with user accounts.
2. **Persistent Merchant Learning:** When a user customizes a category, future statements can remember that vendor via a persistent merchant rule cache.
3. **Multi-Currency:** Statements are assumed to be denominated in USD (`$`). Multi-currency conversion via fixed or historical rates is planned for future versions.
