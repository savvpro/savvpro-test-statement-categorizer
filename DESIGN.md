# Design: Bank Statement Categorizer

## 1. The use case

The user is a freelance software developer in Pakistan. Clients pay in dollars through Upwork, Toptal, Payoneer, Wise or straight to the bank. Money gets spent on GitHub, AWS, the home internet bill, the odd Careem ride and groceries, often from the same account.

At tax time they need to know, per currency:

- how much business income came in,
- what the business spent and on what,
- how much tax the bank already took (advance tax on export proceeds, withholding tax, FED on bank charges),
- and which rows are personal or just money moving between their own accounts.

The app does that sorting and is honest about the rows it can't sort.

## 2. Principles

1. **The brain is my code.** `backend/app/categorizer/engine.py` plus the rules in `rules.yaml`. No AI model is called anywhere in the decision.
2. **Decide only when a rule clearly applies.** Otherwise the row goes to review, with the reason and, where there is one, a suggested category.
3. **Every decision explains itself**, and names the rule that made it.
4. **Keep the source.** The original description, the row or page and line it came from, and the running balance are stored, so any row can be checked against the statement.
5. **Nothing is learned silently.** A fix changes one row. A rule exists only if the user creates it.
6. **Money stays correct.** Refunds are not income. Transfers are not income or spending. PKR and USD never meet. Amounts use `Decimal` and are stored as whole paisa or cents.

## 3. Flow

```text
upload (CSV or PDF)
   |
   |-- CSV  -> find the header row, map column names
   |-- PDF  -> pdfplumber words with positions
   |           page with no text? -> render it and run Tesseract OCR
   |           both -> rebuild table rows from word positions (layout.py)
   v
clean rows (rows.py)  - same checks for every source
   - skip balance and total lines (and remember the opening balance)
   - decide the date format once for the whole file
   - decide the currency once (column, header, or user's choice)
   - turn debit/credit, DR/CR, brackets and minus signs into one signed amount
   - rows that can't be read -> reported, not imported, not guessed
   - put newest-first statements into date order
   - check each running balance; flag rows that don't add up
   - flag low OCR confidence, and repeated rows in the file
   v
the brain (engine.py)  - one decision per row
   v
save (SQLite) -> show on the page -> user reviews, fixes, makes rules -> totals and CSV export
```

## 4. Three separate fields: type, category, status

My first draft mixed these up ("Refund" and "Needs Review" were both categories). Now they are separate:

| Field | Values | Meaning |
|---|---|---|
| `category` | Business Income, Software & Subscriptions, Cloud & Hosting, Internet & Phone, Platform & Payment Fees, Bank Charges, Office & Equipment, Travel & Transport, Meals, Utilities, Tax Deducted, Transfer, Personal | Which bucket the money belongs to. Empty while the row waits for review. |
| `type` | income, expense, transfer, refund, personal, unknown | What kind of movement it is. A GitHub refund has type `refund` and category Software & Subscriptions, so it lowers that category. |
| `status` | `auto`, `needs_review`, `user_corrected` | Who decided. Only `auto` and `user_corrected` rows count in totals. |

The database enforces it: a row that isn't in review must have a category.

Each category has a kind (income, expense, tax, transfer, personal). Totals are built from the kind, so tax taken by the bank is shown apart from business spending, and transfers and personal rows are listed as "not counted".

## 5. How the brain decides

The engine reads the rules in stages, in this order. **The first stage with a matching rule decides the row.**

| Order | Stage | Examples | Why it comes here |
|---|---|---|---|
| 1 | Your rules | anything you created | You told the app what this is. |
| 2 | Tax | WHT, ADV TAX, FED, EXCISE DUTY | "FED ON SMS ALERT CHARGES" is tax, not a bank charge. |
| 3 | Bank charges | SMS ALERT, SERVICE CHARGES, ANNUAL FEE | Bank fees are their own category. |
| 4 | Cash | ATM, CASH WITHDRAWAL | Always review: nobody knows what cash bought. |
| 5 | Transfers | TRANSFER TO SAVINGS, OWN ACCOUNT, CURRENCY CONVERSION | Clear own-account moves are decided. IBFT, RAAST and FUNDS TRANSFER always go to review, because they may go to someone else. |
| 6 | Merchants and payers | GITHUB, AWS, UPWORK, PAYONEER, DARAZ, CAREEM, NETFLIX | Who the money went to or came from. |

All patterns match **whole words** in the upper-cased description, so `WISE` doesn't match `OTHERWISE`.

### Inside a stage: the most specific rule wins

1. `exact` beats `starts_with`, which beats `contains`.
2. A longer pattern that contains a shorter one wins: `AMAZON WEB SERVICES` (Cloud & Hosting) beats `AMAZON` (Office & Equipment), and `UBER EATS` (Meals) beats `UBER` (Travel).
3. If two rules are still tied and disagree, the row goes to review with both rule names. Conflicts are never settled by which rule happens to come first in the file.

### How sure is a merchant rule?

Every merchant rule says how often that merchant is business spending:

