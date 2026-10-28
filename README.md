# Freelance Ledger

A statement categorizer for independent designers. Upload a bank or business-card **CSV** to get a rule-based first pass, review uncertain merchants, correct categories, and export the reviewed transactions. The categorizer is local application code; it does not send transactions to an AI model or an external service.

## Features

- Reads CSV exports with date and description/merchant columns and either a signed amount column or debit and credit columns.
- Recognizes common bank CSV formats: comma, semicolon, and tab delimiters; UTF-8 and Windows-1252; currency symbols, thousands separators, parentheses for negatives, and `CR`/`DR` suffixes.
- Applies specific merchant/transaction phrase rules. Unknowns remain **Needs review** rather than being guessed.
- Distinguishes known transfers, refunds, client income, and expense categories.
- Lets the user edit categories, filter review items, see expense totals, and download a categorized CSV.
- Processes uploaded rows in memory only; the application has no database and does not save statements.

## Run locally

### Backend (Python 3.10+)

From the repository root, in PowerShell:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

The API is available at `http://localhost:8000`. Set `CORS_ORIGINS` to a comma-separated list of trusted frontend origins when running the API from another origin.

### Frontend (Node.js 20.9+)

In a second terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Open `http://localhost:3000`. By default, the frontend calls `http://localhost:8000`. Set `NEXT_PUBLIC_API_URL` before starting Next.js if the API runs elsewhere.

## Tests and checks

```powershell
cd backend
python -m pytest
```

```powershell
cd frontend
npm run lint
npx tsc --noEmit
npm run build
```

## CSV format

The CSV must have a header row and one transaction per row. Accepted date headers include `Date`, `Transaction Date`, and `Posted Date`; description headers include `Description`, `Merchant`, `Details`, and `Payee`. Supply either `Amount` or both `Debit` and `Credit`. Amounts are treated as USD for display; the CSV must not mix currencies. Rows with unknown merchants are returned and marked for review. A malformed row rejects the upload with its line number so the user can fix the source file.

Scanned PDFs and image statements are not supported. Export a CSV from the bank or card provider before uploading. Never upload real statements to a public demo.
