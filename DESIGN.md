# Design

## Use case
A freelance software developer who pays for software, hosting, travel and meals on one business card
and needs totals per tax category. Wrong guesses are costly at tax time, so **uncertainty is a feature**.

## The brain (`backend/app/brain.py`, `rules.py`)
Deterministic pipeline; first match wins:
1. **Normalize** description: uppercase, drop `*`, store numbers, reference codes (`UBER *TRIP 8F3K2` -> `UBER TRIP`).
2. **User rules**: corrections the user made earlier (confidence 1.0).
3. **Not spending**: transfers and card payments are excluded from totals.
4. **Fees / interest**.
5. **Merchant keywords** (longest first, whole-word, so `UBER EATS` beats `UBER` and `AWS` never matches `LAWS`): confidence 0.95.
6. **Ambiguous merchants** (Amazon, PayPal, Square, Walmart, Zelle...): always Needs Review.
7. **Fuzzy match** (rapidfuzz, per word, cutoff 85) for typos: confidence 0.75.
8. **Otherwise** Needs Review. Anything with confidence under 0.7 is also flagged.

Money in is never assumed to be income: a credit from a known merchant is a **refund** (reduces that category),
an invoice/deposit is income, anything else goes to review.

## Messy-data cases handled
| Case | Handling |
|---|---|
| Refunds / returns | Net against the original category, not income |
| Transfers, card payments | Excluded from spending totals |
| Different sign conventions | Inferred from card-payment rows (or if ~all rows are positive); user is warned |
| Debit/Credit split columns, `(45.00)`, `$1,234.50` | Parsed |
| Duplicate rows | Flagged for review (could be real, e.g. two coffees), not silently dropped |
| Ambiguous merchants | Review, never guessed |
| Bad rows (bad date/amount) | Skipped with a visible warning |
| Oversized / wrong file type | 413 / 415 |

## Not handled (honest list)
Foreign currency conversion, split-purpose merchants (a Costco run is review, not split), pending vs posted,
positive Stripe-style "TRANSFER" payouts (matched as a transfer), PDF statements, multi-user storage.

## Structure
`parsing.py` (CSV -> rows), `brain.py` (decisions), `rules.py` (data), `main.py` (API, summary, corrections).
Corrections call `brain.learn`, which also resolves identical pending rows in the same statement.
