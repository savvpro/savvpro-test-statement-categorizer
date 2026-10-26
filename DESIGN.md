# Design

## 1. Use case

**Customer:** a rideshare or delivery driver (Uber, Lyft, DoorDash, Instacart, Amazon Flex…)
who is a US sole proprietor and files **Schedule C**.

**Why this customer:** drivers usually run their business through one personal checking
account and one credit card, so business and personal spending are mixed together. At tax
time they need:

- **Income**: total gig platform payouts (Schedule C line 1).
- **Deductible expenses** grouped by Schedule C line: fuel and maintenance (line 9),
  tolls and parking, insurance (line 15), phone (line 25), and so on.
- **Everything else kept out of the totals**: groceries, Netflix, money moved to savings,
  card payments, and fines.

**The job, start to end:** upload a statement → every row is categorised → unsure rows
wait in *Needs Review* with suggestions → the user fixes them with one click (and the app
learns) → the user sees income, deductible expenses by Schedule C line and an estimated
net profit → the user exports a CSV for their tax software or accountant.

### Categories

| Category | Kind | Schedule C |
| --- | --- | --- |
| Gig Platform Income | income | line 1 |
| Other Business Income | income | line 6 |
| Fuel & EV Charging | expense | line 9 |
| Vehicle Maintenance & Car Wash | expense | line 9 |
| Tolls & Parking | expense | line 9 |
| Vehicle Insurance | expense | line 15 |
| Car Lease / Loan Payment | expense | line 20a |
| Phone & Data | expense | line 25 |
| Apps, Software & Tax Prep | expense | line 27a |
| Driver Supplies | expense | line 22 |
| Licenses, Registration & Checks | expense | line 23 |
| Bank Fees & Interest | expense | line 27a |
| Personal (not deductible) | personal | — |
| Transfers & Card Payments | transfer | — |

The **kind** decides how a row is counted. Income adds to income. Expense rows count as
spending, and refunds subtract from it. Personal rows are shown but never deducted.
Transfers are excluded from all totals.

Two domain choices are worth stating:

- **There is no "Meals" category.** A local driver is not away from their tax home
  overnight, so meals on shift are generally not deductible. Restaurants therefore go to
  *Personal*. A user who disagrees can change them, and the app learns.
- **Fuel/maintenance vs. mileage.** These are only deductible under the actual-expense
  method. The app still tracks them, because the user needs the numbers to choose a
  method, and the UI says so. Tolls and parking are deductible under either method.

## 2. Architecture

```
React UI ──HTTP──> FastAPI routes ──> StatementService ──> ingest.read_statement()  (file → signed rows)
                                              │         ──> brain.Categorizer          (row → decision)
                                              │         ──> duplicate checks / summary
                                              └──> SQLite (statements, transactions, user_rules)
```

- **`ingest/`** turns any supported file into `RawTransaction(date, description, amount)`.
  The amount is always signed from the user's point of view: + money in, − money out.
  Everything after this layer can rely on that.
- **`brain/`** is pure Python with no I/O. It is given one transaction and returns a
  `Decision`: category or `None`, confidence, reasons, suggestions and flags.
- **`services.py`** handles what needs the whole statement or the database: duplicates,
  statements imported twice, learned rules, re-applying rules, totals and export.

## 3. How the brain decides

### Step 0: normalise the description

Bank descriptions are full of noise. These two lines are the same coffee shop:

```
POS PURCHASE SQ *JOES CAFE 9921 SAN JOSE CA
PURCHASE AUTHORIZED ON 03/12 SQ *JOES CAFE #9921 SAN JOSE CA CARD 4417
```

`normalize.py` removes, in order:

1. Bank wrappers: `POS PURCHASE`, `PURCHASE AUTHORIZED ON 03/12`, `CHECKCARD 0312`.
2. Payment processors: `SQ *`, `TST*`, `PAYPAL *`.
3. Noise: card last-4, ACH codes (`PPD ID: …`), reference numbers, phone numbers, mixed
   IDs like `2K4LM19QX`, store numbers and a trailing US state.

Both lines become `JOES CAFE SAN JOSE` with the lookup key `joes cafe san jose`. Short
brand numbers like `PHILLIPS 66` are kept on purpose.

### Step 1: collect evidence, strongest tier first

The first tier that has an answer decides. Lower tiers can only add support or doubt.

| Tier | Evidence | Confidence |
| --- | --- | --- |
| 1 | **The user's own correction** for this merchant *and direction* | 0.99 |
| 2 | **Known merchant** in the knowledge base (428 brand/pattern rules, 51 of them "ambiguous") | 0.70–0.96 |
| 3 | **Keyword** in the text (`TOLL`, `CAR WASH`, `CAFE`, `FUEL`) | 0.60–0.84 |
| 4 | **Misspelt known merchant** (difflib ratio ≥ 0.84, e.g. `CHEVRN`) | 0.70 |
| 5 | **The bank's own category column**, if the export has one | 0.60 |

How the tiers combine:

- If the bank's category agrees with the decision, confidence goes up (+0.03 for a
  merchant match, +0.08 for weaker evidence). If it disagrees, a keyword-based decision
  loses 0.10. Two weak signals that agree can therefore clear the threshold together.
  `SQ *JOES CAFE` alone scores 0.68 and goes to review. With the bank's "Food & Drink"
  label it scores 0.76 and is categorised automatically.
- **Ambiguous merchants** (Amazon, Walmart, Costco, Best Buy, Venmo, Zelle, 7-Eleven,
  bare deposits) are in the knowledge base with no category. They **always go to review**
  with suggestions. The only exception is a keyword that settles the question:
  `7-ELEVEN FUEL` becomes fuel.
