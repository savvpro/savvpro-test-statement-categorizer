# Ledgerly — Statement Categorizer

Ledgerly imports a bank-statement CSV, assigns clear deterministic categories,
flags uncertain transactions for review, and exports the corrected result.

No API key, account, or external finance service is required. Use fictional data only.

## Live demo

[Open Ledgerly on Render](https://ledgerly-statement-categorizer.onrender.com/)

The public demo uses fictional data. Its local demo database can reset when the
hosting service restarts, so use the local setup below for persistent review data.

## Run locally

**Requirements:** Python 3.11+ and Node.js 22+.

From the project root in PowerShell:

```powershell
.\scripts\setup.ps1
.\scripts\start.ps1
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). Keep the terminal open while
using the application; press `Ctrl+C` to stop it.

If PowerShell blocks scripts, run:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
npm.cmd --prefix frontend ci
npm.cmd --prefix frontend run build
.\.venv\Scripts\python.exe scripts/run.py
```

## Try it

1. Click **Try sample data**, or upload a CSV.
2. Review transactions marked **Needs review**.
3. Save any correction and export the result as CSV.

Sample files are in `sample_data/`:

- `freelancer_statement.csv` — standard amount-column statement
- `debit_credit_statement.csv` — debit/credit-column statement
- `invalid_statement.csv` — demonstrates validation feedback

## CSV requirements

Use UTF-8, comma-separated CSV with these columns:

```csv
transaction_id,date,description,amount,currency
fake_001,2026-10-01,ADOBE CREATIVE CLOUD,-59.99,USD
```

`date`, `description`, and `amount` are required. Alternatively, use `debit` and
`credit` columns. `transaction_id` and `currency` are optional. Files can contain
up to 10,000 transactions and be up to 5 MiB.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check backend scripts
npm.cmd --prefix frontend test
npm.cmd --prefix frontend run build
```

## Project structure

```text
backend/       FastAPI API, CSV validation and categorization engine
frontend/      React + TypeScript user interface
sample_data/   Fictional CSV files for testing
scripts/       Local setup and server-start scripts
```

See [DESIGN.md](DESIGN.md) for implementation decisions and [AI_USAGE.md](AI_USAGE.md)
for the required AI-use disclosure.
