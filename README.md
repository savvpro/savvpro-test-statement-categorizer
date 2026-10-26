# Statement Categorizer

Upload a bank or credit card statement (CSV) and the app sorts every transaction into a tax category.
Use case: a **freelancer's business credit card statement at tax time**.

The "brain" is plain Python rules. No AI model decides anything. If the app is not sure, it says
**Needs Review** instead of guessing, and the user fixes those rows in the UI.

## Features

- CSV upload with per-row error reporting (bad rows are skipped, good rows still work)
- Rule-based categories: Software, Travel, Meals, Office, Utilities, Income, Refund, Transfer, Needs Review
- Refunds are not income, and transfers are not spending
- Duplicate rows are flagged, not deleted
- Fix any row from a dropdown; totals recalculate immediately
- "Show only Needs Review" filter

## Tech

- Backend: Python 3.11+, FastAPI, pytest
- Frontend: React (Vite)

## Run it

You need Python 3.11+ and Node 18+.

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend (second terminal)

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. Vite forwards `/api` to the backend on port 8000.

Try `data/sample_statement.csv` first, then `data/messy_statement.csv` (mixed date formats,
`(23.40)` negatives, duplicates, one bad row).

### Tests

```bash
cd backend
source .venv/bin/activate
pytest -v
```

## CSV format

Required columns (any case): `date`, `description`, `amount`.

- Negative amount = money out, positive = money in
- Amounts accepted: `-45.00`, `(45.00)`, `$1,200.50`, `45.00-`
- Dates accepted: `2026-10-01`, `01/10/2026` (day first), `1 Oct 2026`
- Max file size: 2 MB

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Health check |
| GET | `/api/categories` | Allowed categories |
| POST | `/api/upload` | Upload CSV, returns rows, skipped-row errors and totals |
| POST | `/api/totals` | Recalculate totals after the user changes categories |

## Project structure

```
backend/app/brain/   normalizer.py, classifier.py   (the decision logic)
backend/app/         parser.py, service.py, main.py
backend/tests/       parser, classifier and API tests
frontend/src/        React UI
data/                fake sample statements only
```

## More

- [DESIGN.md](DESIGN.md): use case and how the brain decides
- [AI_USAGE.md](AI_USAGE.md): which AI tools were used and how
- [TASK.md](TASK.md): the original task