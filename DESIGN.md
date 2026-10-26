# DESIGN

## Use case

A freelance software developer in Lahore is paid in USD through Payoneer and pays local bills from a PKR account at a fictional bank ("Ravi Commerce Bank Ltd"). At tax time they need every statement row sorted into a category, and the rows nobody can be sure about set aside for a human. The app reads one CSV format (`Date DD-MM-YYYY, Description, Debit, Credit, Balance`), categorizes each row, and reports the uncertain ones as **Needs Review**.

The categorizer is plain Python rules. No LLM or other AI model takes part in any decision, at runtime or in tests. The guiding principle is that a wrong guess is worse than asking: when the brain is not sure, it says so.

## Pipeline

```
CSV text -> parser -> normalizer -> engine (ordered rules) -> passes (whole statement) -> API -> UI
                                                                                          ^
                                                                          user fixes Needs Review rows
```

The code is in `backend/app/`. `cd backend && conda run -n assigment python summarize_sample.py` prints the category counts and the Needs Review list for the sample file.

On the 75-row sample the brain produces 7 rows in Needs Review plus 1 possible duplicate flagged for review (8 rows marked for review). Income is PKR 1,010,000 and spending is PKR 530,601.

## Categories

Income, Transfer, Software & Tools, Utilities, Internet & Phone, Rent/Office, Travel & Transport, Entertainment, Food, Groceries, Shopping, Health, Education, Taxes, Bank Fees, Refund, Cash Withdrawal, and Needs Review.

`Transfer` is not spending. It is used for moves between the user's own accounts and for a failed transaction together with its reversal. `Needs Review` is where the brain puts doubt. It is not an answer, so a user cannot assign it.

## Parsing

- Dates are parsed with the explicit format `%d-%m-%Y`.
- Debit and Credit are merged into one signed `Decimal`: credit positive, debit negative. Money is never a float.
- Thousands separators (`1,173,930`) and empty cells are handled.
- A bad row (invalid date, both or neither of Debit and Credit, a non-numeric or negative amount, `NaN`, an empty description) does not stop the run. It is skipped and reported with its line number. Blank lines are ignored. A missing required column is an error, because nothing can be parsed without it.

## Normalizing

Before matching, the description is uppercased and whitespace is collapsed. Masked card or account numbers (`0042****7781`), `*`, the USD amount, and trailing order or store numbers (`4471920`, `2K4LP8`) are removed, so `FOODPANDA*ORDER 4471920` becomes `FOODPANDA ORDER`. Lowercase and double-spaced descriptions therefore match the same rules. The original text is kept next to the normalized text. A USD amount in the description is remembered as a flag (`usd_hint`) because a foreign-currency charge is a signal, not a category.

## Rule matching and confidence

Rules are data in `rules.py`: an ordered list of `Rule(kind, pattern, category, confidence, reason, direction, usd_only)`. The engine tries them in order and the **first match wins**, so specific rules sit above general ones.

- **kind** is `exact` (the normalized text equals the pattern), `keyword` (a whole-word match) or `regex`.
- **direction** limits a rule to debits or credits. `PAYONEER` is Income only as a credit, and merchant rules apply to debits only, so an unknown credit never becomes a merchant category.
- **confidence** is 0 to 1. Known merchants carry 0.85 to 0.95. Deliberately ambiguous merchants carry 0.3.
- **threshold**: `REVIEW_THRESHOLD = 0.7`. `Transaction.assign` is the one place a result is stored. Under the threshold the category becomes Needs Review, and the original suggestion stays in the reason text (for example `suggested Software & Tools`).
- **reason**: every row stores a short sentence saying which rule fired. The UI shows it.
- If no rule matches, the row is Needs Review with confidence 0. There is no default category.

Order matters in a few places. Bank fees sit above Cash Withdrawal because `WHT ON CASH WDL` contains `CASH WDL`. The known ambiguous merchants sit above the generic ones so they cannot be absorbed by them. The last rule catches a USD charge from an unknown merchant and suggests Software & Tools at 0.5, which is below the threshold, so it goes to review. Only known vendors (GitHub, OpenAI, Namecheap, AWS, Figma, Adobe, Notion, DigitalOcean) are Software & Tools outright.

### Rows that always go to Needs Review

| Row | Why |
|---|---|
| `AMZN MKTP US*...` | Could be tools, shopping or personal |
| `M/S ... TRADERS` | Payment to a firm, purpose unknown |
| `RAAST P2P TO/FROM <person>` | An individual, purpose unknown |
| `IBFT` that is not a recognised own account | Same reason |
| `JAZZCASH ... TOPUP` | Own wallet or someone else's is unknown |
| `LIBERTY BOOKS` | Education or Shopping (see tradeoffs) |
| A `FAILED` or `REVERSAL` row with no partner | Cannot confirm it nets to zero |
| Unknown merchant, unknown credit | Never guessed |

## Special passes

Passes run after the rules and look at the whole statement (`passes.py`), in this order.

1. **Own-account transfers.** `IBFT`, `ITFT` or `FUND TRANSFER` with `TO` or `FROM` and `SAVINGS`, `OWN` or `SELF` becomes Transfer (0.95) with flag `transfer`. It overrides the generic `IBFT` review rule.
2. **Refunds.** A credit containing `REFUND` or `CHARGEBACK` becomes Refund, not Income. The pass looks for an earlier debit from the same merchant (the first word of the description), remembers it in `refund_of`, and says in the reason whether this is a full refund (0.95), a partial one (0.85), or has no matching purchase in this statement (0.75).
3. **Failed transaction and reversal.** A debit containing `FAILED` is paired with a `REVERSAL` credit of the same amount within 7 days. Both become Transfer (0.9) with flag `reversal` and a reason showing the net of 0, so neither counts as spending.
4. **Duplicates.** A debit with the same date, normalized description and amount as an earlier row gets flag `duplicate`, is marked for review, and keeps its category. The reason names the earlier row. The first row is left alone.

