# TaxSort — Bank Statement Categorizer for Freelancers

A production-grade web application that ingests messy bank and credit card statements, classifies every transaction for tax season (IRS Schedule C / business deductions), calculates net tax deductions, and flags ambiguous rows for user review.

> **The One Big Rule:** The categorization brain is 100% deterministic custom Python code. No large AI models (GPT, Claude, Gemini) are used for categorization decisions.

---

## 🚀 Quick Start (1-Click Run)

### Windows:
Double-click `run_app.bat` or run in terminal:
```cmd
run_app.bat
```
This automatically starts the FastAPI backend (port `8000`), the React frontend (port `5173`), and opens your default browser.

### Mac / Linux:
```bash
chmod +x run_app.sh
./run_app.sh
```

---

## 🛠️ Manual Setup

### 1. Backend (Python FastAPI)
```bash
cd backend
python -m pip install -r requirements.txt
python run.py
```
Backend API will be running at `http://localhost:8000` (Swagger docs at `http://localhost:8000/docs`).

### 2. Frontend (React + Vite)
```bash
cd frontend
npm install
npm run dev
```
Frontend will be running at `http://localhost:5173`.

### 3. Run Automated Tests
```bash
cd backend
python -m pytest tests -v
```
All **22 unit tests** pass with 100% success rate testing the normalization pipeline, edge cases, Brain decision rules, and API endpoints.

---

## 🎯 Use Case: Freelance Creative Designer & Tech Consultant

Built specifically for digital freelancers, creative designers, and consultants filing business taxes:

- **100% Deductible Software & Subscriptions:** `Adobe Creative Cloud`, `Figma`, `GitHub`, `Notion`, `AWS`, `Vercel`, `OpenAI`.
- **100% Deductible Travel & Rideshare:** `Uber`, `Lyft`, `Delta Air Lines`.
- **50% Deductible Meals & Client Entertainment:** `Starbucks`, `Blue Bottle Coffee` (50% deduction rule applied to net tax summary).
- **Internal Transfers (Not Expenses):** `TRANSFER TO SAVINGS`, `AUTOPAY CREDIT CARD` are recognized and excluded from expenses.
- **Refunds (Expense Offsets, NOT Income):** Negative expense amounts or returns (e.g. `REFUND: APPLE STORE`) reduce total deductions instead of being falsely counted as taxable income.
- **Needs Review (Ambiguity Detection):** Cryptic or unrecognized venues (`JOES CAFE 9921`) are flagged for user review with a confidence score and explanation.
- **User Feedback Loop:** When a user re-categorizes a transaction in the UI, the Brain learns the override for that merchant and auto-updates similar and future rows.

---

## 📂 Project Structure

```
savvpro-test-statement-categorizer/
├── backend/
│   ├── app/
│   │   ├── engine/
│   │   │   ├── normalizer.py       # POS prefixes, phone, store & state stripper
│   │   │   ├── rules.py            # Tax taxonomy, keywords & movement patterns
│   │   │   ├── brain.py            # "The Brain" deterministic categorizer
│   │   │   ├── memory.py           # User override feedback learning store
│   │   │   └── aggregator.py       # Financial summaries & tax calculations
│   │   ├── parser/
│   │   │   └── csv_parser.py       # Universal bank CSV statement parser
│   │   ├── models/
│   │   │   └── schemas.py          # Pydantic schemas
│   │   └── main.py                 # FastAPI application endpoints
│   ├── tests/
│   │   ├── conftest.py             # Test isolation fixtures
│   │   ├── test_normalizer.py      # Merchant string sanitization tests
│   │   ├── test_brain.py           # Core category assignment tests
│   │   ├── test_edge_cases.py      # Refunds, transfers & Joe's Cafe tests
│   │   └── test_api.py             # Integration tests for FastAPI endpoints
│   ├── requirements.txt
│   └── run.py                      # Backend launcher
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   └── Icons.jsx           # Zero-dependency SVG icons
│   │   ├── App.jsx                 # Main application dashboard
│   │   └── index.css               # Clean dark-mode design system
│   ├── package.json
│   └── vite.config.js
├── sample_data/
│   └── freelancer_bank_statement.csv # 23 realistic transactions with all edge cases
├── DESIGN.md                       # In-depth system design & Brain architecture
├── AI_USAGE.md                     # Transparency log, prompt notes & token counts
├── run_app.bat                     # 1-click Windows runner
├── run_app.sh                      # 1-click Mac/Linux runner
└── README.md                       # Documentation
```

---

## 📋 Documentation Links

- [DESIGN.md](DESIGN.md) — Detailed use case analysis, Brain decision algorithm, confidence formulas, and edge case breakdown.
- [AI_USAGE.md](AI_USAGE.md) — Transparent documentation of AI tools used, mistakes encountered, resolutions, and token accounting.

---

## 👤 Author & Candidate Info

- **Candidate:** Muhammad Usman
- **GitHub:** [@usmhan123](https://github.com/usmhan123)
- **Branch:** `candidate-usmhan123`
- **Assessment Target:** `savvpro/savvpro-test-statement-categorizer` (main branch)
