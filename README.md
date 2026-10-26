# Ledgerly — Statement Categorizer

A complete local app for a freelance designer sorting a dedicated business bank or card statement before tax time. Upload a CSV, inspect the rules behind every decision, resolve uncertain rows, and export transaction and category reports.

**The brain is ordinary Python code.** There are no LLMs, external classification APIs, model downloads, embeddings, or API keys at runtime. The React interface uses the real Python API, including when you try the sample statement.

## Quick start

### Option A: Docker

With Docker Desktop / Docker Engine and Compose available:

```bash
docker compose up --build
```

Open **http://localhost:8000**. The database lives in the `ledger-data` volume and survives restarts. `docker compose down` stops the app without deleting the data. Docker configuration is included; see `docs/VERIFICATION.md` for what was actually executed in the authoring environment.

### Option B: Python + Node.js (tested path)

Use **Python 3.12+** and **Node.js 24 LTS**. All commands below start in the project root. No environment file or credentials are needed.

```bash
python -m venv .venv
```

Activate the environment:

```bash
# macOS / Linux
source .venv/bin/activate
```

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

Then install dependencies, build React, and start Python:

```bash
python -m pip install -r requirements-dev.txt
cd frontend
npm ci
npm run build
cd ..
python -m uvicorn statement_categorizer.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Open **http://localhost:8000**. FastAPI serves the production React build and API from the same origin. API documentation: **http://localhost:8000/docs**. For runtime-only installations, use `requirements.txt` instead of `requirements-dev.txt`.

### Development with hot reload

Keep the Python process running with `--reload`. In a second terminal:

```bash
cd frontend
npm run dev
```

Open **http://localhost:5173**. Vite proxies `/api` to port 8000. If you change frontend code while using the Python-served production build, rebuild and restart Python. Start Python after the first frontend build so its static directory exists at startup.

## Try the workflow in three minutes

1. Click **Try a sample statement**. Every row is fictional; the file contains no account number, bank name, or real customer details.
2. The sample has **20 transactions**, **11 auto-sorted rows**, and **9 rows needing review**. Accepted expenses are **$202.48**, refunds **$20.00**, and net expenses **$182.48**. No income is assumed for the unverified client credit.
3. Open `JOES CAFE 9921`. Read the explanation, choose `Meals`, keep `Expense`, and record a fictional business-purpose note. Net expenses become **$200.88**. Categorization does not assert tax deductibility.
4. Open **Review history** to inspect the change. Refresh the browser: both the decision and audit history remain saved.
5. For possible duplicates, inspect the original statement. Exclude a confirmed duplicate **with a note**, or confirm it as a separate genuine charge. Pending rows must be excluded until a posted version can be imported.
6. Export a **draft** at any point. Once every review row is resolved, the button becomes **Export final**. Final export is also enforced by the server. Download **Summary CSV** for category totals.

Accepted means either auto-sorted or confirmed by the user; it is not an accountant's certification. You can edit auto-sorted rows too. Manual changes apply to the current row only.

## Input contract

**CSV only**, UTF-8 (BOM accepted), comma / semicolon / tab delimiter, maximum **5 MiB** and **5,000 rows**. Header must be the first line; remove bank cover text and opening/closing-balance rows first. Blank lines are skipped. PDFs, images, OCR, Excel workbooks, and arbitrary bank layouts are deliberately unsupported.

| Sample | Amount format | Date format | Currency |
| --- | --- | --- | --- |
| `samples/designer-bank.csv` | Bank: negative = money out | YYYY-MM-DD | USD |
| `samples/designer-card.csv` | Card: positive = charges | MM/DD/YYYY | USD |
| `samples/designer-debit-credit.csv` | Separate debit / credit | DD/MM/YYYY | USD |
| `samples/invalid-rows.csv` | Bank: negative = money out | YYYY-MM-DD | USD |

Choose these settings explicitly. A bank/card sign convention is not guessed. Separate debit and credit columns must contain nonnegative values; only one can be nonzero per row.

```csv
Date,Description,Amount,Currency,Status
2026-04-02,ADOBE CREATIVE CLOUD,-59.99,USD,posted
2026-04-07,ADOBE CREATIVE CLOUD REFUND,20.00,USD,posted
```

Required fields: date, description, and amount (or debit + credit). Header aliases are defined in `backend/statement_categorizer/parser.py`, including `Transaction Date`, `Merchant`, `Withdrawals`, and `Deposits`. Optional fields are `Currency` and `Status`; absent status means posted. Unknown extra columns are ignored, so a `Balance` column is **not** treated as a transaction or used for reconciliation. Mixed amount schemas and ambiguous aliases are rejected.

- Dates must match the chosen format exactly, with a four-digit year. There is no locale guessing.
- Amounts use dot decimals with up to two places. `"1,234.56"`, `-12.34`, `(12.34)` and matching currency symbols are supported; quote amounts containing CSV delimiters. Scientific notation, malformed grouping and extra precision are rejected rather than rounded.
- Supported currencies: USD, EUR, GBP, PKR, CAD, AUD. One currency per import, with **no FX conversion** or currency aggregation.
- `pending` rows always require review and cannot count toward totals. `posted`, `settled`, and `completed` are accepted posting statuses.
- Every invalid row has a source line number. **One invalid row rejects the entire import.** Correct it and upload again; no partial ledger is stored.
- Re-uploading identical bytes with identical settings returns the existing import. Different settings for the same file yield a conflict; delete the old import before correcting its import settings. Imports with different bytes can still produce a possible-duplicate flag.

## What is included

- Python / FastAPI backend, typed domain objects, pure parser and categorization engine.
- React / TypeScript frontend with upload/drop zone, summary bars, searchable/sortable/paginated transactions, review dialog, and review history.
- SQLite persistence with parameterized queries, foreign keys, atomic imports, and version checks for concurrent edits.
- Rule explanations and original decisions preserved even after human overrides.
- Refund handling, transfer exclusion, duplicate warnings, pending/zero/conflicting-sign checks, and conservative unknown-credit handling.
- CSV export that neutralizes formula-like text, plus final-export validation.
- Exact cent arithmetic and reconciliation: raw statement net = accepted net + unresolved net + excluded net.
- Fully pinned dependency files, container setup, CI, unit/integration/browser tests, and documented limitations.

## Export semantics

The transaction CSV includes **every row**, including unresolved and excluded rows, with normalized signed amount, status, category, movement, original rule information, note, and version. Do not add every row's amount together and call that business spending.

The summary CSV lists all expense categories plus Income, Transfers, and Personal. `money_out` and `money_in` are positive totals. For expense categories, incoming amounts are refunds and `net_expenses = money_out − money_in`. Non-expense categories have zero `net_expenses`. The unresolved count is repeated on each category row as a report-level warning; do not sum that column. Excluded/unresolved money never enters the accepted category totals. All reports cover the **selected import**, not all saved statements or a combined tax year.

Draft exports may be incomplete. Final exports require zero unresolved rows but may still include explicitly excluded rows. If refunds exceed spending in a category, negative net expenses are shown correctly. No deduction rates, tax forms, or tax liability are calculated.

## Tests and formatting

Activate the Python virtual environment first:

```bash
python -m pytest --cov=statement_categorizer --cov-report=term-missing
ruff check backend
ruff format --check backend
cd frontend
npm test
npm run format:check
npm run build
npx playwright install chromium
npm run test:e2e
```

Browser tests run against an actual Python server and a fresh temporary SQLite database, on ports **8001** and **5173**. Stop an existing frontend dev server before running them. Set `E2E_PYTHON` if your Python interpreter is outside the root `.venv`; for an already available Chromium executable, set `PLAYWRIGHT_CHROMIUM_EXECUTABLE`. Those overrides are test infrastructure only, not application dependencies.

Tests cover rule collisions, unknown merchants, incoming credits, refunds, exact cents, BOM/multiline CSV, malformed dates, invalid schemas, pending charges, duplicate imports across threads/files, persistence, stale edits, audit history, formula-safe export, and the browser workflow. The measured results are in `docs/VERIFICATION.md`.

## Project structure

```text
backend/statement_categorizer/
  domain.py       Shared categories, movement types, and immutable input objects
  parser.py       Strict CSV decoding and amount/date normalization
  engine.py       The deterministic brain, with rule IDs and explanations
  store.py        SQLite transactions, import deduplication, reviews, audit history
  reporting.py    Exact totals, reconciliation, and safe CSV serialization
  main.py         HTTP validation, request boundaries, routes, and static hosting
