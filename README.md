# FreelanceBooks

FreelanceBooks is an explainable statement categorizer for freelancers working with foreign clients. It reads a CSV statement, classifies transactions with deterministic code, highlights uncertainty, and learns from corrections without using a large language model to make decisions.

![FreelanceBooks review flow](docs/app-flow.svg)

## Why this product

Tax preparation is stressful when a freelancer has client income, software subscriptions, payment fees, transfers, refunds, and mixed personal spending in the same statement. FreelanceBooks creates a reviewable first pass instead of pretending that every transaction can be guessed safely.

The guiding rule is:

> When the evidence is strong, categorize with a reason. When it is weak, ask the user.

## Features

- CSV upload for bank statements and expense datasets
- 1,211-row sample dataset support
- Deterministic categorization brain written in Python
- Income, expense, refund, and transfer detection
- Freelancer and general expense categories
- Confidence score and explanation for every row
- Needs Review workflow for ambiguous transactions
- Private workspace rules learned from user corrections
- Curated shared defaults that never override personal rules
- SQLite persistence
- Workspace isolation
- Password-hashed demo authentication and signed sessions
- Statement history and correction audit trail
- Pending shared-rule candidates for administrator review
- Upload size limit and secure response headers

## Architecture

![FreelanceBooks architecture](docs/architecture.svg)

The frontend is React/Vite. The API is FastAPI. SQLite stores users, workspace membership, statements, transactions, personal rules, audit events, and pending shared-rule candidates.

## Run locally

### Backend terminal

```powershell
cd "D:\KAMMM\SAVVPRO Hiring Task\savvpro-test-statement-categorizer\backend"
py -3.14 -m pip install -r requirements.txt
$env:FREELANCEBOOKS_SESSION_SECRET="local-test-secret"
$env:FRONTEND_ORIGIN="http://localhost:5173"
py -3.14 -m uvicorn app.main:app --reload
```

### Frontend terminal

```powershell
cd "D:\KAMMM\SAVVPRO Hiring Task\savvpro-test-statement-categorizer\frontend"
npm install
npm run dev
```

Open the URL printed by Vite, normally `http://localhost:5173`.

### Demo accounts

```text
User:  demo
Pass:  demo-password-change-me

Admin: admin
Pass: admin-password-change-me
```

These are seeded assessment accounts, not production credentials. Change or remove them before a public deployment.

## Try the app

1. Sign in as `demo`.
2. Select `Freelancer Demo`.
3. Upload `sample_statement.csv` or `combined_expense_dataset.csv`.
4. Review confidence and explanations.
5. Change a category to create a private workspace rule.
6. Switch to `Small Agency Demo` to verify isolation.
7. Sign out and confirm protected data is no longer accessible.

## CSV formats

Standard statement CSV:

```csv
Date,Description,Amount,Currency,Type
2026-01-02,CLIENT PAYMENT,1200,USD,Income
2026-01-03,ADOBE,-30,USD,Expense
```

Expense dataset CSV:

```csv
expense_id,amount,merchant,description,category
SEED0,2713.64,Swiggy,bought groceries at dmart,Food & Dining
```

The supplied `category` column is never trusted as the brain's answer.

## Tests

```powershell
cd backend
$env:PYTHONPATH="."
py -3.14 -m pytest -q
py -3.14 -m compileall -q app tests

cd ..\frontend
npm run build
```

## Inspect SQLite

The generated database is `freelancebooks.sqlite3` at the project root:

```powershell
cd "D:\KAMMM\SAVVPRO Hiring Task\savvpro-test-statement-categorizer"
@'
import sqlite3
c = sqlite3.connect("freelancebooks.sqlite3")
for table in ("users", "workspaces", "statements", "transactions", "rules", "audit_events", "shared_rule_candidates"):
    print(table, c.execute(f"select count(*) from {table}").fetchone()[0])
'@ | py -3.14 -
```

## Deployment

The backend has a [Dockerfile](backend/Dockerfile). Build and run it without reload mode:

```powershell
docker build -t freelancebooks-api .\backend
New-Item -ItemType Directory -Force .\data
docker run --rm -p 8000:8000 `
  -e FREELANCEBOOKS_SESSION_SECRET="replace-with-a-long-random-secret" `
  -e FRONTEND_ORIGIN="http://localhost:5173" `
  -v "${PWD}\data:/data" `
  freelancebooks-api
```

Build the frontend with the API URL configured:

```powershell
$env:VITE_API_URL="https://your-api.example.com/api"
npm run build
```

For a real deployment, put both services behind HTTPS, use strong unique credentials, protect the SQLite volume and backups, and replace seeded users with a managed identity provider.

## Project documents

- [DESIGN.md](DESIGN.md): product decisions and categorization brain
- [AI_USAGE.md](AI_USAGE.md): how AI assistance was used
- [TASK.md](TASK.md): original assessment brief
