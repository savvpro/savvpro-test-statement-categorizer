# Statement Categorizer

Sorts a freelance software developer's bank statement for tax time. Upload a CSV or PDF statement in PKR or USD. Every transaction is either sorted by rules (with the reason shown) or held for you to review. Fix what needs fixing, turn fixes into rules, read the totals per currency and export the result.

The decisions come from Python rules in this repository. No AI model decides a category.

![The page after uploading the sample PKR statement](docs/screenshot.png)

- What it does and doesn't do: [Scope.md](Scope.md)
- How the rules decide: [DESIGN.md](DESIGN.md)
- How I used AI tools while building it: [AI_USAGE.md](AI_USAGE.md)

## What you need

- Python 3.11 or newer
- Node.js 20 or newer
- Tesseract OCR, only for scanned PDFs (optional)
  - macOS: `brew install tesseract`
  - Ubuntu or Debian: `sudo apt install tesseract-ocr`
  - Windows: the installer from the [UB Mannheim build](https://github.com/UB-Mannheim/tesseract/wiki), then add it to `PATH`

Without Tesseract the app still runs. Scanned PDFs just get a message saying OCR isn't installed.

## Run it

Two terminals.

**Backend** (http://127.0.0.1:8000):

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Frontend** (http://localhost:5173):

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The dev server forwards `/api` to the backend.

FastAPI's interactive API docs are at http://127.0.0.1:8000/docs.

## Try it with the sample statements

All sample files are invented. They live in `backend/sample_data/`:

| File | What it shows |
|---|---|
| `pkr_business_account_march.csv` | Bank details above the header, Debit/Credit/Balance columns, day-first dates, an opening balance line, refunds, transfers, tax and bank charges, a duplicated row |
| `usd_freelance_account_april.csv` | Newest first, one signed Amount column, a Currency column, a refund, a currency conversion, one unreadable amount |
| `pkr_statement_april.pdf` | Two-page text PDF with a repeated header, a wrapped description and page footers |
| `pkr_statement_may_scanned.pdf` | An image-only scan, read with OCR |

A good first run: upload the PKR CSV as a **business only** account, review the rows in marigold, fix `JOES CAFE 9921` to Meals and accept the rule offer. Then upload the April PDF as **business and personal** and compare how PTCL is treated.

To rebuild the samples: `pip install -r requirements-dev.txt`, then `python scripts/make_samples.py`.

## Tests and checks

```bash
cd backend
pip install -r requirements-dev.txt
pytest            # 104 tests; the OCR test is skipped if Tesseract is missing
ruff check .

cd ../frontend
npm run lint
npm run build
```

GitHub Actions runs all of these on every push and pull request (`.github/workflows/ci.yml`).

## Settings

All optional. None of them are secrets. See `backend/.env.example`.

| Variable | Default | Meaning |
|---|---|---|
| `APP_DB_PATH` | `backend/data/categorizer.db` | Where the SQLite file lives |
| `APP_MAX_UPLOAD_MB` | `10` | Largest upload accepted |
| `APP_ALLOWED_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Origins allowed to call the API |

To use a `.env` file: `uvicorn app.main:app --env-file .env`.

For the frontend, `VITE_API_URL` points the page at an API on another address (by default it uses the same address and the dev proxy).

## Statement formats

**CSV.** The header row can come after a few lines of bank details. These column names are understood (case doesn't matter):

| Column | Accepted names |
|---|---|
| Date | date, transaction date, txn date, trans date, value date, posting date, booking date |
| Description | description, details, transaction details, narration, particulars, remarks, transaction description, memo |
| Amount | amount, transaction amount, amt |
| Debit | debit, debits, withdrawal, withdrawals, dr, money out, paid out, debit amount |
| Credit | credit, credits, deposit, deposits, cr, money in, paid in, credit amount |
| Balance | balance, running balance, available balance, closing balance |
| Type | type, dr/cr, cr/dr, debit/credit, transaction type |
| Currency | currency, ccy, cur |

A file needs Date, Description, and either Amount or Debit/Credit. With a single Amount column and no Type column, negative means money out.

**PDF.** One table with a header line containing Date, Description and Debit/Credit or Amount, plus an optional Balance, with right-aligned numbers. Up to 30 pages.

## Project layout

```text
backend/
  app/
    main.py              API routes
    service.py           import, fixes, rules, totals, export
    storage.py           SQLite schema and queries
    config.py            settings from environment variables
    parsing/
      csv_parser.py      CSV files
      pdf_parser.py      PDF files, with OCR for scanned pages
      ocr.py             Tesseract wrapper
      layout.py          rebuilds table rows from word positions
      rows.py            the checks every row goes through
      values.py          amounts, dates, descriptions
      columns.py         accepted column names
    categorizer/
      rules.yaml         the built-in rules
      rules.py           loading and matching rules
      engine.py          the brain
  scripts/make_samples.py
  sample_data/           invented statements
  tests/
frontend/
  src/
    App.jsx              the page
    api.js               calls to the backend
    components/          upload, totals, imports, transactions, rules
```

## Privacy

Uploaded files are read in memory and not stored. Extracted rows go into the local SQLite file, which Git ignores. The page has buttons to delete one import or all imported data.