backend/tests/    Parser, engine, API, concurrency, and reporting tests
frontend/src/
  components/     Upload, summary, transaction table, and review dialog
  App.tsx         Workspace orchestration and race-safe selection
  api.ts          Typed HTTP client and display formatting
  types.ts        UI contracts
  styles.css      Responsive design tokens, layouts, and states
frontend/e2e/    Real browser-to-Python workflow tests
samples/        Fictional CSV fixtures only
docs/           Verification evidence, AI-usage record, and security scope
```

## Persistence and operational scope

Native runs store data at `data/ledger.sqlite3`; set `LEDGER_DB_PATH` to another local path if needed. This is a local single-user application, **not a hosted multi-tenant service**. No authentication, encrypted database, account segregation, automatic backups, or rate limiting is claimed. Browser writes are origin-checked and hosts are allowlisted; these are not substitutes for authentication. Default launch instructions and Compose bind to loopback.

Raw upload bytes are discarded after parsing; the filename, SHA-256 hash, transaction data, original rule decisions, and review history are retained. No transaction contents are logged by the app. The **Delete import** action also deletes that import's audit records. Do not use the demo for actual sensitive statements without deciding how to protect the local database. See `docs/SECURITY.md` before shared deployment.

## Submission status

`DESIGN.md` explains the use case and brain. `AI_USAGE.md` honestly records AI assistance and the token-telemetry limitation. `PULL_REQUEST.md` contains a ready-to-use PR description. The user selected file delivery and declined GitHub access, so **no remote repository was changed and no pull request was opened**.

Once these files are in your own repository and a branch is pushed, open a PR using `PULL_REQUEST.md` as the body. With GitHub CLI authenticated, the final command is:

```bash
gh pr create --title "Build Ledgerly statement categorizer with deterministic rules" --body-file PULL_REQUEST.md
```

## Primary references consulted

- [FastAPI file uploads](https://fastapi.tiangolo.com/tutorial/request-files/) and [testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [React with TypeScript](https://react.dev/learn/typescript)
- [Vite getting started](https://vite.dev/guide/)
- [Python sqlite3 documentation](https://docs.python.org/3/library/sqlite3.html)

These references informed framework usage, not the transaction decisions. All categorization rules are in this repository.
