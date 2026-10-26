# Design

## Use Case

I picked a **freelance designer** as the target user. They have a business credit card, and at the end of the year (or each quarter) they need to figure out which transactions are deductible and under which category.

The main pain: statements have 100+ rows, most of which are obvious once you know the merchant, but going through them manually is tedious. A refund isn't an expense. A transfer to savings isn't spending. `ADOBE CREATIVE CLOUD` is obviously software. But `JOES CAFE 9921` could be a client lunch or just coffee - and the app should say so rather than guess.

---

## Categories

| Category | What goes here |
|---|---|
| Software & Subscriptions | Adobe CC, Figma, GitHub, Notion, Zoom, hosting |
| Travel & Transport | Uber, flights, hotels, parking, car rentals |
| Food & Dining | Restaurants, coffee shops, food delivery |
| Office & Supplies | Amazon purchases, Staples, FedEx, equipment |
| Marketing & Advertising | Facebook/Google ads, email marketing tools |
| Education & Training | Courses, conferences, books |
| Professional Services | Accountants, lawyers, freelancers paid via Upwork |
| Health & Wellness | Gym, pharmacy (personal but trackable) |
| Transfer / Non-Expense | Bank transfers, refunds, payroll deposits |
| **Needs Review** | Anything the app isn't confident about |

---

## How the Categorizer Works

The task said: no big AI model for the actual decisions. So I built a rule-based system with three stages. Each stage is a fallback for when the previous one can't find a match.

### Stage 1 — Merchant Lookup

A dictionary of ~100 known merchants maps directly to a category. This covers the majority of common freelancer expenses. The lookup is case-insensitive and does substring matching so `"ADOBE CREATIVE CLOUD 1234"` still hits `"adobe"`.

If found → return with 0.95 confidence. Done.

### Stage 2 — Regex Patterns

About 30 regex patterns cover broader classes of transactions that aren't in the merchant table. Things like:

- `UBER\s*\*` → Travel (catches `UBER * TRIP 8A9B2C`)
- `HOTEL|INN|SUITES` → Travel
- `RESTAURANT|CAFE|BISTRO` → Food & Dining
- `SUBSCRIPTION|SAAS` → Software
- `TRANSFER|ACH|WIRE` → Transfer

One thing I learned: order matters here. `UBER EATS` needs to be in the merchant map and match at stage 1, otherwise the `UBER` regex pattern fires first and sends it to Travel. Fixed that early on.

If a pattern matches → return with 0.80 confidence.

### Stage 3 — Keyword Scoring

Last resort. Each category has a list of keywords with weights. I score the description against all categories and pick the winner.

The confidence is normalised: (winner's score) / (total score) × 2, capped at 1.0. So if one category dominates it gets high confidence, if it's a close race between two categories it gets lower confidence.

If confidence < 0.45 → **Needs Review** instead of returning a bad guess.

### Refund Detection (runs before all stages)

Refunds are handled separately because they're not expenses regardless of what merchant they came from. If the description contains `REFUND`, `REVERSAL`, `CHARGEBACK`, or if the amount is positive (credit card statements show credits as positive), it goes to Transfer / Non-Expense.

---

## Edge Cases I Handled

| Case | What I did |
|---|---|
| Refunds | Positive amount or REFUND keyword → Transfer, not an expense |
| Unknown local businesses (`JOES CAFE 9921`) | Falls through to keyword scoring; if unclear → Needs Review |
| Gibberish POS codes (`XQZR9291 PMT A82`) | No keywords match → Needs Review |
| Mixed-case input | Normalized to uppercase before any matching |
| `$`, commas, parentheses in amounts | Stripped in the parser before amounts reach the categorizer |
| Empty description | Immediately → Needs Review |
| BOM in CSV files | Parser uses `utf-8-sig` encoding to strip it |

---

## Data Flow

```
Upload (CSV or OFX)
  → parser.py: detect format, extract rows, normalize dates/amounts
  → categorizer.py: for each row, run 3-stage pipeline
  → FastAPI: return categorized list as JSON
  → Next.js: render table, let user override any row
  → PATCH /transactions: save override, refresh summary
```
