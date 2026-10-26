# Statement Categorizer

Sorts a freelance designer's bank / credit-card statement into tax categories.
Upload a CSV, see every transaction categorized with a reason and confidence,
fix the rows the app was not sure about, and get per-category tax totals.

The decision-making "brain" is plain Python rules + scoring (no LLM). See [DESIGN.md](DESIGN.md).

## Project layout

```
backend/            FastAPI app (Python 3.11+)
  app/parser.py     messy CSV -> transactions (+ per-row errors)
  app/brain.py      the categorizer (rules, refunds, transfers, duplicates, review logic)
  app/rules.py      merchant/keyword knowledge base
  app/service.py    upload / review / totals (in-memory store)
  app/main.py       HTTP API
  tests/            pytest suite
frontend/           React + Vite single page
sample_data/        fake statement to try it with
```

## Run it

Backend:

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000
```

Frontend (in another terminal):

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 and upload `sample_data/freelancer_statement.csv`.
The Vite dev server proxies `/api` to `localhost:8000`. For other setups set
`VITE_API_URL` (frontend) and `CORS_ORIGINS` (backend, comma-separated).

## Tests

```bash
cd backend
python -m pytest -q
```

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | liveness |
| GET | `/api/categories` | list of categories |
| POST | `/api/statements` | upload CSV (`file` form field) -> transactions, errors, summary |
| GET | `/api/statements/{id}` | fetch a processed statement |
| PATCH | `/api/statements/{id}/transactions/{tx_id}` | `{category, apply_to_same_merchant}` fix a row; the brain remembers the merchant |

## Data

All data in this repo is fake. No keys or secrets are needed.
