# Statement Categorizer

Upload a bank or credit-card statement and get every transaction sorted for tax time, with a plain-language reason for each decision. Anything the app is not sure about goes to **Needs Review** instead of being guessed.

**Use case:** a rideshare or delivery driver (Uber, Careem, Foodpanda) sorting a bank statement into income, deductible business expenses, personal spending and money that is not spending at all. Read [DESIGN.md](DESIGN.md) for the reasoning and [AI_USAGE.md](AI_USAGE.md) for how AI tools were used.

```
Upload CSV → parser (clean rows) → the brain (category + confidence + reason) → review table → totals → export
```

The brain is plain Python and a JSON rules file. **No AI model decides any category.**

## What it does

- Reads messy CSVs: different column names, a few lines above the header, `;` or tab delimiters, `1,234.50` / `(500.00)` / `Rs 1,200` amounts, Excel's BOM, day-first dates. Bad rows are skipped and reported by row number; the rest still load.
- Categorizes each row with a **category, a confidence and a reason**.
- Treats the traps correctly: a refund is not income, transfers and card payments are not spending, cash withdrawals and unknown merchants are asked about.
- Lets you fix any row. One fix also settles look-alike rows (fix `ALI TRADERS 5521` and `ALI TRADERS 7733` follows).
- Shows tax-time totals that net refunds against the expense they reverse, and tell you when unresolved rows could still change them.
- Exports the result as a CSV for your accountant.

## Run it

You need **Python 3.11+** and **Node 22+** (built and tested on Python 3.13 and Node 24).

### 1. Backend (FastAPI), port 8000

```bash
cd backend
python -m venv venv
```

Activate the environment: `venv\Scripts\activate` on Windows, `source venv/bin/activate` on macOS/Linux. Then:

```bash
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

Interactive API docs: <http://localhost:8000/docs>

### 2. Frontend (Next.js), port 3000

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:3000> and click **Try the sample statement**, or upload your own CSV. The sample is also at [`backend/sample_data/driver_statement.csv`](backend/sample_data/driver_statement.csv).

### Configuration

Everything has a working default. Copy `backend/.env.example` to `backend/.env` or `frontend/.env.example` to `frontend/.env.local` to change anything.

| Variable | Where | Default | Purpose |
| --- | --- | --- | --- |
| `NEXT_PUBLIC_API_URL` | frontend | `http://localhost:8000` | Where the backend is |
| `SC_CORS_ORIGINS` | backend | `["http://localhost:3000","http://127.0.0.1:3000"]` | Origins allowed to call the API (JSON list) |
| `SC_MAX_UPLOAD_BYTES` | backend | `5242880` | Largest accepted file |
| `SC_MAX_ROWS` | backend | `5000` | Most rows per statement |
| `SC_MAX_STATEMENTS` | backend | `200` | In-memory statements kept before the oldest is dropped |
| `SC_CURRENCY` | backend | `PKR` | Label shown next to amounts |
| `SC_RULES_PATH` | backend | built-in rules | Use a different rules file |

No keys, passwords or tokens are needed or committed.

## Tests and checks

```bash
cd backend && pytest                          # 255 tests
cd backend && ruff check . && ruff format --check .
cd frontend && npm test                       # 17 tests
cd frontend && npm run lint && npm run build && npm run typecheck
```

CI runs the same commands ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)).

The backend tests cover the parser's formats and failure modes, every branch of the brain, invariants over thousands of random descriptions (a category never contradicts the direction of the money, nothing below the confidence threshold is auto-accepted), the totals, and the full API including CSV-injection-safe export.

## API

| Method and path | Purpose |
| --- | --- |
| `POST /api/statements` | Upload a CSV (`file`, optional `?purchases_positive=true`). Returns the categorized statement. |
| `GET /api/statements/{id}` | Fetch a statement again |
| `PATCH /api/statements/{id}/transactions/{txn_id}` | Fix one row: `{"category": "Fuel"}`. Returns the statement and `updated_ids` of other rows that changed. |
| `GET /api/statements/{id}/export.csv` | Download the categorized statement |
| `GET /api/sample-statement` | The bundled sample CSV |
| `GET /api/categories` | Categories a user may assign |
| `GET /api/health` | Liveness check |

## Project layout

```
backend/
  app/
    main.py            app factory, CORS, error handling
    config.py          settings (env vars)
    categories.py      the category vocabulary and how each one is taxed
    models.py          Transaction, Decision, Statement, summary shapes
    parser.py          CSV → clean transactions (never crashes on one bad row)
    store.py           in-memory storage behind a small interface
    brain/
      normalizer.py    messy description → stable merchant key
      rules.json       the rules (data, not code)
      rules.py         loads and validates the rules at startup
      categorizer.py   THE BRAIN
    services/          upload / fix use cases, totals, CSV export
    api/               routes and request/response schemas
  tests/               pytest suite
  sample_data/         fake statement with deliberate traps
frontend/              Next.js app (see frontend/README.md)
```

## Notes

- Statements live in server memory only. Restarting the backend clears them. A database is the first thing to add for real use (see DESIGN.md).
- All sample data is fake. Do not commit real statements.
- Totals are estimates, not tax advice.
