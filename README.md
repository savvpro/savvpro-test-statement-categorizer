# LedgerLens — Freelance Statement Categorizer

> **Statement Categorizer Assessment**  
> Branch: `candidate-tooba41`  
> Target Persona: **Freelance Creative & Consultant (IRS Schedule C Tax Preparation)**

LedgerLens reads bank and credit card statement CSVs, analyzes each transaction using a **100% custom deterministic heuristic brain** (zero big AI models/LLMs), identifies eligible business tax deductions, credits refunds, filters non-expense transfers, and flags ambiguous rows for review.

---

## Features

- **Custom Deterministic Brain:** Built with pure Python rule engines and regex tokenizers. Strictly complies with **The One Big Rule** (no OpenAI, Anthropic, Gemini, or other LLMs for decisions).
- **Tax-Centric Classification:** Categorizes transactions into Schedule C lines (Software, Travel, 50% Meals, Office Supplies, Advertising, Utilities, Fees, Contract Labor).
- **Accurate Refund & Reversal Handling:** Refunds (e.g. `REFUND ADOBE CREATIVE CLOUD`) are matched to their parent category and credited back against gross expenses—never erroneously counted as taxable client revenue.
- **Transfer & Debt Isolation:** Transfers to savings, checkings, and credit card payoffs (`TRANSFER TO SAVINGS`, `AUTOPAY PAYMENT`) are automatically excluded from business deductions.
- **Safety First ("A wrong guess is worse than asking"):** Ambiguous merchants (e.g. `JOES CAFE 9921`) and unverified deposits default to **Needs Review** with human-readable explanations.
- **Interactive React UI:**
  - Drag-and-drop CSV upload + 1-click **"Try Demo Statement"** button for instant evaluation.
  - Live metric cards (Gross Deductible Expenses, Refunds, Net Deductions, Client Revenue, Needs Review count).
  - Filter tabs (`All`, `Needs Review`, `Verified`, `Expenses`, `Income & Transfers`).
  - Search bar to find merchants instantly.
  - Inline category dropdowns allowing the user to review and fix flagged rows on the fly with real-time recalculation of totals.
  - One-click **Export Reconciled Statement (CSV)**.
- **Robust CSV Parsing:** Accepts multiple header schemas (e.g. `Date`/`Transaction Date`, `Description`/`Merchant`, `Amount` or split `Debit`/`Credit` columns).

---

## Project Structure

```
savvpro-test-statement-categorizer/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── categorizer.py    # The Brain: Heuristic decision engine
│   │   └── main.py           # FastAPI app & endpoints
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_api.py       # API integration tests
│   │   └── test_categorizer.py # Unit tests for the brain
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── assets/
│   │   ├── App.tsx           # React Dashboard component
│   │   ├── main.tsx          # Root mount
│   │   ├── index.css         # Responsive styling
│   │   └── vite-env.d.ts
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
├── sample_statement.csv      # Sample freelance statement
├── pytest.ini
├── .gitignore
├── DESIGN.md                 # Design & architecture documentation
├── AI_USAGE.md               # AI tooling and token metrics report
└── README.md                 # This file
```

---

## Getting Started

### Prerequisites

- **Python:** 3.10+ (tested on Python 3.12)
- **Node.js:** v18+ (tested on Node v22.15 & pnpm v10.25)

---

### 1. Backend Setup & Run

Open a terminal in the project root:

```bash
# Navigate to backend (or activate virtual environment)
cd backend

# If creating a new virtual environment:
python -m venv .venv

# Activate virtual environment
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Mac/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the FastAPI server
uvicorn app.main:app --reload --port 8000
```

The API will be running at `http://localhost:8000` (Swagger docs available at `http://localhost:8000/docs`).

---

### 2. Frontend Setup & Run

Open a separate terminal in the `frontend` folder:

```bash
cd frontend

# Install dependencies
pnpm install
# or: npm install

# Start development server
pnpm dev
# or: npm run dev
```

The application will be live at `http://localhost:5173`.

---

### 3. Running the Test Suite

From the project root:

```bash
# Run pytest (automatically uses pytest.ini configured for backend)
pytest
```

All 23 unit and API integration tests will run and validate the categorizer logic, edge cases, and endpoints.

---

## How to Test the App in 30 Seconds

1. Open `http://localhost:5173` in your browser.
2. Click the **"Try Demo Statement"** button.
3. Observe how:
   - `ADOBE CREATIVE CLOUD` is categorized as `Software & Subscriptions` ($29.99).
   - `UBER TRIP` is categorized as `Travel & Transit` ($18.50).
   - `TRANSFER TO SAVINGS` is marked `Transfer` and excluded from expenses.
   - `REFUND ADOBE CREATIVE CLOUD` is credited against software expenses without counting as income.
   - `JOES CAFE 9921` is highlighted in **Needs Review** with an amber alert.
   - `CLIENT PAYMENT` is categorized as `Client Revenue` ($1,450.00).
4. Select the category dropdown for `JOES CAFE 9921` and switch it to `Meals (50% Deductible)`.
5. Notice the **Needs Review** count drops to 0 and all financial metrics recalculate automatically!
6. Click **"Export Reconciled Statement (CSV)"** to download the clean report.
