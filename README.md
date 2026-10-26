# Statement Categorizer

Upload a bank or credit card statement and get every transaction sorted into a tax
category. The app is built for a **freelance designer's business card**: software
subscriptions, travel, meals, hosting, coworking and so on. Anything it is not sure about
goes to **Needs Review** instead of being guessed. You fix those rows, optionally teach the
app a rule, and export the result.

```
Upload statement -> Read transactions -> The brain -> Category for each row -> You review
```

The brain is plain deterministic Python: phrase rules, structural checks and confidence
scores. There is no call to any AI model anywhere in the decision path. See
[DESIGN.md](DESIGN.md) for how it decides and [AI_USAGE.md](AI_USAGE.md) for how AI tools
were used to build it.

## What it handles

- **Formats:** CSV, TSV and text, Excel (`.xlsx`), PDF, OFX/QFX, ISO 20022 `camt.053` (XML)
  and SWIFT `MT940`. The real format is detected from the content, so a `.csv` that is
  really a PDF is still read, with a warning.
- **Messy input:** byte-order marks, Windows-1252 and UTF-16, semicolon and tab delimiters,
  preamble lines before the header, `sep=` hints, debit/credit columns, `CR`/`DR` suffixes,
  parentheses negatives, `1.234,56` style numbers, ambiguous `03/04/2026` dates, localised
  headers, multi-line and watermarked PDF tables, running-balance cross-checks.
- **Tax-time traps:** refunds are money back and reduce the category they came from (they
  are never income), card payments and transfers are not spending, duplicate lines are
  flagged, foreign-currency rows are not blindly totalled, ambiguous merchants such as
  Amazon, PayPal or fuel stations always ask.
- **Safety limits:** upload size, row and page caps, zip-bomb and XML-entity protection,
  per-client rate limiting, CSV-injection-safe export. Broken files return a clear error
  code and message instead of a crash.

## Run it locally

You need Python 3.11+ and Node 20+.

### Backend (port 8000)

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate      macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend (port 5173)

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 and drop in one of the files from [sample-data/](sample-data/):

| File | What it shows |
|---|---|
| `designer_card_march_2026.csv` | The main demo: refunds, duplicates, ambiguous merchants, a transfer, a card payment, bad rows |
| `bank_debit_credit_april_2026.csv` | Debit/credit columns, a preamble, client income, an income-tax payment |
| `european_semicolon_may_2026.csv` | Semicolons, decimal commas, German headers, a euro statement with one dollar row |
| `card_export_june_2026.ofx` | OFX with a repeated transaction id and a refund |
| `reference/` | Published real-world and standards-based samples. All are synthetic except one real council open-data file, see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) and [sample-data/reference/](sample-data/reference/README.md) |

### Docker

```bash
docker compose up --build
```

The app is then at http://localhost:8080 (nginx serves the UI and proxies `/api` to the
backend). The container files were written for this project but could not be built on the
machine it was developed on, so treat them as untested.

## Configuration

All settings are optional environment variables (see `backend/.env.example`).

| Variable | Default | Meaning |
|---|---|---|
| `SC_MAX_UPLOAD_MB` | 5 | Largest accepted upload |
| `SC_MAX_ROWS` | 5000 | Most transactions in one file |
| `SC_MAX_PDF_PAGES` | 40 | Most pages in one PDF |
| `SC_REVIEW_THRESHOLD` | 0.75 | Confidence below this goes to Needs Review |
| `SC_DEFAULT_CURRENCY` | USD | Used when the file does not say |
| `SC_LARGE_AMOUNT` | 1000 | Rows at or above this get a "large amount" flag |
| `SC_RATE_LIMIT_UPLOADS_PER_MINUTE` | 10 | Uploads per client per minute |
| `SC_RATE_LIMIT_REQUESTS_PER_MINUTE` | 120 | All other requests per client per minute |
| `SC_TRUST_PROXY_HEADERS` | false | Read the client address from `X-Forwarded-For` (only behind a trusted proxy) |
| `SC_CORS_ORIGINS` | `http://localhost:5173` | Comma-separated allowed origins |
| `SC_DATA_DIR` | `var` | Where learned rules are saved |

## API

| Method and path | Purpose |
|---|---|
| `GET /api/health` | Liveness |
| `GET /api/config` | Limits and accepted file extensions |
| `GET /api/categories` | The category list |
| `POST /api/statements` | Upload (`file`, optional `amount_convention`), returns the categorized statement |
| `GET /api/statements/{id}` | Fetch a statement |
| `PATCH /api/statements/{id}/transactions/{txn_id}` | Fix a row, optionally apply to similar rows and save a rule |
| `GET /api/statements/{id}/export.csv` | Download the result |

Interactive docs are at http://localhost:8000/docs. Errors always look like
`{"detail": {"code": "...", "message": "..."}}`, and rate-limited responses are HTTP 429
with a `Retry-After` header.

## Tests

```bash
cd backend
python scripts/fetch_reference_samples.py   # downloads the official camt.053 / MT940 samples
pytest

cd ../frontend
npm test
```

The backend suite checks the brain on unit cases and runs the real-world files in
`sample-data/reference/` through the parsers. Tests that need the downloaded
standards samples skip themselves when those files are absent.

## Project layout

```
backend/app/
  api/         routes and response schemas
  brain/       normalizer, rules (data/merchants.json), classifier, refunds, pipeline
  parsing/     one reader per format plus shared date, amount and table logic
  services/    upload and correction use-cases
  storage/     statement repository and saved user rules
  middleware.py   body-size limit, rate limit, security headers
frontend/src/  React + TypeScript UI
sample-data/   fake demo statements and reference files
```

## Known limits

- Scanned PDFs have no text to read. They are rejected with a message asking for a CSV or
  Excel export (no OCR).
- Statements are kept in memory, so they disappear when the server restarts. Learned rules
  are saved to disk. The storage sits behind a small interface so a database can replace it.
- The built-in categories and rules target one use case. Adding another is a data change
  (`backend/app/brain/categories.py` and `backend/app/brain/data/merchants.json`).
