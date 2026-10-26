# API contract

Base URL: `http://localhost:8000` (frontend reads it from `NEXT_PUBLIC_API_URL`).
All responses are JSON unless noted. Errors always look like:

```json
{ "detail": "Human readable message" }
```

## Conventions

- `amount` is **signed**: negative = money out (a purchase, a fee, a transfer out),
  positive = money in (refund, card payment, income).
- `date` is ISO `YYYY-MM-DD`.
- Categories (fixed list, `GET /api/categories`):
  `Software & Subscriptions`, `Travel`, `Meals`, `Office Supplies`, `Internet & Phone`,
  `Advertising`, `Bank Fees`, `Income`, `Refund`, `Transfer (not spending)`,
  `Card Payment (not spending)`, `Personal`, `Needs Review`.

## Types

### Transaction

```json
{
  "id": 12,
  "statement_id": 3,
  "row_number": 5,
  "date": "2026-05-03",
  "description": "SQ *JOES CAFE 9921",
  "normalized_merchant": "JOES CAFE",
  "amount": -12.5,
  "currency": "USD",
  "category": "Needs Review",
  "confidence": 0.0,
  "reason": "No rule matched 'JOES CAFE'",
  "needs_review": true,
  "is_duplicate": false,
  "source": "none",
  "status": "needs_review",
  "notes": ["Date '03/05/2026' is ambiguous; read as month/day"]
}
```

- `source`: `"rule" | "learned" | "user" | "none"` (`none` = nothing matched).
- `status` (server-computed, drives the pill): `"auto" | "learned" | "user" | "needs_review" | "duplicate" | "not_spending"`.
  Priority: duplicate > needs_review > not_spending > user > learned > auto.

### Statement

```json
{
  "id": 3,
  "filename": "bank_a.csv",
  "uploaded_at": "2026-10-26T14:03:11",
  "row_count": 40,
  "warnings": ["Row 14 skipped: amount is missing"],
  "transactions": [ /* Transaction[] ordered by row_number */ ]
}
```

### StatementListItem

```json
{ "id": 3, "filename": "bank_a.csv", "uploaded_at": "2026-10-26T14:03:11", "row_count": 40, "needs_review_count": 6 }
```

### Summary

```json
{
  "statement_id": 3,
  "totals": {
    "transactions": 40,
    "auto_categorized": 31,
    "needs_review": 6,
    "duplicates": 1,
    "spending": 1234.56,
    "refunds": 30.0,
    "net_spending": 1204.56,
    "income": 2500.0,
    "not_spending": 1300.0
  },
  "categories": [
    { "category": "Software & Subscriptions", "kind": "spending", "total": 120.5, "count": 4 },
    { "category": "Refund", "kind": "refund", "total": 30.0, "count": 1 },
    { "category": "Transfer (not spending)", "kind": "not_spending", "total": 500.0, "count": 1 },
    { "category": "Needs Review", "kind": "review", "total": 87.0, "count": 6 }
  ]
}
```

- Every `total` is a **positive magnitude** (absolute value of the summed signed amounts).
- `kind`: `"spending" | "refund" | "income" | "not_spending" | "review"`.
- `spending` = money out across spending categories. `net_spending = spending - refunds`.
  Transfers and card payments are never in `spending`. Needs Review rows are not counted
  in any category total until fixed.
- `categories` only lists categories with `count > 0`, spending first sorted by total desc.

### LearnedRule

```json
{ "id": 1, "merchant": "JOES CAFE", "category": "Meals", "created_at": "2026-10-26T14:10:00", "times_applied": 2 }
```

## Endpoints

| Method | Path | Body | Returns |
| --- | --- | --- | --- |
| GET | `/api/health` | — | `{"status":"ok"}` |
| GET | `/api/categories` | — | `string[]` |
| POST | `/api/statements` | multipart `file` (`.csv`, ≤ 5 MB) | `Statement` (201) |
| POST | `/api/statements/sample?name=messy` | — (`name` ∈ `bank_a`, `bank_b`, `messy`; default `messy`) | `Statement` (201) |
| GET | `/api/statements` | — | `StatementListItem[]` newest first |
| GET | `/api/statements/{id}` | — | `Statement` |
| GET | `/api/statements/{id}/summary` | — | `Summary` |
| GET | `/api/statements/{id}/export` | — | `text/csv` download (`categorized_<filename>`) |
| PATCH | `/api/transactions/{id}` | `{"category": "Meals"}` | `{"transaction": Transaction, "learned_rule": LearnedRule \| null, "also_updated": number[]}` |
| GET | `/api/rules/learned` | — | `LearnedRule[]` |
| DELETE | `/api/rules/learned/{id}` | — | 204 |

### Upload errors (400)

- not a `.csv` file → `"Only .csv files are supported"`
- larger than 5 MB → `"File is larger than 5 MB"`
- empty file / no data rows → `"The file is empty"` / `"No transactions found in the file"`
- columns not recognised → `"Could not find a date column"` etc.

### PATCH behaviour

- Sets `category`, `source="user"`, `confidence=1.0`, `needs_review=false`,
  `is_duplicate=false`, reason `"Set by you"`.
- Unless the new category is `Needs Review`, saves a learned rule
  `normalized_merchant → category` (upsert), and applies it to other rows of the **same
  statement** with the same merchant that are not user-set and not duplicates; their ids
  are returned in `also_updated`. Future uploads match the rule (source `learned`, confidence 1.0).
- Unknown category → 422. Unknown id → 404.
