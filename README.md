# SortedHisab

**Every rupee, in the right place.** A local statement categorizer for Pakistani freelance software developers whose work and everyday spending share an account.

Upload a statement, verify its columns and direction, review explainable decisions, and export records for your accountant. The classification brain is entirely deterministic Python: no LLM, API key, bank connection, or external classification service.

## Run locally

Prerequisites: Python 3.11+ (tested locally with 3.14), [uv](https://docs.astral.sh/uv/getting-started/installation/), and Node.js 22.12+ (tested with Node 24).

From the repository root:

```sh
uv sync --frozen
npm ci --prefix frontend
npm run build --prefix frontend
uv run uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000**. FastAPI serves the built React app and API on one origin. Choose **Explore a demo** for 36 fictional credit card transactions, or upload a file from `sample_data/`.

For development, start the API as above, then in a second terminal:

```sh
npm run dev --prefix frontend
```

Open http://127.0.0.1:5173. Vite proxies `/api` to port 8000. API documentation: http://127.0.0.1:8000/docs.

No environment variables are required. SQLite is created at `.local/sortedhisab.sqlite3` (gitignored). Set `SORTEDHISAB_DB` to change the path. Data persists across restarts; statements can be removed from the Statements screen. Removing a statement also removes its rows and review history, but retains saved rules.

## Try the complete flow

1. Upload `sample_data/developer-credit-card.csv` and name the account.
2. Confirm day-first dates, currency, and detected debit/credit mappings. Validate all 36 rows, then import.
3. Search for **NAYATEL** and open its row. The category is recognized, but business purpose requires your judgment.
4. Choose **Mixed**, enter **60%** business share, add a note, and save. Of PKR 4,200, PKR 2,520 enters business totals and PKR 1,680 enters personal totals.
5. Review an AI subscription as Business; identify ambiguous transfers from the bank fixture; review refunds with the same purpose as their original expense.
6. See currency-separated category totals and reconciliation in Overview. Export transactions or category totals. Exports retain outstanding review flags.
7. Optionally remember an exact description for that account. It applies on future imports; existing rows are never silently rewritten.

## Supported statements

| File | Support |
| --- | --- |
| CSV | Header row, comma/semicolon/tab delimiter, UTF-8 or Windows-1252; user maps columns |
| XLSX | One sheet with a header row; same mapping workflow; date cells supported |
| PDF | **Only** the supplied text-based `SortedHisab Synthetic Statement v1` table layout |
| Scans, encrypted PDFs, other bank PDF layouts | Not supported; use an unlocked CSV/XLSX export |

This is not a universal Pakistani bank PDF parser. Bank, credit card, wallet, and international accounts share a normalized model, but require valid mappings and explicit amount conventions. Credit card **debit/credit means charge/payment**, not a guess based on account type.

Required columns: Date, Description, and either signed Amount **or** separate nonnegative Debit and Credit. Optional: Currency, Original Amount, Original Currency. Supported currencies: PKR, USD, EUR, GBP, AED; two decimal places. Normalize positive amounts to money out, negative to money in. Never combine currencies or infer an exchange rate.

Dates: ISO `YYYY-MM-DD`, `DD Mon YYYY`, `DD-Mon-YYYY`, or slash/hyphen numeric dates using the selected order. Unsupported formats are surfaced as errors. No automatic year inference.

Limits: 5 MB, 5,000 transaction rows, 40 columns, 30 PDF pages. Every invalid row is reported; imports are atomic and blocked until all errors are fixed. PDF transaction counts must reconcile. Exact-file duplicates are blocked per account; possible overlaps are retained and flagged, never silently deleted.

## Fictional fixtures

- `developer-credit-card.csv`: AI tools, software, hosting, entertainment, groceries, food, household shopping, utilities, transport, education, equipment/installments, healthcare, donations, fees, levies, refunds, repayment, unknown POS.
- `developer-bank.csv`: client receipts, family-recipient transfer, own savings, card repayment, ATM, RAAST, wallet top-up, unknown credit.
- `developer-wallet.csv`: local spending and ambiguous transfers.
- `developer-international.csv`: USD/EUR receipts, service fees, subscriptions, refund and outgoing transfer.
- `developer-statement.xlsx` / `.pdf`: the same 12 synthetic bank transactions.
- `invalid-rows.csv`: errors to demonstrate all-or-nothing validation.

Names, references, amounts, fee rates and descriptions are invented. They do not represent actual bank formats, current provider pricing, exchange rates, or Pakistani tax rules. Rebuild binary fixtures with `uv run python scripts/generate_samples.py`.

## Checks

```sh
uv run pytest -q
uv run ruff check backend scripts
uv run ruff format --check backend scripts
npm run build --prefix frontend
cd frontend
npx playwright install chromium
npm run test:e2e
```

Browser tests start isolated API/Vite servers on ports **8001/5174** and use `.local/e2e.sqlite3`, separate from your normal workspace. They clear only isolated test statements/rules. CI runs the same checks. Playwright uses Chromium; other browsers are not yet covered.

## Product boundaries

This is a single-user local assessment app. Keep the server bound to loopback. It has no hosted authentication, encrypted database, account synchronization, OCR, tax filing, or automated tax eligibility decisions. Upload bytes are processed transiently; normalized rows, original row fields, filenames, review history, and rules are stored locally. No telemetry or runtime AI calls. System fonts avoid a runtime font service.

Refunds with explicit wording reduce category expenses; unknown credits require review. Merchant recognition does not prove business use. Cash withdrawals are movements whose spending purpose is unresolved. Equipment and installments require review; the app does not calculate depreciation or infer original installment principal. Cross-account transfers are not automatically paired, and possible overlap warnings remain included in totals until you remove/correct the source statement.

Read [DESIGN.md](DESIGN.md) for decision order and accounting invariants, [AI_USAGE.md](AI_USAGE.md) for AI assistance and token evidence, and [docs/SUBMISSION.md](docs/SUBMISSION.md) for the original submission instructions.
