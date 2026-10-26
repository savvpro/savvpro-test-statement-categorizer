# Design: Freelance Designer Statement Categorizer

## Use case

**Customer:** Alex, a freelance UI/UX designer filing Schedule C–style business expenses at tax time.

**Input:** Exports from a business credit card (CSV). Descriptions are noisy: mixed case, store numbers, payment credits, and internal transfers.

**Goal:** Every row gets a tax-relevant category or an explicit **Needs Review** flag. Alex fixes uncertain rows, then uses category totals for bookkeeping—not a wrong silent guess.

## Flow

```
Upload CSV → Parser normalizes rows → Brain (rules) → UI review → User overrides → Updated totals
```

## Parser (`backend/app/parser/statement_parser.py`)

Real exports differ by bank. The parser:

1. Sniffs delimiter (`,`, `;`, tab).
2. Scans the first ~15 rows to find a header line (needs date + description + amount or debit/credit).
3. Maps common column aliases (`Memo`, `Payee`, `Posting Date`, etc.).
4. Parses amounts with `$`, commas, parentheses (accounting negatives), and separate debit/credit columns.
5. Skips blank lines and rows without a usable amount.

**Failure modes handled:** missing columns, empty files, header not on row 1.

## The brain (`backend/app/brain/categorizer.py`)

**No LLM.** Decisions are ordered rules on normalized descriptions and amounts.

### Decision order

1. **Transfer / not spending** — patterns like `TRANSFER TO`, `PAYMENT THANK YOU`, `SAVINGS`. These are not deductible business spend.
2. **Refund** — keywords `REFUND`, `REVERSAL`, `CHARGEBACK`, etc. Refunds are credits, not income.
3. **Client income on card** — large incoming credits labeled payroll/client payment → not spending (edge case on mixed exports).
4. **Positive amount without refund text** — small credits default to **Refund** (medium confidence); large ones → **Needs Review** (low confidence).
5. **Merchant rules** — regex lists for software (Adobe, Figma), travel (Uber trip), meals (café patterns), marketing, equipment, utilities, etc. Some matches are **medium** confidence (e.g. generic “café” or Amazon marketplace) so the UI shows caution.
6. **Generic store ID** — descriptions ending in long numeric IDs (e.g. `JOES CAFE 9921`) → **Needs Review** (unknown).
7. **Default** — **Needs Review** with reason text.

### Philosophy

- **High confidence** only for distinctive vendors or clear non-spend/refund patterns.
- **Medium** when the pattern is broad (food, office retail).
- **Unknown / Needs Review** when a wrong label would misstate taxes.

### Categories

| Category | Typical examples |
|----------|------------------|
| Software & Subscriptions | Adobe, Figma, Notion |
| Travel & Transportation | Uber trip, airlines |
| Meals & Entertainment | Starbucks, DoorDash |
| Office Supplies | Staples, Amazon marketplace |
| Professional Services | Upwork, CPA |
| Marketing & Advertising | Google Ads |
| Equipment & Hardware | Apple Store, B&H |
| Utilities & Internet | Comcast, Verizon |
| Transfer / Not Spending | Savings transfer, card payment |
| Refund | Merchant credits |
| Needs Review | Unknown merchants |

## API

- `POST /api/categorize` — upload CSV, returns categorized rows + summaries.
- `PATCH /api/transactions` — user override; summaries recalculate using `user_category`.
- `GET /api/categories` — list for dropdowns.

Session state is in-memory (single-user local demo).

## Frontend

React (Vite): upload, summary cards, filter “Needs review”, per-row category `<select>`, confidence badges, and short “why” explanations from the brain.

## Sample data

`sample_data/freelance_designer_statement.csv` — entirely fictional merchants and amounts.
