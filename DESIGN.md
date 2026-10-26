# Design

## Use case
A **freelance designer** with one business credit card who must sort a year of purchases into categories at tax time. They want totals per category and a short list of rows that need their decision.

Categories: Software, Travel, Meals, Office Supplies, Advertising, Utilities, plus three special ones: **Not Spending**, **Refund**, **Needs Review**.

## How the brain decides
The brain is `backend/app/categorizer.py`. It uses only rules, so the same input always gives the same answer and every answer has a written reason.

1. **Clean the text.** `Uber *Trip 8821` becomes `UBER TRIP` (uppercase, symbols and reference numbers removed).
2. **Transfers.** Phrases like `TRANSFER TO`, `TO SAVINGS`, `PAYMENT THANK YOU` mean money moved between accounts, so the row is **Not Spending**.
3. **Money coming in.** A refund is money back, not income.
   - Refund wording, or a merchant we recognise, becomes **Refund**. It is subtracted from the category it came from (a refund from Adobe lowers Software).
   - Money in from an unknown source goes to **Needs Review** (it might be client income).
4. **Keyword match for charges.** Keywords match whole words only (`AWS` does not match `LAWS`). If several match, the **longest keyword wins**, so `UBER EATS` is Meals while `UBER` alone is Travel.
5. **When unsure, ask.** The row becomes **Needs Review** when: no rule matches, the merchant is ambiguous (`AMAZON` sells software and paper), two different categories tie, the description is empty, or a charge says "refund".

## Messy cases handled
| Case | What happens |
|---|---|
| Refunds | Own category, reduce the original category total |
| Transfers / card payments | Not Spending, left out of totals |
| Unknown or ambiguous merchant | Needs Review with a reason |
| Same date, amount and merchant twice | Flagged "possible duplicate" (not removed) |
| Day/month vs month/day dates | Format is detected from the whole file |
| `$1,234.50`, `(20.00)` amounts | Parsed correctly |
| Debit/credit as two columns | Supported |
| Purchases positive vs negative | User picks which one their file uses |
| Bad rows (bad date or amount) | Skipped and listed, the rest still works |
| Wrong file, wrong columns, empty, too big | Clear error message |

## User review
Changing a row's category also changes every row from the same merchant, and the totals are recalculated by the backend (`POST /api/summary`) so totals have one source of truth. The sorted result can be downloaded as CSV.

## Limits
- Keyword lists are small and written for this use case. More merchants means adding words to `rules.py`.
- CSV only. Amounts are treated as one currency.
- User fixes live in the browser; they are not saved between sessions.
