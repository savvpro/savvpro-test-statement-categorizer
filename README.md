# Freelancer Statement Categorizer

Upload a freelancer's business credit-card or bank statement (CSV). The app sorts every
transaction into a tax category, shows totals per category, and leaves anything it is not
sure about in **Needs Review** for you to fix.

The categorizer is plain, deterministic Python (rules + checks). **No AI model makes any
decision.** See [DESIGN.md](DESIGN.md) for how it works and [AI_USAGE.md](AI_USAGE.md) for how
AI tools were used to *write* the code.

```
backend/    FastAPI app: CSV parser, categorizer ("the brain"), API, tests
frontend/   React (Vite) app: upload, review table, summary, CSV export
backend/sample_data/freelancer_statement.csv   fake statement to try
```

## Requirements

- Python 3.11+
- Node.js 18+

## Run it

Backend (terminal 1):

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate      macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000
```

Frontend (terminal 2):

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173, choose `backend/sample_data/freelancer_statement.csv` and click **Categorize**.
The dev server proxies `/api` to the backend on port 8000.

## Using it

1. Upload a CSV with a date, a description and an amount column (or separate debit/credit columns).
2. If your card shows purchases as positive numbers, tick the checkbox.
3. Review the summary. Open the **Needs review** tab and pick a category for each row.
   A fix applies to every row from the same merchant.
4. **Export CSV** to download the categorized result.

## Tests

```bash
cd backend && pytest          # parser, categorizer, API
cd frontend && npm test       # formatting / CSV export helpers
```

## API

`POST /api/categorize` (multipart): `file` (CSV, max 2 MB), `positive_is_charge` (bool),
`overrides` (JSON `{merchant_key: category}`). Returns transactions, summary, skipped-row
issues and warnings. `GET /api/health` for a liveness check.

## Notes

- Everything is stateless: nothing is stored on the server, and statements are not logged.
- All sample data is fake. Do not commit real statements.
