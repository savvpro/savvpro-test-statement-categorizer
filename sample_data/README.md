# Sample data

All data here is **fictional**. The account holder is a made-up freelance software
developer in Islamabad, Pakistan ("Hamza Qureshi"). Every person, client, account
number, card number, reference number and balance is invented. Real company names
(Adobe, AWS, GitHub, PTCL, Careem, ...) appear only as merchants. Period: September 2026.

## Files

### `bank_a_card.csv` (business credit card, 31 rows)

- Columns: `Date,Description,Amount,Currency`
- Date: `YYYY-MM-DD`
- Amount is **signed**: negative = charge, positive = payment or refund.
- Currency per row: `USD` for foreign SaaS, `PKR` for local spending.

Edge cases:
- Exact known merchants: Adobe, GitHub, AWS, DigitalOcean, Namecheap, JetBrains, Canva, Notion, Zoom, Careem, PIA, Airblue
- `AWS EMEA AWS.AMAZON.CO` contains "AMAZON". It must match AWS (Hosting), not the ambiguous Amazon rule.
- Processor prefixes: `SQ *`, `PAYPAL *`, `UBER *`, `POS `
- Keyword-only matches: `SKYLINE HOSTING SVCS`, `BLUE BIRD CAFE`, `PAPERWORLD STATIONERS`, `HAFEEZ CENTRE COMPUTERS`
- Conflicting keywords: `UBER EATS` (Uber = Travel, Eats = Meals). Expected: Meals (case tag `specific_beats_generic`).
- Ambiguous merchants: `AMAZON.COM`, `DARAZ.PK` → Needs Review
- Unknown merchant: `XYZ TRADERS 4471` → Needs Review
- Full refund matching an earlier charge: Adobe -59.99 on row 1, +59.99 on row 24
- Partial refund: Airblue -24,750 on row 23, +8,250 on row 26
- FX fee: an AWS USD charge followed by a separate `FOREIGN TXN FEE` line in PKR
- Card annual fee and late payment fee
- Card bill payment `PAYMENT THANK YOU` (+185,000) → Transfer, not income
- Personal spending on the business card: `NETFLIX` → Personal. `KFC` → Needs Review (it could be a client meal).
- `PAYPAL *UPWORK` is a charge (buying Connects) → Professional Services. Compare it with Upwork as income in bank B.

### `bank_b_checking.csv` (business bank account, 25 rows)

- Columns: `Txn Date,Details,Debit,Credit,Balance`
- Date: `DD/MM/YYYY`
- `Debit` and `Credit` are separate, unsigned columns. Exactly one is filled per row.
- Amounts use thousands separators and are quoted when needed, e.g. `"1,250.00"`.
- All amounts are in PKR, and `Balance` reconciles row by row (opening balance 412,350.00).

Edge cases:
- Client income: `PAYONEER`, `WISE TRANSFER FROM CLIENT ...`, `UPWORK ESCROW`
- Transfers to and from savings. A credit is not automatically income.
- Card bill payment `CREDIT CARD BILL PAYMENT` (-185,000) matches bank A row 31. Both are Transfer.
- Internet and phone: PTCL, Jazz, Zong (exact match), `STORMFIBER INTERNET BILL` (keyword)
- Bank charges: inward remittance charge, SMS alert charge, FED (tax on bank charges), maintenance fee
- `FED ON CHARGES` appears twice with different dates and amounts. It is **not** a duplicate.
- Bill reversal (`REVERSAL PTCL ...`) → Refund
- ATM cash withdrawal → Needs Review (what the cash was spent on is unknown)
- IBFT to a person, RAAST P2P from a person, and an uncleared cheque → Needs Review
- Electricity bill (no matching category, could be part home office) → Needs Review
- Withholding tax on a cash withdrawal → Tax Withheld (kind `tax`: an advance tax credit, not an expense; shown as "Tax already paid" in the summary)
- Chartered accountants → Professional Services (keyword)

### `messy_statement.csv` (15 data lines, same columns as bank A)

Deliberately broken data to test the parser:

| Line | Problem | Expected |
|---|---|---|
| 1 | leading, trailing and inner whitespace, lowercase | parses → Software |
| 2 | mixed case | parses → Software |
| 3 | blank line | `SKIPPED` |
| 4 | missing amount | `PARSE_ERROR` |
| 5 | invalid date `2026-13-45` | `PARSE_ERROR` |
| 6 | amount `(45.00)` = negative | parses → Software, -45.00 |
| 7 | `Rs 500` currency symbol, positive | parses → Refund, +500 |
| 8 | `-$12.99` currency symbol | parses → Hosting, -12.99 |
| 9 | repeated inner whitespace | parses → Travel |
| 10, 11 | exact duplicate rows | both parse. Row 11 is flagged `needs_review=true` as a possible duplicate. |
| 12 | extra column | `PARSE_ERROR` |
| 13 | unknown merchant with padding | parses → Needs Review |
| 14 | thousands separator in a signed column | parses → Transfer, +185,000 |
| 15 | wrong date format (`DD/MM/YYYY` in a `YYYY-MM-DD` file) | `PARSE_ERROR` |

### `expected_labels.csv` (ground truth)

Columns: `file,row_number,expected_category,expected_kind,expected_needs_review,case_tag`

- `row_number` is 1-based and excludes the header. It counts **physical lines**, so the
  blank line in `messy_statement.csv` is row 3. For the two clean files, this equals the data row index.
- `PARSE_ERROR` rows should be rejected by the parser with an error. `SKIPPED` is a blank line
  that should be ignored silently. Both leave `expected_kind` and `expected_needs_review` empty.
- For rows sent to Needs Review, `expected_kind` is still filled in from the money direction
  (for example, a debit to an unknown merchant is still an `expense`).
- Exception: a possible duplicate keeps its best-guess category but has `expected_needs_review=true`.
