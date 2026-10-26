# Statement Categorizer

A web app that reads a PKR bank statement (CSV), sorts every transaction into a category, and sets aside the rows it is not sure about as **Needs Review**. You upload the file, look at how each row was categorized and why, fix the uncertain rows by hand, and see totals per category.

**Use case.** A freelance software developer in Lahore is paid in USD through Payoneer and pays local bills (rent, utilities, internet, software subscriptions, taxes) from a PKR account at a fictional bank, "Ravi Commerce Bank Ltd". At tax time they need every row sorted, with transfers between their own accounts, refunds, failed transactions and duplicate charges handled correctly.

**No AI model decides a category.** The categorization "brain" is plain rule-based Python (ordered rules, a confidence score, and a few whole-statement passes). There is no LLM, no external AI API and no ML model anywhere in the app, the API or the tests. When the brain is not sure, the row goes to Needs Review instead of getting a guess.

How the brain decides is described in [DESIGN.md](DESIGN.md). Which AI tools were used to build the project is described in [AI_USAGE.md](AI_USAGE.md).

## Prerequisites

- [conda](https://docs.conda.io/) (Miniconda is enough) with Python 3.11
- Node.js 22 and npm 10 (developed with Node v22.22.2, npm 10.9.7)

## Setup and run

All commands start from the repo root. Open two terminals.

**1. Backend (port 8000)**

```bash
conda create -n assigment python=3.11 -y      # skip if the env already exists
conda run -n assigment python -m pip install -r backend/requirements.txt
cd backend
conda run -n assigment python -m uvicorn app.main:app --reload
```

Check it: <http://localhost:8000/docs> shows the interactive API docs.

**2. Frontend (port 3000)**

```bash
cd frontend
npm install
cp .env.example .env.local     # optional: the default API URL is already http://localhost:8000
npm run dev
```

**3. Try it**

Open <http://localhost:3000>, then drag `sample_statement_pkr.csv` (repo root) onto the upload box or click it to choose the file. You should see 75 rows, 7 in Needs Review and 1 flagged as a possible duplicate (8 rows marked for review in total). Change a Needs Review row's category in the table: it leaves the Needs Review list and the totals update.

Notes:

- The backend keeps one statement in memory. A new upload replaces the old one, and restarting the backend clears it.
- The backend only accepts requests from `http://localhost:3000` (CORS). If you run the frontend on another port, change `allow_origins` in `backend/app/main.py`.
- The `conda run ... python -m ...` form is deliberate: it guarantees the tools come from the `assigment` env even if another Python on your `PATH` also provides `pytest` or `uvicorn`.

## Tests and checks

```bash
# backend (from backend/)
conda run -n assigment python -m pytest -q          # 74 tests
conda run -n assigment python -m ruff check
conda run -n assigment python -m ruff format --check

# frontend (from frontend/)
npm test                                            # Vitest, 11 tests
npm run lint
npm run build
```

To print what the brain does with the sample file without starting the API:

```bash
cd backend && conda run -n assigment python summarize_sample.py
```

## API

Base URL `http://localhost:8000`. Money amounts are JSON strings (for example `"-1840"`) so no precision is lost.

| Endpoint | What it does | Example |
|---|---|---|
| `POST /upload` | Parse and categorize a CSV (field `file`, `.csv`, UTF-8, at most 1 MB). Replaces the current statement. Returns `{transactions, skipped_rows}`. Bad file gives `400` with a readable `detail`. | `curl -F file=@sample_statement_pkr.csv localhost:8000/upload` |
| `GET /transactions` | List rows. Optional `needs_review=true\|false` and `category=...`. | `curl 'localhost:8000/transactions?needs_review=true'` |
| `PATCH /transactions/{id}` | Set a row's category. `Needs Review` is not a valid target. Returns the full list. | `curl -X PATCH localhost:8000/transactions/10 -H 'content-type: application/json' -d '{"category":"Shopping"}'` |
| `GET /summary` | Net per category, `total_income`, `total_spending`, `needs_review_count`. | `curl localhost:8000/summary` |
| `GET /categories` | Categories a user may assign. | `curl localhost:8000/categories` |

Every transaction has `id`, `date`, `description`, `normalized`, `amount`, `balance`, `category`, `confidence`, `reason`, `needs_review`, `flags`, `usd_hint`, `user_edited` and `refund_of`.

## Project structure

```
backend/
  app/
    main.py        FastAPI routes
    schemas.py     Pydantic models, review threshold
    parser.py      CSV to transactions (signed Decimal amounts)
    normalizer.py  clean descriptions before matching
    rules.py       the rule list (data) and the category list
    engine.py      apply rules, confidence, reason
    passes.py      transfers, refunds, failed + reversal, duplicates
    summary.py     totals per category, income vs spending
    store.py       in-memory store for one statement
  tests/           pytest: parser, normalizer, rules, passes, API
  summarize_sample.py  print the sample result
  requirements.txt
frontend/          Next.js (App Router, TypeScript, plain CSS)
  app/             page and global styles
  components/      UploadZone, SummaryCards, CategoryBars, FilterBar, TransactionsTable
  lib/             api.ts (all network calls), format.ts (formatting helpers, Vitest tested)
sample_statement_pkr.csv   75-row fake statement
gen_sample_statement.py    regenerates the CSV
DESIGN.md  AI_USAGE.md     design decisions, AI tool usage
docs/token-usage/          token usage proof for AI_USAGE.md
CLAUDE.md prd.md implementation_plan.md active_context.md progress.md system_patterns.md
                           the project memory files used with Claude Code (kept to show the workflow)
```

## Sample data

`sample_statement_pkr.csv` is **entirely fake**: the bank, names, masked card and account numbers, phone numbers and amounts are made up. No real person or real statement is used anywhere in the repo. Regenerate the file from the repo root:

```bash
conda run -n assigment python gen_sample_statement.py
```

The output is deterministic, so a regenerated file is identical to the committed one. It deliberately includes the messy cases the brain must handle: a refund, own-account transfers, a failed ATM withdrawal with its reversal, a duplicate charge, ambiguous `AMZN MKTP` and `M/S ... TRADERS` rows, Raast payments to individuals, and bank taxes and fees.

## Known limits

- One CSV format (`Date DD-MM-YYYY, Description, Debit, Credit, Balance`) and one currency (PKR). USD appears only as a hint inside a description.
- Merchant coverage is a small list of common Pakistani and international names. Anything else goes to Needs Review.
- Own-account transfer detection relies on words such as `SAVINGS`, not on account numbers.
- The failed transaction and reversal window is fixed at 7 days.
- The rules do not learn from user corrections.
- State is in memory only: one statement at a time, cleared on restart. There is no database.
- The UI does not paginate, has no undo for an edit, and has no dark-mode toggle (it follows the system setting).
- The UI has no browser-level end-to-end test; only the formatting helpers have unit tests.
