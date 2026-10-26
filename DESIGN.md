# Design

## Customer and scope

A freelance designer imports a business account's USD CSV statement, reviews
uncertain transactions and exports a categorized ledger for bookkeeping.
The app covers upload through review, category totals and export. Data remains
in process/browser memory; the API is stateless and has no database or accounts.

## Decision engine

`parser.py` validates each row and produces Decimal-valued transactions.
`categorizer.py` applies precompiled regular expressions from `rules.py`, ordered
by priority. Every output retains a rule ID, confidence and explanation.
Transaction type determines accounting treatment; business category describes
what the transaction relates to. Neither classification invokes a language model.

Order: own-account transfer descriptions and ATM withdrawals; explicit P2P
contractor payments; positive refunds; processing fees; bank fees; vendor
invoices; known incoming client payments; recognized expense merchants; fallback.
Each rule can require a positive or negative amount. Outgoing descriptions that
mention refund/reversal bypass expense rules and require review. Word boundaries
avoid matching AWS inside unrelated names such as Lawson.

The selected customer uses a business account, so known subscription and travel
merchants are suggested as business expenses. This does not establish tax
eligibility or the business purpose of a purchase. Generic merchants and P2P
payments remain unknown. Transfer descriptions are an assumption, not evidence
that the user owns the destination account.

## Refunds and duplicates

Positive refunds for recognized expense merchants reduce the corresponding
category. This does not require the original purchase to be in the same period.
For display, an optional link identifies a unique purchase sharing the same
recognized merchant pattern and exact amount, dated on/before the refund.
Input order does not determine eligibility. Ambiguous purchase links are omitted;
partial refunds may be categorized without a link. Generic refunds require review.

Duplicates share date, normalized description and Decimal amount. All rows are
retained and flagged. Both require review and are excluded from confirmed totals
until approved. There is no delete/exclude-duplicate action in this version; if a
source file repeats a row accidentally, fix the source and reimport it.

## Summaries and review

Unknown type/category, Needs Review status and contradictory amount directions
remain unresolved even if a client submits a confirmed status. Unresolved dollar
volume is tracked separately and makes the operating result provisional. Known,
resolved rows contribute as follows:

- Income adds positive revenue.
- Expenses and fees add absolute outflows to their separate totals.
- Refunds reduce category totals and net expenses.
- Transfers add to transfer volume and do not affect operating results.

`net_expenses = total_expenses - matched_refunds`

`net_operating_result = total_income - net_expenses - total_fees`

Category totals are signed sums, so they do not change when rows are reordered.
Net expenses may be negative when the period includes prior-period refunds.
Category totals include income, expenses and fees; they are not tax deductions.
All money uses Decimal, with two fractional decimal places and a bounded range.

The browser sends its ledger to the API for recalculation. Edits commit to local
state only after the API returns; controls are disabled during saving to prevent
competing responses. Unknown rows cannot be approved without classification.
Selecting a category for an unknown row suggests its accounting type, which the
user can change. The original rule ID remains in the exported audit information.
This is client-supplied state, not a tamper-proof accounting audit log.

## Import and deployment boundaries

CSV only, 5 MB maximum. The upload handler reads at most the limit plus one byte;
the multipart layer may spool incoming data before the handler runs, so production
hosting should also enforce a request-size limit. Duplicate headers are rejected;
bad rows are skipped with warnings, never silently accepted into totals.
Ambiguous non-ISO dates use month/day and warn. UTF-8 and Latin-1 are supported.
The parser does not infer a statement-wide date convention.

No authentication or persistence is implemented. CORS defaults to local frontend
origins. There are no runtime AI credentials. Only synthetic statements belong in
this repository. Exported text is protected against spreadsheet formulas.

## Verification

Pytest covers rules, parser failures, refund linking, summary invariance, review
boundaries and API behavior. Lint and the production build check the frontend.
CI repeats these checks. Browser interactions still need manual verification;
there is no end-to-end browser suite.
