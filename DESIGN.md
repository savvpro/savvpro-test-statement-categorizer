# Design

## 1. Use case

**Persona:** Sam, a solo freelance designer and developer in the US. Sam files Schedule C, has
one business checking account and one business credit card, and gets paid by clients through
ACH, Stripe and Upwork. A few times a year Sam (or Sam's accountant) has to turn a pile of
statement exports into "how much did I spend on software, travel, meals...?".

**The job:** upload a statement export and get each row sorted into a Schedule C category.
The app is confident where it can be and asks about the rest. Fix those rows once, and the fix
is remembered. Finally, read the totals and the estimated deductible, and export a clean CSV
for the accountant.

**Why this scope:**
- A freelancer's statements mix business, personal and non-operating money (card payments,
  transfers, estimated tax). That is exactly where a naive "every outflow is an expense"
  categorizer gives wrong totals.
- Schedule C gives a real, fixed target taxonomy with known lines and a known 50% meals rule,
  so "correct" is well defined.
- Checking and credit card exports differ in sign convention and layout. Supporting both
  forces the parser to be robust instead of tuned to one file.

Out of scope on purpose: PDF statements, multi-currency, payroll and inventory, and
multi-user accounts (see [Trade-offs](#10-trade-offs) and [Future work](#11-future-work)).

## 2. Category taxonomy

Defined in `backend/app/brain/data/categories.yaml` and validated on load: unique ids, known
kinds, `deductible_pct` between 0 and 100, and nothing but expenses deductible.
`non_operating` means money that moves but is neither business income nor a business expense.

| id | Label | Kind | Schedule C line | Deductible |
|---|---|---|---|---|
| `software_subscriptions` | Software & Subscriptions | expense | Line 18 - Office expense | 100% |
| `hosting_cloud` | Hosting & Cloud | expense | Line 27a - Other expenses | 100% |
| `equipment` | Equipment | expense | Line 13 - Depreciation and section 179 | 100% |
| `office_supplies` | Office Supplies | expense | Line 22 - Supplies | 100% |
| `advertising_marketing` | Advertising & Marketing | expense | Line 8 - Advertising | 100% |
| `contract_labor` | Contract Labor | expense | Line 11 - Contract labor | 100% |
| `professional_services` | Legal & Professional Services | expense | Line 17 - Legal and professional services | 100% |
| `education_training` | Education & Training | expense | Line 27a - Other expenses | 100% |
| `phone_internet` | Phone & Internet | expense | Line 25 - Utilities | 100% |
| `travel` | Travel | expense | Line 24a - Travel | 100% |
| `meals` | Business Meals | expense | Line 24b - Deductible meals | 50% |
| `coworking_rent` | Coworking & Rent | expense | Line 20b - Rent or lease (other business property) | 100% |
| `insurance_business` | Business Insurance | expense | Line 15 - Insurance (other than health) | 100% |
| `bank_fees` | Bank & Card Fees | expense | Line 27a - Other expenses | 100% |
| `platform_fees` | Platform & Payment Fees | expense | Line 10 - Commissions and fees | 100% |
| `taxes_licenses` | Taxes & Licenses | expense | Line 23 - Taxes and licenses | 100% |
| `postage_shipping` | Postage & Shipping | expense | Line 27a - Other expenses | 100% |
| `client_income` | Client Income | income | Line 1 - Gross receipts or sales | 0% |
| `interest_income` | Interest Income | income | - | 0% |
| `transfer` | Transfer | non_operating | - | 0% |
| `card_payment` | Credit Card Payment | non_operating | - | 0% |
| `refund` | Refund | non_operating | - | 0% |
| `owner_draw` | Owner Draw | non_operating | - | 0% |
| `tax_payment` | Estimated Tax Payment | non_operating | - | 0% |
| `personal` | Personal | non_operating | - | 0% |
| `needs_review` | Needs Review | review | - | 0% |

## 3. The brain

The brain lives in `backend/app/brain/`. It is pure Python: no DB, no web framework, no
network and no AI model. A test imports it in a subprocess and asserts that no SQLAlchemy or
FastAPI module was loaded. Input: parsed rows (`amount > 0` is money in, `< 0` is money
out) plus the user's learned rules. Output: one `Decision` per row with a category,
confidence, status, reasons, suggested category, `merchant_key`, `rule_id` and flags. The
same input always gives the same output (tested).

### 3.1 Pipeline

1. **Normalize** the description to a `merchant_key` (`normalizer.py`). This uppercases
   the text, strips stacked processor prefixes (`SQ *`, `TST*`, `PAYPAL *`, `POS`,
   `PURCHASE AUTHORIZED ON 01/02`, ...) and removes masked card numbers, phone numbers,
   dates, `#123` store numbers and reference ids. Domains are reduced to their name
   (`NETFLIX.COM` becomes `NETFLIX`), and a trailing `CITY ST` is dropped. For example,
   `SQ *JOES CAFE 9921` becomes `JOES CAFE`. The raw text is kept for display and for
   patterns that need it (`UBER *EATS` vs `UBER *TRIP`).
2. **Signals** each propose zero or more `Candidate(category, score, reason, source)`:

   | Source | Score | Example |
   |---|---|---|
   | user rule (learned from a correction) | 0.99 | `JOES CAFE` → meals |
   | structural rule | 0.95 | `TRANSFER TO SAVINGS` → transfer, `PAYMENT THANK YOU` → card_payment, `IRS USATAXPYMT` → tax_payment, refund wording → refund |
   | merchant dictionary (exact or longest whole-word prefix, ~85 entries) | 0.92 | `ADOBE` → software_subscriptions |
   | regex pattern | 0.85 | `UBER *TRIP` → travel, `UBER *EATS` → meals, `STRIPE TRANSFER` → client_income |
   | fuzzy merchant (rapidfuzz) | 0.70 to 0.80, scaled by similarity | `ADOBE CREATIV CLD` → software (suggestion only) |
   | keyword | 0.60 | `CAFE`, `BISTRO` → meals |

   Structural and pattern rules can be restricted to one direction (`in` or `out`) and one
   account type. For example, `card_payment_received` only fires for money in on a credit
   card.
   Fuzzy matching runs only when there is no dictionary hit. It needs `token_set_ratio >= 90`
   **and** a plain `ratio >= 80` and a key of at least 5 characters, because
   `token_set_ratio` alone scores a subset as 100 ("BEST" vs "BEST BUY").
3. **Direction check.** A candidate whose category cannot fit the money direction is dropped
   and the drop is noted in the reasons. Money in can never be an expense, money out can never
   be income, `refund` must be money in, and `tax_payment` and `owner_draw` must be money
   out. So a credit from Adobe is not "software", and a user rule cannot force a deposit into
   an expense category.
4. **Aggregate.** Each category keeps its best score. When two or more *different* sources
   agree, it gets +0.03. Ties are broken by category id, so ordering is deterministic.
5. **Recurring boost.** When the same merchant and amount appear in two or more different
   months, and the top category is an expense, it gets +0.05 ("recurring: same amount in 3
   months").
6. **Ambiguity override** (next section).
7. **Decide**, with thresholds in `engine.Thresholds`:
   - **auto** when `top >= 0.80` **and** `top - second >= 0.15`
   - otherwise **needs_review**, with a reason: `no match: ...`, `conflict: X vs Y` or
     `low confidence: best guess X (fuzzy)`, and the best guess as the suggestion.
8. **Post-processing over the whole statement:** duplicate detection, refund linking and
   pending flags (see [section 5](#5-messy-cases)).

What this means for each source on its own:
- A dictionary merchant (0.92), a structural rule (0.95) or a learned rule (0.99) clears the
  bar.
- A pattern (0.85) clears it only when nothing else competes within 0.15.
- Fuzzy (at most 0.80) and keyword (0.60) matches can only ever *suggest*.

### 3.2 Why "a wrong guess is worse than asking"

A wrong auto category is silent: it lands in a total, nobody looks at it, and the deduction
is either lost or overstated. A row in Needs Review costs the user a few seconds and is
remembered afterwards. So the thresholds are chosen for **precision of auto rows**, not
coverage:
- The 0.15 margin sends close calls to review even when the top score is high.
- Weak evidence (fuzzy, keyword) never auto-assigns.
- Unknown merchants always go to review.

The evaluation (section 8) enforces auto-precision of at least 97% with zero income/expense
flips. It also caps the review rate at 35%, so the system cannot buy precision by asking about
everything.

### 3.3 Ambiguous merchant policy

Some merchants cannot be categorized from the description alone. They are listed in
`ambiguous.yaml`, each with a reason and an optional suggestion:

| Rule | Matches | Why it needs a human | Suggests |
|---|---|---|---|
| amazon | AMAZON, AMZN (but not AWS / Amazon Web Services) | Amazon sells everything; check the order | best guess |
| big_box | WALMART, TARGET, COSTCO | mixed-use store | best guess |
| p2p | VENMO, ZELLE, CASH APP | could be a contractor, a client or personal | best guess |
| paypal_non_fee | PAYPAL (not a fee) | PayPal hides the real merchant or payer | best guess |
| apple_bill | APPLE.COM/BILL | App Store charges are often personal | best guess |
| atm | ATM withdrawals | cash: what was it spent on? | owner_draw |
| check | CHECK #1043 | a paper check does not say who it paid | best guess |
| generic_deposit | a deposit without a payer or invoice reference | deposit without a payer or invoice | client_income |
| chargeback | DISPUTE, CHARGEBACK | confirm whether the original charge was reversed | refund |

An ambiguous row always goes to review, with the reason and suggestion shown. There is one
exception: a user rule or a structural rule (for example `AMAZON ... REFUND` matched by
refund wording) is strong enough to settle it. Chargebacks are marked `always` and go to
review even then.

## 4. The learning loop

1. The user picks a category for a row. It becomes `user_confirmed` with confidence 1.0 and
   the reason "set by user".
2. If **remember** is ticked, a `MerchantRule(merchant_key → category)` is created or
   updated.
3. Every *non-confirmed* row with that `merchant_key`, across **all** statements, is
   re-categorized. The brain is re-run over each affected statement as a whole, so context
   signals still apply (recurring, refunds, duplicates), and only the target rows are
   written. The API returns how many rows changed, and the UI shows "Updated N other
   transactions".
4. Future uploads load all rules as user-rule signals (0.99). Each rule counts its hits: rows
   it actually auto-assigned.

Learned rules are still subject to the direction check and to duplicate detection. A
remembered "meals" rule will not hide a same-day duplicate or turn a refund into an expense.
Rows the user already confirmed by hand are never overwritten. Deleting a rule stops future
use; rows it already changed keep their category.

## 5. Messy cases

### Parsing (`backend/app/parsing/`, pure)

| Case | How it is handled | Test |
|---|---|---|
| Junk lines (account name, period, blanks) above the header | scan the first rows for the best header match | `tests/parsing/test_columns.py` |
| Different column names and layouts (`Details`, `Posting Date`, `Transaction Date` vs `Post Date`, `Debit`/`Credit`) | synonym table, matched ignoring case and punctuation; transaction date beats post date; unknown columns kept in `raw` | `test_columns.py` |
| No recognizable header | file-level error listing the expected column names | `test_columns.py`, `tests/api/test_statements_api.py` |
| UTF-8 BOM, cp1252, `;`/tab/pipe delimiters | BOM-aware decoding with fallback; delimiter sniffing that ignores quoted thousands | `test_readers.py` |
| XLSX with real date and number cells; xlsx renamed to .csv | detected by file magic, not extension; cells converted exactly | `test_readers.py` |
| Legacy .xls, random binary, a zip that is not a workbook, an empty file | clear 400 error | `test_readers.py`, `test_statements_api.py` |
| Amounts like `$1,234.56`, `(45.00)`, `45.00-`, `45.00 CR`, `45.00CR` | Decimal-only parsing, never float | `test_amounts.py` |
| Dates: ISO, `MM/DD/YYYY`, `MM/DD/YY`, `05 Jan 2026`, day-first files | date order detected per column from the values; impossible dates become row errors | `test_dates.py` |
| Sign conventions: checking as-is, card charges positive or negative, debit/credit columns, DR/CR type column, CR/DR markers | normalized to "> 0 is money in". Card files are auto-detected from payment rows and a majority vote, with a warning; the `charges_positive` override wins | `test_signs.py` |
| Opening/closing balance and `TOTAL` footer rows | skipped with a warning; a dated `TOTAL WINE` purchase is kept | `test_rows.py` |
| Blank rows, extra cells, whitespace | skipped or stripped silently | `test_rows.py` |
| Pending rows (status column or `PENDING` prefix) | parsed and flagged; excluded from totals | `test_rows.py`, `tests/api/test_summary_api.py` |
| Unparseable rows | reported as row errors with line number and reason, never dropped silently | `test_rows.py`, `test_statements_api.py` |
| Huge files | 5 MB upload limit (413) and a 10,000-row limit | `test_statements_api.py`, `test_readers.py` |

### Categorization (`backend/app/brain/`)

| Case | How it is handled | Test |
|---|---|---|
| Refund / return of an earlier purchase | `refund`, linked to the latest earlier purchase from the same base merchant within 90 days with amount ≥ refund; each purchase is linked at most once; partial refunds link | `tests/brain/test_edge_cases.py` |
| Refund with no matching purchase | still `refund`, never income; reported separately in the summary | `test_edge_cases.py`, `test_summary_api.py` |
| Chargeback / dispute credit | always review, suggested `refund`, linked to the disputed charge | `test_edge_cases.py` |
| Credit card payment seen from checking **and** on the card | `card_payment` on both sides (non-operating), so it is not counted twice as spending | `test_edge_cases.py` |
| Transfers between own accounts | `transfer` | `test_edge_cases.py` |
| Client payouts (Stripe transfer, Upwork withdrawal, ACH with an invoice) vs an unexplained deposit | `client_income` vs review with `client_income` suggested | `test_edge_cases.py` |
| Platform fees vs payouts from the same platform | fees are expenses (`platform_fees`), not negative income | `test_edge_cases.py` |
| IRS estimated tax | `tax_payment`, not deductible | `test_edge_cases.py` |
| Interest earned vs interest charged | `interest_income` vs `bank_fees` by direction | `test_edge_cases.py` |
| Foreign merchant + foreign transaction fee | the fee is `bank_fees`; the foreign merchant is still categorized by its words (`HOTEL LISBOA` → travel), and an unknown one goes to review | `test_edge_cases.py` |
| Exact duplicate rows | the repeat goes to review with `possible_duplicate` and the original's category as the suggestion; never dropped | `test_edge_cases.py`, `tests/parsing/test_samples.py` |
| `UBER *TRIP` vs `UBER *EATS` | travel vs meals by pattern | `test_edge_cases.py` |
| AWS vs Amazon retail | AWS is hosting; Amazon marketplace is ambiguous | `tests/brain/test_engine.py` |
| Money in from an expense merchant | expense candidates dropped by the direction check, with a note | `test_engine.py` |
| Unknown merchant | review with "no match" | `test_engine.py`, `tests/test_evaluation.py` (unseen rows) |
| Close candidates | review with "conflict: X vs Y" | `test_engine.py` |
| Fuzzy near miss | suggestion only, never auto | `test_engine.py` |
| Recurring subscription | +0.05 boost when the same amount repeats monthly | `test_engine.py` |
| Descriptions that look like spreadsheet formulas | escaped in the CSV export | `test_statements_api.py` |

## 6. Summary math

`services/summary_service.py`, per statement (tested against hand-computed numbers for
`credit_card.csv` in `tests/api/test_summary_api.py`):

- **Pending** rows are excluded from every total and reported as a count and an amount.
- **Needs review** rows are not in any category total. Their count and absolute amount are
  shown so the user knows how much is undecided.
- **Refunds** linked to an expense purchase are added to that purchase's category. For
  example, the Best Buy return cancels the Best Buy purchase, so `equipment` is $0.00.
  Unlinked refunds are shown on their own line and are **never income**.
- **Income** is the sum of income-kind categories (`client_income`, `interest_income`).
- **Expenses** is the sum of net spend over expense categories.
- **Estimated deductible:** each expense category's net spend × its `deductible_pct`,
  rounded half-up to the cent per category. Meals are 50%: $59.55 of meals gives $29.78.
- **Non-operating** categories (transfer, card_payment, owner_draw, tax_payment, personal)
  are listed separately and are in neither income nor expenses. On `credit_card.csv` the
  $5,060.56 of card payments would otherwise look like income.

## 7. Architecture and data model

```
React (Vite) ── /api ──> FastAPI routers ──> services ──> parsing (pure) ──> brain (pure)
                                                 └──> SQLAlchemy ──> SQLite
```

- **Parsing** and **brain** are pure libraries with no I/O, which makes them easy to test
  and reuse.
- **Services** (`ingest`, `review`, `summary`, `export`) are the only code that touches
  both the DB and the brain.
- **Routers** are thin. Service errors map to HTTP statuses in one place
  (`api/errors.py`), and every error is `{"detail", "code"}` JSON.

Data model:
- **Statement:** id, filename, account_type, uploaded_at, row_count, parse_errors (JSON),
  warnings (JSON), detected_format (JSON), file_hash (sha256, unique).
- **Transaction:** statement_id (FK, cascade), row_index (unique per statement), date,
  description_raw, merchant_key, amount_cents, category_id, suggested_category_id,
  confidence, status, reasons, rule_id, flags, is_pending, linked_transaction_id (FK, set
  null), dedupe_hash, updated_at.
- **MerchantRule:** merchant_key (unique), category_id, source, hits, created_at.

Rule data (merchants, patterns, keywords, ambiguity, taxonomy) is YAML. It is validated at
load time: unknown categories, bad regexes, bad directions or accounts, and duplicate ids
all fail fast with a clear error.

## 8. Evaluation

`samples/labels/` holds a hand-labelled expected category for each of the 134 sample rows.
Rows a human would need a receipt for are labelled `needs_review`: restaurants, an unknown
cafe, P2P payments, checks, ATM withdrawals and chargebacks. `scripts/evaluate.py` reports:

```
file                   rows auto   ok review precision
bank_messy.csv           14   13   13      1    100.0%
checking_simple.csv      45   35   35     10    100.0%
credit_card.csv          50   36   36     14    100.0%
credit_card.xlsx         25   20   20      5    100.0%

auto-precision 100.0% | review rate 22.4% | coverage 100.0% | direction errors 0
```

- **Auto-precision:** auto rows whose category matches the label. An auto row labelled
  `needs_review` counts as wrong.
- **Review rate:** share of all rows sent to review.
- **Coverage:** labelled (non-review) rows that were auto-assigned correctly.

**Honest note on overfitting.** The merchant list and patterns were written with these
samples in view, so 100% is an upper bound, not an estimate for unseen statements. Guards in
`tests/test_evaluation.py`:
- **Unseen rows:** 10 hand-written rows that are not in any sample: unknown vendors, an
  unknown bakery, Cash App, a deposit with no invoice, and known merchants in new forms
  (United Airlines, Hilton Garden Inn, a Fiverr withdrawal, GitHub with a city suffix).
  Unknown ones must go to review, and known ones must auto-assign correctly.
- **Review-rate cap:** the review rate must stay at or below 35%. Making the brain timid can
  therefore not pass the precision gate.
- The precision floor (≥ 97%) and **zero income/expense flips** are tests, so any rule change
  that breaks them fails CI.

## 9. Production choices

- **Money is integer cents** in the DB, `Decimal` in code and decimal **strings** in JSON.
  Floats are rejected at the money boundary, and rounding is half-up.
- **Upload limits:** `.csv`/`.xlsx` only, 5 MB (413) and at most 10,000 rows. The
  framework still receives the whole multipart body. In Docker, nginx caps request bodies at
  6 MB in front of it.
- **Duplicate files** are detected by sha256 and return **409** with the existing statement
  id. The UI offers to open it.
- **SQLite foreign keys** are enabled per connection (`PRAGMA foreign_keys=ON`), so
  deleting a statement really cascades to its transactions.
- **CSV export escapes formula-like cells** (`=`, `+`, `-`, `@`) against spreadsheet
  injection.
- **Logs** are structured JSON. An upload logs filename, row count, error count, review count
  and duration, and **never transaction descriptions or amounts**.
- **One error shape** for every 4xx/5xx; unhandled errors are logged with a traceback and
  return a generic 500.
- **Samples endpoint** uses an allowlist, so no user input is ever joined into a file path.
- **Config** comes from env and `.env` (`pydantic-settings`). There are no secrets anywhere.
- **Tests never touch the dev DB.** They use an in-memory engine with a dependency override.

## 10. Trade-offs

- **Rules over ML.** A rule engine is explainable ("why?" always has an answer), works with
  zero training data and fits the requirement that the brain be my own code. The cost is
  coverage: new merchants go to review until a rule exists or the user teaches one.
- **SQLite and create-on-start**, no migrations. Simple to run; a schema change means
  deleting `backend/data/app.db`.
- **Global learned rules** (no users). Fine for a single freelancer; multi-user would need
  per-user rules.
- **Re-categorizing a whole statement on "remember"** is O(rows of the affected statements).
  That is negligible at statement sizes, and it keeps context signals correct.

## 11. Future work

- **More formats:** PDF statements (table extraction), OFX/QFX, multi-currency with FX
  rates.
- **Auth and multi-tenancy**, with per-user rules, and Postgres with Alembic migrations.
- **Learning from confirmations:** use `user_confirmed` rows as labels to train a small
  ranking model (for example on merchant-token features) that **orders suggestions**. The
  thresholds and the review policy would stay rule-based and auditable.
- **Split transactions** (one Costco receipt that is part business, part personal) and
  receipt attachments.
- **Year view** across statements, with a Schedule C draft per line.
