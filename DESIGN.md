# Ledgerly — Design

## 1. Use case

**Customer:** a small, self-managing residential landlord with one to four rental units, one business checking account and one credit card.

**Their tax-time job:** turn a year of messy bank and card statements into the numbers for **IRS Schedule E, Part I**, keeping out everything that isn't rental income or a deductible expense.

**Why it's hard (and why it's a good test of a rule engine):**

| Real-world mess | What a naive categorizer gets wrong | What Ledgerly does |
|---|---|---|
| A tenant pays $1,250 by Zelle with no memo | "Income" with no idea why | Rent at 70% confidence. Becomes automatic only if the same payer and amount repeat monthly |
| A tenant pays a security deposit | Counts it as income | `Security deposit received`: held for the tenant, not counted |
| Home Depot refunds $42 | Counts it as income | Keeps `Repairs` and reduces the repairs total |
| A tenant's payment bounces ("RETURNED ITEM") | Counts it as an expense | Reverses rent received |
| Mortgage payment | Deducts the full payment | Asks: only the interest part is deductible, and a statement can't show the split |
| Home Depot $3,400 | Counts it as a repair | Asks: over the $2,500 de-minimis limit it may be a depreciable improvement |
| Amazon / Walmart / Costco | Guesses | Asks: these stores sell both business and personal items |
| Zelle to a person | Guesses | Asks, and flags a possible 1099 once payments to that person reach $600 |
| Transfer to savings, card autopay | Double-counts spending | `Not counted on Schedule E` |
| Pending + posted copies, overlapping statements | Double-counts | Marks the duplicate and skips it, with a reason |

> Organizational aid only, not tax advice. All demo data is fictional.

## 2. Categories

Income: **Rents received** (Sch. E line 3; includes late and pet fees).

Expenses (Sch. E lines): Advertising (5), Auto and travel (6), Cleaning and maintenance (7), Commissions (8), Insurance (9), Legal and other professional fees (10), Management fees (11), Mortgage interest paid to banks (12), Other interest (13), Repairs (14), Supplies (15), Taxes (16), Utilities (17), Other (19).

**Not counted on Schedule E** (shown separately, never in totals): security deposit received / returned, loan principal, capital improvement, transfer between accounts, credit card payment, owner contribution / draw, personal, interest earned.

**Status is separate from category.** `Sorted` (auto), `Needs your review`, `Confirmed by you`, `Duplicate (skipped)`. A row that needs review keeps the brain's *suggestion*, but it has no category, and it stays out of the totals until the user confirms it. This is ADR-006.

Every category declares which money directions it allows (`backend/app/domain/taxonomy.py`). That one table drives brain validation, API validation and the options in the UI's category picker.

## 3. Architecture

```
Next.js UI ──/api──▶ FastAPI ─▶ services ─▶ ingest ─▶ normalize ─▶ BRAIN ─▶ SQLite (SQLAlchemy)
                                                                     ▲
                                                 rules/*.yaml + remembered user corrections
```

- **Modular monolith, clean layering.** `api → services → (ingest, normalize, brain, db) → domain`. The `domain/` and `brain/` packages import no web or database framework. They are pure functions of their inputs, so they're deterministic and trivially testable.
- **Money is integer cents** everywhere (ADR-002). `Decimal` is used only while parsing.
- **Contract-first API.** Pydantic schemas → `openapi.json` → generated TypeScript types. CI fails on drift.
- **Rules are data.** `backend/rules/*.yaml` is validated at startup: unique IDs, known categories, compilable regexes, no alias mapped to two categories. The engine is code.

Full detail: [docs/plan/01-architecture.md](docs/plan/01-architecture.md). ADRs: [docs/adr/](docs/adr/).

## 4. How the brain decides

> **No AI model decides anything.** The brain is about 600 lines of plain Python in `backend/app/brain/`. CI fails if any LLM/ML SDK appears in the dependencies (`scripts/check_no_llm_deps.sh`).

### 4.1 Pipeline (per transaction)

| # | Stage | Looks at | Example |
|---|---|---|---|
| 1 | **Structural** (`structural.yaml`) | description + memo, direction, account type | `ONLINE TRANSFER TO SAVINGS` → Transfer (0.99), which stops further matching |
| 2 | **Channel** (`stages/channel.py`) | Zelle/Venmo/ACH/check, counterparty, memo | Zelle from a person + memo "security deposit" → Security deposit received (0.92). Zelle to a person → flag *payment to individual* |
| 3 | **Memory** | the user's earlier "remember" corrections | `JOES CAFE` → Personal (0.98) |
| 4 | **Known merchants** (`merchants.yaml`) | cleaned merchant key, whole-token match | `HOME DEPOT` → Repairs (0.88) |
| 5 | **Keywords** (`keywords.yaml`) | merchant key + memo | `…COUNTY TREASURER` → Taxes (0.95) |
| 6 | **Fuzzy merchant** (rapidfuzz) | only when no exact merchant hit | `HOEM DEPOT` ≈ Home Depot (90%) → Repairs (0.73) |
| 7 | **Policy flags** | merchant lists, amounts | Amazon → *mixed-use merchant* |

