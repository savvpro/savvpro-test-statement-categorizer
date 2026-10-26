# Design

Status: everything here is built and tested: the pipeline and rules (sections 3-7), the
storage and API (8-9) and the review screen (10). GitHub Actions runs the checks on every
push and pull request (section 11); it has not been seen running yet. The page was checked
in a headless browser from 375 px to 1280 px wide. Section 9 lists one totals decision that
is still open.

## 1. Use case
- Freelance software developer in Pakistan, business card + business bank account
- Paid by foreign clients through Upwork, Fiverr, Payoneer and Wise; pays for SaaS,
  hosting, travel and local bills
- At tax time they need spending sorted into deductible categories, income totalled,
  and non-spending (transfers, card payments, refunds) excluded
- The job, start to end: upload a CSV statement → every row gets a category, a kind and
  a reason → the user fixes the rows marked Needs Review → totals → export

## 2. Categories and kinds
- Category = what it is for tax; kind = what kind of money movement it is
- Why separate: a refund is money back, not income; a card bill payment is not spending
- Categories: Software & Subscriptions, Hosting & Cloud, Hardware & Equipment,
  Internet & Phone, Travel, Meals, Office Supplies, Professional Services, Bank Fees,
  Income, Transfer, Refund, Personal, Tax Withheld, Needs Review
- Kinds: expense, income, transfer, refund, fee, tax
- A rule can set the kind. If it does not, the sign decides: money out = expense,
  money in = income. Rows sent to Needs Review still get a kind from the sign.
- Totals only count kinds that matter for tax
- Totals: tax rows count in neither total expenses nor income. They only appear in
  "Tax already paid". Mixing them in would overstate business expenses.
- Refund of withheld tax: keep it as category Tax Withheld, kind tax, with a positive
  amount. Then "Tax already paid" is just the net sum of tax rows, and the sign handles
  it. Don't call it a refund. The refund kind means a merchant gave money back on a purchase.

## 3. Pipeline
- Ingest → Parse → Normalize → Classify → Post-check → Review
- Why separate stages: each one is testable on its own; a wrong category can be
  traced to one stage
- Where each stage lives:
  - Ingest + Parse: `ingest/formats.py` (a profile per bank layout, picked from the
    header row), `ingest/parser.py`, `ingest/amounts.py`
  - Normalize: `brain/normalizer.py`
  - Classify: `brain/classifier.py`, rules in `brain/rules.yaml`, schema in `brain/rules.py`
  - Post-check: `brain/postcheck.py` (needs the whole file, so it runs after classify)
  - Review: the frontend (section 10) and the correction logic in `services/corrections.py`
- Every physical line after the header ends up in exactly one of: parsed rows, errors,
  skipped (blank). Nothing is dropped silently, and a bad row never stops the file.

## 4. The brain (rule order and why)
Each stage exists because of a row in `sample_data/` that goes wrong if the order changes.

1. User rules (what the user already corrected wins). Exact match on the merchant key,
   confidence 1.0
2. Structural: card payments, savings and own-account transfers, tax withheld, refunds
   and reversals, bank and card fees
   - `FOREIGN TXN FEE AWS EMEA` (card row 4) contains AWS. If merchants ran first it would
     be Hosting & Cloud. `fx_fee` runs first and makes it a Bank Fee (kind fee)
   - `PAYMENT THANK YOU` (card row 31, +185,000.00) is money in on a card, so it reads as a
     refund or as income. `card_payment` makes it a Transfer. The matching bank debit
     `CREDIT CARD BILL PAYMENT ****8842` (bank row 23) is a Transfer too, so the bill is
     counted once, as the purchases on the card statement
   - Refunds sit here so money coming back from any merchant is never income
3. Exact merchants. Merchant rules carry `direction: out`, so a credit from the same merchant
   falls through to step 6 (the Adobe refund, card row 24, becomes a Refund this way).
   Income platforms (Upwork, Payoneer, Wise) are `direction: in` and `account_type: bank`
   - `AWS EMEA AWS.AMAZON.CO LU` (card row 3) contains AMAZON. The `aws` rule runs before the
     Amazon guard in step 4, otherwise cloud hosting would be sent to review
   - `UBER EATS LAHORE` (card row 15) and `UBER *TRIP` (row 21) both contain UBER. `uber_eats`
     (Meals) is listed before `uber_trip` (Travel): the more specific rule has to come first
   - `IBFT TO KASHIF & CO CHARTERED ACCOUNTANTS` (bank row 17) matches the generic
     "IBFT to a person" review rule in step 4. `chartered_accountants` runs first, so a known
     payee is Professional Services and is not sent back to the user