## API

FastAPI app in `backend/app/main.py`. State is one in-memory statement (`store.py`): a new upload replaces the old one, and a restart clears it. CORS allows `http://localhost:3000`.

| Endpoint | Behaviour |
|---|---|
| `POST /upload` | Multipart CSV in field `file`. Must end in `.csv`, be at most 1 MB, be UTF-8, and contain the five columns. Otherwise `400` with a readable `detail`. Bad rows are skipped and listed in `skipped_rows`. A file with no valid rows is a `400`. Returns `{transactions, skipped_rows}`. |
| `GET /transactions` | Optional `?needs_review=true\|false` and `?category=...`. |
| `PATCH /transactions/{id}` | Body `{"category": "..."}`. The category must be in `GET /categories` (`400` otherwise, `404` for an unknown id). It sets `user_edited`, clears `needs_review`, sets confidence 1.0 and the reason "Edited by user". Returns the full transaction list. |
| `GET /summary` | Net per category, `total_income`, `total_spending`, `needs_review_count`. Computed on each call, so it reflects edits. |
| `GET /categories` | The categories a user can assign (everything except Needs Review). |

**Money is a string in JSON** (`"-1840"`). Pydantic encodes `Decimal` that way, and a string never loses precision.

**Summary rules.** `total_income` is the sum of Income rows. `total_spending` is the sum of debits outside Transfer, Refund and Income, so Needs Review debits and duplicates are included. A Refund row remembers the purchase it pays back. In the summary it is booked against that purchase's category, so that category's `net` shrinks and `total_spending` drops by the refunded amount. A refund with no matching purchase stays under Refund and does not touch spending. Because the link follows the purchase, re-categorizing the purchase moves its refund too. Each category's `net` is signed: debits negative, credits positive.

## Frontend

One page (`frontend/app/page.tsx`; Next.js App Router, TypeScript, plain CSS, no UI library). The page owns state and network calls. `frontend/components/` holds small presentational pieces: `UploadZone`, `SummaryCards`, `CategoryBars`, `FilterBar`, `TransactionsTable`.

**Data flow.** On load the page asks `GET /categories` (this also surfaces an "API is down" message) and `GET /transactions`, so a statement still held by the backend reappears after a refresh. An upload posts the CSV, stores the returned rows, then fetches `GET /summary`. An edit calls `PATCH /transactions/{id}`, replaces the whole row list with the response, then refetches `/summary`. The summary is never computed in the browser, so it always matches the backend.

**Layout.** A quiet finance dashboard: a header, a drag-and-drop upload zone (also a keyboard-focusable file input), four stat cards (Income, Spending, Net, Needs Review), category totals as CSS bars, and the transactions table with a sticky header. The Needs Review card is a button that switches to the Needs Review tab. Amounts are right-aligned with a `+` or `-` sign and a green or red colour. The reason is a muted second line under each description. Confidence is a small bar plus a percent. Needs Review rows are tinted amber. Badges mark Needs Review, Edited by you, Duplicate, Reversal, Transfer and Refund of #n. The filter bar has tabs (All, Needs Review, Edited), a category select and a description search, which combine, plus a live "Showing n of m rows" count. There is a toast after an edit, a skeleton during the first load, and empty states. On narrow screens the cards go to two columns and the table scrolls sideways inside its card.

**Styling.** Colours, radius and spacing are CSS variables at the top of `globals.css`. A dark palette follows `prefers-color-scheme` by redefining the same variables, so there is no theme toggle. The font is IBM Plex Sans through `next/font`.

**Decisions.**
- Money stays a string end to end. `Intl.NumberFormat` formats the string directly, with no float round trip, and the debit or credit colour comes from the leading `-`. The only derived figure, Net (income minus spending), is computed with BigInt cents in `lib/format.ts`, so it is exact. Bar widths use `Number()` for proportion only.
- `lib/api.ts` is the only place that calls `fetch`. It turns network failures and FastAPI error bodies into one readable error message.
- State is plain `useState`. The backend holds one statement, so the page does too.
- The API base URL comes from `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`).

## Tradeoffs

- **First match wins** instead of scoring every rule. It is easy to read and debug, at the cost of ordering rules carefully.
- **Duplicates use the normalized text**, so two orders with different order numbers but the same merchant, amount and day are also flagged. The row is only flagged for review, which errs on the safe side.
- **Duplicates still count as spending.** They keep their category and their `duplicate` flag and might be real charges. The user decides.
- **A failed ATM withdrawal plus its reversal is Transfer**, so the pair is never counted as spending and the net effect of 0 is visible in the reason.
- **Needs Review cannot be assigned by the user.** It marks doubt, not an answer, so an edit always resolves a row.
- **Liberty Books goes to review** because a bookstore could be Education or Shopping.
- **Netflix is Entertainment** (0.9). **PSO fuel and Careem trips are Travel & Transport** (0.85).
- **In-memory storage**, no database. A reviewer can run the app in minutes, and the statement is a single upload.

## Known limits

- One CSV format and one currency (PKR). USD appears only as a hint inside the description.
- Merchant coverage is a small list of common Pakistani and international names. Anything else goes to Needs Review.
- Own-account detection relies on words such as `SAVINGS`, not on account numbers, because masked digits are stripped.
- The reversal window is fixed at 7 days.
- Rules do not learn from user corrections.
- State is in memory only: one statement at a time, cleared on restart.
- The UI does not paginate, has no undo for an edit, and has no dark-mode toggle.
- The UI has no browser-level end-to-end test. Only the formatting helpers have unit tests (Vitest).
