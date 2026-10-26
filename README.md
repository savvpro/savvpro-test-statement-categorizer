
# Statement Categorizer

A rule-based transaction categorization application designed for freelancers reviewing financial transactions for tax preparation.

## Features

- Upload CSV transaction statements.
- Categorize recognized merchants using explicit Python rules.
- Identify refunds and transfers separately from ordinary expenses.
- Mark unknown transactions as `Needs Review` instead of guessing.
- Manually correct transaction categories in the frontend.
- Export reviewed transactions to CSV.
- Validate CSV headers, amounts, and upload size.
- Run automated tests for categorization and API behavior.

## Technology Stack

- Backend: Python, FastAPI
- CSV processing: Python standard library
- Frontend: React, TypeScript, Vite
- Testing: pytest, FastAPI TestClient

No large language model is used to make categorization decisions.

## Project Structure

```text
.
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   └── categorizer.py
│   ├── tests/
│   │   ├── test_api.py
│   │   └── test_categorizer.py
│   └── requirements.txt
├── frontend/
│   └── src/
├── README.md
├── TASK.md
├── DESIGN.md
└── AI_USAGE.md
```

## Prerequisites

- Python 3.11 or newer
- Node.js and npm

## Run the Backend

From the repository root:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API runs at `http://127.0.0.1:8000`.

Interactive API documentation is available at `http://127.0.0.1:8000/docs`.

## Run the Frontend

Open a second terminal at the repository root:

```powershell
cd frontend
npm install
npm run dev
```

Open the local URL printed by Vite, usually `http://localhost:5173`.

## CSV Format

The initial implementation expects a CSV with these columns:

```csv
description,amount
GitHub subscription,-10.00
Uber trip,-18.50
Adobe refund,25.00
Unknown merchant 123,-42.00
```

The amount should be a numeric value. This example uses negative amounts for money spent and positive amounts for money received. Actual bank statement formats vary, so users must confirm the sign convention before relying on results.

## Run Tests

From the repository root:

```powershell
cd backend
python -m pytest -v
```

## Important Limitations

- Categorization is based on transparent keyword rules, not a tax advisor or a large AI model.
- Unknown transactions are sent for manual review.
- A refund is identified using description keywords; the original purchase is not automatically matched.
- Tax deductibility is not determined by the application.
- The current version does not persist reviewed transactions in a database.
- CSV upload is supported; PDF statements are not currently supported.
- Only the documented CSV schema is supported.

Use synthetic sample data only. Do not upload or commit real bank statements, credentials, or personal financial information.
