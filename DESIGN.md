# Design

## Use case

**LedgerLane** sorts a **rideshare / delivery driver's** bank and credit card statements for tax time (US Schedule C).

A driver who works for Uber, Lyft, DoorDash or Instacart mixes business and personal money on the same accounts. At tax
time they need to know: how much they earned, which costs are deductible (fuel, tolls, maintenance, phone, insurance…),
and what was personal. The app reads their statement, sorts every row, explains each decision, and asks about anything
it is not sure of. The result is totals per category and a CSV export for an accountant.

## Flow

```
CSV upload ─▶ ingest/parsing.py ─▶ ingest/normalize.py ─▶ brain/engine.py ─▶ services/statements.py ─▶ API / UI
               find columns,        clean merchant         per-row decision     duplicates, pending,
               fix signs, skip      names into a key       + confidence +       refunds, totals
               junk rows                                    reason
```

## The brain (`backend/app/brain/`)

No AI model is involved. `engine.py` holds the decision logic; `rules.py` holds the knowledge (patterns, merchants,
thresholds) as plain data so it can be read and extended without touching the logic.

Each row goes through six layers **in order**; the first layer that is sure decides:

| # | Layer | What it decides |
|---|---|---|
| 1 | Learned rules | A merchant the user already fixed gets the user's category (confidence 0.97). |
| 2 | Money movement | Card payments and transfers between own accounts are *not spending*. Zelle / Venmo / Cash App always go to review: they can be personal, business or a refund. |
| 3 | Money in | Platform payout words (`PAYOUT`, `DIRECT DEP`, `EARNINGS`…) from a known platform are income; `TIP` / `BONUS` / `QUEST` are tips & bonuses; refund words or money back from a known shop are refunds. A credit on the driver's own food order is a refund, not earnings. Money in from anything else is **not counted as income** until the user confirms. |
| 4 | Fees | Bank fees and card interest. |
| 5 | Known merchants | Ordered regex list (fuel, EV charging, car wash, maintenance, tolls, parking, phone, insurance, driver apps, supplies, restaurants, personal subscriptions, groceries) with sanity checks. |
| 6 | Fallback | Unknown merchants go to Needs Review. |

Every decision returns `category`, `confidence`, a human `reason`, the `rule` that fired, and, when sent to review,
a `suggestion` (the best guess) so the user can confirm with one click.

### When the app says "not sure"

A wrong guess is worse than asking, so these go to **Needs Review** with the reason:

- confidence below **0.75**;
- **ambiguous stores** that sell business and personal items (Amazon, 7-Eleven, Costco, Best Buy…);
- a **fuel-station charge under $15**: probably snacks, not fuel;
- **peer-to-peer** payments (Zelle, Venmo, Cash App);
- **money in from an unknown source** (a mobile deposit is not automatically income);
- **platform money in without payout words** (could be a refund);
- a **possible duplicate** (same date, description and amount) and **pending** charges (statement-level checks).

### Statement-level logic (`services/statements.py`)

- **Duplicates:** the second identical row goes to review, pointing at the first.
- **Pending:** a pending charge can change or disappear, so it goes to review with its suggested category.
- **Refunds:** a refund is linked to the purchase category at the same merchant and **reduces that category**; it is
  never counted as income.
- **Totals:** income, deductible expenses (net of refunds), personal spending, not-spending, and per-category totals.

### Learning from the user

When the user fixes a row, the app can apply the same category to the other *unsure* rows from that merchant, and
remembers `merchant + direction (money in or out) → category` in SQLite, so filing a purchase never re-files a refund from the same shop. The next statement uses it in layer 1. It never overwrites rows the brain
was already sure about.

## Reading messy statements (`backend/app/ingest/`)

- Header row found even after a preamble (bank name, account, period lines).
- Columns matched by synonym: `Date` / `Transaction Date` / `Posted Date`, `Description` / `Memo` / `Payee`…
- One signed `Amount` column, or separate `Debit` / `Credit` columns.
- Amounts like `$1,234.56`, `(45.10)`, `12.34-`, `99.00 CR`, `5.00 DR`; dates in six formats.
- **Sign convention:** card exports show purchases as positive and payments as negative. The parser detects this when
  the "PAYMENT THANK YOU" rows are negative *and* most other rows are positive (a phone bill on autopay does not fool it).
  The user can override it in the UI.
- Blank lines, `Total` / balance lines, zero-amount authorization holds and rows with an unreadable date or amount are
  skipped and **reported**, never silently dropped.
- Merchant names are cleaned (`SQ *`, `TST*`, `POS PURCHASE`, store numbers, masked card numbers, dates, state + ZIP) into
  a stable two-word key, so `SQ *JOES CAFE #9921 DALLAS TX` and `JOES CAFE 0412` match the same learned rule.

## Trade-offs and next steps

- Rules are regex lists. That keeps every decision explainable, but needs curating per region and per bank.
- The two-word merchant key can occasionally merge two different merchants that share their first two words.
- Next: PDF statements, multi-statement year view with mileage, per-user accounts, and an admin page to edit rules.
