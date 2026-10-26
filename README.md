# Statement Categorizer

Upload a freelancer's bank or credit card statement and get every transaction sorted into US
Schedule C tax categories. Rows the app is not sure about go to **Needs Review**, with the
reason why.

The categorization "brain" is plain, deterministic Python: rules, a merchant dictionary,
patterns and fuzzy matching with explicit confidence thresholds. No AI model decides any
category. See [DESIGN.md](DESIGN.md) for how it decides and [AI_USAGE.md](AI_USAGE.md) for how
AI tools were used to build it.

> Estimates only, not tax advice.

## Features

- **Upload CSV or XLSX** bank and card exports (drag and drop, max 5 MB). The app finds the
  header row and column names, then handles date formats, debit/credit columns, `CR`/`DR`
  markers, `(45.00)` and `45.00-` amounts, and card sign conventions. It also skips balance
  and total rows.
- **Explainable categories:** every row shows a confidence pill, a status and the reasons
  behind the decision.
- **Needs Review queue** for ambiguous merchants (Amazon, Venmo, Zelle, ATM, checks, ...),
  conflicts, unknown merchants and possible duplicates.
- **Fix and remember:** correct a row and tick "remember for this merchant". The app learns a
  rule, re-applies it to the other unconfirmed rows from that merchant, and uses it for future
  uploads.
- **Tax summary:** income, business expenses, estimated deductible (meals at 50%), a total per
  category with its Schedule C line, and non-operating money (transfers, card payments,
  personal) listed separately. Refunds are netted against the original purchase, never
  counted as income.
- **Edge cases:** refunds linked to their purchase, chargebacks, card payments seen from both
  accounts, own-account transfers, client payouts vs platform fees, estimated tax, interest
  earned vs charged, FX fees, duplicates and pending rows.
- **Import notes:** the detected format, the sign convention with the reason it was chosen,
  warnings, and the rows that could not be read (with line numbers).
- **CSV export** for an accountant.
- **Production basics:** typed API with consistent JSON errors, upload limits, a 409 on
  re-uploading the same file, structured JSON logs without transaction descriptions, CI,
  Docker and a Makefile.

## Tech stack

| Layer | Choice |
|---|---|
| Backend | Python, FastAPI, Pydantic v2, SQLAlchemy 2.0, SQLite |
| Parsing | stdlib `csv`, openpyxl, python-dateutil |
| Brain | rapidfuzz, PyYAML, regex: deterministic rules, no AI model |
| Frontend | Vite, React 19, TypeScript, plain CSS (light/dark) |
| Tests | pytest, Vitest, Testing Library |
| Tooling | ruff, oxlint, GitHub Actions, Docker Compose, Make |

## Prerequisites

- **Python 3.12+** (CI runs 3.12 and 3.14)
- **Node.js 20.19+ or 22.12+** (Vite 8 requires it; CI uses Node 22)
- `make` (optional; the manual steps below need only Python and npm)

## Quick start

### With make

```bash
make setup      # backend/.venv + pip install -e ".[dev]", then npm ci
make backend    # terminal 1: API on http://localhost:8000
make frontend   # terminal 2: UI on http://localhost:5173
```

Then open **http://localhost:5173**. Run `make help` to list every target (`test`, `lint`,
`eval`, `clean`).

### Manual steps

Backend (terminal 1):

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/uvicorn app.main:app --reload --port 8000
```

Frontend (terminal 2):

```bash
cd frontend
npm ci
npm run dev
```

Then open **http://localhost:5173**. The Vite dev server proxies `/api` to `localhost:8000`.
Check that the backend is up with `curl http://localhost:8000/api/health`, which should return
`{"status":"ok"}`. The SQLite database is created at `backend/data/app.db` on first start.

### Docker

```bash
docker compose up --build
```

This opens the UI at **http://localhost:8080**. nginx serves the built frontend and proxies
`/api` to the backend container. Data is kept in the `app-data` volume.

**Status: the Docker files are provided but were not verified on this machine.** Docker was
not installed where this project was built, so the images have not been built or run. The
Makefile and manual routes above were run end to end.

## Using the app

