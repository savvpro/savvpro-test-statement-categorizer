# Design

## Use case

**Customer:** a freelance designer who pays for software, travel and client meals on a
business credit card and needs the statement sorted for tax time.

**Categories:** Software, Travel, Meals, Office, Marketing, Internet & Phone, Personal,
plus special ones: Income, Refund, Transfer (not spending), Duplicate (ignore), Needs Review.

Each category has a tax hint: `yes`, `partial` (Meals, Internet & Phone), `no`, `n/a`, `unknown`.

## Flow

```
Upload CSV -> Parse -> Normalise -> Brain (per row) -> Category + confidence + reason
          -> User reviews and fixes -> Totals recalculate
```

## The brain

Pure rule-based Python in `backend/app/brain/`. No AI model is called.
Rules live in `data/rules.json`; each rule type is its own file in `brain/checks/`.

Each row passes through checks **in this order; the first match decides**:

| # | Check | Rule | Result |
|---|---|---|---|
| 1 | Transfer | Whole-word match: TRANSFER, AUTOPAY, CREDIT CARD PAYMENT, ... | Transfer (not spending) |
| 2 | Currency | Currency is not USD | Needs Review (amount not converted) |
| 3 | Refund | Money in + REFUND / RETURN / REVERSAL / CHARGEBACK | Refund |
|   |        | Refund word but money out | Needs Review |
| 4 | Income | Money in + CLIENT / INVOICE / STRIPE PAYOUT / ... | Income |
| 5 | Keyword | Merchant keyword, longest match wins (`UBER EATS` beats `UBER`) | Category, or Needs Review |
| 6 | Fallback | Nothing matched | Needs Review |

After the checks, a **duplicate pass** compares (date, description, amount, currency).
A repeat is moved to Needs Review with the reason "Possible duplicate of row N".

### When the brain is "not sure"

The task says a wrong guess is worse than asking, so these always become **Needs Review**
with `confidence: low`:

- Unknown merchant (`JOES CAFE`)
- Ambiguous merchants that are business or personal (`AMAZON`, `WALMART`, `TARGET`)
- Money **in** from an expense merchant (`ADOBE SYSTEMS +20.00`): maybe a refund, maybe not
- Money **in** from an unknown source
- Refund wording but money went out
- Foreign currency
- Possible duplicates

## Messy cases handled

| Case | Handling |
|---|---|
| Refund | Its own category. Subtracted from expenses, never added to income |
| Transfer / card payment | Not spending; excluded from totals |
| Duplicate row | **Flagged, not deleted.** Two identical coffees can be real, so the user decides |
| Recurring subscription | Same amount on a different date is not a duplicate |
| Merchant noise | `UBER *TRIP 8821` becomes `UBER TRIP` (symbols and number IDs removed) |
| Date formats | ISO, `MM/DD/YYYY`, then `DD/MM/YYYY` as fallback |
| Amount formats | `-5.00`, `(5.00)`, `5.00-`, `$5`, `1,200.00` |
| Foreign currency | Not converted (no rates); flagged for review |
| Bad rows | Skipped **and reported** in `skipped`, never silently lost |
| Bad file | Clear 400 error (empty, missing columns, wrong encoding); 413 if over 2 MB |

## Totals

- `expenses` = money out in confirmed expense categories
- `refunds` = total in the Refund category
- `net_expenses` = expenses - refunds
- `income` = total in the Income category
- Transfers and ignored duplicates are excluded
- **Needs Review rows are excluded from expense totals until the user resolves them**,
  so the numbers never include a guess.

## Decisions and trade-offs

- **First match wins** keeps the brain easy to explain and test. Every decision has a reason string.
- **Rules in JSON**: keywords change without code changes.
- **One file per check**: a new rule is a new file added to the `CHECKS` list.
- **Store behind an interface** (`services/store.py`): in memory now, database later.
- **Duplicate detection is my own addition**, not in the task. A statement export that
  repeats a row is a common real-world problem.

## Assumptions and limitations

- `10/02/2026` is read as month/day. Statements with day/month dates that are also valid
  month/day (like `03/04/2026`) are ambiguous; a per-upload date-format option would fix this.
- No currency conversion.
- Rules are keyword based, so unseen merchants go to review. Learning from user corrections
  (saving a fixed merchant as a new rule) is a natural next step.
- One statement at a time, kept in memory; no users or persistence.
- CSV only (no PDF).