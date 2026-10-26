# TaxSort – Statement Categorizer for US Freelancers

TaxSort is an automated, deterministic statement categorizer tailored for US freelancers, sole proprietors, and 1099 contractors filing **IRS Form 1040 Schedule C**.

It ingests bank and credit card statements (CSV or PDF), runs them through a deterministic categorization engine, applies statutory IRS tax deduction rules (such as the 50% business meal limitation under IRC § 274(n)), filters non-spending transfers and refunds, and provides an accountant-ready dashboard with live Schedule C audit summaries and Excel/CSV export capabilities.

> **Deterministic Guarantee:** TaxSort does NOT use any cloud LLM or AI model in the classification path. Categorization is 100% deterministic, private, local, and auditable.

---

## Key Features

- **IRS Schedule C Compliance:** Automatically aggregates deductions into official tax lines: Line 1 (Gross Receipts), Line 8 (Advertising), Line 9 (Vehicle), Line 11 (Contract Labor), Line 15 (Insurance), Line 17 (Legal/Professional), Line 18 (Office/Software), Line 24a (Travel), and Line 24b (Meals).
- **Statutory 50% Meals Limit:** Applies IRC § 274(n) to automatically cut dining expenses by 50% for accurate deductible totals.
- **Refund Netting:** Detects refund tokens and nets them against original expense categories instead of artificially inflating taxable gross income.
- **Transfer Exclusion:** Identifies credit card payments, owner draws, and inter-account transfers to exclude them from business expenses.
- **Smart "Needs Review" Safe Queue:** Flags ambiguous or mixed-use merchants (e.g. Amazon, local diners) for user confirmation with explanatory notes.
- **Persistent User Rules:** One-click rule creation allows users to remember custom merchant mappings deterministically for future uploads.
- **Accountant-Ready Exports:** One-click downloads of compliant CSV and formatted Excel worksheets (`.xlsx`).
- **Clean SaaS Dashboard:** Mercury/Ramp-inspired UI built with Next.js 16, TypeScript, and accessible vector SVGs.

---

## Documentation Links

- **[DESIGN.md](./DESIGN.md):** Detailed use case, IRS tax mapping specifications, and deterministic categorization pipeline architecture.
- **[AI_USAGE.md](./AI_USAGE.md):** Disclosure of AI pairing tools (Google Antigravity IDE, Claude Opus 4.6, Gemini 3.8 Flash), corrections made, and token usage metrics.

---

## Project Structure

```
savvpro-test-statement-categorizer/
├── backend/
│   ├── app/
│   │   ├── api/             # FastAPI REST routes (statements, transactions, auth, export)
│   │   ├── brain/           # 100% deterministic categorization engine & merchant dictionary
│   │   ├── parsers/         # CSV and PDF statement parsers
│   │   ├── models.py        # SQLModel ORM models
│   │   ├── schemas.py       # Pydantic request/response schemas
│   │   └── main.py          # FastAPI application entrypoint
│   ├── tests/               # 79 pytest unit and integration tests
│   └── pyproject.toml       # Python dependencies and build config
├── frontend/
│   ├── app/
│   │   ├── components/      # UI components (MetricCards, Table, Modals, SVGs)
│   │   ├── context/         # AuthContext with PBKDF2 authentication
│   │   ├── transactions/    # Full transactions table & review workflow
│   │   ├── categories/      # Schedule C tax line breakdown
│   │   ├── export/          # CSV & Excel report generators
│   │   ├── upload/          # Statement upload page
│   │   ├── login/           # Authentication login
│   │   └── page.tsx         # Executive financial overview dashboard
│   ├── package.json         # Next.js 16 dependencies
│   └── next.config.ts       # Next.js configuration
├── sample_data/             # Bundled testing statements (Amex & Checking CSVs)
├── DESIGN.md                # System design & architecture document
├── AI_USAGE.md              # AI pairing & token report
└── README.md                # Setup and execution guide
```

---

## Getting Started

### Prerequisites
- **Python 3.10+** (tested on 3.10 – 3.14)
- **Node.js 18+** & **npm**

---

### 1. Backend Setup (FastAPI)

1. Open a terminal in the `backend/` directory:
   ```bash
   cd backend
   ```

2. Create and activate a virtual environment:
   ```bash
   # Windows (PowerShell)
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1

   # macOS / Linux
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -e .
   ```

4. Run the automated test suite (79 tests):
   ```bash
   python -m pytest
   ```

5. Start the backend development server:
   ```bash
   python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```
   The backend API will be live at `http://127.0.0.1:8000` with interactive Swagger docs at `http://127.0.0.1:8000/docs`.

---

### 2. Frontend Setup (Next.js)

1. Open a separate terminal in the `frontend/` directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Build the production bundle (optional check):
   ```bash
   npm run build
   ```

4. Start the frontend development server:
   ```bash
   npm run dev
   ```

5. Open your browser and navigate to **`http://localhost:3000`**.

---

## How to Test the Application

1. **Sign In:** Use the pre-filled demo login button or create a local account.
2. **Review Metrics:** View the top KPI metric cards and expenses breakdown for the current statement.
3. **Resolve Review Items:**
   - Click **Review Now** on the "Needs Review" metric card or **Resolve** in the Tax Readiness section.
   - The app filters directly to unconfirmed statement items (such as Amazon or Joe's Cafe).
   - Click **Assign**, select an IRS Schedule C category (e.g. `Office Supplies (Line 18)`), keep "Always categorize this way" checked, and save.
   - Notice the status immediately updates to `User Confirmed` and the database updates.
4. **Upload Statements:**
   - Navigate to `/upload` or click **Upload Statement** in the top bar.
   - Click one of the bundled one-click sample buttons (`freelancer_amex.csv` or `freelancer_checking.csv`) or drag and drop your own CSV/PDF bank statement.
5. **Audit Categories:** Navigate to `/categories` to see IRS Schedule C lines, deductibility percentages, and compliant tax calculations.
6. **Export Reports:** Navigate to `/export` to download accountant-ready `.csv` and `.xlsx` files.

---

## Submitting Your Work

To submit for assessment:
1. Ensure all changes are committed on your branch (`candidate-<your-github-username>`):
   ```bash
   git status
   git add .
   git commit -m "feat: complete statement-categorizer assessment"
   git push origin candidate-<your-github-username>
   ```
2. Open a Pull Request from your fork to `savvpro/savvpro-test-statement-categorizer:main` with title:
   `feat: complete statement-categorizer assessment`