4. Ambiguous guard (Amazon, Daraz, cash, person-to-person, cheques → always review). It runs
   after the merchants so that it only catches what no known rule explained: `IBFT TO ALI RAZA`
   is a person, and the app cannot know whether it was a client, a supplier or personal
5. Keywords. All matching keyword rules are collected. If they point at different
   categories the row goes to review with "conflicting rules: ...". Otherwise the single
   category wins, if its confidence is high enough (section 5)
6. Direction: positive amount on a card and no rule matched → Refund (confidence 0.85)
7. Nothing confident → Needs Review, reason "no rule matched"
- First decisive match wins; inside a section the order in the file is the order tried
- Rules live in YAML, not code. The file is validated at startup (unknown keys, bad
  categories, bad regexes, duplicate ids all stop the app with a message naming the rule)
- Matching runs on the normalized text: uppercase, spaces collapsed, processor prefix
  (`SQ *`, `PAYPAL *`, `POS `, `TST*`) removed. `UBER *` is not stripped: Uber is the
  merchant. `contains` matches whole words only
- The merchant key is the normalized text with every token that contains a digit removed,
  so "SQ *JOES CAFE 9921 ISLAMABAD" and "SQ *JOES CAFE 1002 ISLAMABAD" are one merchant

## 5. Confidence and Needs Review
- Threshold: 0.8. A match below it is not trusted: the row goes to Needs Review and the
  rule's category is kept as `suggested_category`. A score of exactly 0.8 is trusted
- Why a threshold at all: a wrong guess is worse than asking. A wrong category silently
  changes a tax total; a row in Needs Review costs the user one click
- Why 0.8: the scores in use are 0.95 (rules), 0.85 (keyword rules with an explicit score, and
  the card-refund fallback) and 0.75 (the keyword default). 0.8 sits between the last two, so
  a keyword is trusted only when its author gave it a score on purpose. It is a judgement, not
  a value tuned on data. Example: `BLUE BIRD CAFE` matches `kw_cafe` (0.85) and is Meals;
  `HOLIDAY INN LAHORE` matches `kw_hotel` (0.75) and goes to review with Travel suggested
- Defaults: rules 0.95; keyword rules 0.75, below the threshold on purpose. A keyword
  rule is only trusted when its author sets a confidence of 0.8 or more for a specific,
  low-risk word (HOSTING, CAFE, STATIONERS). Broad words (HOTEL, FUEL, SOFTWARE) stay at
  0.75 and only suggest
- A row can be in review for four reasons: an always-review rule, low confidence,
  conflicting keywords, no rule matched. A possible duplicate is a fifth, added after
  classification (section 6)
- Every decision stores rule_id + reason; the UI shows the reason next to each row

