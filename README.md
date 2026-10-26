# Ledgerly: statement categorizer

A small local app for freelance software developers and independent IT consultants in Pakistan organizing their records for tax time. Upload a PKR statement, review handwritten rule decisions, correct categories, and export the result. Included examples are fictional. Categories help organize records; they do not establish tax deductibility or taxable income.

## What it does

- Validates a whole CSV before saving any transactions.
- Categorizes known developer subscriptions, hosting, explicit internet bills, travel and bank fees with explanations.
- Keeps incoming client payments, refunds, transfers and unknown payments separate.
- Flags duplicate-looking entries without deleting them, with confirmation separate from category editing.
- Saves statements and category corrections in SQLite.
- Provides search, category and review filters, expense totals by category, and safe CSV export.

## Requirements

- Python 3.11 or newer.
- Node.js 22.12 or newer and npm. Node 24 is also supported.
- Two terminals, one for the API and one for the frontend.

## Setup and run

Run these commands from the repository root. On Windows, use `py -3.11` instead of `python` if needed. If PowerShell blocks `npm.ps1`, use `npm.cmd` for npm commands.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

In another terminal:

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev
```

Open http://127.0.0.1:5173. The frontend forwards `/api` requests to port 8000. Keep both servers running. API documentation is at http://127.0.0.1:8000/docs.

On macOS or Linux, use `python3 -m venv .venv` and `.venv/bin/python` in place of the Windows Python paths. No virtual environment activation is required.

The database is created at `backend/data/statements_pkr.sqlite3`. The earlier EUR database at `backend/data/statements.sqlite3` is left untouched. Set `DATABASE_PATH` before starting the backend to choose another **PKR-only** database; do not point it at an existing EUR database. There is no currency migration or conversion. Restarting the app preserves imports, corrections and duplicate confirmations. The newest import opens on page load; use the statement selector to revisit earlier imports. Reimporting a file creates a separate statement.

## CSV format

Use UTF-8, optionally with a BOM, with comma-separated columns and a header. Amounts are assumed to be **PKR when the Currency column is absent**. If Currency is supplied, every value must explicitly be PKR, ignoring case and surrounding spaces. Blank, foreign or ambiguous currency indicators are rejected. The app does not convert currencies. Values are displayed as `PKR 125,000.00`, but CSV amounts must omit grouping separators and currency labels.

Signed amounts use **negative for money leaving the account and positive for money entering it**:

```csv
Date,Description,Amount
2026-09-01,CLIENT PAYMENT NORTHSTAR TECH INV 1042,250000.00
2026-09-02,GITHUB COPILOT,-5600.00
```

Alternatively, supply nonnegative Debit and Credit columns. Debit is money out, Credit is money in. One side may be empty or zero, but both cannot be positive. Both sides cannot be empty. An explicit zero is retained for review.

```csv
Date,Description,Debit,Credit
01/09/2026,CLIENT PAYMENT PAPER KITE LABS,,175000.00
02/09/2026,VERCEL,5600.00,
```

Supported header aliases, ignoring case, surrounding spaces and underscores:

| Field                     | Accepted headers                                         |
| ------------------------- | -------------------------------------------------------- |
| Date                      | Date, Transaction Date, Booking Date                     |
| Description               | Description, Details, Narrative, Transaction Description |
| Amount                    | Amount, Transaction Amount                               |
| Debit                     | Debit, Debit Amount, Money Out                           |
| Credit                    | Credit, Credit Amount, Money In                          |
| Optional transaction type | Type, Transaction Type                                   |
| Optional currency         | Currency, Currency Code                                  |

Additional columns are allowed but are not stored. Duplicate or conflicting supported columns are rejected. Amount and Debit/Credit formats cannot be mixed. Do not upload unsigned card-charge amounts in the Amount column; use Debit/Credit if the bank represents spending as positive charges.

Dates must be exactly `YYYY-MM-DD`, `DD/MM/YYYY`, or `DD.MM.YYYY`. US month-first dates are unsupported. Amounts accept an optional sign, a decimal point and up to two decimal places, with at most ten integer digits. Currency symbols, thousands separators, parentheses and scientific notation are rejected. Descriptions must contain 1 to 500 characters; optional transaction types allow up to 80. Control characters in these fields are rejected.

Limits: **1 MiB per CSV and 5,000 transactions per statement**. Empty files, blank transaction rows, malformed quoting, invalid dates, invalid values and inconsistent row lengths reject the whole import. Errors identify affected rows, up to the first 20 errors. Nothing is partially imported.

Two fictional samples are in [samples/](samples/). Download them from the format guide in the app or select **Try fictional sample data** to import the signed example.

The signed sample includes client income, subscriptions, cloud hosting, a Nayatel internet bill, bank charges, internal savings movements, an Adobe refund, supplier/contractor transfers, a generic Raast receipt, a Daraz purchase, cash withdrawal, repeated hosting charges and a zero-value entry. The debit/credit sample also includes a PTCL internet bill. These are examples of payment purposes, not tax deductions.

## Review and financial totals

Category edits save immediately and take precedence over automatic decisions. The original automatic category and explanation remain available. Incoming amounts cannot be assigned expense categories; outgoing amounts cannot be assigned Client Income or Refund. Zero amounts remain Needs Review.

Matching date, case-insensitive description and amount within one statement flags every matching entry as a possible duplicate. All entries stay in the statement and totals. **Confirm entry** records that a repeated entry is legitimate without changing its category or correction status. Editing a category does not confirm the duplicate. An entry needs review while its category is unknown or its duplicate flag is unconfirmed. Both decisions persist, and the duplicate warning remains visible. There is no automatic removal or cross-statement deduplication.

Only explicit movement between own accounts is automatically classified Transfer, such as `TRANSFER TO OWN SAVINGS ACCOUNT` or `TRANSFER BETWEEN OWN ACCOUNTS`. A generic Transfer type, supplier payment, IBFT or Raast payment does not establish internal movement. A generic incoming Raast receipt is not assumed to be client income. An explicit Client Payment indicator is required.

If refund wording conflicts with an explicit client-payment or internal-transfer indicator, the entry needs review rather than being assigned either financial category.

Expenses include categorized outgoing payments. Identified income includes explicit client payments. Refunds are shown separately without reducing gross expenses. Transfers show the sum of money transferred in and out, with each direction underneath. Unknown amounts are shown separately and excluded from classified totals. Net movement includes every transaction. Category totals describe spending, not deductibility.

Export always includes the entire selected statement, including unresolved rows, regardless of table filters. It includes PKR currency, the current and original categories, explanations, correction status, duplicate flags and duplicate confirmation. Text that could start a spreadsheet formula is prefixed with an apostrophe. Numeric amounts keep their signed decimal values. Reimporting an export runs the automatic rules again; it does not restore manual corrections or duplicate confirmations from exported columns.

## Tests and production build

From the repository root:

```terminal
python -m pytest -c backend/pytest.ini -q
```

From `frontend/`:

```terminal
npm test
npm run typecheck
npm run build
```

Backend tests cover parsing, boundaries, conservative matching, direction, precedence, correction persistence, summaries, atomic failures and spreadsheet export safety. Frontend tests cover upload, errors, searching, filters, corrections, restored state and download using a mocked API. Vitest uses a single thread worker so the same command works in the Windows assessment environment.

The installed Starlette test client emits one upstream deprecation warning for httpx; it does not fail the tests. Verification results are recorded in [AI_USAGE.md](AI_USAGE.md).

To inspect the built frontend, run `npm run preview` from `frontend/` while the backend is running. This local preview also forwards `/api` to port 8000.

React StrictMode can make two initial API requests per endpoint in development. This stops after initialization; the production build makes one. To stop Uvicorn, press Ctrl+C once and let shutdown finish. A second interrupt can force cancellation and print a shutdown traceback on Windows.

## Limitations

- Local single-user app, without authentication, statement deletion, tax calculations or bank integrations. Bind the API to localhost.
- Only the documented CSV formats and PKR are supported. No PDF, OCR or Excel import.
- Deliberately small merchant list. Generic shops, cafes, invoice references alone and unexplained incoming payments need human review.
- Equipment, meals and professional services are available for manual classification; automatic rules do not assume their purpose.
- No saved merchant rules. Each correction applies to its transaction only.
- All rows for one statement are loaded together, with 25 displayed per table page.
- API clients must send CSV bytes as the request body, not multipart form data. For example: `POST /api/statements?filename=statement.csv` with `Content-Type: text/csv`.

See [DESIGN.md](DESIGN.md) for decisions and [AI_USAGE.md](AI_USAGE.md) for assistance disclosure. The original assessment is in [TASK.md](TASK.md).
