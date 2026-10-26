# Statement Categorizer

Upload a business credit card / bank statement (CSV) and get every transaction sorted for tax time.
Use case: a **freelance software developer**. The categorizer is plain Python rules, no AI model (see `DESIGN.md`).

## Run the backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload        # http://localhost:8000/docs
pytest                               # run tests
```

## Run the frontend
```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev                          # http://localhost:3000
```

Upload `fixtures/sample_statement.csv` (fake data) to try it.

## Supported input
CSV with a date column, a description column and either one `Amount` column or `Debit`/`Credit` columns.
Max 1 MB / 5,000 rows. Dates: `YYYY-MM-DD`, `MM/DD/YYYY`, `MM/DD/YY`, `DD-Mon-YYYY`.

## Known limits
Statements and learned rules are stored in memory (lost on restart). CSV only, no PDF. US-style dates only.
