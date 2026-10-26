# Statement Categorizer

A Python / Next.js app for freelance designers sorting USD bank and credit card
transactions for bookkeeping. The categorization engine uses Python rules only;
no AI service receives statement data or decides categories.

## Run locally

Requires Python 3.12+ and Node.js 22+.

```powershell
python -m venv .venv
.venv/Scripts/Activate.ps1
python -m pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000
```

On macOS/Linux, activate with `source .venv/bin/activate` instead.
In a second terminal:

```sh
cd frontend
npm ci
npm run dev
```

Open http://localhost:3000. Select **Load Sample Freelancer Statement** or upload
`data/sample_statement.csv`. All included records are synthetic.
API documentation is available at http://localhost:8000/docs.

To use a different backend, set `NEXT_PUBLIC_API_URL` in `frontend/.env.local`
before starting/building the frontend. The backend accepts a comma-separated
`CORS_ORIGINS` environment variable; the default allows localhost:3000 and
127.0.0.1:3000.

## Workflow

1. Upload a CSV (maximum 5 MB) or load the sample.
2. Inspect the category, transaction type, confidence, explanation and rule ID.
3. Filter **Needs Review**. Choose a category and the correct accounting type,
   then approve any flagged classifications you have verified.
4. Export the full ledger, including corrections and audit information.
   Unresolved statements export as **Draft CSV**.

Edits update the ledger and totals together after the API succeeds. Failed saves
show an error and preserve the last saved state. Changes live in browser memory;
refreshing or opening a new statement loses them. Export before leaving.

## CSV format

Required headers are `Date,Description,Amount` (case insensitive). Extra named
columns are ignored. Duplicate headers are rejected. Rows with missing values,
extra cells, invalid dates or invalid amounts are skipped with visible notices.
If no valid rows remain, the import is rejected.

```csv
Date,Description,Amount
2024-01-03,CLIENT PAYMENT - DESIGN PROJECT,1500.00
2024-01-05,ADOBE CREATIVE CLOUD,-54.99
2024-01-08,TRANSFER TO SAVINGS,-500.00
2024-01-10,JOES CAFE 9921,-18.40
2024-01-16,REFUND - ADOBE CREATIVE CLOUD,54.99
```

Positive amounts mean money in; negative amounts mean money out. Convert bank
exports that use a different sign convention before uploading. Quote amounts or
descriptions containing commas. Dollar signs and thousands separators are
accepted. Amounts must be finite, within +/-999999999999.99, with at most two
fractional decimal places. Calculations use Decimal.

Use ISO dates (`YYYY-MM-DD`) for certainty. Month/day/year and day/month/year
forms are also accepted; ambiguous dates default to month/day with a warning.
UTF-8 with an optional BOM is preferred; Latin-1 fallback produces a notice.

## Accounting behavior

- Known merchants receive categories through ordered, direction-aware rules.
- Unknown merchants and generic P2P payments require review.
- Transfers do not affect operating results.
- Possible duplicates remain visible; both are held out of operating totals
  until reviewed. Approve both only if both charges actually occurred.
- Recognized positive merchant refunds reduce their expense category. Unknown
  refunds stay in review. A purchase link is optional and requires a unique
  same-merchant, same-amount purchase dated on or before the refund.
- All unresolved rows are excluded from operating totals. Their absolute dollar
  volume remains visible and the result is provisional. An unknown category or
  a direction inconsistent with the transaction type cannot finalize a result.
- Refunds can exceed purchases in the imported period, producing negative net
  expense totals. Category totals are independent of statement row order.
- CSV export protects text fields against spreadsheet formula interpretation.

## Verification

```sh
python -m pytest -q
cd frontend
npm run lint
npm run build
```

GitHub Actions runs these checks on pushes and pull requests. Backend tests cover
CSV validation, rule precedence, directions, refund linking, duplicate review,
summary calculations and API corrections. Frontend verification covers lint,
TypeScript and production compilation; there is no browser automation suite.

## Project layout

- `backend/`: FastAPI endpoints, models, parser, rules, categorizer and summaries
- `frontend/src/`: Next.js dashboard, API client and CSV export
- `tests/`: backend unit and API integration tests
- `data/sample_statement.csv`: synthetic sample statement
- `DESIGN.md`: use case, decisions and limitations
- `AI_USAGE.md`: AI assistance and available usage evidence

This version supports CSV and one assumed USD account per upload. It does not
read PDFs, persist records, learn merchant rules or calculate tax deductions.
Merchant rules are bookkeeping suggestions based on the assumption that this is
a business account; the user must verify personal/mixed purchases. Transfers are
inferred from description patterns rather than verified account ownership.

## Assessment submission

Use a fork and branch `candidate-<your-github-username>`. Push that branch and open
a PR to `savvpro/savvpro-test-statement-categorizer:main` titled
`feat: complete statement-categorizer assessment`. See `TASK.md` for the original
requirements. Its deadline must be confirmed separately; no date is specified.
