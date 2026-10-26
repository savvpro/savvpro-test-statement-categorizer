# Statement Categorizer

[![CI](https://github.com/ahmeddawood9/savvpro-test-statement-categorizer/actions/workflows/ci.yml/badge.svg?branch=candidate-ahmeddawood9)](https://github.com/ahmeddawood9/savvpro-test-statement-categorizer/actions/workflows/ci.yml)

A tax-time statement categorizer for a **freelance software developer in Pakistan**. You upload a
CSV statement from a business credit card or bank account. The app reads every row, gives it a
category, a kind (expense, income, transfer, refund, fee, tax), a confidence and a reason, and
sends anything it is not sure about to **Needs Review**. You fix those rows, see totals per
category and per currency, and download the categorized CSV.

The categorization is plain rule-based Python driven by a YAML file. No AI model decides anything.
How the rules are ordered, and why, is in [DESIGN.md](DESIGN.md).

## Prerequisites

- [uv](https://docs.astral.sh/uv/) for the backend. It installs Python **3.12** for you (the
  project needs 3.12.x), so the first run needs internet access.
- Node **22.12 or newer** and npm for the frontend. Node 20 is not enough for the test runner.
- Free ports **8000** (backend) and **5173** (frontend).
- Tested on Linux (uv 0.12, Node 26). The CI workflow uses Node 22.

## Run the backend

Run these **from the `backend/` folder**. Starting the app from the repository root fails with
`No module named 'app'`.

```bash
cd backend
uv sync
uv run uvicorn app.main:app --port 8000
```

The first start creates the SQLite database at `backend/data/app.db`. Check it with
`curl localhost:8000/health`. Interactive API docs are at http://localhost:8000/docs.

## Run the frontend

In a second terminal, with the backend already running:

```bash
cd frontend
npm ci
npm run dev
```

Open http://localhost:5173. In development Vite forwards `/api` and `/health` to port 8000, so no
CORS setup is needed.

## Try it

The files in `sample_data/` are fictional. With an empty database:

| File | What you should see |
|---|---|
| `bank_a_card.csv` | 31 rows, 4 need review |
| `bank_b_checking.csv` | 25 rows, 5 need review |
| `messy_statement.csv` | 10 rows, 4 lines that could not be read, 1 blank line skipped, 2 need review |

1. Upload `bank_a_card.csv`. Review rows are highlighted.
2. Click **Fix** on `XYZ TRADERS`, pick a category, tick **Remember for this merchant** and save.
   Other rows and later uploads with the same merchant use your choice.
3. Upload `messy_statement.csv` and look at the rows it could not read, with the reason for each.
4. Check the summary (PKR and USD are totalled separately) and click **Download categorized CSV**.

`sample_data/expected_labels.csv` holds the correct answer for every sample row. A test compares the
app's output with it. `sample_data/README.md` explains each file.

## Tests and checks

```bash
cd backend && uv run pytest && uv run ruff check
cd frontend && npm test && npm run lint && npm run build
```

The same commands run in GitHub Actions on every push and pull request
(`.github/workflows/ci.yml`).

## Configuration

Settings come from environment variables. Copy the `.env.example` in each folder to `.env` to
override a default. Never commit a real `.env`.

| Variable | Where | Default | Meaning |
|---|---|---|---|
| `DATABASE_URL` | backend | `sqlite:///./data/app.db` | Database. A relative path is relative to the folder you start the backend from |
| `CORS_ORIGINS` | backend | `http://localhost:5173` | Allowed browser origins, comma-separated |
| `MAX_UPLOAD_MB` | backend | `5` | Largest file accepted |
| `VITE_API_URL` | frontend | empty | API address. Leave empty in development; set it only if the API is on another origin |

## Reset the data

Stop the backend, delete `backend/data/app.db`, and start it again. The tables are recreated empty.

## Project layout

```
backend/
  app/
    main.py        app start-up: loads and checks rules.yaml, creates tables, CORS
    api/           HTTP routes (statements, transactions, categories)
    services/      the logic behind the routes: ingest, corrections, summary, export
    ingest/        the two CSV layouts, the parser, amount parsing
    brain/         normalizer, classifier, duplicate check, rules.yaml
    core/          settings, categories and kinds (domain.py), money conversion
    db.py  models.py  schemas.py
  tests/
frontend/
  src/             App.tsx, components/, api/client.ts (typed API calls), tests
sample_data/       fictional statements and expected_labels.csv
docs/              SUBMISSION_GUIDE.md, ai-usage/
.github/workflows/ci.yml
```

**The rules** are in `backend/app/brain/rules.yaml`, in four sections tried in this order:
`structural` (fees, card payments, transfers, tax, refunds), `merchants`, `review` (always send to
review) and `keywords` (lower confidence). The file's header explains every field. To add a rule,
add an entry to the right section, for example:

```yaml
  - id: linear
    match:
      contains: "LINEAR"
    category: Software & Subscriptions
    direction: out
    reason: "Linear subscription"
```

Then restart the backend and run `uv run pytest`. A mistake in the file (unknown field, bad
category, duplicate id) stops the app at start-up with a message naming the rule. The list of
categories is in `backend/app/core/domain.py`.

## Limits and troubleshooting

- **CSV only**, in one of two layouts (the header row decides which). Card: `Date,Description,
  Amount,Currency` with dates as `YYYY-MM-DD` and a signed amount. Bank: `Txn Date,Details,Debit,
  Credit,Balance` with dates as `DD/MM/YYYY`. Anything else is rejected with a message that lists
  the supported formats.
- Files must end in `.csv` and be at most 5 MB. There is no paging, so a file with tens of
  thousands of rows loads slowly. Real statements are far smaller.
- Currencies are totalled separately and never converted. Amounts are assumed to have two
  decimals. There is no login: one local user.
- Refunds are shown next to expenses and are not subtracted from them.
- Some short words in `rules.yaml` match more than intended, and not every rule has a test. Details
  are in [DESIGN.md](DESIGN.md).
- `No module named 'app'`: you started the backend outside `backend/`.
- The page says "Cannot reach the server": the backend is not running on port 8000.
- `npm ci` or the tests fail on an old Node: use 22.12 or newer.
- A port is already in use: stop whatever is on 8000 or 5173.

## More documents

- [DESIGN.md](DESIGN.md): the use case, how the rules decide, the data and API, the limits.
- [AI_USAGE.md](AI_USAGE.md): the AI tools used, how they helped, where they were wrong, and the token logs.
- [docs/ai-usage/log.md](docs/ai-usage/log.md): the running log that feeds AI_USAGE.md.
- [docs/SUBMISSION_GUIDE.md](docs/SUBMISSION_GUIDE.md): the fork-and-submit instructions this repository started with.
