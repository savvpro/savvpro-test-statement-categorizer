# Design

## Use case

A **freelancer** (designer, developer, writer) who mixes work and life on one card, gets paid
through platforms like Upwork, Fiverr and Payoneer, and needs a clean list of deductible expenses
at tax time. Typical statement problems:

- Cryptic merchant text (`SQ *JOES CAFE 9921`, `UBER *EATS 8841`).
- Money moving between their own accounts (not spending, not income).
- Refunds and card payments that look like income.
- Personal subscriptions mixed with business ones.
- Foreign-currency fees from international clients and tools.
- Duplicate lines, summary rows and unreadable dates/amounts.

The app answers: *how much did I spend per category, how much did I earn, and which rows need me?*

## Flow

```
CSV upload -> parser -> normalizer -> categorizer (the brain) -> summary -> user reviews/fixes
```

## The brain (`backend/app/categorizer.py`, `rules.py`)

Fully deterministic, explainable code. Every row carries a `reason` and `confidence`.

1. **Normalize.** Uppercase, strip punctuation and terminal prefixes (`SQ`, `POS`...). A
   *merchant key* (first two identifying words, digits dropped) groups `JOES CAFE 9921` and
   `JOES CAFE 4410` as one merchant.
2. **User correction wins.** If the user already fixed this merchant key, use it (confidence 1.0).
3. **Rule match.** Rules are data in `rules.py`: keywords matched as whole words (`ATM` never
   matches `PLATMAN`), optionally only for money in or out. Highest confidence wins, then the
   longest keyword (`UBER EATS` beats `UBER`).
4. **Direction logic.** Money in plus an expense category is a **refund**: it reduces that category
   and is never income. Income rules only fire for money in. An unrecognised deposit is
   *not* assumed to be income (could be a loan, gift or refund).
5. **Sanity checks** that cap confidence: repeated identical rows (possible duplicate), single
   expenses over 5000, meals over 300.
6. **Threshold.** Confidence below 0.7, or no match, becomes **Needs Review**. The best guess is
   shown as a suggestion, so a wrong guess is never silently accepted.

### Confidence in practice

| Situation | Confidence | Result |
|---|---|---|
| Known merchant (`ADOBE`, `FIGMA`, `DELTA AIR`) | 0.90-0.98 | categorized |
| Generic word (`CAFE`, `PIZZA`) | 0.60 | review, suggests Meals |
| Ambiguous merchant (`AMAZON`, `PAYPAL`, `ATM`) | 0.35-0.45 | review |
| Nothing matches | 0 | review, no suggestion |
| Duplicate / very large / large meal | capped at 0.5-0.6 | review |

### Categories

Software & Subscriptions, Travel, Meals & Entertainment, Office & Equipment, Advertising &
Marketing, Professional Services, Bank & Platform Fees, Internet & Phone, Education & Training
(business); Personal (kept out of business totals); Income; Transfer (excluded entirely).

## Edge cases handled

- Refund vs income, partial refunds net against the category.
- Own-account transfers and card payments excluded from spending and income.
- Unknown deposits and ambiguous merchants asked, not guessed.
- Personal subscriptions separated from business expenses.
- Foreign transaction fees recognised as bank fees.
- Duplicate rows flagged (first kept, repeats sent to review).
- Parser: `(45.00)`, `$1,234.56`, `45.00 DR/CR`, Unicode minus, debit/credit columns, BOM and
  Windows-1252 files, d/m vs m/d dates inferred from the whole file with a warning when
  ambiguous, summary/blank/zero/invalid rows reported with line numbers instead of guessed.
- Amount sign convention for cards (positive = purchase) is a user option.
- CSV export neutralises spreadsheet formulas in descriptions.

## Architecture decisions

- **Stateless API.** The browser keeps the file and the corrections and re-submits them. No
  database, no stored financial data, simple to reason about and deploy.
- **Rules are data.** Adding a merchant is a one-line edit in `rules.py`, not a logic change.
- **`Decimal` for money** on the server, floats only at the JSON edge.
- **Limits.** 2 MB upload and 5000 rows; CORS limited to the dev origin.

## Known limitations / next steps

- CSV only (no PDF/OFX import).
- Rule list is small and English/US-centric; persisting a user's corrections between sessions
  would make it learn over time.
- Merchant key uses the first two words, so two different merchants starting with the same two
  words share one correction.
- Deduction rules (e.g. meals being 50% deductible) are not computed; this is a sorting aid, not
  tax advice.