| `business_use` | Business-only account | Business and personal account | Examples |
|---|---|---|---|
| `always` | decided | decided | GitHub, AWS, JetBrains, Upwork |
| `usually` | decided | review, with a suggestion | PTCL, Nayatel, Zoom, Wise |
| `sometimes` | review, with a suggestion | review, with a suggestion | Daraz, Amazon, Careem, Foodpanda, K-Electric |
| `never` | decided as Personal | decided as Personal | Netflix, Spotify, Imtiaz |

This is how the app handles "a merchant match doesn't prove business use" without sending everything to review.

### Direction checks

After a rule matches, the engine checks the money went the right way:

- A spending or tax rule on money coming in, with no refund word, goes to review.
- An income rule on money going out goes to review.

These catch parser sign mistakes as well as odd transactions.

### Refunds

A description with REFUND, REVERSAL, REVERSED or CHARGEBACK is a refund. The stages still run to find out *what* is being refunded. Then:

1. Money going out with a refund word goes to review.
2. The engine looks for the original purchase: same rule (so the same merchant), same currency, money out, at least as large as the refund, within the last 90 days, and not itself a refund line.
3. **Exactly one match:** the refund gets that purchase's category and type `refund`, and is linked to it. It lowers the category total. It is never income.
4. **No match, or more than one:** review, with the merchant's category as the suggestion.

An equal amount alone never links a refund. A GitHub refund can't attach to an Adobe purchase of the same size.

### Unknown rows

No rule at all: review, with "Unknown merchant" for money out or "Money in from an unknown source" for money in.

### Problems found while reading the file

Some rows are fine for the rules but suspect as data. These "flags" are added before the engine runs, and **a flagged row always goes to review**. The rule's answer becomes the suggestion:

- the running balance doesn't add up,
- the OCR engine was under 80% confident about the line,
- a scanned page had no balance column to check against,
- the same date, amount and description already appear earlier in this file or in an earlier import.

### Worked examples from the sample files

| Description | Amount | Result | Why |
|---|---|---|---|
| POS GITHUB.COM SAN FRANCISCO | −1,120 PKR | Software & Subscriptions | `SW-GITHUB`, always business |
| GITHUB.COM REFUND | +1,120 PKR | Software & Subscriptions, type refund | linked to the 3 Mar purchase, lowers the category |
| AMAZON WEB SERVICES AWS.AMAZON.COM | −8,450 PKR | Cloud & Hosting | longer pattern beats `AMAZON` |
| FED ON SMS ALERT CHARGES | −32 PKR | Tax Deducted | tax stage runs before bank charges |
| NAYATEL INTERNET BILL | −4,999 PKR | Internet & Phone, or review on a mixed account | `usually` business |
| IBFT OUTWARD 0213XXXX | −15,000 PKR | review, suggests Transfer | could be paid to someone else |
| CLIENT PAYMENT ACME LTD | +95,000 PKR | review, suggests Business Income | payer not confirmed; one rule fixes it for good |
| HOME REMITTANCE FROM ABROAD | +60,000 PKR | review, suggests Business Income | could be family money |
| FOODPANDA ORDER 5512 (twice) | −2,350 PKR | both in review, second flagged as a duplicate | `sometimes` business, and a repeated row |
| JOES CAFE 9921 | −1,800 PKR | review | unknown merchant |
| SQ *48392 | −18.50 USD | review | unknown merchant |
| AWS EMEA, amount "31.2O" | | not imported, reported | a letter O where a zero should be |

## 6. User rules

After fixing a row, the page offers a rule built from the description, with reference numbers removed (`POS 4471 JOES CAFE 9921` becomes `JOES CAFE`). The user can edit the pattern, the match type and the category.

Before saving, the preview shows:

- which rows still in review would change, and what they would become,
- how many already-sorted rows also match (these don't change),
- any rules it overlaps, and what happens where both match.

Saving a rule re-checks **only rows in review**. Rows the app already sorted and rows the user changed are never touched. The rule also applies to every later import. Rules can be switched off or deleted; rows they already sorted keep their category.

A user rule is always treated as "always business" for its category, because the user decided it.

## 7. Reading statements

### CSV

- The header row can sit below a few lines of bank details. The parser looks at the first 15 lines.
- Accepted column names are in `backend/app/parsing/columns.py` and the README. A currency in brackets, as in "Debit (USD)", is used as the statement currency.
- Either one Amount column (negative is money out, or a DR/CR type column) or Debit and Credit columns. A file with both is refused, because it isn't clear which one to trust.
- Encoding: UTF-8, then Windows-1252. Delimiter: comma, semicolon, tab or pipe.

### PDF and OCR

- `pdfplumber` gives words with positions. A page with almost no text is treated as a scan: it is rendered at 300 dpi and read with Tesseract.
- Both go through `layout.py`, which groups words into lines, finds the header line, and puts each word in a column. Numbers are matched to the column whose right edge they line up with, because statements right-align amounts.
- A wrapped description line is joined to the row above. Page footers and repeated headers are ignored. A line starts a new row only if it has a date or amounts.
- Tesseract runs in "sparse text" mode (`--psm 11`). The default mode glued neighbouring words together ("CAREEMRIDE"), which made rules miss.
- Supported PDF layout: one table with Date, Description, Debit/Credit or Amount, and an optional Balance, with right-aligned numbers.

### Values

- Amounts: `1,250.00`, `(1,250.00)`, `1,250.00 DR`, `1250.00-`, `Rs. 500`, `$12.99`. Anything else is refused, including lakh-style `1,25,000` and more than two decimals, because those are more likely misreads than real amounts.
- Dates: the format is decided once per file. A day above 12 proves day-first, a middle number above 12 proves month-first. If every date could be read both ways (03/04/2026), the upload asks the user. Text months (05 Mar 2026, 05-MAR-26) and ISO dates always work.

## 8. Storage

SQLite, three tables: `statements`, `transactions`, `user_rules`.

- Amounts are stored as **integers in paisa or cents**, so sums are exact.
- Each statement stores a SHA-256 of the file, so the same file can't be imported twice.
- Each row stores a fingerprint (date, currency, amount, normalised description) to spot overlapping statements.
- Each row keeps what the app decided (`app_category`, `app_reason`) next to the current values, so a fix can be undone.
- Schema versions live in `PRAGMA user_version`. A schema change is a new step in `MIGRATIONS`, never an edit to an old one.

## 9. API

| Method and path | What it does |
|---|---|
| `GET /api/meta` | Categories, whether OCR is available, upload limit |
| `POST /api/statements` | Upload a file with `account_type`, `currency`, `date_format` |
| `GET /api/statements` | Imports with row and review counts and their import reports |
| `DELETE /api/statements/{id}` | Delete one import and its rows |
| `DELETE /api/statements` | Delete all imported data (rules are kept) |
| `GET /api/transactions` | Rows, optionally for one statement or one status |
| `PATCH /api/transactions/{id}` | Set a category, or `null` to let the rules decide again |
| `GET /api/summary` | Totals per currency and category, plus what isn't counted |
| `GET /api/export.csv` | Reviewed rows as CSV |
| `GET /api/rules` | Your rules and the built-in ones |
| `POST /api/rules/preview` | What a new rule would change |
| `POST /api/rules` | Create a rule and re-check rows in review |
| `PATCH /api/rules/{id}`, `DELETE /api/rules/{id}` | Switch a rule on or off, or delete it |

Errors come back as `{"detail": "..."}` with a sentence the page can show as it is.

The CSV export puts a `'` in front of any text cell that starts with `=`, `+`, `-` or `@`, so a description can't run as a formula in Excel. Amounts stay plain numbers.

## 10. Frontend

One page in React with Tailwind:

- **Add a statement:** file picker or drag and drop, the account-type question, currency and date-format choices.
- **Totals:** income, spending and the difference per currency, tax taken by the bank, a bar of where the business money went, and a list of what isn't counted.
- **Imports:** pick one statement or all of them, delete an import, and read its report (rows skipped, rows that couldn't be read, warnings).
- **Transactions:** filter by needs review, all, sorted by rules, or changed by you. Rows in review show the suggestion ready to confirm. A fix offers a rule.
- **Your rules:** switch rules on and off, delete them, and browse the built-in rules.

The colours come from Pakistani truck art: navy, marigold, rani pink and emerald, with one colour per category. Marigold always means "waiting for you".

## 11. Testing

`backend/tests` has 104 tests over synthetic data:

- `test_values.py`: amount and date formats, refusals, ambiguous dates.
- `test_csv_parser.py`: column names, preambles, debit/credit and DR/CR, currency detection, unreadable rows, newest-first files, running balance, repeated rows.
- `test_pdf_parser.py`: the text PDF sample, the scanned sample through Tesseract, and the layout code fed with OCR-style word positions to test low confidence, misread amounts and scans with no balance column.
- `test_engine.py`: every stage, specificity, conflicts, business-use levels, direction checks, all refund paths, user rules and flags. Each test checks the status and the reason, not only the category.
- `test_api.py`: upload end to end, duplicate files, overlapping statements, fixes and undo, rule preview and creation, disabled rules, totals per currency, CSV export, deletes.

## 12. Trade-offs and limits

- **Rules over models.** Easy to explain and test, but every new merchant needs a rule. User rules cover the long tail.
- **Careful by default.** On the sample PKR statement, 9 of 20 rows wait for the user. That is on purpose: most of them are genuinely unclear.
- **One PDF layout.** Real banks print many layouts. Adding one means adding header names or a small layout adapter, not changing the engine.
- **OCR.** Tesseract has to be installed. Without it, scanned PDFs get a clear message and everything else works.
- **Refunds are matched within one currency and 90 days.** A refund that arrives later goes to review.
- **SQLite and one user.** Right for a local tool. A hosted version would need accounts and a server database.
- **No tax advice.** Categories organise records. They don't decide what is deductible.