## 6. Messy data handled
| Case | How it is handled | Test |
|---|---|---|
| Blank or whitespace-only line | skipped, still counted in the row number | `test_whitespace_only_line_is_skipped_and_counted` |
| Missing amount | row error, raw line kept | `test_bad_bank_a_lines_become_errors` |
| Invalid or wrong-format date (`2026-13-45`, `12/09/2026` in an ISO file, `2026-9-1`) | row error; the date format is never guessed | `test_bad_bank_a_lines_become_errors`, `test_messy_values_and_reasons` |
| Extra or missing column | row error "expected N columns, got M" | `test_messy_values_and_reasons`, `test_bad_bank_b_lines_become_errors` |
| `(45.00)`, `Rs 500`, `-$12.99`, `185,000.00` | `parse_amount` reads them as Decimal | `test_parse_amount_valid` |
| `1rs2`, `5 USD 5`, `1,23.00`, `1.234,56`, `(-5)` | rejected, never guessed | `test_parse_amount_invalid` |
| Debit and credit both filled or both empty; negative debit | row error | `test_bad_bank_b_lines_become_errors` |
| Extra whitespace, mixed case | normalized for matching; `raw_description` never changed | `test_normalize`, `test_raw_description_is_untouched` |
| BOM, CRLF line ends, reordered columns, quoted comma | handled | `test_bom_and_crlf_handled`, `test_header_may_be_reordered`, `test_quoted_description_with_comma` |
| Unknown header | error that lists the supported formats | `test_unknown_header_lists_supported_formats` |
| Exact duplicate row | later copies go to review, keep their category, reason "possible duplicate of row N" | `test_second_occurrence_is_flagged_and_keeps_its_category` |
| Refund looks like income | refund rules, direction filters, card fallback | `test_direction_filter_lets_a_refund_fall_through_to_the_fallback`, `test_card_credit_from_upwork_is_not_income` |
| Card bill payment looks like income or spending | structural rule → Transfer, on both the card and the bank side | `test_labels_match` |
| FX fee line names the merchant | structural before merchants | `test_structural_beats_merchant` |
| AWS contains AMAZON; UBER EATS contains UBER | known merchants before the guard and before shorter names | `test_merchant_beats_review`, `test_first_match_in_a_section_wins` |
| Conflicting keywords | Needs Review, reason lists the rules | `test_keywords_from_different_categories_conflict` |
| Withholding tax | Tax Withheld, kind tax | `test_labels_match` |
| Zero amount | Needs Review | `test_zero_amount_goes_to_review` |
| Amount with more than 2 decimals (`-4.005`) | row error, never rounded, because money is stored in minor units | `test_amount_with_more_than_two_decimals_is_an_error_not_a_rounding`, `test_more_than_two_decimals_is_refused_not_rounded` |
| Upload that is not a `.csv`, is empty, is not UTF-8 text or is over the limit | 400, 400, 400 and 413, each with a readable message | `test_non_csv_is_a_400`, `test_empty_file_is_a_400`, `test_unreadable_file_is_a_400`, `test_oversized_upload_is_a_413` |
| Personal spending on the business card | its own block, never in expenses | `test_personal_spending_is_reported_apart_from_expenses` |
| USD and PKR rows on one card | totalled per currency, never added | `test_currencies_are_summed_separately` |
| Rows still in review | outside every total, reported in their own block | `test_review_rows_are_kept_out_of_every_total_and_reported_on_their_own` |
| A duplicate flag when a merchant is remembered | kept | `test_duplicate_flag_survives_a_remember_re_run` |
| Description that starts with `=` | prefixed with `'` in the export so a spreadsheet cannot run it | `test_export_does_not_let_a_description_become_a_spreadsheet_formula` |
- `test_labels_match` runs parse → classify → post-check on all three sample files and
  compares category, kind and needs_review with `sample_data/expected_labels.csv`
  (the ground truth; it is never edited to make a test pass)

## 7. Learning from corrections
- "Remember for this merchant" → saves a user rule (merchant key → category, optional
  kind) → re-runs the statement
- User rules win over every rule in the file (stage 1) and match the merchant key
  exactly, so one correction covers every store number of the same merchant
- A row the user fixed by hand is never changed by a re-run
- Status: built end to end. The "Remember for this merchant" checkbox in the row editor
  (section 10) sends `remember: true` to `PATCH /api/transactions/{id}`, which saves the rule
  (section 8). `test_remember_reclassifies_other_rows_but_not_hand_edited_ones` covers the
  server side

## 8. Storage and API
- SQLite through SQLAlchemy 2.0. The tables are created on startup. Alembic migrations are
  the production next step; `create_all` does not change a table that already exists
- Tables:
  - `statements`: id, filename, profile_name, account_type, uploaded_at, skipped_count
    (blank lines are only counted)
  - `transactions`: id, statement_id, row_number, date, raw_description, merchant_key,
    amount_minor, currency, the decision (category, kind, confidence, rule_id, reason,
    needs_review, suggested_category) and `edited_by_user`
  - `parse_errors`: id, statement_id, row_number, raw_line, reason (so the user sees what
    was rejected and why)
  - `user_rules`: id, merchant_key (unique), category, kind (optional), created_at
- Money is an integer in minor units (paisa / cents). SQLite has no exact decimal type and
  money is never a float. `core/money.py` converts to and from Decimal. An amount with
  more than 2 decimals is a parse error, never rounded. This assumes every currency has 2
  decimal places, which is true for PKR and USD
- A manual fix overwrites the decision on its row: category and kind as chosen,
  confidence 1.0, rule_id `manual`, reason "set by you", needs_review false, and
  `edited_by_user` true. The brain's original answer is not kept
- Logic lives in `services/` (ingest, corrections, summary, export). The routes only
  translate HTTP
- Settings come from environment variables (`.env.example`): `DATABASE_URL`,
  `CORS_ORIGINS` (comma-separated), `MAX_UPLOAD_MB`