1. **Try a sample.** Click one of the "Try a sample" buttons, for example
   *Credit card (CSV)*. The file is fetched from the API and uploaded like a real one.
2. **Read the summary.** Cards show income, business expenses, the estimated deductible and
   how much is still waiting for review. The table below them lists each category with its
   Schedule C line.
3. **Review.** The table opens on **Needs Review** when there is anything to review. Click
   **Why?** on a row to see the reasons, for example `ambiguous: Amazon sells everything;
   check the order`, `conflict: X vs Y` or `no match: no rule or known merchant fits`.
4. **Fix.** Pick a category; the suggestion is pre-selected when there is one. Click
   **Save**.
5. **Remember.** Tick **Remember for this merchant** before saving. The other unconfirmed
   rows from that merchant are re-categorized ("Updated N other transactions"), and future
   uploads use the rule.
6. **Export.** **Export CSV** downloads date, description, amount, category, Schedule C line,
   status, confidence and reasons.

Uploading the exact same file twice is refused with a link to the existing statement. Delete
a statement from the sidebar to upload it again.

## Tests and evaluation

```bash
make test   # backend: 343 pytest tests, frontend: 18 Vitest tests
make lint   # ruff check, ruff format --check, oxlint
make eval   # score the brain against the hand-labelled golden set
```

The same checks without make:

```bash
cd backend && .venv/bin/pytest -q && .venv/bin/ruff check . && .venv/bin/ruff format --check .
cd backend && .venv/bin/python scripts/evaluate.py
cd frontend && npm test && npm run lint && npm run build
```

Current evaluation output (all 134 sample rows are labelled in `samples/labels/`):

```
file                   rows auto   ok review precision
bank_messy.csv           14   13   13      1    100.0%
checking_simple.csv      45   35   35     10    100.0%
credit_card.csv          50   36   36     14    100.0%
credit_card.xlsx         25   20   20      5    100.0%

auto-precision 100.0% | review rate 22.4% | coverage 100.0% | direction errors 0
```