- **Conflicting evidence:** if a strong keyword in a *different* part of the description
  points to a different category, the row goes to review. For example, in `SHELL CAR WASH`
  the brand says fuel and the words say car wash. The keyword is ignored when it lies inside
  the merchant match (`PARKING CITATION` is matched as a whole by the "fine" rule).
- **Rule priority within the knowledge base:** specific merchants beat ambiguous ones,
  then higher confidence wins, then the longer match. So `COSTCO GAS` is fuel even though
  `COSTCO` alone is ambiguous.

### Step 2: sanity checks (they can only lower confidence)

**Direction.** Every rule says whether it expects money in, out or either.

- *Money in from a merchant you normally pay* is a **refund**. It keeps the merchant's
  category and is flagged, so it **reduces** that category's total instead of counting as
  income. If the bank wrote `REFUND`/`RETURN`/`REVERSAL`, confidence is unchanged.
  Otherwise it drops by 0.15. Rules written for incoming money, like fee reversals and card
  rewards, are not penalised.
- *Money in from an unknown source* is **never assumed to be income**. It goes to review
  with "not counted as income until you confirm it".
- *Money in from a gig platform without a payout label* (`UBER BV $25.00`) could be
  earnings or a refund on an Uber Eats order. It goes to review.
- *Money out to an income category* (possible clawback) goes to review.
- `UBER USA EDI PYMNTS` (in) is income. `UBER *EATS` and `UBER *TRIP` (out) are personal.
  The same brand is handled differently depending on direction.

**Amount.** Each expense category has a normal maximum, e.g. $200 for fuel and $150 for
tolls. A $412 charge at Shell goes to review. Gas-station rules also have a *minimum*:
$4.50 at Shell is probably snacks, so it goes to review with *Fuel* and *Personal* as the
suggestions.

### Step 3: threshold

If confidence is below **0.75** (configurable), the guess is withdrawn: the category
becomes `None`, the guess becomes the first suggestion, and the row joins *Needs Review*.
A wrong guess is worse than asking, so the review queue has the best guesses ready as
one-click buttons.

Every decision stores **why** it was made (`reasons`) and **where the decision came from**
(`source`). The UI shows both when you click the status badge.

### Statement-level checks (in `services.py`)

- **Duplicate rows:** if two rows in the same file have the same date, amount and raw
  description, the second goes to review with a link to the first.
- **Imported twice:** if a row exactly matches a row in another statement (for example,
  overlapping date ranges), it goes to review.
- These flags survive re-categorisation, so learning a rule never hides a duplicate.

### Learning from the user

When a user fixes a row with "remember" on:

1. A rule `(merchant_key, direction) → category` is saved. Direction is part of the key,
   so teaching it that `JOES CAFE` purchases are personal says nothing about money coming
   *from* Joe's Cafe.
2. The brain runs again on that merchant's rows that the user has not touched, in the
   current statement. All the sanity checks still apply: a learned "Shell = fuel" rule
   still sends a $450 Shell charge to review.
3. Future uploads use the rule as tier 1.

Rows the user set by hand are marked `reviewed` and are never overwritten. The brain's
original decision is kept in `engine_category` for auditing.

## 4. Messy input handled by ingestion

| Problem | Handling |
| --- | --- |
| Account info lines above the header | Scans up to 25 lines for a header row |
| No header at all | Finds the date, amount and description columns from the data |
| `;` / tab / `\|` delimiters, quoted commas | Picks the delimiter that splits the most lines into the same number of columns (`csv.Sniffer` fails when the preamble has a different width) |
| BOM, Windows-1252 encoding | Tries `utf-8-sig`, then `cp1252` |
| `$1,234.56`, `(12.00)`, `12.00-`, `45.00 CR`, `1.234,56` | `parse_amount` |
| `MM/DD` vs `DD/MM` | One format is chosen **per file**, not per row. Day-first only wins if a day is above 12. Ambiguous files get a warning |
| Separate Debit/Credit columns, or a Type column | The direction comes from the columns |
| Charges positive (cards) vs negative (banks) | Uses the sign of `PAYMENT THANK YOU` rows if any, otherwise the sign of most rows. The user can override |
| Pending rows, zero-amount holds, total/balance lines, bad amounts | Skipped and listed with the reason, never silently dropped |
| Memo column | Added to the description |
| OFX/QFX | Parsed directly. OFX amounts are already signed for the account holder |

## 5. Production considerations

- **Money** is stored in integer cents and parsed with `Decimal`. There are no floats.
- **Security:** uploads are checked for extension and size, and the size is enforced while
  reading. Sample imports use fixed names, so they can't be used for path traversal. SQL
  uses parameters. CSV export escapes cells starting with `=`, `+`, `-` or `@` (formula
  injection). CORS only allows listed origins. There are no secrets in the repo.
- **Errors:** parse errors return a user-friendly 422. Unknown IDs return 404.
- **Testability:** the brain is pure and takes its rules and threshold as parameters. The
  app is built with a factory (`create_app(settings)`), so tests use temporary databases.
- **CI:** lint, format check, 135 backend tests, frontend typecheck, tests and build.

### Known limits and next steps

- Single user, with no authentication. A real product would add accounts and keep each
  user's rules separate.
- Phone, insurance and car costs are often only *partly* business use. A business-use
  percentage per category would make the totals more accurate.
- PDF statements are not supported. Most banks offer CSV/OFX downloads.
- The knowledge base is US-centric and hand-curated. It is the part that needs regular
  maintenance, and its integrity is tested: every rule must point to a real category.
