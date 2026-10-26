# Design Document — Statement Categorizer

## Use case

A freelance developer/designer uploads a business credit card statement (CSV)
and needs every transaction categorized for tax time. The app:

1. Parses the CSV (messy real-world formats).
2. Categorizes each transaction with a deterministic, rule-based brain.
3. Flags uncertain transactions as "Needs Review" (a wrong guess is worse
   than asking).
4. Lets the user fix rows and persists merchant overrides for future uploads.
5. Shows per-category totals (Transfer excluded from spending; Refunds shown
   as negative spend).

Target user: freelance web designer / developer who puts business expenses on
a credit card and needs tax-ready categories at year-end.

## Categories

| Category | Notes |
|----------|-------|
| Software | SaaS, dev tools, cloud (Adobe, GitHub, Figma, AWS, etc.) |
| Travel | Airlines, hotels, rideshare (Uber, Lyft, Delta, Hilton, etc.) |
| Meals | Restaurants, cafes (Starbucks, Chipotle, McDonalds, etc.) |
| Office Supplies | Staples, Office Depot, Home Depot |
| Marketing | Ad platforms (Google Ads, Meta Ads, LinkedIn Ads) |
| Utilities | Internet, phone, power (Comcast, Verizon, Duke Energy) |
| Subscriptions | Streaming, media (Netflix, Spotify, Hulu, Disney+, etc.) |
| Income | Money coming in (invoice deposits, payroll) |
| Refund | Money back from a merchant — not income |
| Transfer | Internal transfers / card payments — excluded from spending totals |
| Needs Review | Brain couldn't confidently categorize |

## Brain pipeline

The categorization brain is **100% deterministic Python code**. No LLM/AI API
is used for category decisions.

Pipeline (in order):

### 1. Normalize
- Uppercase
- Strip noisy prefixes: `SQ *`, `TST*`, `AMZN MKTP US*`, `POS`, `PURCHASE`,
  `PAYPAL *`
- Strip trailing store/reference numbers (e.g. `#1234`, 6+ digit runs)
- Collapse whitespace

### 2. User overrides
If the normalized merchant has a saved override, apply it with confidence
1.0 and reason "user correction". Overrides persist across uploads
(in-memory store).

### 3. Structural rules
- **Transfer**: `TRANSFER TO/FROM`, `PAYMENT THANK YOU`, `AUTOPAY`,
  `CARD PAYMENT` → category "Transfer" (excluded from spending totals).
- **Refund**: positive amount + (`REFUND`/`REVERSAL` keyword OR known
  merchant name) → category "Refund", reason mentions the merchant. Refunds
  are NOT income.
- **Income**: positive amount + (`INVOICE`/`PAYROLL`/`DEPOSIT`/`CLIENT`
  keyword) → category "Income".

### 4. Merchant rules (from `config/rules.yaml`)
- Exact match → confidence ~0.95
- Keyword/contains match → confidence ~0.80

52 merchants are defined across 10 spending/income categories.

### 5. Ambiguity → "Needs Review"
- Best confidence < 0.70
- Top-2 confidence gap < 0.10 (close match between two categories)
- No merchant rule matches
- Description is blank
- Description contains inherently ambiguous merchant: AMAZON, AMZN, PAYPAL
  (unless a user override exists)

All thresholds and weights are constants in
`backend/app/brain/constants.py` — no magic numbers scattered in the code.

## Confidence logic

| Source | Confidence |
|----------|-----------|
| User override | 1.00 |
| Structural rule | 0.98 |
| Exact merchant match | 0.95 |
| Keyword merchant match | 0.80 |
| Ambiguous / no match | 0.00 (Needs Review) |

Thresholds:
- `CONFIDENCE_MIN = 0.70` — below this → Needs Review
- `CONFIDENCE_GAP_MAX = 0.10` — top-2 gap smaller → Needs Review

## Edge cases handled

| Edge case | Handling |
|-----------|----------|
| Single Amount column vs Debit/Credit columns | Both supported, auto-detected from headers |
| Header name variants | Date/Posting Date/Transaction Date, Description/Details/Memo, Debit/Credit variants |
| Date formats | YYYY-MM-DD and MM/DD/YYYY |
| Amount formats | `$1,234.50`, `(45.00)`, `-45.00`, empty cells |
| Duplicate rows | Flagged with `is_duplicate=true`, not silently dropped |
| Blank descriptions | Warned, categorized as Needs Review |
| Foreign currency lines | Warned, categorized as Needs Review |
| Malformed rows | Skipped with warning, app does not crash |
| Sign convention | Spending normalized to negative, money in to positive |
| Empty file / missing columns | Clear error messages via HTTP 400 |

## File size & type validation

- Only `.csv` files accepted
- Maximum 10 MB
- Clear error messages for invalid type, empty file, or oversized file

## State management

In-memory only (no database). A global `TransactionStore` holds transactions
and overrides in dicts. Suitable for a single-user take-home app.

**Production choice: PostgreSQL.** Rationale:
- Persistence across server restarts (in-memory is lost on restart)
- Concurrent access safety
- Query performance for large statements
- ACID transactions for update + override persistence

This is documented as a limitation; the code is structured so the store layer
could be swapped for a Postgres-backed repository without changing the API or
brain.

## API design

- `POST /api/upload` — multipart CSV → transactions + summary + warnings
- `PATCH /api/transactions/{id}` — `{category}` → updated row + summary
  (also stores merchant override)
- `GET /api/summary` — per-category totals, spending total, needs review total
- `GET /api/export` — CSV download

CORS enabled for Vite dev server (`http://localhost:5173`).

## Tech stack

- **Backend:** Python 3.11+, FastAPI, Pydantic v2, pytest, ruff, PyYAML
- **Frontend:** React + Vite + TypeScript, plain CSS (no UI library)
- **State:** in-memory (no DB)
- **Tests:** 103 tests (34 parser + 43 brain + 5 overrides + 11 API)

## Limitations

1. In-memory state is lost on server restart — use Postgres in production.
2. Override store is thread-unsafe (single-user app assumption).
3. No persistent storage of upload history — each upload replaces the previous
   data.
4. Date parsing limited to ISO and US formats; DD/MM/YYYY not supported
   (ambiguous).
5. Merchant rules are static YAML — no learning from user corrections beyond
   the override store.