- Endpoints (prefix `/api`, except `/health`):
  - `POST /statements`: multipart CSV. Parses, classifies with the saved user rules,
    post-checks, saves, and returns the statement with its rows and parse errors
  - `GET /statements`: all statements, newest first, with counts
  - `GET /statements/{id}`: the statement, its transactions, its parse errors, the
    skipped-line count
  - `GET /statements/{id}/summary`: totals (section 9)
  - `GET /statements/{id}/export`: the categorized CSV
  - `PATCH /transactions/{id}`: `{category, kind?, remember}`
  - `GET /categories`: the categories and kinds
  - `GET /health`
- Amounts in JSON are strings (`"-1850.00"`), never numbers
- Errors: unreadable file, unknown header or a name that does not end in `.csv` → 400 with
  the parser's message (which lists the supported formats); over `MAX_UPLOAD_MB` → 413;
  unknown id → 404; invalid category, "Needs Review" as a fix, or `remember` on a row with
  no merchant key → 422
- Fixing a row (`PATCH`):
  - The category is required and cannot be Needs Review: a fixed row is no longer in review
  - The kind is the one given. If none is given, Income, Transfer, Refund, Bank Fees and
    Tax Withheld imply income, transfer, refund, fee and tax; any other category follows
    the sign (money out = expense). Without this a row fixed to Transfer would count as spending
  - `remember: true` saves one user rule per merchant key (a second save updates it). The
    rule stores a kind only if one was given or implied. Then every other row with that
    merchant key, in every statement, is classified again, except rows the user fixed by
    hand. The duplicate check runs again for those statements, so a "possible duplicate"
    flag is kept. The response says how many rows changed
- Export columns: Date, Description, Amount, Currency, Category, Kind, Confidence,
  Needs Review, Reason. Amount is signed (negative = money out) for both layouts. A
  description that starts with `=`, `+`, `-` or `@` gets a leading `'` in the export, so a
  spreadsheet cannot run it as a formula; the stored description is unchanged
- No login: one local user. User rules apply to every statement

## 9. Summary and totals
- Per currency. The card has USD rows and PKR rows, and adding them together would be
  wrong. There is no FX conversion
- Each currency gets, from the rows by kind:
  - expenses (kind expense): a total and a total per category
  - personal (category Personal): a count and a total. Personal spending is not deductible,
    so it is never in expenses or in the per-category list, whatever its kind
  - fees (kind fee), income (kind income), refunds (kind refund)
  - tax already paid (kind tax), the net sum of tax rows (section 2)
  - transfers (kind transfer): a row count and the amount out and in. They are shown so the
    user can see they were left out, and they are not spending
- Spending, fees and tax are reported as positive amounts; income and refunds are positive
- A row that is still marked needs_review is in none of those totals. It is counted in a
  separate `needs_review` block (count, amount out, amount in), so a total is never quietly
  wrong, and it moves into the totals once the user fixes it. A possible duplicate is in
  that block too until the user confirms it
- The response also has the number of rows needing review and the number of parse errors
- One decision is open and not built: refunds are shown beside expenses and are not
  subtracted from them. There is no net figure
- These figures help the user prepare for tax time. They are not tax advice

## 10. Frontend (the Review stage)
- Vite + React + TypeScript (strict), plain CSS with variables (light and dark theme), no UI
  library. Tests: Vitest + React Testing Library with `fetch` mocked. Linter: oxlint, the
  one the Vite template ships
- In development Vite forwards `/api` and `/health` to the backend on port 8000, so the
  browser sees one origin and no CORS setup is needed. `VITE_API_URL` is empty unless the
  API lives elsewhere (`frontend/.env.example`)
- Structure: `api/client.ts` (typed fetch wrapper, one function per endpoint; an error shows
  the API's own `detail` message), `format.ts` (display helpers), `useStatement.ts` (loads
  a statement and its summary), `components/`, `App.tsx` (layout and state)
- One page, top to bottom:
  - Upload: a .csv file input, the two supported formats listed, and the API's error
    message shown as it is (unsupported format, too large, not a .csv)
  - Statement list: filename, date, rows and rows to review; click to open
  - For the open statement: a counts bar (rows, auto-categorized, needs review, parse
    errors), the summary, the transactions table, the lines that could not be read, and a
    "Download categorized CSV" link to the export endpoint
- Amounts stay strings from the API and are formatted as text (thousands commas and the
  currency code), so no rounding is possible. Money out is red and money in is green
- Summary: one block per currency, never mixed. Cards for expenses, fees, income, refunds,
  tax already paid, personal ("not deductible"), transfers ("not spending") and unreviewed
  ("not in any total"). Transfers and Unreviewed show In and Out on two lines. A card with
  no rows behind it is dimmed, not hidden. Below the cards: expenses by category
