# Ledgerly — Statement Categorizer

A full-stack transaction categorization tool designed for **freelancers and independent consultants** preparing business records for tax time. Upload a bank-exported CSV, review deterministic category suggestions, correct uncertain rows, and export the result.

## Features
- React + Vite responsive finance dashboard.
- Python + FastAPI backend with CSV parsing, validation, a 10 MB upload limit, and JSON API.
- Explainable, deterministic merchant rules; no large language model makes category decisions.
- `Needs Review` fallback for unknown transactions and ambiguous positive amounts.
- Separate treatment for transfers, refunds, business income, and expenses.
- Search, category review, live summary metrics, sample data, and categorized CSV export.
- Automated tests for categorization, parsing, and accounting edge cases.

## Requirements
- Python 3.12+
- Node.js 20+
- Windows, macOS, or Linux

## Run locally

### 1. Backend
From the repository root:

```bash
python -m venv .venv
# Windows CMD:
.venv\Scripts\activate
# macOS/Linux:
# source .venv/bin/activate
python -m pip install -r backend/requirements.txt
uvicorn main:app --app-dir backend --reload
```

API health: `http://127.0.0.1:8000/api/health`  
Interactive API docs: `http://127.0.0.1:8000/docs`

### 2. Frontend
Open a second terminal at the repository root:

```bash
cd frontend
npm install
npm run dev
```

Open the local address printed by Vite (usually `http://localhost:5173`).

### 3. Tests
From the repository root, with the Python environment active:

```bash
python -m pytest -q
```

## CSV format
The parser accepts CSV files with a header row. It recognizes common columns such as `Date`, `Description`/`Merchant`, and `Amount`; or `Date`, `Description`, `Debit`, and `Credit`. Amounts may contain currency symbols, thousands separators, or parentheses for negative values. Unknown or malformed rows produce an explicit error rather than silently disappearing.

A fake example:

```csv
Date,Description,Amount
2026-10-02,ADOBE CREATIVE CLOUD,-59.99
2026-10-05,CLIENT PAYMENT - INV 104,1850.00
2026-10-06,TRANSFER TO SAVINGS,-300.00
2026-10-07,AMAZON REFUND,32.49
2026-10-10,MYSTERY VENDOR 999,-21.00
```

## Categorization principles
Rules are transparent and deterministic. Known merchant patterns map to a category with a rationale. Transfers are excluded from income/expense totals. Refunds are kept separate from income. Positive amounts are categorized as income only when their description contains a recognized income signal. Anything else goes to `Needs Review`; the tool favors asking the user over making an unsupported guess. This is a bookkeeping aid, not tax or accounting advice.

## Privacy and limitations
Use only fake or anonymized data for this assessment. Uploaded CSV data is processed in memory by the local API; this demo does not persist statements to a database. Do not upload credentials or bank login details. PDF and image statements are not supported in this version. Currency is displayed as USD in the sample interface; production use should infer or ask for the account currency.

## Project layout
```text
backend/main.py           FastAPI endpoints, parser, rules, summaries
backend/requirements.txt  Python dependencies
frontend/                 React UI and styles
tests/                    Python unit tests
README.md                 Setup and run instructions
DESIGN.md                 Use case and decision logic
AI_USAGE.md               AI assistance disclosure
```

## API overview
- `GET /api/health` — service health.
- `GET /api/categories` — supported categories.
- `POST /api/categorize` — multipart CSV upload and categorized transactions.
- `POST /api/demo` — synthetic sample data.
- `PATCH /api/transactions/{id}` — validates a requested category (client currently manages its in-session state).

## Security notes
No secrets or keys are required. CORS is restricted to local Vite origins for development. Before deployment, configure explicit production origins, authentication, upload rate limits, audit logging, and storage/retention controls.
