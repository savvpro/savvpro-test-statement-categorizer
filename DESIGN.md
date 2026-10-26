# Design

## Use case: the freelance designer

A freelance designer pays business costs on one credit card: Adobe, Figma,
fonts, stock images, rideshare to client meetings, a coworking desk, meals
with clients. At tax time they need those costs grouped into categories, and
they need to know which charges are **not** costs at all.

The app reads their statement, sorts every row, and gives a total per
category plus a deductible total. Anything it cannot place goes to
**Needs review**, and the user fixes it in one click.

## Principle

> A wrong guess is worse than asking.

A wrong confident category quietly changes a tax number. A "Needs review"
row costs the user ten seconds. So every rule below prefers to ask.

## Pipeline

```
CSV -> parser.py -> categorizer.py (the brain) -> API -> React table
```

- `parser.py` turns messy CSV into clean transactions. Negative = money out,
  positive = money in.
- `rules.py` holds the keyword lists and the confidence threshold.
- `categorizer.py` decides. Every row gets a category, a confidence, a reason
  and a `needs_review` flag.

## How the brain decides, in order

1. **User rule first.** If the user already fixed this merchant, use that
   (confidence 1.0). The merchant is matched by a normalized key, so
   `JOES CAFE 9921` and `JOES CAFE 4410` are the same merchant.
2. **Zero amount** goes to review.
3. **Money out** (negative):
   - Transfer or card payment keyword: **Not spending**, so it is not a cost.
   - Merchant that sells many kinds of things (a store that could be office
     supplies, software or personal): **review**, with suggested options.
   - Exactly one category matches: use it (confidence 0.85).
   - Several categories match, or none: **review**.
4. **Money in** (positive):
   - Income keyword: **Income**.
   - Transfer or card payment: **Not spending**, not income.
   - Refund keyword with an earlier charge from the same merchant in this
     statement: **Refund: that category**, so it reduces that category.
   - Refund keyword with one clear keyword match but no original charge in the
     file: refund with lower confidence (0.8).
   - Refund keyword but the merchant is unclear: **review**.
   - No refund keyword but the merchant was paid earlier: **review**, because
     it could be a refund or something else.
   - Unknown source: **review**. Unknown money in is never assumed to be income.
5. **Safety net.** Any non-review result below the confidence threshold is
   moved to review.

Keywords match **whole words only**, so `RESTAURANT` does not match
`RESTAURANTS DEPOT`. Noise such as `POS`, `*`, `#1234` and long id numbers is
stripped before matching.

## Messy cases handled

| Case | Behavior |
|---|---|
| Refund | Money back, not income. Reduces the category of the original charge. |
| Transfer to savings / card payment | Not spending, not income. Excluded from totals. |
| Same word, two categories (`ZOOM VIDEO` and `ZOOM RESTAURANT`) | A later `ZOOM REFUND` goes to review, because we cannot tell which charge it belongs to. |
| A charge we could not place, then its refund | Review. We do not offset a charge we never understood. |
| Refund before its charge on the same day | Charges are processed before credits on the same date. |
| Duplicate rows | Flagged as **possible duplicate**, never removed. Two identical coffees can be real. |
| Ambiguous stores | Review with suggested options. |
| Card files that list purchases as positive | A checkbox flips the sign. |
| Different amount formats | `(45.00)`, `45.00-`, `$1,234.50`, or separate Debit / Credit columns. |
| Several date formats | ISO, US and day-first formats are accepted. |
| Bad rows | Skipped and listed with line number and reason. Nothing disappears silently. |
| Empty rows, BOM, NaN amounts | Ignored or rejected safely. |

## Totals

- Per-category totals count only confident rows. Review rows are shown
  separately with their count and total, so the user sees exactly what is
  still unsorted.
- Deductible total is every expense category except **Personal**.
- Not-spending rows are counted but excluded from all totals.

## Architecture choices

- **Stateless API.** The browser stores the user's fixes and re-sends the file
  with them. The backend recomputes everything. No database, no accounts, and
  no private financial data is kept on a server.
- **Decimal, not float**, for all money.
- Upload limits: `.csv` only, 5 MB max. User rules are validated against the
  known category list.
- CSV export escapes cells that start with `= + - @` to prevent spreadsheet
  formula injection.

## Known limits

- CSV only. No PDF or bank-specific formats.
- English keywords only.
- Refunds are matched to charges by the first word of the merchant name.
- Fixes live in the browser session. Reloading the page forgets them.
- Display currency is USD.