- Transactions table:
  - Filters: All, Needs Review, Fixed by me, each with a count
  - A row in review is highlighted and also carries a "Needs review" badge, so colour is
    not the only signal. Its suggested category, if any, is shown under the category
  - Confidence is shown as a percentage, except on rows in review, where it shows "—" with a
    tooltip. For those rows the stored number belongs to the rule that flagged the row, and
    a number next to "Needs Review" would read as a guess
- Row editor (Fix on review rows, Edit on any row):
  - Category: a list without Needs Review, starting on the suggested category if there is
    one. Kind: optional; "Automatic" sends nothing, so the API applies its own default
    (section 8)
  - "Remember for this merchant": disabled, with a tooltip and a visible hint, when the row
    has no merchant name. It is never sent as true for such a row
  - After a save the page shows "Saved." or "Saved. N other rows updated.", then fetches the
    statement, its summary and the list again
- Loading, empty and error states exist for the list, the statement, the summary and the
  parse errors. A server that cannot be reached says so
- An error boundary wraps the app: if a component throws while rendering, the page shows
  "Something went wrong — reload the page." with a Reload button instead of a blank screen.
  It does not catch errors in event handlers or requests; the app reports those itself
- Layout was checked in a headless browser from 375 px to 1280 px: the page does not scroll
  sideways (the transactions table scrolls inside its own box). At 320 px the upload panel
  is still about 35 px too wide
- Accessibility: every input has a label, actions are real buttons, filters are buttons
  with `aria-pressed`, focus moves to the category field when the editor opens, and the
  editor can be completed with the keyboard alone (tested)

## 11. Trade-offs and known limits

### Trade-offs (choices I made)
- CSV only (no PDF): reliability over coverage in the time available
- Rules only, no ML: explainable, and the brief requires the brain to be my code
- Two bank layouts, picked from the header row. Another bank needs a new profile
- Money as Decimal in the code and as integer minor units in the database; raw description
  never changed. Confidence is a float (a score, not money)
- A manual fix overwrites the decision on its row, so the brain's original answer is not
  kept. Simpler, and a re-run can never undo a correction
- Rows in review stay out of every total until the user fixes them, so a total is never
  quietly wrong. The cost is that the totals look low until the review is done
- One local user, no login. User rules apply to every statement
- Checks: `pytest` and `ruff` for the backend, Vitest (with `fetch` mocked), oxlint and the
  TypeScript build for the frontend. GitHub Actions runs them on every push and pull request

### Known limits (not handled)
- **Large files.** There is no paging. A generated 4.67 MB file with 96,565 rows took 26 s to
  upload and returned 36 MB, and the page needed about 54 s to render it. The 5 MB limit is in
  bytes, not rows. Real statements are far smaller. The limit is also checked after the file
  has been received, so it protects the parser and the database, not the network
- The database path is relative to the folder the backend is started from, so start it from
  `backend/`
- A statement cannot be deleted, so repeated uploads pile up in the list
- Money assumes 2 decimal places. A currency with 0 or 3 (JPY, KWD) would be stored wrongly.
  There is no currency conversion
- Tables are created with `create_all`: a later column change does not migrate an existing
  database. Alembic is the next step. No locking
- A quoted CSV field cannot span two lines
- The bank export has one signed Amount column; the original Debit, Credit and Balance
  columns are not stored
- Refunds are shown beside expenses and are not subtracted from them (section 9)
- `rules.yaml`: some short or broad words match more than intended (for example `zoom`,
  `PIA`, a `starts_with: UBER` with no word boundary, `JAZZ CASH` read as telecom), and 33 of
  the 76 rules are not yet covered by a sample row. Careem is treated as rides; a Careem Food
  order would be wrong
- Frontend: the statement list is refreshed only on load, upload and save, and if the refresh
  after a successful save fails the old data stays on screen with no message. The filters are
  toggle buttons, not ARIA tabs, so there is no arrow-key navigation between them. On a phone
  the transactions table scrolls sideways inside its box, which hides Amount and Category.
  The page was checked in one Chromium-based browser and not with a screen reader

## 12. What I'd build next
- Paging (or a row limit) for large files, and a way to delete a statement
- A test for every rule, so a rule that matches nothing shows up, and tighter versions of the
  broad rules listed in section 11
- Decide the open totals question in section 9 (refunds against expenses)
- See the CI workflow run on GitHub and fix whatever it finds
- Fix the 320 px overflow and give phones a card layout for the transactions
- Alembic migrations
- PDF/OFX import, more bank profiles, a rule management screen
