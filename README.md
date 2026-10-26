# Landlord Statement Categorizer

Upload a landlord's bank statement (CSV). The app sorts every transaction into
tax-ready categories, splits mortgage payments into interest and principal, and
sends anything it is unsure about to **Needs Review** instead of guessing.

The categorizing logic is plain Python rules and scoring. **No AI model makes
any decision.** See [DESIGN.md](DESIGN.md) for how it works and
[AI_USAGE.md](AI_USAGE.md) for how AI tools were used to write the code.

## Requirements

- Python 3.10 or newer
- Node.js 20 or newer

## Setup and run

Open two terminals at the project root.

**Terminal 1: backend**

```cmd
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

On macOS/Linux, activate with `source .venv/bin/activate`.
The API runs at http://127.0.0.1:8000 (interactive docs at `/docs`).

**Terminal 2: frontend**

```cmd
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 (the backend only allows this origin).

## Try it

1. Upload `backend/data/bank_a.csv` (or `bank_b.csv`, a different bank layout
   with the same transactions).
2. Without loan details, 15 rows need review (12 are mortgage payments).
3. Enter loan details: 200000, 6, 360, 2025-01-01. Only 3 rows are left.
4. Pick a category for a remaining row. Every row with the same description is
   fixed too.

## Run the tests

```cmd
cd backend
python -m pytest -q
```

## API

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/statements` | Upload a CSV (optional `loan` JSON field) |
| GET | `/api/statements/{id}` | Fetch a statement again |
| PATCH | `/api/statements/{id}/transactions/{tx_id}` | Correct one row; applies to similar rows |
| PUT | `/api/statements/{id}/loan` | Add or change loan details; mortgage rows are re-split |
| GET | `/health` | Health check |

## Project layout

```
backend/
  app/
    api.py          routes, upload limits, validation
    store.py        in-memory statement store
    summary.py      totals per category
    models.py       Pydantic schemas
    parsing/        CSV reading, column detection, row validation
    brain/          normalize.py, rules.py, categorizer.py, mortgage.py
  tests/
  data/             fake sample statements
frontend/           Vite + React
```

## Notes

- Data is stored in memory and lost on restart. This is a deliberate
  simplification (see DESIGN.md, Limitations).
- All sample data is fake.