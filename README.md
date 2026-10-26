# Proofsheet

Proofsheet sorts a freelance designer's credit-card statement before tax time. Upload a CSV, review the rows the rules are willing to file, and confirm the ones they are not.

The category decision is ordinary Python: merchant rules, statement-shape rules, and merchants you have confirmed before. No large language model chooses a category.

## Run it

Use two terminals. Python 3.11+ and Node 20+ are enough.

Backend:

```bash
cd backend
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

macOS or Linux:

```bash
source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Open http://127.0.0.1:5173. The page talks to the API through the Vite proxy.

Click **Load the Studio North sample** to try a fictional January statement. To use your own export, choose credit card or bank so the signs are read the right way, then upload a CSV.

## Tests

```bash
cd backend
python -m pytest
```

## What the screen is showing

- **Deductible expenses** includes filed expense categories after refunds. Needs-review rows, personal charges, card payments, and transfers stay out of it.
- **Still to review** is the work list. Saving a category files that row. "Remember merchant" reuses your choice on later statements.
- Money out is a normal amount. Money in is shown in green with a minus.

`DESIGN.md` explains the rules. `AI_USAGE.md` explains which AI tools helped write this project.

## Layout

```text
backend/app/parser.py      CSV reading and amount signs
backend/app/brain.py       category rules
backend/app/service.py     totals, duplicates, corrections
backend/app/memory.py      saved merchants (SQLite)
backend/sample_statements  fictional Studio North statement
frontend/src               upload, review, and export screen
```

Saved merchants are stored in `backend/data/memory.db`. Uploaded statements live in memory and clear when the API restarts.

## Statement file

CSV, up to 5 MB. A preamble before the header is fine. These headers are recognized: date, description (or memo, merchant, narrative), amount, or separate debit and credit columns. A transaction-type column can say Sale, Return, or Payment. Dates can be `MM/DD/YYYY`, `YYYY-MM-DD`, or `02-Jan-2026`. Amounts can include `$`, commas, parentheses, a trailing minus, or a `CR` / `DR` suffix.
