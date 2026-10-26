# Freelancer Statement Categorizer

A statement review app for freelance designers, built with Python FastAPI
and React. Users upload a CSV, review rule-based categories, correct
transactions, view totals, and export saved results.

No large language model is used to categorize transactions.

## Features

- CSV upload with validation and clear error messages.
- Deterministic merchant and transaction-type rules.
- Separate handling for expenses, income, refunds, and transfers.
- Needs Review status for unknown or conflicting descriptions.
- Editable transaction types and categories.
- Category totals recalculated after saved corrections.
- CSV export of saved results.
- Automated backend tests.

## Requirements

- Python 3.12 (used during development).
- Node.js and npm compatible with the installed Vite version.
- Two terminals: one for the backend and one for the frontend.

## Run the backend — Windows PowerShell

From the repository root:

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

Backend: http://127.0.0.1:8000
API documentation: http://127.0.0.1:8000/docs

## Run the frontend

Open a second terminal from the repository root:

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev -- --port 5173 --strictPort
```

Open http://localhost:5173.

## CSV format

Required columns:

```csv
date,description,amount,currency
2026-10-01,ADOBE CREATIVE CLOUD,-6500,PKR
2026-10-02,CLIENT PAYMENT PROJECT ALPHA,50000,PKR
2026-10-03,ADOBE REFUND,2000,PKR
```

- UTF-8 encoding.
- Dates use YYYY-MM-DD.
- Negative amounts represent outgoing money.
- Positive amounts represent incoming money.
- Amounts must have no thousands separators and at most two decimal places.
- One currency per statement.
- Supported currencies: PKR, USD, GBP, EUR, SAR, AED.
- Maximum upload size: 2 MB.
- Maximum transactions per upload: 5,000.

Use the fictional sample at `samples/sample.csv`. Do not upload real
bank statements or personal information for this assessment.

## Demo workflow

1. Upload `samples/sample.csv`.
2. Confirm 7 transactions and 1 transaction needing review.
3. Confirm net categorized expenses of PKR 8,800.
4. Find UNKNOWN SHOP.
5. Change its type to expense and category to Office Supplies.
6. Click Save.
7. Confirm net expenses become PKR 10,300 and review count becomes zero.
8. Export saved results.

Unresolved amounts and transfers are excluded from categorized expenses.
Refunds reduce expenses in their assigned category.

## Validation

Backend tests, from the backend folder:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Frontend checks, from the frontend folder:

```powershell
npm.cmd run build
npm.cmd run lint
```

Development validation:
- 24 backend tests passed.
- Frontend production build passed.
- ESLint passed.
- Backend tests emitted a dependency deprecation warning involving
  Starlette TestClient and httpx; it did not fail the tests.

## Project files

- `backend/main.py`: API routes, temporary storage, correction validation.
- `backend/categorizer.py`: CSV validation and classification rules.
- `backend/summary.py`: Decimal-based totals.
- `backend/test_app.py`: automated tests.
- `frontend/src/App.jsx`: upload, review, correction, and export interface.
- `frontend/src/App.css`: dashboard styling.
- `samples/sample.csv`: fictional demonstration data.
- `DESIGN.md`: decisions and limitations.
- `AI_USAGE.md`: disclosure of AI assistance.

## Limitations

- CSV only; PDF and image statements are not supported.
- Statements are stored in memory and disappear when the backend restarts.
- Refreshing the frontend clears the displayed statement.
- Run the backend with a single worker.
- No authentication, database, or multi-user isolation.
- Rules cover a small set of merchants and English descriptions.
- Merchant matches do not establish business purpose or tax deductibility.
- Duplicate transactions are not automatically detected or removed.
- Export contains saved row classifications; re-uploading it runs
  categorization again rather than restoring prior corrections.
- Google Fonts requires internet access; local fallback fonts are provided.

This is a local assessment prototype, not a production banking or
tax-filing service.