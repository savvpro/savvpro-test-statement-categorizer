# System Patterns

Architecture, brain design and conventions. Update when a pattern is added or changed.

## Stack
- Backend: Python 3.11, FastAPI, conda env `assigment`
- Frontend: React / Next.js
- Database: Supabase, only if persistence is required. Default is in-memory.

## Architecture

```
Upload CSV -> Parser -> Normalizer -> Brain (rules + confidence) -> Special passes -> API -> React UI
                                                                          ^
                                                               User fixes Needs Review rows
```

```
backend/
  app/
    main.py          FastAPI app, routes
    schemas.py       Pydantic models
    parser.py        CSV -> list of Transaction
    normalizer.py    clean description strings
    rules.py         rule definitions (data)
    engine.py        apply rules, confidence, reason
    passes.py        transfers, refunds, duplicates
    summary.py       per-category net, income, spending (refunds offset their purchase)
    store.py         in-memory store, one statement (swap for Supabase only if needed)
  summarize_sample.py  prints sample results
  tests/
  requirements.txt
frontend/            Next.js app (App Router, TypeScript, plain CSS)
  app/page.tsx       single client page: owns state and network calls, composes components
  app/globals.css    design tokens (CSS variables, light + prefers-color-scheme dark) and all styles
  components/        UploadZone, SummaryCards, CategoryBars, FilterBar, TransactionsTable (presentational)
  lib/api.ts         typed fetch helpers, single error-handling point
  lib/format.ts      PKR format, signed format, exact net, bar sizing, row filters (Vitest tested)
sample_statement_pkr.csv
gen_sample_statement.py
DESIGN.md            created after first working brain
```

## Data model

`Transaction`: `id`, `date`, `description`, `normalized`, `amount` (signed Decimal, PKR), `balance`, `category`, `confidence` (0-1), `reason`, `needs_review` (bool), `usd_hint` (bool), `flags` (list: `duplicate`, `reversal`, `transfer`), `user_edited` (bool), `refund_of` (id of the purchase a Refund pays back).

Amount sign: credit is positive, debit is negative.

## Brain design

1. **Normalize**: uppercase, collapse whitespace, strip `*`, store or order numbers, masked card or account digits, currency hints kept as a feature.
2. **Match rules in order** (first strong match wins):
   - exact or known merchant
   - keyword / regex group
   - amount or direction hints (credit vs debit)
3. **Confidence**: each rule carries a base confidence. Ambiguous merchants get a low value. A row below the threshold becomes Needs Review.
4. **Reason**: every row stores which rule fired, shown in the UI.
5. **Special passes** (after rules):
   - transfers between own accounts: Transfer, excluded from spending
   - refunds: credit tied to a merchant, category Refund, not Income
   - failed transaction plus reversal: flag both, net zero
   - duplicates: same normalized description, amount and date, flag the later row
6. **Unknown means Needs Review.** Never default to a "best guess" category.

## Conventions

- No LLM or AI model call in the brain, API, or tests.
- Rules are data (list or YAML), engine logic is code. Add a rule by adding data plus a test.
- Money: `Decimal`, PKR. Dates: explicit `%d-%m-%Y`.
- Pure functions for normalizer, rules and passes so they are trivial to test.
- Money in API JSON is a string (Decimal). Upload errors are `400` with a readable `detail`.
- API returns the full transaction list after a PATCH so the UI stays in sync with totals.
- Tests use only the fake sample data.
- Secrets (for example Supabase URL and key) live only in `.env`. Provide a `.env.example` with empty values.
- Frontend styling: colors, radius and spacing only via CSS variables in `globals.css`; no UI library; one font via `next/font`. Net is the only derived money value (BigInt cents).
- Frontend: money stays a string, formatted by `Intl.NumberFormat`; all network calls go through `lib/api.ts`; summary always refetched from `/summary`, never computed in the browser.
- Python commands run through `conda run -n assigment ...`.
- Claude never runs commit or push. The user does.

## Known limits (list in DESIGN.md)
- One CSV format, one currency
- Rule coverage limited to common Pakistani merchants and bank terms
- In-memory storage resets on restart (unless Supabase is added)