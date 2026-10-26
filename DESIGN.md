# DESIGN.md

## Use case
**Customer:** a freelance designer who pays for software, travel, supplies and ads on a business
credit card, and receives client payments. At tax time they need every transaction sorted into a
category, with refunds and internal transfers handled correctly, and a clear list of rows that still need
a human decision.

## Flow
1. User uploads a CSV (max 5 MB, max 20,000 rows).
2. FastAPI validates the file, finds the description/amount/date (or debit/credit) columns and parses amounts.
3. `categorize_transaction()` returns `{category, kind, reason}` for each row.
4. React shows rows, totals, filters and a category dropdown per row.
5. The user fixes `Needs Review` rows and exports a CSV (formula-injection safe).

## How the brain decides (`backend/categorizer.py`)
Rules run in a fixed order. Keywords are regular expressions matched on **word boundaries**, so
"training" does not match "train".

1. Empty description or zero amount -> **Needs Review**.
2. Transfer / card-payment wording ("transfer to savings", "payment thank you", "autopay"...) -> **Transfer**
   (kind `transfer`, excluded from spending).
3. Refund wording ("refund", "chargeback", "reversal"):
   - positive amount -> Needs Review (wording and sign disagree);
   - exactly one merchant category matches -> that category, kind `refund` (reduces the expense);
   - unknown or ambiguous merchant -> Needs Review. A refund is never income.
4. Income wording ("client payment", "stripe payout"...) -> **Income**, but a negative amount or an
   expense keyword in the same text -> Needs Review.
5. Merchant keywords:
   - several different categories match (e.g. "monthly fee adobe") -> Needs Review;
   - one category matches with a negative amount and no refund wording -> Needs Review;
   - one category matches -> that category.
6. Nothing matches -> **Needs Review** ("a wrong guess is worse than asking").

Every result carries a plain-English `reason` shown under the description in the UI.

## Messy cases handled
Refunds, card payments with negative amounts, internal transfers, "Uber" vs "Uber Eats", currency formats
(`$1,234.50`, `(25.00)`, `25.00 CR`), debit/credit column files, UTF-8 BOM, blank lines, extra whitespace
and case, bad amounts (error with row number), non-UTF-8 / non-CSV / oversized files.

## Data model
Transaction: `id, row, date, description, amount, category, kind, reason, original_category,
manually_reviewed`. `kind` is one of `expense | refund | income | transfer | review`.
The API is stateless (no database or login); edits are kept in the browser, and `PATCH /api/transactions/{id}`
validates the category list.

## Totals
- Net expenses = expenses - refunds (per category). Transfers and income are reported separately.
- "Needs review" shows the row count and the amount still uncategorized.

## Limitations / future work
- The keyword list is small and users cannot add rules in the UI yet.
- The sign convention (positive = charge) is assumed; some banks export the opposite. Rows where sign and
  wording disagree go to review, which limits the damage.
- Edits are not persisted; production would need auth, a database, an audit log and learning from corrections.
- Currency is displayed as USD only; no multi-currency or date validation.
