# Freelance Ledger — Statement Categorizer

**Assessment Submission for SAVV Pro Solutions Technical Assessment (Test 1)**  
**Repository:** [savvpro/savvpro-test-statement-categorizer](https://github.com/savvpro/savvpro-test-statement-categorizer)  
**Authoritative Specification:** [`TASK.md`](TASK.md) · **Architectural Design:** [`DESIGN.md`](DESIGN.md) · **AI Usage Log:** [`AI_USAGE.md`](AI_USAGE.md)

---

## 1. Overview & Purpose

**Freelance Ledger** is a web application designed for independent freelance designers and creative consultants to import messy bank and business credit card statements, automatically categorize each transaction for **U.S. IRS Form 1040 Schedule C** tax preparation, resolve ambiguous items in a dedicated review queue, and review verified spending totals.

### The Big Rule: 100% Deterministic Engine
In strict compliance with `TASK.md`:
> **The brain is our own deterministic code.** No calls to large AI models (GPT, Claude, Gemini, etc.) or external classification APIs are made at runtime. All categorization, confidence scoring, transfer exclusions, and refund offsets are handled by transparent, local, auditable Python heuristics.

---

## 2. Key Features

- **Layered Decision Hierarchy:** Evaluates internal transfers first, refunds second, personal draws third, inbound client revenue fourth, exact merchant SaaS mappings fifth, processor-mangled vendors sixth, and general domain heuristics seventh.
- **Conservative "Needs Review" Routing:** When an entry is ambiguous (e.g. `JOES CAFE 9921`, `AMAZON.COM`), the engine routes it to Needs Review rather than guessing.
- **Refunds Offset Expenses:** Returns and credits are tracked as recovered expense offsets; they are **never** misclassified as taxable business income.
- **Transfers Excluded from Spend:** Account transfers and credit card bill payments are excluded from operating expenses and revenues to prevent catastrophic double-counting.
- **Schedule C Compliance:** Meals and dining are labeled with the IRS 50% business meal deduction limitation (Schedule C Line 24b).
- **Duplicate Charge Detection:** Identical transactions occurring within a 3-day window are flagged with an interactive warning badge.
- **Strict Decimal Arithmetic:** Calculations use Python's `decimal.Decimal` and fixed-point math to prevent IEEE-754 floating-point rounding errors.
- **Interactive Review & CSV Export:** Users can inline-edit categories, observe immediate recalculations of all metrics, and download the reviewed statement as CSV.

---

## 3. Technology Stack

- **Backend:** Python 3.11+, FastAPI (REST API), Pydantic v2 (data modeling), `uvicorn` (ASGI server), `pytest` (automated testing).
- **Frontend:** React 18, Vite, TypeScript, Lucide Icons, Vanilla CSS with custom design system.
- **Package Management:** `pip` / `uv` for Python; `npm` for Node.js.

---

## 4. Setup and Installation

### Prerequisites
- Python 3.11+ installed.
- Node.js 18+ and npm installed.

### A. Backend Setup

1. Open PowerShell or a terminal and navigate to the project root:
   ```bash
   cd "path/to/savvpro-test-statement-categorizer"
   ```

2. Create and activate a Python virtual environment:
   - **Windows (PowerShell):**
     ```powershell
     python -m venv backend\.venv
     backend\.venv\Scripts\Activate.ps1
     ```
   - **macOS / Linux:**
     ```bash
     python3 -m venv backend/.venv
     source backend/.venv/bin/activate
     ```

3. Install backend dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```

4. Run the FastAPI development server:
   ```bash
   cd backend
   uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```
   *The API will be live at `http://127.0.0.1:8000` (OpenAPI Swagger docs available at `http://127.0.0.1:8000/docs`).*

### B. Frontend Setup

1. Open a second terminal window and navigate to the `frontend/` directory:
   ```bash
   cd frontend
   npm install
   ```

2. Start the Vite development server:
   ```bash
   npm run dev
   ```
   *The web application will open at `http://localhost:5173/`.*

---

## 5. Running Automated Tests

A comprehensive suite of 39 automated tests is included, testing the categorizer, parsing edge cases, financial calculations, and FastAPI endpoints.

To run the backend test suite:
```bash
cd backend
.venv\Scripts\python -m pytest tests -v
```

*(Expected result: 39 passed tests in < 1 second).*

To test the frontend production build:
```bash
cd frontend
npm run build
```

---

## 6. How to Use the Application

1. **Load or Upload a Statement:**
   - Click **"Load Synthetic Freelancer Demo"** to immediately load the bundled demo file (`sample_data/demo_freelancer_statement.csv`).
   - Or drag-and-drop any standard statement CSV (click **"CSV Template"** to download a reference format).
2. **Review Summary Metrics:**
   - Inspect **Operating Expenses**, **Client Revenue**, **Net Cash Flow**, and **Needs Review Alerts**.
   - Check the **Category Distribution** progress bars for percentage allocations and Schedule C tax badges.
3. **Resolve "Needs Review" Items:**
   - Click the **"Needs Review"** card or filter button to view unverified rows (such as `JOES CAFE 9921` or `AMAZON.COM`).
   - Select the correct category from the inline dropdown (e.g. change Joe's Cafe to `Meals & Coffee`).
   - Notice the summary cards and breakdown automatically recalculate instantly.
4. **Inspect Decision Explanations:**
   - View the **"Engine Decision & Reason"** column to inspect why the deterministic engine chose each category or confidence level.
5. **Export Reviewed Statement:**
   - Click **"Export Reviewed CSV"** to download a complete, reconciled CSV containing your manual corrections, category decisions, and duplicate audit flags.

---

## 7. Supported CSV Statement Formats

The parser automatically detects column headers and supports:

### Format A — Signed Amount Column
```csv
Date,Description,Amount
2026-01-03,ADOBE CREATIVE CLOUD,-59.99
2026-01-04,CLIENT PAYMENT,1250.00
```

### Format B — Separate Debit and Credit Columns
```csv
Date,Description,Debit,Credit
2026-01-03,ADOBE CREATIVE CLOUD,59.99,
2026-01-04,CLIENT PAYMENT,,1250.00
```

### Additional Format Flexibility:
- **Amount Notations:** Parses standard `-$59.99`, parentheses `(59.99)`, trailing minus `59.99-`, and accounting `DR` / `CR` notations (`45.00 DR` / `500.00 CR`).
- **Date Formats:** Handles `YYYY-MM-DD`, `MM/DD/YYYY`, `DD/MM/YYYY`, `YYYY/MM/DD`, and `Month DD, YYYY`.
- **Column Aliases:** Automatically identifies headers like `Transaction Date`, `Post Date`, `Merchant`, `Details`, `Memo`, `Withdrawal`, `Deposit`.

---

## 8. GitHub Submission Workflow (From Original Repository)

To submit this assessment per the official SAVV Pro Solutions requirements:

### Step 1: Fork the Repository
1. Go to: `https://github.com/savvpro/savvpro-test-statement-categorizer`
2. Click **Fork** to create a copy under your personal GitHub account.

### Step 2: Clone Your Fork
```bash
git clone https://github.com/<your-github-username>/savvpro-test-statement-categorizer.git
cd savvpro-test-statement-categorizer
```

### Step 3: Create Your Candidate Branch
Branch pattern: `candidate-<your-github-username>`
```bash
git checkout -b candidate-<your-github-username>
```

### Step 4: Commit and Push Your Work
```bash
git add .
git commit -m "feat: complete statement-categorizer assessment"
git push origin candidate-<your-github-username>
```

### Step 5: Open the Pull Request
1. Go to your forked repository on GitHub.
2. Click **Compare & pull request** (or click **Pull requests** > **New pull request** > **compare across forks**).
3. Ensure the PR settings match:
   - **Base repository:** `savvpro/savvpro-test-statement-categorizer`
   - **Base branch:** `main`
   - **Head repository:** `<your-github-username>/savvpro-test-statement-categorizer`
   - **Compare branch:** `candidate-<your-github-username>`
   - **PR Title:** `feat: complete statement-categorizer assessment`
4. Submit the pull request before the deadline.
