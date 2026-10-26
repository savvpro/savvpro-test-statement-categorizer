# Design

## Use case

**A US freelance designer preparing for tax time** (Schedule C). They upload the
CSV export of their business card or bank account. The app files every row into a
tax bucket (Software, Advertising, Office, Travel, Meals 50%, Phone & Internet,
Professional Services, Education, Bank Fees, Client Income), keeps money movement
(transfers, card payments) and personal spending out of the totals, and sends anything
it is not sure about to **Needs Review**. The job is done when "Needs review" reaches 0
and the totals say **Ready for tax**.

## Pipeline

```
CSV upload -> parser -> normalise merchant -> brain.decide -> sanity checks -> review threshold -> UI
                                     ^                                                         |
                                     +-------------- user fixes are remembered ----------------+
```

## How the brain decides (backend/app/brain.py)

Rows are processed oldest first. For each row:

1. **Normalise the merchant.** Strip POS prefixes, `SQ *`/`TST*` processor prefixes,
   store numbers, dates, zip codes, masked card numbers and long reference numbers:
   `POS PURCHASE SQ *BLUE BOTTLE #123 08/14 CA 94105` -> `blue bottle`.
2. **Money movement first.** Card payments (`PAYMENT THANK YOU`) and transfers
   (`TRANSFER TO SAVINGS`) are not spending or income.
3. **Money in (credits)**
   - Looks like a refund (`REFUND`, `RETURN`, `REVERSAL`...) or comes from a merchant we
     already saw a purchase from -> **refund**: filed under the *original purchase's*
     category and *reduces* it. A refund is never income.
   - Refund but original category unknown -> review.
   - Looks like an invoice / Stripe payout -> Client Income.
   - Zelle/Venmo from a person -> review (client payment or a friend paying back?).
   - Anything else -> review.
4. **User memory.** If the user already filed this merchant, reuse their choice.
5. **Mixed-use stores** (Amazon, Target, Costco, PayPal...) are never auto-filed.
6. **Merchant rules** (backend/app/rules.py). Every rule has a strength (0-1).
   All matching rules are scored; if two categories score within 0.15 of each other
   the brain refuses to pick and lowers confidence.
7. **Sanity checks**
   - Same date + merchant + amount as another row -> possible duplicate -> review.
   - Purchases >= $2,000 -> review (may need depreciation instead of expensing).
8. **Review threshold.** Confidence < 0.7 -> **Needs Review**. The best guess is kept as
   a one-click *suggestion*, but it is not counted in totals until the user confirms.

Every decision carries a human-readable `reason` and a `confidence`, shown in the UI.

**A wrong guess is worse than asking**, so the defaults lean to review: unknown merchants,
ambiguous stores, P2P money in, duplicates and large purchases all ask.

## Learning from the user

When the user fixes a row, the brain stores `merchant key -> category` (first two words
of the normalised merchant). Other rows from the same merchant that are still in review
are filed the same way, and future uploads use it too. Refunds are not learned from, so a
refund cannot teach the brain that a merchant is "income".

## Messy statements the parser handles (backend/app/parser.py)

- Bank preamble lines before the header row; "Total"/"Balance" summary rows.
- Header variants (Date / Transaction Date / Posted; Description / Details / Memo).
- One signed Amount column or separate Debit / Credit columns.
- `$1,234.56`, `(45.00)`, `45.00 CR`, `45.00 DR`, `45.00-`.
- Several date formats.
- Bad rows (bad date, missing amount, no description) are reported back to the user
  with their line number instead of being silently dropped.

## Totals

- Refunds reduce their category.
- Transfers, card payments and personal are excluded.
- Rows still in review are excluded, and the UI says so.
- Meals is labelled 50% deductible; the gross amount is shown.

## Production notes / next steps

- Storage is in memory behind `StatementService`; swap for Postgres without changing the API.
- Rules could move to a per-user editable table.
- Add PDF/OFX import, export to CSV for an accountant, auth and per-user memory.
