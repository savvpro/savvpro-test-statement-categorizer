# Statement Categorizer

This app helps an independent web designer review business credit-card transactions before tax time. It accepts a CSV statement, categorizes each row with deterministic Python rules, highlights uncertain rows, recalculates totals after review, and exports the corrected CSV.

The categorization brain is local application code. It does not call a large language model at runtime. See [DESIGN.md](DESIGN.md) for the use case and rule precedence.

## Requirements

- Python 3.11+
- Node.js 20+
- npm

## Run the Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API runs at `http://localhost:8000`. Its health check is `http://localhost:8000/health`.

Run backend tests:

```powershell
cd backend
python -m pytest
```

## Run the Frontend

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open the Vite URL shown in the terminal. Upload `sample-data/designer-statement.csv` to try the full flow.

Build the frontend for production with:

```powershell
cd frontend
npm run build
```

## Workflow

1. Upload a CSV with `date`, `description`, and `amount` columns.
2. Review automatic categories, confidence, and rule reasons.
3. Filter to uncertain transactions and choose corrected categories.
4. Confirm spending, refund, transfer, and review totals.
5. Export the reviewed transactions as CSV.

Only fake sample data is included. Uploaded files are processed in memory and are not stored by the backend.

More design decisions are documented in [DESIGN.md](DESIGN.md), and development assistance is recorded in [AI_USAGE.md](AI_USAGE.md).