Before matching, the normalizer has already turned `SQ *JOES CAFE 9921 SEATTLE WA` into the merchant key `JOES CAFE`. It strips processor prefixes, store numbers, card masks, reference IDs and trailing city/state, and extracts the payment channel and counterparty.

### 4.2 Whole-statement passes

- **Duplicates:** the same OFX transaction ID twice; a pending row with a posted twin (same amount and merchant, within 5 days); a fingerprint seen in an earlier upload. Two genuinely identical purchases in one file are **not** merged, because the fingerprint includes an occurrence counter.
- **Recurring:** the same payer and amount (±10%) in two or more months adds evidence (0.55) to that row's leading category. This is how a monthly tenant Zelle with no memo becomes confidently *rent*.
- **Outliers:** an amount more than 1.5× a payer's regular rent, or more than 5× a merchant's typical charge, is flagged.
- **1099:** payments to the same individual totalling $600 or more are flagged.
- **Refund linking:** a refund is linked to the most recent matching purchase ("Matches the Mar 06 purchase, row 12").

### 4.3 Turning evidence into a decision

1. **Direction check.** Candidates whose category can't apply to the money's direction are dropped. An expense category on an inflow survives only as a refund, and only with evidence (`REFUND`, `RETURN`, `REVERSAL`…). If every candidate is dropped, the row is flagged *direction conflict*.
2. **Noisy-OR per category.** `p = 1 − Π(1 − sᵢ)`. Independent evidence that agrees raises confidence, while a single weak hit stays weak. Example: Zelle rent without a memo (0.70) plus monthly recurrence (0.55) gives `1 − 0.30 × 0.45 = 0.865`.
3. **Status.** `Sorted` **only if** the top category has p ≥ **0.85**, it leads the runner-up by ≥ **0.20**, **and** there's no blocking flag. Otherwise `Needs your review`, with the top category kept as a suggestion.
4. **Explanation.** Every row carries plain-English reasons, such as "Matched known merchant 'Home Depot' → Repairs." or "Over the de-minimis limit, so this may be a capital improvement…". The UI shows them next to the decision.

Blocking flags: mixed-use merchant, possible capital improvement, mortgage split required, payment to individual, check without payee, direction conflict, amount outlier, unknown merchant, low information, zero amount, ambiguous match. Informational flags: rent reversal, possible 1099, recurring.

### 4.4 Learning from the user

When the user confirms a row with **"Remember for <merchant>"**, a merchant rule is stored. It outranks the built-in rules on every later upload. **"Also apply to N similar rows"** re-labels unconfirmed rows with the same merchant key in that statement. Every correction is kept in an immutable audit table.

### 4.5 Precision first

"A wrong guess is worse than asking." The thresholds are set so that an automatic answer is never wrong on the labelled set, and everything uncertain goes to the user with the brain's best suggestion pre-selected. That makes each review a one-keystroke confirmation, not a lookup.

## 5. Evaluation

`make eval` (or `uv run python scripts/evaluate_brain.py`) runs the real parse → normalize → brain pipeline over six fictional statements (CSV, messy CSV, OFX 1.x SGML, OFX 2.x XML, and an overlapping second upload) and compares the results with hand-checked labels.

| Metric | Result | Gate (CI) |
|---|---|---|
| Auto precision: automatic answers that are correct | **100%** | 100% |
| Review recall: rows that must be asked about and were | **100%** | 100% |
| Coverage: rows sorted without asking | **71%** | reported |
| Rows evaluated | 126 | |

The one row asked about unnecessarily is an April rent payment whose earlier months were in a *previous* upload. Recurrence is detected per statement, which is conservative by design.

## 6. Edge cases

There are 79 catalogued cases: 25 parsing, 44 landlord-domain and 10 security. Each has an ID, an expected outcome, and a test named after the ID (for example `test_D12_refund_reduces_repairs_not_income`). The catalog is in [docs/plan/04-edge-cases-and-fixtures.md](docs/plan/04-edge-cases-and-fixtures.md). Highlights not covered above:

- **Parsing:** UTF-8 BOM, Windows-1252, `;` delimiters with decimal commas, preamble and footer rows, separate debit/credit columns, `(45.00)` / `45.00 CR` / `$-45.00`, ambiguous `MM/DD` vs `DD/MM` resolved file-wide, credit-card sign conventions, OFX 1.x SGML and 2.x XML, `.csv` files that are really OFX, CRLF.
- **Partial files:** up to max(2 rows, 5%) malformed rows import with warnings. More than that is refused with row numbers, because a silent half-import is worse than an error.
- **Security:** oversized files, binaries renamed to `.csv`, XXE and billion-laughs OFX, path-traversal filenames, CSV formula injection in exports, very long descriptions. See [SECURITY.md](SECURITY.md).

## 7. Trade-offs and limits

- Rules beat ML here: there's no real labelled data, decisions must be explainable, and the task forbids an AI model deciding.
- US Schedule E only. No per-property allocation, mileage or depreciation schedules yet.
- Single user, no authentication (local tool). The service layer has a seam for adding workspaces.
- Recurrence and outlier detection work within one statement. A multi-statement year view is future work.
- PDF statements are out of scope. CSV and OFX/QFX exports are available from almost every US bank.
