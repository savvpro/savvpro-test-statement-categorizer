# Design Document - Ledgerline

## What it is

Ledgerline categorizes bank/credit-card statement rows to IRS Schedule C lines for US freelancers and sole proprietors. It handles the messy reality of bank exports - inverted signs, split debit/credit columns, bank preamble rows, mixed-use merchants, refunds - and produces a tax-ready Schedule C summary.

---

## Architecture

### Backend (Python 3.12 / FastAPI)

```
backend/
├── app/
│   ├── brain/          ← Pure deterministic categorization engine (no DB, no I/O)
│   │   ├── normalize.py    merchant name cleaning
│   │   ├── kinds.py        transaction type detection (CC payment, transfer, refund, income…)
│   │   ├── merchants.py    curated dictionary of 80+ known merchants
│   │   ├── keywords.py     keyword rules with confidence weights
│   │   ├── scorer.py       candidate scoring (user rule > dict > strong keyword > weak keyword)
│   │   └── engine.py       orchestrates the pipeline, produces Decision objects
│   ├── ingest/         ← File parsing (also pure, no DB)
│   │   ├── sniff.py        format/encoding/delimiter detection
│   │   ├── columns.py      header synonym mapping (Date|Posting Date|Trans Date…)
│   │   ├── dates.py        multi-format date parsing + ambiguity resolution
│   │   ├── amounts.py      amount parsing ($, parens, CR/DR, sign inversion)
│   │   └── csv_reader.py   assembles rows, handles preamble/footer/blank rows
│   ├── api/v1/         ← REST endpoints (thin controllers, delegate to services)
│   ├── services/       ← Business logic (import orchestration, categorize service)
│   ├── models/         ← SQLAlchemy 2.0 ORM models
│   └── core/           ← Config, DB, errors
└── tests/
    ├── unit/brain/     ← 81 tests for normalize, kinds, engine
    ├── unit/ingest/    ← 30 tests for amounts, dates, csv_reader
    └── integration/    ← 11 end-to-end API tests
```

### Why pure functions for the brain

The brain (`engine.categorize`) is a **pure function**: same input → same output, no DB, no I/O, no randomness. This has several advantages:
- **100% unit testable** with simple parameterized tables
- **Explainable** - every Decision carries an ordered `reasons[]` trail
- **Fast** - no async overhead, runs inline inside a DB transaction
- **Safe to re-run** - re-categorizing doesn't touch user-confirmed rows

### Confidence scoring

Evidence sources with fixed weights (no ML):

| Source | Confidence |
|--------|-----------|
| User rule (explicit override) | 0.99 |
| Curated merchant dictionary (exact match) | 0.95 |
| Strong keyword match | 0.85 |
| Weak keyword match | 0.65 |

**Needs Review** triggers (any one is sufficient):
- Confidence < 0.75 (configurable)
- Top-2 candidate margin < 0.15 (conflict)
- Mixed-use merchant (Amazon, Uber, Lyft, Airbnb, PayPal generic…)
- Equipment purchase > $2,500 de-minimis
- Unknown inflow (could be income, gift, or loan)
- Owner draw / ATM withdrawal

User rules bypass both the margin check and the mixed-use check - an explicit rule is always final.

### Two-step upload

1. `POST /imports` - sniff format, parse preview (10 rows), store base64 draft
2. `POST /imports/{id}/commit` - parse full file, fingerprint, deduplicate, categorize, persist in one DB transaction

This lets the UI show a mapping editor and sign/date toggles before committing anything to the database.

### Deduplication

Each transaction gets a **fingerprint**: `md5(account_id|date|amount_cents|merchant|occurrence_index)`. The occurrence index counts how many times that key appeared earlier in the same file, so two genuine identical coffees from the same merchant on the same day both survive. Re-uploading the same file (same SHA-256) returns HTTP 409.

---

## Data model

```
Account ─┬─< Statement ─< Transaction
         └─< Rule
```

- **Money is always stored as integer cents** (no floats, no rounding errors).
- `Transaction.status`: `auto | needs_review | confirmed`
- `Transaction.kind`: `income | expense | transfer | cc_payment | owner_draw | owner_contrib | tax_payment | loan_payment | refund | interest_income | interest_expense | fee | personal | unknown`
- `Category.slug` is the primary key (e.g. `software`, `meals`, `travel`)
- `Rule` is a learned or user-created override; `source: "user" | "correction"`.

---

## Frontend (Next.js 15 / React 19)

### Route structure

```
/                      Landing page (cinematic hero, no sidebar)
/(app)/
  dashboard            KPIs, category donut, monthly bars
  upload               Two-step file upload with mapping editor
  statements           Statement list
  statements/[id]      Statement detail + skipped rows
  transactions         Full table with filters + drawer
  review               One-at-a-time review queue
  rules                User rules CRUD
  categories           Schedule C taxonomy
  reports              Schedule C summary + CSV export
  settings             Theme, thresholds, data management
  how-it-works         Brain pipeline explanation
```

