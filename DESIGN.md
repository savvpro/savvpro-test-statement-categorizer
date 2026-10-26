# Design decisions

## Customer and workflow

The customer is a freelance software developer or independent IT consultant in Pakistan preparing PKR records for an accountant. Developer subscriptions, hosting and explicit internet bills are common enough to recognize. Purchases from general retailers and cafes need personal context, so the app leaves those for review. Nayatel and PTCL internet bills get a service category; a bare Nayatel description or Daraz purchase remains uncertain. None of these categories establishes deductibility.

The workflow is upload, inspect totals and explanations, filter uncertain rows, correct categories, confirm legitimate repeated entries, then export. Existing statements remain selectable. The desktop dashboard keeps its table. At widths up to 850px, the same transaction cells form stacked rows with visible signed amounts, full-width category selectors and confirmation controls. Responsive CSS avoids a second mobile implementation.

## Rule order

The engine is plain Python. It does not call an AI service.

1. A stored manual category wins. Automatic decisions are retained separately.
2. Zero amounts require review.
3. Refund indicators combined with explicit internal-transfer or client-payment indicators require review.
4. Explicit movement between own accounts is excluded from ordinary income and expenses in either direction.
5. Refund indicators classify incoming money as Refund. Outgoing refunds need review.
6. Incoming money becomes Client Income only with an explicit Client Payment type or description prefix.
7. Generic outgoing Transfer, IBFT and Raast payments need context before classification. Other outgoing transactions may match the small merchant list.
8. Everything else needs review.

Descriptions are normalized for case, punctuation and repeated whitespace. Merchant expressions match the whole normalized description, optionally followed by a numeric reference of at least three digits. `GITHUB COPILOT` matches; `NOTGITHUB COPILOT` and `GITHUB COPILOT CONSULTING` do not. This misses some legitimate bank-specific descriptions in exchange for fewer accidental matches.

The optional Type column recognizes exact normalized `Internal Transfer`, `Refund` and `Client Payment` indicators. A generic `Transfer` type is not evidence of internal movement. Own-account descriptions match whole phrases: `TRANSFER TO/FROM [OWN] SAVINGS [ACCOUNT]`, `TRANSFER BETWEEN OWN ACCOUNTS`, or `INTERNAL TRANSFER` optionally to/from savings. `TRANSFER TO SUPPLIER` and `IBFT TO CONTRACTOR` stay Needs Review. A generic `RAAST PAYMENT RECEIVED` stays unknown; an invoice reference alone also does not prove client income. Refund descriptions begin or end with the word `REFUND`, and client payment descriptions begin with `CLIENT PAYMENT`. Users can explicitly correct automatic decisions, subject to amount direction.

## Review and money

The UI shows review status and short explanations, without confidence percentages. Review is required if the category is Needs Review or a suspected duplicate is unconfirmed. A manually selected category and duplicate confirmation are separate persisted fields. Neither action implies the other. Confirming an unknown entry leaves its category unresolved. The original automatic decision remains available, and no confirmation removes a transaction or changes totals.

Money is parsed, stored and summed without binary floating point: Python Decimal for arithmetic, canonical decimal strings in SQLite and JSON. The frontend converts amounts only for display and sorting category totals. It does not calculate financial summaries.

PKR is the only supported currency. Missing Currency means PKR; an explicit value must be PKR. The new default `backend/data/statements_pkr.sqlite3` keeps the previous EUR database untouched. A `DATABASE_PATH` override must point to a PKR-only database. No amounts are converted or migrated from EUR.

Expenses are gross categorized outflows. Refunds stay separate. Transfers show gross movement with incoming and outgoing subtotals. Unknown payments are excluded from classified expense and income totals but included in statement net movement. Duplicate-looking rows contribute to totals until the user checks the source statement. This preserves the ledger rather than silently deleting legitimate repeat purchases.

For a statement to reconcile:

```text
net movement = income + refunds + transfers in + unclassified in
               - expenses - transfers out - unclassified out
```

API corrections enforce category direction. Zero values cannot be converted into income, spending or transfers. Categories organize records and make no conclusive tax claims.

## Implementation tradeoffs

FastAPI and Pydantic validate API boundaries. Standard-library CSV parsing handles quoting and BOM; rows are validated before a single SQLite import transaction begins. The upload endpoint reads bounded CSV bytes directly, avoiding a multipart dependency and enforcing the file limit during streaming. Errors use a consistent `detail` string and do not expose server traces.

SQLite keeps the assessment easy to run. Each operation uses a short-lived connection and parameterized queries. There is one statements table and one transactions table, with original decisions, optional manual categories and a duplicate confirmation flag. Startup adds that flag if absent, using an idempotent column check. Existing categories remain as stored, and duplicate confirmation defaults to false rather than guessing past intent. No migration or repository framework is needed.

The React frontend uses component state, native controls and plain CSS variables. Categories come from the API. A category correction or duplicate confirmation returns fresh statement data and summary together, so the UI uses the same backend calculations after each action. A file limit and table pagination keep the simple whole-statement approach practical. React StrictMode stays enabled in development; the initial effect has cleanup to ignore responses after unmount.

Exports neutralize formula-like text while preserving numeric amount cells. They include unresolved entries and both current and original decisions. Export is a review artifact, not a backup format for restoring manual corrections through import.

Saved merchant rules were omitted. Applying a correction only to one transaction avoids turning a context-specific purchase into a misleading future rule. Authentication, deployment, a migration framework, deletion and multi-user concurrency are also outside the assessment.
