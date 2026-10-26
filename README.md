# TaxBrain: Bank & Credit Card Statement Categorizer

> **IRS Schedule C Tax Categorization Engine for Freelance Creatives & Solo Proprietors**  
> *Built with Python (FastAPI), React (Vite), and a 100% deterministic, zero-LLM decision engine.*

---

## 📌 Executive Summary & Assessment Requirements

This project fulfills the **Statement Categorizer Assessment** as specified in [TASK.md](file:///d:/Programs/statement_categorizer/savvpro-test-statement-categorizer/TASK.md):

- **Target Persona**: **Freelance Digital Creatives & Tech Contractors** preparing their federal tax returns (**IRS Form 1040 Schedule C**).
- **The Big Rule**: **The Brain is 100% custom code.** No big AI models (GPT, Claude, Gemini) are used to categorize transactions. Classification is completely deterministic, transparent, and auditable.
- **Safety First ("When in doubt, ask")**: Ambiguous vendors (such as `JOES CAFE 9921`, `Target`, or `Walmart`) are flagged for **Needs Review** rather than guessed blindly.
- **Real-World Edge Cases**:
  - **Refunds**: Classified as *Expense Offsets*, reducing expenses rather than falsely inflating taxable revenue.
  - **Transfers & Credit Card Autopay**: Classified as *Non-Expenses*, excluded from tax deductions.
  - **Business Meals**: Automatically calculated with the statutory **50% IRS deduction limit** (IRC § 274(n)).

---

## 🚀 Key Features

1. **The 7-Layer Brain Decision Engine**:
   - Normalizer strips statement noise (prefixes like `POS DEBIT`, `SQ *`, card masks `XXXX-1234`, phone numbers, state codes).
   - Cash-flow direction checks (Refunds vs. Transfers vs. Gross Revenue).
   - Deterministic high-confidence regex matching across SaaS, Travel, Equipment, Office, and Legal services.
   - Fuzzy matching algorithm for statement abbreviations and typos (e.g. `ADOB CREATV CLD` matches `Adobe`).
   - Safety shield for ambiguous merchants (`JOES CAFE 9921` $\rightarrow$ Needs Review).
   - Session memory for user custom rules.
2. **Interactive Schedule C Tax Dashboard**:
   - Real-time financial KPI metrics: Gross Income, Deductible Expenses, Net Taxable Profit, and Needs Review rows.
   - Deductions breakdown by Schedule C line item with visual progress bars.
   - 1-Click preset switcher with 3 realistic messy statements (`Freelance Designer CC`, `Sole Proprietor Checking`, `Tech Contractor Q4`).
   - Drag-and-drop CSV uploader with auto-detection for Chase, Amex, Bank of America, Wells Fargo, Capital One, and generic formats.
3. **Human-in-the-Loop Review & Export**:
   - Resolve uncertain rows in 1 click with suggested categories and audit notes.
   - "Remember this rule" toggle to persist vendor categories.
   - Export audit-ready reports: Categorized Transactions CSV, Schedule C Tax Summary CSV, or full JSON audit package.

---

## 🛠️ Quick Start & Setup Guide

### Prerequisites
- **Python**: 3.10+ (tested on Python 3.12)
- **Node.js**: 18+ and `npm`

---

### 1. Backend Setup & Run (FastAPI)

```bash
# Navigate to repository root
cd savvpro-test-statement-categorizer

# Create Python virtual environment
python -m venv backend/.venv

# Activate virtual environment
# Windows (PowerShell):
.\backend\.venv\Scripts\Activate.ps1
# Mac / Linux:
# source backend/.venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt

# Start the FastAPI server
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

The API will be available at: `http://127.0.0.1:8000`  
Interactive Swagger API documentation: `http://127.0.0.1:8000/docs`

---

### 2. Frontend Setup & Run (React + Vite)

In a new terminal window:

```bash
# Navigate to the frontend directory
cd savvpro-test-statement-categorizer/frontend

# Install dependencies
npm install

# Start Vite dev server
npm run dev
```

Open your browser at: **`http://localhost:5173`**

---

### 3. Run Automated Tests

To run the complete test suite (23 unit and integration tests):

```bash
# From repository root with virtual environment activated:
# Windows (PowerShell):
$env:PYTHONPATH="backend"; .\backend\.venv\Scripts\pytest backend/tests

# Mac / Linux:
# PYTHONPATH=backend pytest backend/tests
```

**Test Coverage Highlights:**
- `test_normalizer.py`: Prefix stripping, card masking, location parsing, signal flag detection.
- `test_brain.py`: SaaS matching, travel matching, equipment Safe Harbor, 50% meals rule, ambiguous cafe review routing, fuzzy typo matching.
- `test_edge_cases.py`: Refunds as expense offsets, transfers/autopay as non-expenses, currency symbol parsing (`$1,234.56`, `(50.00)`), and Schedule C deduction math.
- `test_api.py`: FastAPI endpoints, multipart CSV file upload, custom rule endpoints.

---

## 📁 Repository Structure

```
savvpro-test-statement-categorizer/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI application & API endpoints
│   │   ├── models.py            # Pydantic schemas for transactions & tax summary
│   │   └── brain/
│   │       ├── __init__.py
│   │       ├── taxonomy.py      # IRS Schedule C category definitions & 50% tax rules
│   │       ├── normalizer.py    # Statement noise stripping & token extraction
│   │       ├── rules.py         # Deterministic regex patterns & vendor registries
│   │       ├── categorizer.py   # Core 7-layer Brain decision engine
│   │       └── parser.py        # Flexible bank statement CSV parser
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_normalizer.py   # Text sanitization tests
│   │   ├── test_brain.py        # Core classification tests
│   │   ├── test_edge_cases.py   # Refunds, transfers, and tax calculation tests
│   │   └── test_api.py          # FastAPI endpoint integration tests
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js           # Vite configuration with backend proxy
│   └── src/
│       ├── main.jsx
│       ├── App.jsx              # Main dashboard application
│       ├── index.css            # Custom obsidian glassmorphism design system
│       ├── services/
│       │   └── api.js           # Backend API client
│       └── components/
│           ├── Header.jsx       # Navigation bar & zero-LLM compliance badge
│           ├── SampleSelector.jsx # 1-click presets & drag-and-drop uploader
│           ├── MetricsOverview.jsx # Financial KPI summary cards
│           ├── TaxSummaryCard.jsx  # Schedule C expense progress breakdown
│           ├── TransactionTable.jsx # Interactive table with search & filters
│           ├── ReviewModal.jsx  # Human-in-the-loop review drawer & rule memory
│           └── ExportModal.jsx  # Audit package CSV/JSON export dialog
├── data/
│   ├── freelance_designer_messy_cc.csv # Sample credit card with refunds & Joe's Cafe
│   ├── sole_prop_checking_mixed.csv    # Sample checking with client deposits & draws
│   └── tech_contractor_q4.csv          # Sample contractor Q4 tax prep statement
├── README.md                    # Setup, running, and testing instructions (this file)
├── DESIGN.md                    # In-depth use case and 7-layer brain architecture
├── AI_USAGE.md                  # Comprehensive AI usage & token transparency report
└── TASK.md                      # Original assessment description
```

---

## 📑 Assessment Documentation Links

- **Architecture & Decision Engine**: [DESIGN.md](file:///d:/Programs/statement_categorizer/savvpro-test-statement-categorizer/DESIGN.md)
- **AI Tooling & Token Usage**: [AI_USAGE.md](file:///d:/Programs/statement_categorizer/savvpro-test-statement-categorizer/AI_USAGE.md)
- **Original Task Specification**: [TASK.md](file:///d:/Programs/statement_categorizer/savvpro-test-statement-categorizer/TASK.md)
