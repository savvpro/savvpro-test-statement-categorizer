# Statement Categorizer

Statement Categorizer is for **UK freelancers and sole traders**. You upload a business bank or card statement and the app does four things:

- Sorts every transaction into HMRC Self Assessment (SA103) categories
- Explains each decision
- Sends anything uncertain to **Needs Review**, rather than guessing
- Turns the reviewed result into a tax estimate

Categorization is done by a deterministic rule engine written for this project. No AI model is called at runtime. See [DESIGN.md](DESIGN.md) for the use case, the architecture and how the engine decides, and [AI_USAGE.md](AI_USAGE.md) for development tooling.

## Features

**Categorization**
- **Explained decisions:** every row gets a category, a confidence score and a plain-English reason.
- **Review when unsure:** unknown merchants, conflicting signals, weak matches, mixed-use shops (Amazon, PayPal) and unexplained money in all go to Needs Review, with a suggested category where one exists.
- **Messy-data handling:**
  - refunds are matched to the original purchase and net it off (never counted as income)
  - transfers and card repayments are excluded
  - duplicate rows are flagged
  - HMRC payments are kept apart from expenses
  - large purchases are flagged as possible capital assets

**Reviewing**
- **One-click fixes:** use the suggested category, or apply a fix to every row from the same merchant.
- **Learns from corrections:** "Always use this for <merchant>" saves a rule. Saved rules apply to every future upload and can be managed in the UI.
- **Search and filtering:** search the table, filter by category (click a total card) or show only rows that need review. A progress bar tracks the review.
- **Recurring payments:** monthly subscriptions are detected and flagged.
- **Export:** a categorized CSV with reasons. Export is unlocked once nothing is left to review.

**Tax**
- **Self Assessment estimate (2025/26):** shows profit, income tax and Class 4 NIC, and how much to set aside. It applies the £1,000 trading allowance automatically when that beats actual expenses, and tapers the personal allowance for income over £100,000.

## Quick start

### Option 1: Docker

```bash
docker compose up --build
```

Open http://localhost:8080.

### Option 2: Local development

Requirements: Python 3.9+ and Node 18+.

```bash
make install    # creates backend/.venv and installs frontend packages
make backend    # API on http://localhost:8000 (docs at /docs)
make frontend   # UI on http://localhost:5173, proxies /api to the backend
```

To try it, upload [`samples/freelancer_statement.csv`](samples/freelancer_statement.csv). All of its data is fake.

### Tests

```bash
make test
```

The test suite covers the CSV reader, every classifier, refunds, duplicates, recurring detection, learned rules, tax calculations, the repository and the API end to end. CI runs the backend tests and the frontend build on every push (`.github/workflows/ci.yml`).

## Project structure

```
backend/app/
  main.py               app factory: wires settings, adapters and services together
  config.py             environment-driven settings
  api/                  HTTP routes and request/response schemas (thin layer)
  services/             use cases: categorize a statement, manage merchant rules
  domain/               models, categories, domain errors
  ingestion/            StatementReader interface, ReaderRegistry, CSV reader
  categorization/       normalizer, rulebook, classifier chain, confidence policy,
                        post-processors, engine, factory (composition root)
  learning/             merchant-rule repository (in-memory and JSON file)
  reporting/            category totals, Self Assessment estimate
  data/rules.json       merchant and keyword knowledge (edit without code changes)
backend/tests/          pytest suite
frontend/src/
  components/           UI components
  hooks/                useStatement (state and actions), useTaxEstimate
  lib/                  API client, formatting, CSV export
samples/                fake statement for demos
```

## Supported statement format

The app reads CSV files with a header row and accepts common bank variants:

- **Columns:** `Date` or `Transaction Date`; `Description`, `Details` or `Narrative`; either one signed `Amount` column or separate `Money Out` / `Money In` (`Debit` / `Credit`) columns
- **Dates:** `2026-03-01`, `01/03/2026`, `01/03/26`, `1 Mar 2026`
- **Amounts:** `£1,234.50`, `(12.00)`, `12.00 DR`, `12.00 CR`
- **Encodings:** UTF-8 (with or without BOM) and Latin-1

Unreadable rows are listed in the UI and don't stop the rest of the file from being processed.

## API

| Method | Path                  | Purpose                                     |
|--------|-----------------------|---------------------------------------------|
| GET    | `/api/health`         | Liveness check                              |
| GET    | `/api/categories`     | Available categories                        |
| POST   | `/api/categorize`     | Upload a statement (multipart `file`)       |
| POST   | `/api/tax-estimate`   | Estimate tax from categorized rows          |
| GET    | `/api/rules`          | List saved merchant rules                   |
| PUT    | `/api/rules`          | Save a rule (`{merchant, category}`)        |
| DELETE | `/api/rules/{merchant}` | Remove a rule                             |

Interactive docs are at `http://localhost:8000/docs`.

## Configuration

All configuration is through environment variables. Defaults are in `backend/app/config.py`.

| Variable               | Default                          | Purpose                                   |
|------------------------|----------------------------------|-------------------------------------------|
| `CORS_ORIGINS`         | `http://localhost:5173`          | Allowed frontend origins (comma-separated) |
| `MAX_UPLOAD_BYTES`     | `5242880`                        | Upload size limit                         |
| `MAX_ROWS`             | `10000`                          | Row limit per statement                   |
| `CONFIDENCE_THRESHOLD` | `0.7`                            | Below this score, rows go to review       |
| `AMBIGUITY_MARGIN`     | `0.2`                            | Minimum score gap between the top two categories |
| `LARGE_AMOUNT`         | `1000`                           | Threshold for the capital-asset flag      |
| `RULES_STORE_PATH`     | `backend/var/merchant_rules.json` | Where learned rules are stored           |

The repo contains no secrets, and all data in it is fake.
