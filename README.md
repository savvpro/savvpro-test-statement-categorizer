# Statement Categorizer

Sorts a **business credit-card statement for tax time** — built for a freelance
designer. Upload a CSV statement, every transaction gets a category and a
confidence score, and anything the code is unsure about goes to **Needs Review**
instead of being guessed.

> **The one big rule, honored:** the categorization "brain" is 100% deterministic
> rule code (`backend/app/brain/`). No GPT/Claude/Gemini — no AI model anywhere in
> the decision path. AI tools were used only to help *write* the code (see
> [AI_USAGE.md](AI_USAGE.md)).

## How it works

```
Upload statement → Read transactions → The brain → Category for each row → User reviews the result
      (CSV parse)      (normalizer)    (rules +        (per row, with          (fix dropdowns,
                                        confidence)     reasons shown)          totals update live)
```

Special flows the brain handles (the messy parts):

- **Transfers** (`TRANSFER TO SAVINGS`, `CREDIT CARD PAYMENT`) — moving your own
  money is not spending, excluded from totals
- **Refunds** — money back is not income; where possible the refund is linked to
  the original expense category (`REFUND - STARBUCKS` → offsets Meals & Coffee)
- **Income vs. unknown credits** — a `STRIPE PAYOUT` is income, but an
  unidentified credit is *asked about*, never silently called income
- **Duplicates** — same date + amount + merchant is flagged, not merged
- **Unreadable rows** — bad dates / missing amounts survive the upload and go to
  Needs Review with a human-readable reason

## Tech

| Layer     | Choice                                       |
| --------- | -------------------------------------------- |
| Backend   | Python 3.12 · FastAPI · Pydantic v2          |
| Brain     | Own rule engine (`backend/app/brain/`)       |
| Frontend  | React 18 + Vite (plain CSS, no UI framework) |
| Tests     | pytest (52 tests: brain, parser, API)        |
| Deploy    | Single process: FastAPI serves the built SPA |

## Run it

### 1. Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend (dev mode, second terminal)

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173, proxies /api to :8000
```

### Production-ish mode (one process)

```bash
cd frontend && npm install && npm run build
cd ../backend && uvicorn app.main:app --port 8000   # serves frontend/dist too
# open http://localhost:8000
```

### Docker

```bash
docker compose up --build     # builds frontend, serves everything on :8000
```

## Try it

Sample statements (all fake data) live in
`backend/app/data/samples/`:

- `sample_statement_designer.csv` — the happy path + all special flows
- `sample_statement_messy.csv` — duplicates, unreadable dates, missing amounts,
  parentheses amounts, a summary row, mixed formatting

## Tests

```bash
cd backend && python3 -m pytest tests -v
```

- `tests/test_engine.py` — the brain: rules, confidence bands, refund vs income,
  transfers, duplicates, summary math
- `tests/test_parser.py` — column variants (Debit/Credit, Type, signed amounts),
  furniture rows, error handling
- `tests/test_api.py` — end-to-end uploads, rejections, audit-readiness

## API

| Endpoint             | Method | Purpose                                  |
| -------------------- | ------ | ---------------------------------------- |
| `/api/categorize`    | POST   | multipart CSV upload → categorized JSON  |
| `/api/health`        | GET    | liveness + active rules version          |
| `/api/categories`    | GET    | current category list (from rules.json)  |
| `/api/rules-info`    | GET    | rule-set metadata                        |

## Configuration

Categories, keywords and weights live in
[`backend/app/data/rules.json`](backend/app/data/rules.json) — data, not code.
Add a category or retune a weight without touching the engine. Thresholds and
paths are in [`backend/app/config.py`](backend/app/config.py).

## Repo map

```
backend/
  app/
    api.py            # HTTP layer (upload -> JSON)
    config.py         # thresholds, paths, bucket names
    models.py         # Pydantic schemas (audit fields on every row)
    brain/
      normalizer.py   # "SQ *JOES CAFE, 9921" -> "joes cafe"
      rules.py        # loads + validates rules.json
      engine.py       # THE BRAIN: decide + score one transaction
      rules.json      # categories, keywords, weights (data, not code)
    parser/
      statement_parser.py  # lenient CSV reader (variants, bad rows)
    data/samples/     # fake statements
  tests/              # 52 pytest cases
frontend/
  src/
    App.jsx           # state + live totals recompute
    components/       # UploadZone, SummaryCards, ReviewQueue, TransactionTable
    export.js         # client-side categorized-CSV download
```

