# Design

## The user and the job

**Who:** a rideshare or delivery driver in Pakistan (Uber, Careem, Foodpanda, similar) who is self-employed. They do not use accounting software. At tax time they have a bank statement and need three numbers: what they earned, what they can deduct, and what is left.

**The job:** turn a messy statement into those numbers without making mistakes that cost money. The risky mistakes are quiet ones: counting a refund as income, deducting a personal purchase, or dropping a real payment because it looked like a transfer.

**The principle that drives every decision:** *a wrong guess is worse than asking.* Asking costs the driver ten seconds. A silent wrong guess changes their tax return. So the brain never guesses silently. Every row carries a category, a confidence and a reason, and anything it cannot justify becomes **Needs Review**.

## Categories and how each is taxed

| Category | Kind | In the totals as |
| --- | --- | --- |
| Income | income | Income (platform payouts) |
| Fuel, Car Maintenance, Tolls & Parking, Phone & Internet, Platform Fees | deductible | Business expenses |
| Personal | personal | Personal spending, not deductible |
| Transfer, Card Payment | excluded | Left out: money moving, not spending |
| Refund | refund | Subtracted from the business expense it reverses; never income |
| Needs Review | review | Not counted; shown as unresolved money in and out |

The category list lives in one place ([`backend/app/categories.py`](backend/app/categories.py)) and is sent to the UI with every statement, so the two cannot drift. Phone & Internet is often only partly business use; the app does not apportion it, which is a deliberate simplification.

## The brain

Plain Python in [`backend/app/brain/`](backend/app/brain/): a normalizer, a rules file, and a categorizer. No AI model is called anywhere. It is deterministic: the same row always gets the same answer, and a reason can always be given.

### Step 0: clean the description

`FOODPANDA*ORDER 77812` and `shell petrol stn #4421 Lahore` become `FOODPANDA ORDER` and `SHELL PETROL STN`. The normalizer upper-cases, strips punctuation, dates, branch and order numbers (`#4421`, `STN 9`, `TXN12345`), and city/noise words from `rules.json`. Short mixed tokens such as `M2` and `4G` are kept because they are real words. The result is a stable **merchant key**, used both to match rules and to remember what the user taught the app.

### The decision steps, in order (first to decide wins)

| # | Step | Result |
| --- | --- | --- |
| 0 | Nothing readable, or zero amount | Needs Review |
| 1 | **Learned:** the user already fixed this merchant, and the direction of the money fits | That category (97%) |
| 2 | **Structural:** transfers to your own account, card payments | Transfer / Card Payment |
| 3 | **Cash and wallets:** ATM, cash withdrawal, Easypaisa, JazzCash, Raast, IBFT | Needs Review: only the driver knows what it was for |
| 4 | **Money in:** payout wording → Income; refund wording → Refund; both → ask; a merchant you normally pay with no refund wording → ask (suggest Refund); anything else → ask | |
| 5 | **Money out:** payout or refund wording on money going *out* → ask; keyword rules; rules for more than one category → ask | |
| 6 | **Fuzzy match** against what the user taught (typos, small variations) | That category if similar enough, else suggestion only |
| 7 | Nothing matched | Needs Review |

Every `Decision` has a `category`, a `confidence` between 0 and 1, a human-readable `reason` (shown in the UI), and optionally a `suggestion` (which way a Needs Review row leans) and a `related_category` (for refunds: what was refunded).

### Confidence and the threshold

Each rule in `rules.json` carries its own confidence. After any rule decides, a gate applies: **if confidence is below `review_threshold` (0.75) the row goes to Needs Review, with the leaning category kept as a one-click suggestion.** For example, `TRANSFER TO ALI KHAN` could be your own account or a payment to a person. The generic `TRANSFER TO` rule has 0.6 confidence, so the row is flagged, while `TRANSFER TO SAVINGS` (0.99) is accepted. A property test asserts that nothing below the threshold is ever auto-accepted.

### Rules are data

[`rules.json`](backend/app/brain/rules.json) holds the patterns, confidences, noise words and thresholds. Adding a merchant is a JSON edit. Patterns match **whole words only**, so `PSO` does not fire inside `PSOLUTIONS` and `TOLL` does not fire inside `STOLLEN`. The file is validated at startup (unknown category, bad regex, a rule that assigns Needs Review): a typo stops the server instead of mis-categorizing a tax return.

### Learning from a fix

When the user fixes a row, the merchant key is remembered **for that statement**, and the brain is re-run over every row the user has not fixed themselves. So fixing `ALI TRADERS 5521` settles `ALI TRADERS 7733` too, and the UI says how many other rows changed. Rules of the road:

- **Cash and wallet rows are never learned.** Each withdrawal has its own purpose.
- **The direction of the money must fit.** A learned "Income" is ignored on a row where money went out.
- **Rows the user fixed are never overwritten.**
- **Fuzzy matching uses `token_sort_ratio`, not `token_set_ratio`.** The latter scores 100 when one name is a subset of another, so a learned `ALI` would swallow `ALI AND SONS WORKSHOP SUPPLY`. Below about 88% similarity the match is only a suggestion (`0.85 × score` must reach the 0.75 threshold).
- Learning is scoped to one statement. With no login, a shared memory would leak one user's merchants into another's.