The rules were written with these samples in view, so treat 100% as an upper bound.
[DESIGN.md](DESIGN.md#8-evaluation) explains the guards against overfitting.

CI (`.github/workflows/ci.yml`) runs all of this on every push and pull request.

## Sample files

All sample data is invented: the business, the people, the bank and every account number.
Details are in [samples/README.md](samples/README.md).

| File | Account | Rows | What it exercises |
|---|---|---|---|
| `checking_simple.csv` | checking | 45 | clean export; client deposits, payouts, transfers, card autopay, estimated tax, ATM, checks, Zelle/Venmo |
| `credit_card.csv` | credit card | 50 | charges as positive numbers; subscriptions, Uber trip vs Eats, Amazon, refund, dispute, duplicate, card payments |
| `bank_messy.csv` | checking | 14 + 1 bad row | BOM, `;` delimiter, junk lines above the header, debit/credit columns, `45.00-`, an invalid date, pending, balance/total rows |
| `credit_card.xlsx` | credit card | 25 | Excel date and number cells, transaction and post dates, charges as negative numbers |

Regenerate them with `cd backend && .venv/bin/python scripts/make_samples.py`. A test checks
that the committed files match the generator byte for byte.

## API

All endpoints are under `/api`. Errors are always JSON: `{"detail": "...", "code": "..."}`.
Interactive docs are at http://localhost:8000/docs.

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | liveness check |
| GET | `/categories` | the category taxonomy |
| POST | `/statements` | upload (multipart: `file`, `account_type`=`checking`\|`credit_card`, optional `charges_positive`). Returns 201 with the statement and its rows. Errors: 400 (bad file), 409 (same file already uploaded; includes `statement_id`), 413 (over 5 MB), 422 (missing field) |
| GET | `/statements` | list uploaded statements |
| GET | `/statements/{id}` | one statement with the detected format, warnings, row errors and review count |
| DELETE | `/statements/{id}` | delete a statement and its transactions |
| GET | `/statements/{id}/transactions?status=` | rows, optionally filtered by `auto`, `needs_review` or `user_confirmed` |
| PATCH | `/transactions/{id}` | `{"category_id": "meals", "remember": true}`. Confirms the row; with `remember`, saves a merchant rule and re-applies it. Returns `{transaction, updated_count}`. Unknown category: 422 |
| GET | `/statements/{id}/summary` | totals per category, income, expenses, estimated deductible, review and pending counts |
| GET | `/statements/{id}/export.csv` | categorized CSV download |
| GET | `/rules` | learned merchant rules |
| DELETE | `/rules/{id}` | forget a rule (rows it already changed keep their category) |
| GET | `/samples/{name}` | serves one of the four sample files (allowlist) |

Amounts are decimal strings (`"-59.99"`), never floats.

## Project structure

```
.
├── backend/
│   ├── app/
│   │   ├── main.py            # app factory, CORS, routers, error handlers
│   │   ├── config.py          # settings from env / .env
│   │   ├── api/               # routers: statements, transactions, rules, samples, categories, health
│   │   ├── services/          # ingest, review (learned rules), summary, export
│   │   ├── parsing/           # pure: bytes -> rows (readers, columns, amounts, dates, signs)
│   │   ├── brain/             # pure: rows -> decisions
│   │   │   ├── normalizer.py  # description -> merchant_key
│   │   │   ├── signals/       # user rules, structural, merchants, patterns, fuzzy, keywords, recurring
│   │   │   ├── engine.py      # aggregate, direction check, thresholds, ambiguity
│   │   │   ├── refunds.py, duplicates.py
│   │   │   └── data/          # categories, merchants, patterns, keywords, ambiguous (YAML)
│   │   ├── db/                # SQLAlchemy models, session, integer-cents money helpers
│   │   └── schemas/           # Pydantic request/response models
│   ├── scripts/               # evaluate.py (golden set), make_samples.py
│   ├── tests/                 # parsing, brain, api, evaluation
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── api/               # typed client + types
│   │   ├── components/        # UploadPanel, SummaryCards, TransactionTable, ...
│   │   └── App.tsx
│   ├── Dockerfile, nginx.conf
├── samples/                   # fake statements + labels/ (golden set)
├── docs/ai-usage/             # session log and token usage reports
├── .github/workflows/ci.yml
├── docker-compose.yml, Makefile
└── README.md, DESIGN.md, AI_USAGE.md, TASK.md
```

## Configuration

The backend reads environment variables, or `backend/.env`. Copy
[`backend/.env.example`](backend/.env.example) to get started. None of these are secrets.

| Variable | Default | Meaning |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./data/app.db` | SQLAlchemy URL (relative to `backend/`) |
| `MAX_UPLOAD_MB` | `5` | upload size limit |
| `CORS_ORIGINS` | `http://localhost:5173` | comma-separated allowed origins |
| `LOG_LEVEL` | `INFO` | log level for the JSON logs |
| `SAMPLES_DIR` | repo `samples/` | folder served by `/api/samples/{name}` |

## Troubleshooting

- **`ModuleNotFoundError: No module named 'app'` on macOS with Python 3.14** (outside pytest).
  Python 3.14 skips `.pth` files that carry the macOS `hidden` flag, which silently disables
  the editable install. Clear the flag (`make setup` does this for you):
  ```bash
  chflags nohidden backend/.venv/lib/python3*/site-packages/*.pth
  ```
- **Database errors after pulling new code** (for example `no such column`). There are no
  migrations; the schema is created on startup. Delete the local database and restart:
  `rm backend/data/app.db`.
- **Port already in use.** Find the process with `lsof -i :8000` (or `:5173`) and stop it, or
  pick other ports: `uvicorn app.main:app --port 8001`. The Vite proxy target is in
  `frontend/vite.config.ts`.
- **`npm ci` or Vite complains about the Node version.** Vite 8 needs Node 20.19+ or 22.12+.
  Check with `node -v`.

## Known limitations

- CSV and XLSX only: no PDF, OFX/QFX or legacy `.xls`.
- Single currency (USD formatting). Foreign merchants are categorized, but amounts are taken
  as already converted.
- US Schedule C defaults for a solo freelancer. The line mapping is the common default and
  an accountant may reclassify.
- No authentication or multi-user support. The learned rules are global.
- **Not tax advice.** Totals are estimates to prepare for an accountant, not a filing.
