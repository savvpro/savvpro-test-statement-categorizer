
# Statement Categorizer

A web application for organizing business transactions from bank statements, designed for freelancers and independent designers.

## Features

- Upload bank statements in CSV or PDF format.
- Extract transaction dates, descriptions, and amounts.
- Categorize transactions using deterministic keyword-based rules.
- Assign unknown transactions to `Needs Review`.
- Review transactions and edit their categories.
- Display transaction summaries.

## Technology Stack

- **Backend:** Python, FastAPI, pandas, pdfplumber, Pydantic
- **Frontend:** React, Vite
- **Testing:** pytest

## Project Structure

```text
statement-categorizer-submit/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── models/
│   │   ├── routers/
│   │   ├── services/
│   │   └── utils/
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   ├── package.json
│   └── package-lock.json
├── DESIGN.md
├── AI_USAGE.md
└── TASK.md
```

## Prerequisites

Install Python and Node.js with npm before running the application.

## Run the Backend

Open a terminal in the project root:

```powershell
cd backend
python -m venv .venv
```

Activate the virtual environment on Windows:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies and start FastAPI:

```powershell
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

The backend should be available at `http://127.0.0.1:8000`.

Interactive API documentation: `http://127.0.0.1:8000/docs`.

## Run the Frontend

Open a **second terminal** in the project root:

```powershell
cd frontend
npm install
npm run dev
```

Open the local URL printed by Vite in the terminal.

Keep both backend and frontend terminals running while using the application.

## API Endpoints

- `GET /health` — check backend health.
- `POST /api/upload` — upload a statement.
- `GET /api/transactions` — retrieve transactions.
- `PATCH /api/transactions/{transaction_id}` — update a transaction category.

## Run Backend Tests

From the project root:

```powershell
cd backend
python -m pytest -v
```

## Design and AI Usage

See [DESIGN.md](DESIGN.md) for the architecture, categorization rules, and limitations.

See [AI_USAGE.md](AI_USAGE.md) for a record of AI-assisted development and validation.

## Important Limitations

- Categorization is based on predefined merchant keywords and may require manual review.
- The current implementation treats all negative amounts as refunds.
- PDF extraction depends on the statement's table layout.
- Transaction data is stored in memory and may be cleared when the backend restarts.
- Use only synthetic or otherwise non-sensitive statement data when testing.

## Assessment Submission Instructions

The original assessment repository is:
https://github.com/savvpro/savvpro-test-statement-categorizer

1. Read [TASK.md](TASK.md).
2. Work on the branch `candidate-MuntazirHussainQasme`.
3. Commit and push your changes to your fork.
4. Open a pull request from your candidate branch to `main` of `savvpro/savvpro-test-statement-categorizer`.

Follow the original assessment requirements and deadline.
