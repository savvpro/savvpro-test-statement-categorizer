# Statement Categorizer

A full-stack application that imports bank statements, categorizes transactions using explainable rules, and lets users review and correct uncertain results.

## Features

- Upload bank statements in CSV, XLSX, or XLS format.
- Validate statement columns and handle common date, description, amount, debit, and credit formats.
- Categorize transactions using deterministic, rule-based logic.
- Mark uncertain transactions as **Needs Review** instead of guessing.
- Manually correct transaction categories.
- View transaction summaries and financial metrics.
- Filter, search, and export categorized transactions to CSV.
- Keep uploaded statements and their transactions in a SQLite database.

## Technology Stack

- **Backend:** Python, FastAPI, SQLAlchemy
- **Frontend:** React, TypeScript, Vite
- **Database:** SQLite
- **Testing:** pytest

## Prerequisites

Install:

- Python 3.10 or a compatible version supported by the dependencies
- Node.js and npm
- Git

## Setup and Installation

Clone the repository and switch to the assessment branch:

```bash
git clone https://github.com/MaqsoodAhmed110/savvpro-test-statement-categorizer.git
cd savvpro-test-statement-categorizer
git checkout candidate-MaqsoodAhmed110
```

### 1. Start the backend

Open a terminal in the repository root:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If PowerShell blocks activation, use a terminal where script activation is permitted, or run the virtual environment's Python executable directly.

Start FastAPI:

```powershell
uvicorn app.main:app --reload
```

Backend URL: http://127.0.0.1:8000

Interactive API documentation: http://127.0.0.1:8000/docs

### 2. Start the frontend

Open a second terminal:

```powershell
cd E:\savvpro-test-statement-categorizer\frontend
npm install
npm run dev
```

Open the local URL printed by Vite, normally http://localhost:5173.

The frontend API client connects to `http://127.0.0.1:8000`. Run both services while using the application.

## Running Tests

From the backend directory, activate its virtual environment and run:

```powershell
pytest -q
```

## Using the Application

1. Open the frontend in your browser.
2. Upload a supported bank statement.
3. Review the automatically assigned categories and financial summary.
4. Search or filter transactions.
5. Correct uncertain categories when you have enough information.
6. Export the displayed transactions using the categorized CSV download.

## Categorization Examples

| Description | Expected category |
|---|---|
| Adobe Creative Cloud | Software |
| Uber Trip | Transportation |
| Salary Payment | Income |
| Transfer to Savings | Transfer |
| An unfamiliar merchant such as JOES CAFE 9921 | Needs Review |

Refunds are treated separately from income. Transfers are excluded from ordinary spending calculations. Unrecognized merchants should be reviewed instead of being assigned a confident category without evidence.

## Data and Privacy

Uploaded statements are stored in the local SQLite database. Use synthetic or appropriately anonymized financial data for testing. Do not commit real bank statements, credentials, database files containing personal financial data, or other secrets to version control.

## Project Structure

```text
.
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── db/
│   │   └── services/
│   ├── sample_data/
│   └── tests/
├── frontend/
├── README.md
├── DESIGN.md
└── AI_USAGE.md
```

The exact contents of individual folders may evolve as the project develops.
