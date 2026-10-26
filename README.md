# E-commerce Statement Categorizer

A web application that helps e-commerce business owners organize financial transactions by automatically assigning categories using explicit Python rules. Users can review the results and manually change categories when needed.

## Features

- Upload transaction statements in CSV format.
- Validate required columns, dates, amounts, and file size.
- Categorize transactions using deterministic Python rules.
- Display an explanation for each categorization decision.
- Flag unrecognized transactions as **Needs Review**.
- Manually change transaction categories in the frontend.
- View transaction counts and category totals.
- Run automated backend tests.

## Technology Stack

- **Backend:** Python, FastAPI
- **Frontend:** React, Vite
- **Categorization:** Explicit Python rule-based logic
- **Testing:** pytest, FastAPI TestClient

## Project Structure

```text
savvpro-test-statement-categorizer/
├── backend/
│   ├── main.py
│   ├── categorizer.py
│   ├── test_api.py
│   ├── test_categorizer.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   └── App.css
│   ├── package.json
│   └── package-lock.json
├── sample_data/
│   └── sample_transactions.csv
├── README.md
├── DESIGN.md
├── AI_USAGE.md
└── .gitignore
```

## Requirements

- Python 3.11 or later
- Node.js and npm

## Setup and Run

### 1. Start the backend

Open a terminal in the project root and run:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

Interactive API documentation is available at `http://127.0.0.1:8000/docs`.

### 2. Start the frontend

Open a second terminal in the project root:

```powershell
cd frontend
npm install
npm run dev
```

Open the local URL printed by Vite, usually `http://localhost:5173`.

Keep both development servers running while using the application.

## Input CSV Format

The CSV file must contain these columns:

| Column | Description |
|---|---|
| `date` | Transaction date in `YYYY-MM-DD` format |
| `description` | Transaction description or merchant |
| `amount` | Numeric transaction amount |

Example:

```csv
date,description,amount
2026-09-01,CLOUDHOST MONTHLY,-24.99
2026-09-02,PACKAGING SUPPLIES,-82.50
2026-09-03,ONLINE ORDER PAYOUT,350.00
```

A fictional sample statement is provided in `sample_data/sample_transactions.csv`.

## Run Tests

From the project root:

```powershell
cd backend
python -m pytest -v
```

The tests cover categorization rules and API validation, including invalid dates, amounts, duplicate headers, missing fields, empty statements, and oversized files.

## Categorization Overview

The application uses explicit Python rules rather than calling a large language model at runtime. Known transaction descriptions are matched against predefined rules. Transfers and refunds have dedicated handling, while unrecognized transactions are flagged for review.

See [DESIGN.md](DESIGN.md) for the architecture, rule order, and limitations.

## Limitations

- CSV files only; PDF and spreadsheet formats are not supported.
- Categorization depends on the descriptions covered by the predefined rules.
- Manual category changes are held in frontend state and are not saved permanently.
- Currency is not inferred from the CSV.
- Category totals are for transaction organization only; they do not determine tax deductibility or provide tax advice.

## AI Usage

AI assistance was used during development. The categorization logic itself runs through explicit Python rules and does not require an external AI model. See [AI_USAGE.md](AI_USAGE.md) for details.