### Design system - "Ledger & Highlighter"

Rather than generic AI-app aesthetics (ivory, Instrument Serif, dark-gradient washes), the design derives from the subject:

- **Green ledger paper** (`#EEF3EE` light / `#0F1B2A` dark base) - the physical medium
- **Navy ink** (`#13263F`) - bookkeeper's pen color, not generic near-black
- **Ledger green accent** (`#1D6B48` / `#4FBF8B`) - the ruling-line color
- **Highlighter yellow** (`#F2C94C`) - the tool an accountant uses to flag a row for review
- **Red ink** (`#B42318`) - debit amounts, in the bookkeeping tradition

Signature design decisions:
1. **Needs-Review rows** get a CSS `background-image` linear-gradient that animates in like a real highlighter stroke
2. **Reports page** mimics the Schedule C form layout with real line numbers
3. **Faint ledger rules** behind transaction tables (1px `var(--rule-line)` borders)
4. **Fraunces** (variable optical font, expressive at large sizes) for display; **Public Sans** (US government typeface, echoes IRS forms) for UI
5. **Landing hero animation**: messy bank rows sort themselves into Schedule C buckets; one uncertain row is highlighted and pulled aside - Framer Motion scroll-driven

### Theming

`next-themes` with `attribute="data-theme"` and `defaultTheme="system"`. All colors are CSS custom properties on `:root`, redefined under `[data-theme="dark"]` and `@media (prefers-color-scheme: dark) :root:not([data-theme="light"])`. No color flash on load.

---

## Taxonomy

| Slug | Schedule C Line | Deductible |
|------|----------------|-----------|
| `client_income` | Line 1 | - |
| `other_income` | Line 6 | - |
| `advertising` | Line 8 | 100% |
| `car_truck` | Line 9 | 100% |
| `commissions` | Line 10 | 100% |
| `contract_labor` | Line 11 | 100% |
| `insurance` | Line 15 | 100% |
| `interest_expense` | Line 16b | 100% |
| `legal_professional` | Line 17 | 100% |
| `office` | Line 18 | 100% |
| `rent_cowork` | Line 20b | 100% |
| `repairs` | Line 21 | 100% |
| `supplies` | Line 22 | 100% |
| `taxes_licenses` | Line 23 | 100% |
| `travel` | Line 24a | 100% |
| `meals` | Line 24b | 50% |
| `utilities` | Line 25 | 100% |
| `software` | Line 27a Other | 100% |
| `education` | Line 27a Other | 100% |
| `bank_fees` | Line 27a Other | 100% |
| `equipment` | Line 13 | 100% - review if > $2,500 |
| `interest_income` | Schedule B | 0% (informational) |
| `non_pl` | - | - (transfers, card payments, owner draws) |

---

## Edge cases handled

| Scenario | How handled |
|----------|------------|
| Purchases listed as positive (credit card export) | Auto-detected by sign convention inference (≥ 5 rows, 100% positive → invert). User toggle in mapping editor. |
| DD/MM vs MM/DD ambiguity | Scan all date values; find a day > 12 to resolve. US default + warning if truly ambiguous. |
| Split Debit/Credit columns | `parse_debit_credit()` - debit col always negative, credit col always positive |
| Bank preamble rows | Detect by scanning rows for a header-like pattern; skip until found |
| Footer/balance rows | Pattern match "balance", "closing", "total" with large amount → skip |
| Duplicate rows | Fingerprint with occurrence index; identical file re-upload → 409 |
| Refund detection | Credit + REFUND/RETURN keyword, OR credit at merchant with prior debit in same batch/context |
| Mixed-use merchant | Flag for review; include human-readable note ("Amazon sells both business and personal items") |
| Equipment > $2,500 | Always flag regardless of confidence; reviewer must split personal/business if applicable |
| `DEPOSIT 2839021` (bare deposit, no company name) | Unknown kind → Needs Review (can't tell if income, gift, or loan) |

---

## Testing

```
backend/tests/
├── unit/brain/
│   ├── test_normalize.py   15 cases: processor prefix stripping, URL, phone, store#, state code
│   ├── test_kinds.py       28 cases: CC payment, transfer, tax, owner_draw, interest, refund, income, unknown
│   └── test_engine.py      27 cases: all category/status combos, user rule override, equipment threshold, refund
├── unit/ingest/
│   ├── test_amounts.py     14 cases: $, parens ($1,234.56), trailing -, CR/DR, sign inversion
│   ├── test_dates.py       10 cases: MM/DD/YYYY, DD/MM/YYYY, ISO, natural language, short year
│   └── test_csv_reader.py  11 cases: preamble, blank rows, footer, debit/credit cols, sign inversion
└── integration/api/
    └── test_api.py         11 end-to-end tests: health, seed, CRUD, upload, commit, rules, reports
```

Total: **122 tests, all green.**
