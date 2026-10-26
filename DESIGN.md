# SortedHisab design

## Customer and job

A fictional Pakistan-based freelance software developer receives client remittances and buys AI tools, hosting, software, and courses while also paying for entertainment, groceries, family support, healthcare, utilities, transport, and savings. Statements alone rarely establish business purpose. SortedHisab organizes evidence and asks for judgment instead of inventing intent or tax treatment.

## Architecture

React + TypeScript + Vite frontend; FastAPI backend; local SQLite. `parsers.py` extracts and validates; `engine.py` is the independent deterministic brain; `reports.py` performs integer accounting; `store.py` owns transactional persistence; `main.py` exposes the API. Components separate import, table/filtering, review, and app navigation. No model SDK, provider credentials, classification network call, or training data is required.

```text
Upload -> extract -> explicit mapping/direction -> validate every row
       -> atomic import -> rules per row -> review -> reconciled export
```

Inspect returns headers and six sample rows. Preview validates the entire file and returns all errors plus ten normalized sample rows. Commit parses again; the server never trusts a client preview or client-provided classification. Raw upload bytes are not persisted. SHA-256 is retained for exact-file detection.

## Normalized record

- Original description, original row fields, source row, statement ID and account.
- ISO posting date, currency, signed integer minor-unit amount (positive money out).
- Optional original amount/currency, separate from posted amount.
- Type, category, purpose, category confidence, review flag, review status.
- Explanation, rule ID, version, business share, user note, possible-overlap flag.

Types distinguish expense, refund, income, transfer, card payment, cash, unresolved. Category describes what; purpose describes business/personal/mixed/unknown/excluded. `categorized` means an engine decision; `confirmed` means an individual user review. Category confidence is ordinal rule strength, not a statistical probability. Purpose unknown always requires review.

## Decision order

1. Normalize case and punctuation while preserving original text.
2. Explicit card repayment and own-account transfer descriptions are excluded movements.
3. ATM/cash withdrawal is a movement requiring review.
4. Find bounded merchant aliases. Specific Copilot rule excludes the broad GitHub match.
5. Negative amount with refund/reversal wording is a refund; confirm original category/purpose. Refund wording on an outgoing amount is a conflict.
6. IBFT, RAAST, wallet and generic transfer descriptions are uncertain transfers. Exact account-scoped user transfer rules may identify them.
7. Other credits are candidate freelance income only with explicit remittance/payout/client wording; otherwise unresolved. Never classify an incoming recognized merchant as purchase or automatically as income.
8. Explicit taxes/levies and fee wording are separated. Provider-named ambiguous fees can remain merchant candidates requiring review.
9. Apply saved exact-description expense rules, scoped to one account.
10. A single merchant category yields high category confidence. AI tools, hosting, software, courses, transport, dining, equipment, internet, and utilities still require business-purpose review. Entertainment, grocery and healthcare merchants have editable personal defaults.
11. Multiple categories or no reliable match require review. No fuzzy guessing or arbitrary numeric confidence.

Structural rules outrank saved rules: a refund cannot be converted to income/purchase by a remembered merchant rule. Rules are full normalized descriptions, deliberately narrower than merchant-wide matching. They may need recreation for reference numbers that change. They apply only on future imports. Deleting a rule does not rewrite history.

## Accounting invariants

All backend calculations use integer hundredths; Decimal parses and formats amounts. Allocation rounds half away from zero to a minor unit; personal share is the remainder, so allocation always reconciles.

For each currency independently:

```text
net movement = money out - money in
net expenses = gross expenses - refunds
net expenses = reviewed business share + allocated personal share + unallocated expense amount
```

Personal merchant defaults may enter personal totals without an individual review; business totals require a resolved purpose from review or a previously saved rule. Unconfirmed refunds remain unallocated, which can be negative. No original and posted foreign amounts are added together. Excluded movements show absolute movement volume, not spending or net transfers; importing both sides can increase this volume.

Income candidates remain reviewable and are separate from expenses. Unresolved other movements remain in statement cashflow reconciliation. Category exports contain expense/refund categories; full transaction exports retain every row and type. Overview labels workspace-wide totals explicitly; account filtering controls the transaction list and review count.

## Messy data and recovery

- Every nonblank data row must parse. Errors block the whole statement, preventing silent loss and misleading totals.
- Mapping does not guess signed amount direction, account ownership, business share, original exchange rate, remittance gross amount, or processor deductions.
- Exact same bytes/account are rejected. Across imports, equal account/date/description/amount/currency rows are flagged as possible overlap and retained. Legitimate repeated purchases are never silently deduplicated.
- Remove an erroneous statement, fix its source and reimport. Review history for that statement is removed; rules remain. Cash expense splitting and individual duplicate suppression are not implemented.
- Partial/unmatched explicit refunds require review; automatic purchase linkage is deferred. User assigns the correct category and allocation with a note.
- Hardware installments are review candidates. No depreciation, financing schedule or full principal is inferred.
- Selecting Family support on an outgoing transfer explicitly changes it to a personal expense. Only user confirmation can establish that relationship. The resulting exact purchase rule can apply to future outgoing transfers with that description, never to an incoming credit.
- PDF compatibility is a defined synthetic tabular template with declared row count, not a bank-brand claim. Other layouts, scans and encrypted files fail with a CSV/XLSX alternative.
- Multi-sheet workbooks fail instead of silently choosing one. Formulas without cached numeric values fail validation. Workbook expansion is bounded.

## Persistence and trust boundary

SQLite schema version 1 contains statements, transactions, exact rules, and before/after reviews. Foreign keys cascade on statement deletion. Imports and reviews commit atomically; SQL is parameterized. Built assets and sample downloads use constrained paths; spreadsheet exports escape formula-like text.

This is a loopback-only single-user app, not a hosted service. No permissive CORS; mutation requests with foreign origins are rejected. Upload and workbook bounds reduce accidental resource abuse, but multipart processing and PDF extraction are not an isolation boundary for adversarial files. Database encryption, identity, per-user storage, streaming upload quotas, parser sandboxing, backups, migration tooling beyond v1, and an immutable audit API would be needed for hosting.

## Validation

Tests cover financial invariants, credits/refunds, merchant boundaries/conflicts, uncertainty, decimals, sign/date conventions, invalid rows, duplicate/overlap handling, currency separation, allocations, rule scope, persistence, export escaping and the full review flow. Browser tests exercise desktop/mobile and CSV/PDF/XLSX imports. See README for commands and `docs/design/QA.md` for render verification.
