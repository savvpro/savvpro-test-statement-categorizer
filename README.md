# Statement Categorizer

Upload a bank or credit-card statement (CSV) and get every transaction sorted into
tax categories. Built for a **freelance designer** at tax time.

The categorisation "brain" is plain, rule-based Python. **No AI model (GPT, Claude, Gemini, etc.)
is used to make decisions.** When the brain is not sure, it says so and marks the row
**Needs Review** instead of guessing.

## Features

- CSV upload with validation (empty file, missing columns, bad encoding, size limit)
- Messy-data handling: mixed date formats, `(45.00)` / `1,200.00` amounts, merchant IDs
- Refunds are not income; transfers and card payments are not spending
- Possible duplicates and foreign-currency rows are flagged, never silently dropped
- Every row carries a category, a confidence (`high`/`low`) and a human-readable reason
- Tax-deductible hint per category (`yes` / `partial` / `no`)
- React UI: upload a statement, see how each row was categorised, fix **Needs Review** rows
  from a dropdown, and watch the totals recalculate

## Requirements

- Python 3.10+
- Node.js 18+

## Setup and run

You need two terminals: one for the backend, one for the frontend.

### 1. Backend (FastAPI)

```bash
cd backend
python -m venv venv
# Windows:   venv\Scripts\activate
# Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

- API: http://localhost:8000
- Interactive docs: http://localhost:8000/docs

### 2. Frontend (React + Vite)

```bash
cd frontend
npm install
npm run dev
```

- App: http://localhost:5173

The frontend talks to the backend at `http://localhost:8000` by default.
To change that, copy `frontend/.env.example` to `frontend/.env` and set `VITE_API_URL`.

### 3. Try it

Open http://localhost:5173 and upload `sample_data/fake_statement.csv`.
You will see categorised rows, a totals summary, and several rows marked **Needs Review**
that you can fix from the dropdown.

## Run tests

```bash
cd backend
pytest -v
```

Frontend lint and production build:

```bash
cd frontend
npm run lint
npm run build
```

## API

| Method | Path | Purpose |
|---|---|---|
| POST | `/upload` | Upload a CSV, returns transactions, skipped rows and summary |
| GET | `/transactions` | List current transactions |
| PATCH | `/transactions/{id}` | User sets a category; returns updated row and summary |
| GET | `/categories` | Allowed categories |
| GET | `/health` | Health check |

### CSV format

Required columns: `date`, `description`, `amount`. Optional: `currency` (defaults to USD).
Negative amount = money out, positive = money in.

## Project structure

```
backend/
  app/
    api/         HTTP routes
    parser/      CSV reading and normalising
    brain/       decision logic (checks/ = one file per rule)
    services/    summary totals, in-memory store
    data/rules.json   keywords and categories (edit rules without touching code)
  tests/
frontend/
  src/
    api/         API client
    components/  UploadForm, TransactionTable, CategorySelect, CategorySummary
    constants/   category list
    styles/      CSS
sample_data/     fake statement (fake data only)
DESIGN.md        use case and how the brain decides
AI_USAGE.md      AI tools used, mistakes, token usage
```

## Configuration

| Variable | Where | Default | Purpose |
|---|---|---|---|
| `CORS_ORIGINS` | backend | `http://localhost:5173` | Comma-separated allowed origins |
| `VITE_API_URL` | frontend | `http://localhost:8000` | Backend URL |

No secrets are needed. See `.env.example` files.

## Documentation

- [`DESIGN.md`](DESIGN.md): the use case, the brain's decision order, messy cases, trade-offs
- [`AI_USAGE.md`](AI_USAGE.md): AI tools used, where they were wrong, token usage

## Notes

- All data is fake. Never upload real statements.
- The store is in memory (one statement at a time). Swapping in a database only
  requires changing `services/store.py`.