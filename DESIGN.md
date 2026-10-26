# Design

## Use case

This app helps freelance designers sort business statement transactions for
tax-time review. A known design-software purchase such as Adobe is categorized
as Software; a known grocery, dining, transport, shopping, bill, or healthcare
merchant is categorized by a small explicit rule set. A description that does
not match a rule is marked **Needs Review**, rather than assigned a speculative
category.

## Architecture

- `app/main.py` exposes a FastAPI API. `POST /categorize` accepts a CSV upload
  in the multipart `file` field and returns categorized transactions, invalid
  rows, signed category totals, and the number of data rows. `/health` and
  `/categories` provide a health check and the category list.
- `app/csv_parser.py` decodes UTF-8 CSV, maps supported header aliases,
  normalizes dates and amounts, validates each row, and delegates valid rows
  to the categorizer.
- `app/categorizer.py` contains the deterministic rules. No model or external
  service makes category decisions.
- `frontend/` is a Vite/React/TypeScript client. It uploads a statement,
  displays results and invalid rows, calculates the current displayed totals
  and category counts, and lets the user change a category or mark an
  uncertain transaction reviewed.

## CSV parsing and validation

Statements must include a date column, a description column, and either one
amount column or debit/credit columns. Header names are normalized for case,
spaces, and punctuation before matching supported aliases. Dates are accepted
in ISO year-first, slash-separated year-first, US month-first, and abbreviated
English month formats documented in the README.

Amounts accept currency symbols, grouping separators, comma or dot decimal
separators, and parentheses for negative values. An amount-column sign is
preserved (negative is an outflow, positive is an inflow). Debit-column values
are normalized to negative and credit-column values to positive. A row with
both debit and credit set is invalid.

Bad data in an individual row does not discard other valid rows. The API
returns its CSV row number, field-specific errors, and original row data.
Missing required headers, unreadable UTF-8, or other structurally invalid CSV
input is returned as an API error instead of an empty success response.

## Deterministic categorization

The brain uses case-insensitive, explicit description keyword rules in
`app/categorizer.py`; there is no probabilistic model or AI call. Matching
priority is:

1. **Transfers:** descriptions matching transfer, XFER, move-money, or savings
   phrases are assigned Transfers.
2. **Refunds:** refund, return, reversal, merchant-credit, and purchase-credit
   markers are detected before income. The marker is removed, then the
   remaining merchant description is matched against known categories. A
   matched refund keeps the CSV amount sign and uses the original purchase's
   category, so it is not counted as Income. If its merchant cannot be matched,
   it is Needs Review.
3. **Income:** descriptions matching payroll, direct deposit, salary, client
   payment, invoice paid, freelance payment, or interest-credit phrases are
   assigned Income.
4. **Known merchants:** explicit keyword lists map recognized descriptions to
   Groceries, Dining, Transport, Shopping, Bills, Healthcare, Software, or
   Other.
5. **Unmatched descriptions:** assigned Needs Review with a reason and a
   review flag; the system does not guess.

Category totals are the signed sum of categorized transaction amounts by
category. The frontend recomputes totals and transaction counts from the
currently displayed rows, so changing a category immediately updates the
breakdown. Marking a row reviewed clears its review flag in the current browser
session.

## Uncertainty, review, and limitations

Review is deliberately conservative: keyword matching cannot establish tax
deductibility or reliably identify every merchant. An unknown merchant remains
Needs Review. Refunds are not linked to a specific original transaction; a
known merchant is used as a best-effort category proxy, and an unmatched refund
is sent to review. Transfer detection is based on description phrases and can
miss transfers worded differently or misidentify a merchant whose description
contains a transfer keyword.

The current app supports CSV only; it does not parse PDF or image statements.
Header aliases and date formats are finite, and amount parsing targets common
formats rather than every bank's locale or statement convention. The displayed
currency is USD and is not inferred from the file. The API does not persist
uploads or user edits, and category changes/review actions are local to the
current page session; there is no export, authentication, multi-user storage,
or lasting feedback loop. Category rules are an illustrative starting point,
not tax or accounting advice.

All development and test data should be synthetic. Do not upload or commit real
people's financial details or statements.
