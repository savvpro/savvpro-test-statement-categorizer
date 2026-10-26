# Design

## Use case

A freelance designer uploads their business credit card statement at tax time. The app labels each
transaction with a tax category and shows a total per category. Rows it is unsure about go to
**Needs Review** so the user can fix them. A wrong guess is worse than asking.

## Flow

```
Upload CSV -> parse rows -> normalize description -> classify -> totals -> user reviews and fixes
```

## How the brain decides

The brain is `backend/app/brain/`. It is pure rules, with no AI model and no network calls.

1. **Normalize** (`normalizer.py`): uppercase, remove digits and symbols, collapse spaces.
   `UBER *TRIP 8821` becomes `UBER TRIP`, so one rule matches every variant.
2. **Decide** (`classifier.py`), in this order, first match wins:
   1. Empty description: Needs Review
   2. Transfer keywords (`TRANSFER TO`, `TRANSFER FROM`...): **Transfer**, shown but not counted as spending
   3. Zero amount: Needs Review
   4. Money in (positive):
      - refund keyword (`REFUND`, `REVERSAL`, `RETURN`): **Refund** (money back, not income)
      - income keyword (`CLIENT PAYMENT`, `INVOICE`...): **Income**
      - anything else: Needs Review
   5. Money out (negative): match merchant keywords
      - no match: Needs Review (unknown merchant)
      - conflict: Needs Review
      - ambiguous merchant (Amazon, Walmart, PayPal...): Needs Review
      - otherwise the matched category

Every result carries a short **reason** ("matched 'ADOBE'", "unknown merchant") shown in the UI,
so the user can see why a row got its category.

### Why these choices

- **Longest keyword wins.** `UBER EATS` (Meals) beats `UBER` (Travel). `AMAZON WEB SERVICES`
  (Software) beats `AMAZON` (ambiguous). If two different categories tie, it is a conflict and goes to review.
- **Whole-word matching** so a short keyword never matches inside another word.
- **The sign of the amount matters.** The same merchant can be a purchase or a refund.
- **Rules are data.** Merchants live in dictionaries at the top of `classifier.py`, so adding one is a one-line change.
- **Totals are computed in one place** (backend) and reused after user edits through `/api/totals`.

## Messy cases handled

| Case | Behavior |
|---|---|
| Refund | Category Refund, not Income |
| Transfer to savings | Category Transfer, not spending |
| Unknown merchant | Needs Review |
| Ambiguous merchant (Amazon) | Needs Review |
| Duplicate rows | Flagged "possible duplicate", kept (two identical coffees can be real) |
| Mixed date formats | Day-first formats and ISO accepted |
| `(45.00)`, `$1,200.50`, `45.00-` | Parsed with `Decimal` (no float rounding errors) |
| Bad row (invalid date or amount) | Skipped and listed with its line number; other rows still work |
| Blank rows | Ignored |
| Empty file, wrong columns, wrong extension, huge file | Clear error (400, 413, 422), no crash |
| Excel BOM, mixed-case headers | Handled |

## Assumptions

- Negative amount means money out. Some banks export the opposite; this is not auto-detected.
- Dates like `03/10/2026` are read day first (3 October), because the client is Australian.
- One currency per statement.

## Limitations and next steps

 User corrections are kept in the browser only, so they are lost on reload.
 Rules are English merchants only. A next step is learning from the user's corrections
 ("always put JOES CAFE in Meals") and storing them.
 Sign convention auto-detection and CSV export of the final result.