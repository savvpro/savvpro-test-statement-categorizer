# Sample statements

All data here is invented for "Sam Rivera Design LLC", a fictional freelance designer, for
January to March 2026. Client names, people, the bank and every account number are made up.
Well-known merchant names (ADOBE, UBER, AWS, ...) appear only as merchants. Regenerate with
`python backend/scripts/make_samples.py`. Output is deterministic, and a test checks these
files match the generator.

**`checking_simple.csv`**: a clean business checking export with `Date,Description,Amount,Balance`,
`MM/DD/YYYY` dates and money out as negative. 45 rows covering:
- client ACH deposits with invoice references, Stripe payouts and Upwork withdrawals
- transfers to savings and credit card autopay
- an IRS estimated tax payment
- a monthly service fee and interest earned
- ATM withdrawals, checks (`CHECK #1043`) and Zelle/Venmo to and from invented people
- coworking, internet and phone bills

**`credit_card.csv`**: a business card export (`Date,Description,Amount`) where charges are
**positive** and payments/credits negative. 50 rows covering:
- recurring subscriptions at the same monthly amount (Adobe, Figma, Notion, Google Workspace, AWS)
- `UBER *TRIP` vs `UBER *EATS`, an airline and a hotel
- processor prefixes (`SQ *`, `TST*`), `AMAZON MKTPLACE` and `APPLE.COM/BILL`
- LinkedIn ads and Upwork service fees
- a foreign merchant followed by a foreign transaction fee
- a Best Buy purchase and its later `RETURN`
- an exact duplicate row (`SQ *JOES CAFE 9921` on 02/11)
- a `DISPUTE CREDIT` for an earlier purchase
- three `PAYMENT THANK YOU` rows
- personal rows (groceries, Netflix) and unknown merchants

**`bank_messy.csv`**: the same kind of checking data exported badly:
- UTF-8 BOM and `;` delimiter
- three junk lines before the header: an account line with a masked `****1234`, the statement
  period and a blank line
- a `Posting Date;Details;Debit;Credit;Balance` header and `05 Jan 2026` style dates
- debits mixing `$1,234.56` and trailing-minus `45.00-`
- an `OPENING BALANCE` row (skipped with a warning)
- blank lines between rows
- one impossible date (`31 Feb 2026`), which must become a row error
- a `PENDING` row
- a `TOTAL` footer (skipped with a warning)

**`credit_card.xlsx`**: card data in a different layout: `Transaction Date, Post Date,
Description, Category, Amount`. The dates are real Excel date cells and the amounts are numeric
cells. Charges are **negative** and payments positive. The bank's own `Category` column is kept
as raw data only.
