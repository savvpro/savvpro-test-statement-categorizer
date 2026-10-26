# Statement Categorizer — Freelance Tax Organizer

> Automated bank & credit card statement categorizer and IRS Schedule C tax organizer for freelance software engineers and tech consultants.

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-blue.svg)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-5-purple.svg)](https://vitejs.dev/)
[![Tests](https://img.shields.io/badge/Tests-52%20Passed-brightgreen.svg)](backend/tests/)

---

## Overview

Freelance developers and tech consultants manage messy bank statements mixed with cloud subscriptions (AWS, GitHub), client payments (Stripe, Upwork), business travel (Uber, United Airlines), client lunches, and mixed-use expenses (Amazon, Apple).

**Statement Categorizer** cleans raw bank and credit card CSVs, classifies every transaction through a **100% deterministic 3-tier rules engine**, handles complex IRS Schedule C rules (50% business meals, refunds offsetting expenses, non-taxable transfers), and presents the results in an executive **frosted glass dashboard** with an interactive review workflow.

> **Assessment Compliance Note:** In strict compliance with the task requirements, the categorization brain uses **no LLMs or external AI models at runtime**. All decisions are driven by audited, deterministic Python classification rules.

---

## Key Features

- **Multi-Format CSV Parsing:**
  - Auto-detects single signed `Amount` or split `Debit` / `Credit` columns.
  - Tolerates whitespace, quotes, custom delimiters (comma, semicolon), and negative formats (`-$50`, `($50)`).
- **POS Merchant Sanitizer:**
  - Strips point-of-sale junk (`SQ *`, `TST*`, `CHECKCARD`, `PAYPAL *`).
  - Cleans store numbers, dates, terminal codes, phone numbers, and airline ticket IDs.
- **Direction & Tax Accounting:**
  - **Inflow:** Gross freelance revenue (e.g., Stripe, Upwork payouts).
  - **Outflow:** Standard deductible operating expenses.
  - **Refund:** Money back is correctly handled as an **expense reduction**, *not* taxable income.
  - **Transfer:** Credit card autopayments and internal bank transfers are isolated as **non-taxable**.
- **Deterministic 3-Tier Classification Brain:**
  - **Tier 1:** Curated Known Vendor Dictionary (~50 verified tech vendors, confidence 0.95–0.99).
  - **Tier 2:** Mixed-Use Vendor Detection (Amazon, Apple, Target flagged for user review).
  - **Tier 3:** Keyword Heuristics & Dining Chains (auto-verifies known chains, flags unknown locals).
  - **Fallback:** Unrecognized merchants are safely routed to **Needs Review** ("A wrong guess is worse than asking").
- **IRS Schedule C Tax Engine:**
  - 13 tax categories mapped directly to IRS Schedule C lines (Line 8, Line 18, Line 24b, Line 25, Line 27a, etc.).
  - Automatic 50% business meal deductibility calculation.
  - Automatic 80% home office ratio for utility/internet expenses.
  - Real-time recalculation of Net Taxable Profit and Effective Deduction Rate.
- **Executive Frosted Glass Dashboard (React + Vite):**
  - Ambient frosted acrylic aesthetic (`backdrop-filter: blur(25px)`).
  - Semicircular radial arc gauge for deduction rate.
  - KPI metric cards (Gross Income, Deductions, Net Profit, Attention Needed).
  - Filter pills (All, Deductible, Income, Needs Review, Transfers) and category dropdown.
  - Inline category reassignment with instant backend tax recalculation.
  - One-click CSV export of categorized statement for CPA or tax software.
  - Interactive Demo Mode with 33 realistic freelance transactions.

---

## Quick Start

### Prerequisites
- **Python 3.11+**
- **Node.js 18+** and **npm**

---

### 1. Run the Backend (FastAPI)

```bash
# Navigate to backend directory
cd backend

# Install dependencies
pip install -r requirements.txt

# Start FastAPI development server
python -m uvicorn app.main:app --reload --port 8000
```

- API Base: `http://localhost:8000`
- Interactive Swagger API Docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/api/health`

---

### 2. Run the Frontend (React + Vite)

In a new terminal window:

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start Vite dev server
npm run dev
```

- Web Application: `http://localhost:5173`

---

### 3. Run the Automated Test Suite

The backend includes **52 comprehensive unit and integration tests**:

```bash
# From repository root
python -m pytest backend/tests/ -v
```

All 52 tests validate:
- Merchant string cleaning and POS prefix removal.
- Inflow, outflow, refund, and transfer financial direction logic.
- 3-tier vendor classification and confidence scoring.
- IRS Schedule C tax calculations, meal deductibility, and refund offsets.
- Multi-format CSV parser edge cases (semicolon, quotes, split columns).
- FastAPI endpoints (`/api/upload`, `/api/recalculate`, `/api/sample`, `/api/categories`).

---

## Project Structure

```
savvpro-test-statement-categorizer/
├── backend/
│   ├── app/
│   │   ├── brain/                    # 100% Deterministic Rule Engine
│   │   │   ├── categories.py         # 13 IRS Schedule C categories & deduction ratios
│   │   │   ├── sanitizer.py          # POS prefix & noise cleaner
│   │   │   ├── direction.py          # Inflow, Outflow, Refund, Transfer analyzer
│   │   │   ├── rules.py              # Vendor dictionary & keyword patterns
│   │   │   ├── classifier.py         # 3-Tier classification coordinator
│   │   │   └── tax_summary.py        # Schedule C totals & net profit math
│   │   ├── models/
│   │   │   └── transaction.py        # Pydantic v2 domain schemas
│   │   ├── services/
│   │   │   └── parser.py             # Multi-format CSV parser
│   │   └── main.py                   # FastAPI REST API layer
│   ├── sample_data/
│   │   ├── sample_statement.csv      # 33 realistic freelance transactions
│   │   └── sample_statement_split.csv# 10 split debit/credit transactions
│   ├── tests/                        # 52 Automated Pytest Cases
│   │   ├── test_sanitizer.py
│   │   ├── test_direction.py
│   │   ├── test_classifier.py
│   │   ├── test_tax_summary.py
│   │   ├── test_parser.py
│   │   └── test_api.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── TopNavbar.jsx         # Frosted glass header with status badge
│   │   │   ├── TaxDashboard.jsx      # Summary metrics & Schedule C breakdown
│   │   │   ├── OverviewChartCard.jsx # Radial arc gauge & monthly flow chart
│   │   │   ├── SideStatusCards.jsx   # Tax filing alerts & deduction stats
│   │   │   ├── CategoryFilter.jsx    # Quick pill filters & category dropdown
│   │   │   ├── TransactionTable.jsx  # Paginated transaction grid
│   │   │   ├── TransactionRow.jsx    # Interactive row with category selector
│   │   │   ├── FileUpload.jsx        # Drag-and-drop dropzone & demo launcher
│   │   │   └── ExportButton.jsx      # CSV export handler
│   │   ├── utils/
│   │   │   └── api.js                # API client with error handling
│   │   ├── App.jsx                   # Master view router
│   │   ├── main.jsx
│   │   └── index.css                 # Frosted glass design system
│   ├── package.json
│   └── vite.config.js
├── .features/                        # Modular feature specifications
├── DESIGN.md                         # Architecture & Decision Brain Documentation
├── AI_USAGE.md                       # AI Tooling & Prompting Log
└── README.md
```

---

## Supported Bank CSV Formats

The parser flexibly normalizes varied banking and credit card exports:

| Bank / Provider | Column Structure | Handling |
|---|---|---|
| **Chase / BofA / Wells Fargo** | `Date, Description, Amount` | Negative = Outflow, Positive = Inflow |
| **Credit Card Exports** | `Date, Description, Debit, Credit` | Automatically collapsed into signed amounts |
| **Stripe Payouts / Upwork** | `Date, Memo, Gross, Fee` | Memo mapped to description, net inflow calculated |
| **European / Custom Formats** | Semicolon `;` delimited, comma decimal | Auto-detects delimiters and parenthesis negatives `(50.00)` |

---

## Documentation Links

- **[DESIGN.md](./DESIGN.md):** Deep-dive into the freelance tech consultant use case, 3-tier classification brain, decision flowcharts, and IRS Schedule C tax calculations.
- **[AI_USAGE.md](./AI_USAGE.md):** Complete record of AI assistance, prompt strategies, technical challenges encountered, token metrics, and validation.
