# Statement Categorizer

Upload a CSV bank or credit card statement and get every transaction sorted
into tax categories. Built for **freelance designers** doing their taxes.
The categorizing "brain" is plain, deterministic Python rules. No AI model
decides any category. When the code is not sure, it says so and asks you.

## Project layout

```
backend/    FastAPI app (parser, rules, categorizer, API) and pytest tests
frontend/   React (Vite) single page app
sample_data/fake_statement.csv   Fake data only
DESIGN.md   Use case and how the brain decides
AI_USAGE.md AI tools used, mistakes, token usage
```

## Requirements

- Python 3.11+
- Node.js 20+

## Run the backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

The API runs on http://localhost:8000. Check http://localhost:8000/api/health
and the interactive docs at http://localhost:8000/docs.

## Run the frontend

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 and upload `sample_data/fake_statement.csv`.
To point the frontend at another API, set `VITE_API_URL`.

## Run the tests

```powershell
cd backend
python -m pytest -v
```

## Using the app

1. Choose a CSV file (columns like `Date, Description, Amount`, or separate
   `Debit` / `Credit` columns). Tick the box if your card lists purchases as
   positive numbers.
2. Click **Categorize**. Each row shows its category and the reason.
3. Rows highlighted as **Needs review** are ones the app was not sure about.
   Pick a category from the dropdown. It applies to every row from the same
   merchant, and the totals update.
4. Click **Download CSV** to export the result.

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Health check |
| GET | `/api/categories` | Categories a user can pick |
| POST | `/api/categorize` | Multipart: `file`, `charges_positive`, `user_rules` (JSON). Returns `rows`, `summary`, `skipped` |

The API is stateless. The browser keeps the user's fixes and sends them with
each request. No database, no accounts, nothing is stored on the server.

## Notes

- All data in this repo is fake. Do not commit real statements.
- No keys or secrets are needed to run the project.