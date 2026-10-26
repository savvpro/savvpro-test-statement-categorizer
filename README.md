# Statement Categorizer

Upload a business credit card statement (CSV). The app sorts every purchase into a tax category with plain Python rules (no AI model), marks anything unclear as **Needs Review**, and lets you fix those rows. Use case: a **freelance designer** preparing for tax time. See `DESIGN.md` for how decisions are made.

## Requirements
- Python 3.10+
- Node.js 18+

## Run the backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Run the frontend (new terminal)
```bash
cd frontend
npm install
npm run dev
```
Open http://localhost:5173 and upload `backend/sample_data/statement.csv` (fake data).

## Run the tests
```bash
cd backend
python -m pytest
```

## Project layout
```
backend/app/rules.py        keyword lists (edit here to teach the app a merchant)
backend/app/categorizer.py  the brain: one transaction -> category + reason
backend/app/parser.py       CSV reading, column/date/amount handling, bad-row reporting
backend/app/service.py      builds result rows and the summary totals
backend/app/main.py         API: POST /api/statements, POST /api/summary, GET /api/categories
backend/tests/              pytest tests
frontend/src/               React app (upload, summary, editable table)
```

## Notes
- Only fake data is included. No keys or secrets are used.
- Upload limits: .csv only, 2 MB, 5000 rows.
