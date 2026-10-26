# DriveLedger — statement categorizer for gig drivers

DriveLedger sorts a rideshare/delivery driver's bank and credit-card transactions into
US **Schedule C** categories for tax time. You upload a statement, it categorises every
row, it sends anything it is unsure about to **Needs Review**, and it shows totals per
category plus an estimated net profit. When you fix a row it remembers that merchant for
next time.

The decisions come from rule-based code in [`backend/app/brain/`](backend/app/brain/).
**No LLM or ML model is involved.** [DESIGN.md](DESIGN.md) explains how it works, and
[AI_USAGE.md](AI_USAGE.md) explains how AI tools were used to build it.

> All data in this repo is fake. The sample statements in [`samples/`](samples/) were
> written by hand for testing.

## Features

- Upload **CSV, OFX or QFX** exports. It copes with preambles, missing headers, `;` or tab
  delimiters, debit/credit columns, BOMs/Windows encodings, European number formats,
  pending rows, total rows and zero-amount holds.
- Detects the **sign convention** automatically (most banks show spending as negative;
  many card exports show it as positive). You can override it.
- Each decision shows its **confidence and reasons**. Click the status badge.
- **Needs Review** queue with one-click suggestions.
- Handles messy real-world cases: refunds reduce their category and are not counted as
  income. Transfers and card payments are excluded from totals. Fines are not deductible.
  It also flags duplicate rows, statements imported twice, gas-station snack purchases and
  unusually large amounts.
- **Learns from corrections**: when you fix a merchant, that choice applies to its other
  rows now and to future uploads. You can view and delete what it has learned.
- **Export** to CSV with Schedule C lines and a summary block.

## Quick start

Requirements: **Python 3.11+** and **Node 20+**.

### 1. Backend (FastAPI on :8000)

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:create_app --factory --reload --port 8000
```

The API docs are at http://localhost:8000/docs. Data is stored in SQLite at
`backend/data/driveledger.db`, which is created automatically.

### 2. Frontend (React + Vite on :5173)

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The dev server proxies `/api` to the backend. Click
**Checking account (Q1)** or **Credit card (Q1)** to load a fake statement, or upload your
own export.

## Tests and checks

```bash
# backend: 135 tests (parsing, normalisation, the brain, services, HTTP API)
cd backend && pytest && ruff check . && ruff format --check .

# frontend: unit and component tests, typecheck, production build
cd frontend && npm test && npm run typecheck && npm run build
```

CI runs all of these on every push ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)).

## Configuration

The backend reads these environment variables. All of them are optional.

| Variable | Default | Purpose |
| --- | --- | --- |
| `DRIVELEDGER_DB_PATH` | `backend/data/driveledger.db` | SQLite file |
| `DRIVELEDGER_CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Allowed browser origins |
| `DRIVELEDGER_MAX_UPLOAD_MB` | `5` | Upload size limit |
| `DRIVELEDGER_REVIEW_THRESHOLD` | `0.75` | Below this confidence, a row goes to review |
| `DRIVELEDGER_SAMPLES_DIR` | `samples/` | Folder holding the demo statements |

The frontend reads `VITE_API_BASE` (default: same origin) and `VITE_API_PROXY` (the dev
proxy target, default `http://127.0.0.1:8000`).

## Project layout

```
backend/
  app/
    brain/          the decision engine (no AI): categories, normaliser, knowledge base, engine
    ingest/         file reading: CSV/OFX parsing, amounts, dates, sign conventions
    services.py     import, duplicate checks, review, learning, summary, CSV export
    db.py           SQLite schema and connections
    main.py         FastAPI app factory and routes
  tests/            pytest suite
frontend/
  src/
    components/     upload, statement list, summary cards, transaction table, rules
    lib/            formatting and filtering helpers (unit tested)
    api.ts          typed API client
samples/            fake statements for demos and tests
docs/               the original assessment submission guide
```

## API overview

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/api/statements` | Upload a file (`file`, optional `sign_convention`) |
| `GET` | `/api/statements` | List statements |
| `GET` | `/api/statements/{id}` | Statement with transactions and summary |
| `PATCH` | `/api/statements/{id}/transactions/{txId}` | `{category, remember}`. Set or clear a category |
| `GET` | `/api/statements/{id}/export.csv` | CSV export |
| `DELETE` | `/api/statements/{id}` | Delete a statement |
| `GET` / `DELETE` | `/api/rules`, `/api/rules/{direction}/{merchantKey}` | Learned merchant rules |
| `GET` | `/api/categories`, `/api/samples` | Reference data |
| `POST` | `/api/samples/{name}` | Import a bundled fake statement |

*This is not tax advice.*