## Edge cases handled

| Case | What happens |
| --- | --- |
| Refund | Money in with refund wording is a Refund, never Income. It is netted against the expense it reverses (`SHELL PETROL REFUND` reduces Fuel). |
| Money in from a merchant you normally pay | Asked, with Refund suggested. It does not say "refund", so it is not assumed. |
| Transfers and card payments | Excluded from spending. A transfer to an unknown destination is asked about, because it could be a real payment. |
| `AUTOPAY` on a phone bill | Not treated as a card payment (a naive pattern would hide a real expense). |
| Foodpanda | `FOODPANDA PAYOUT` is income; `FOODPANDA ORDER` is a personal purchase; bare `FOODPANDA` is asked. |
| Platform fee vs bank fee | `UBER SERVICE FEE` is a platform fee (90%). A bare `SERVICE FEE` is only 70%, so it is asked. |
| Payout shown as money out | Possible reversal or clawback: asked. |
| Rules that disagree (`SHELL DARAZ`) | Fuel and Personal conflict: asked. |
| Unknown merchant, cash, wallets | Asked. |
| Category vs sign | A category can never contradict the direction of money (no Fuel on money in); verified by a property test over thousands of random descriptions. |
| Duplicate-looking rows | Kept (two tolls on one day are normal) but flagged for a second look. |
| Messy descriptions | Case, punctuation, branch numbers, city names, non-Latin scripts. |

Parser edge cases: Debit/Credit columns or one signed Amount column; credit-card exports where purchases are positive (a checkbox); `(500.00)`, `500.00 DR`, trailing minus, `Rs`/`PKR`/`$` prefixes, `1.234,56` European format; header row below account-info lines; `,` `;` tab `|` delimiters; UTF-8 BOM, Windows-1252 and UTF-16 files; opening/closing balance rows (skipped, but `TOTAL PARCO` is not mistaken for a total); impossible dates (`31/02/2026`), incomplete dates (`10/2026`), ISO dates (`2026-10-01` is October, not January); amounts with more than two decimals (refused, not silently rounded); NaN and Infinity (rejected); binary files renamed `.csv`; empty files; oversized files; row limits. Every skipped row is reported with its row number and reason.

## Architecture

```
frontend (Next.js) ── HTTP/JSON ──▶ api/routes ──▶ services ──▶ parser, brain, store
```

- **Thin routes, logic in services.** `StatementService` holds the use cases (upload, fix). Routes only translate HTTP.
- **The brain is stateless.** What the user taught it is passed in per call, which makes it trivial to test and safe to share between requests.
- **Money is `Decimal`**, never `float`. It is serialized to JSON numbers for the UI.
- **The store is behind a tiny interface** (`add`, `get`), with a bounded in-memory implementation so memory cannot grow forever. Swapping in a database touches one file.
- **App factory** (`create_app`) so every test gets a fresh app and store.
- **Validated configuration** via environment variables; **validated rules** at startup.
- **Frontend:** one page, all server access in `lib/api.ts`, response types mirroring the backend, design tokens in CSS (light and dark), native `<select>` for accessibility, stacked-card table on phones, live-region announcements for saves.

## Privacy and security

- Statements are financial data. They are held in server memory only, never written to disk, and **logs contain counts only**, never descriptions or amounts.
- The statement id is a random UUID because there is no login; it is the only thing that grants access to a statement.
- Uploads are size-limited, extension-checked and rejected if binary. File names are reduced to a safe base name.
- **CSV injection:** bank descriptions are untrusted text. In the export, any cell starting with `=`, `+`, `-`, `@`, tab or CR is prefixed with `'` so a spreadsheet will not run it as a formula.
- React escapes all rendered text. CORS is limited to configured origins. No secrets exist in the repo; `.env` files are ignored.
- All sample data is fake.

## Deliberate limits

- **Estimates, not tax advice.** The profit figure is income minus business expenses and ignores allowances, partial business use and anything outside the statement.
- **Rules are tuned for a Pakistani driver** (merchant names, cities, currency label). The engine is general; the data file is not.
- **A refund is tied to an expense by its wording** (`SHELL PETROL REFUND` → Fuel). A refund with no recognizable merchant is shown separately rather than guessed.
- **No persistence.** Restarting the backend clears everything.

## What I would add next

1. **A database (SQLite, then Postgres)** and accounts, so statements and learned merchants persist per user and carry across months.
2. **PDF statement import**, which is what many banks actually provide (text extraction first, OCR as a fallback).
3. **Learned rules that survive between statements**, with a screen to review and undo what the app has learned.
4. **Partial deductions** (for example 60% business use of a phone) and per-category notes for the accountant.
5. **Multi-currency and locale-aware number and date detection** with a preview step before categorizing.
6. **Rate limiting and authentication** on the API, and a retention policy for uploaded data.
7. **Evaluation set:** a growing file of real (anonymized) descriptions with expected categories, to measure rule changes before shipping them.
