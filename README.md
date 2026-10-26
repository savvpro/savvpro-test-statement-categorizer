# ClearLedger - Statement Categorizer

A rule-based bank/credit-card statement categorizer for **freelance designers** (and similar small
freelance businesses) preparing their records for tax time.

Upload a CSV statement -> a Python rule engine categorizes every row -> you review and fix the rows it
was not sure about -> export the result.

> The "brain" is plain Python rules in `backend/categorizer.py`. No GPT/Claude/Gemini or any other AI
> model decides a category.

## Features
- Upload CSV statements (`description` + `amount`, or `debit`/`credit` columns; `date` optional).
- Deterministic rules with a reason shown for every row.
- When unsure (unknown merchant, conflicting rules, odd sign, zero amount) the row is flagged **Needs Review**.
- Refunds reduce the matching expense category and are never counted as income.
- Transfers and card payments are excluded from spending.
- Review UI: edit categories, search, filter, per-category totals, export the reviewed CSV.
- Fake sample data and 40+ automated tests.

## Requirements
- Python 3.11+
- Node.js 20+ and npm

## Run the backend (terminal 1)
Linux / macOS:
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```
Windows (PowerShell):
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload
```
API: http://localhost:8000 - interactive docs: http://localhost:8000/docs

## Run the frontend (terminal 2)
```bash
cd frontend
npm install
npm run dev
```
Open http://localhost:5173 and click **Try sample**, or upload `sample_data/sample_statement.csv`.

If the backend runs elsewhere, copy `frontend/.env.example` to `frontend/.env` and set `VITE_API_URL`.
To allow other frontend origins, set `CORS_ORIGINS` (comma separated) before starting the backend.

## Run the tests
```bash
cd backend
python -m pytest -v
```
Frontend production build check: `cd frontend && npm run build`.

## CSV format
| Column | Notes |
|---|---|
| `description` (or transaction / merchant / details / memo / payee) | required |
| `amount` | required unless `debit`/`credit` columns exist. Accepts `$1,234.50`, `(25.00)`, `-$10`, `25.00 CR` |
| `date` | optional |

Sign convention: **positive = money charged/spent, negative = credit/money back.**

## Project layout
```
backend/    FastAPI app (main.py), rule engine (categorizer.py), tests
frontend/   React + Vite review UI
sample_data/sample_statement.csv   fake statement
DESIGN.md   use case and how the brain decides
AI_USAGE.md AI tools used and what went wrong
```

## Privacy
Use synthetic data only. Nothing is stored on the server; edits live in the browser session.
