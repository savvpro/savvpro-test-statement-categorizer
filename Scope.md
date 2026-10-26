# Scope: Bank Statement Categorizer

## 1. What this is

A small app that sorts a freelance software developer's bank statement before tax time.

You upload a statement as CSV or PDF. The app reads every transaction, runs it through rules I wrote in Python, and shows each row with a category and the reason for it. When the rules can't be sure, the row goes to **Needs review** and waits for you. You fix those rows, and you can turn a fix into a rule for next time. At the end you get totals per category and a CSV export.

I built it for the SAVV Pro Solutions assessment.

## 2. Who it is for

**A freelance software developer in Pakistan** who earns in US dollars from foreign clients (Upwork, Toptal, Payoneer, direct clients) and spends in rupees and dollars. That person usually has:

- a PKR account where client money lands and local bills are paid,
- often a USD account as well,
- and often one account used for both business and personal spending.

That is why the app supports **PKR and USD**, keeps their totals apart, and asks one question at upload: *is this account used only for business, or for business and personal?*

## 3. Currencies

- Only PKR and USD.
- The app never converts between them and never adds them together. Each currency has its own totals.
- A statement's currency comes from a currency column, a header such as "Debit (USD)" or "Currency: PKR", or the user's choice at upload. If none of these settles it, the upload stops and asks the user to pick.

## 4. What the app does

1. Reads bank statements in CSV and PDF format.
2. Reads text PDFs, and scanned PDFs through OCR (Tesseract), when Tesseract is installed.
3. Pulls out the date, description, amount and running balance of each row, and turns every format into one signed convention: positive is money in, negative is money out.
4. Decides each row with project-owned Python rules. No AI model decides a category.
5. Keeps three things apart for every row: its **type** (income, expense, transfer, refund, personal), its **category** (Software & Subscriptions, Bank Charges and so on) and its **status** (sorted by rules, needs review, changed by you).
6. Shows the reason for every decision, including which rule matched.
7. Lets the user fix any row, and undo the fix.
8. Offers to turn a fix into a rule, shows which rows the rule would change before saving it, and never creates or applies a rule on its own.
9. Shows totals per category and per currency, and says clearly what is *not* counted (transfers, personal spending, rows still in review, rows that couldn't be read).
10. Exports the reviewed rows to CSV.
11. Stores everything locally in SQLite.

## 5. What the app does not do

1. **Credit card statements.** They use different sign conventions and have card payments and credits that need their own rules. This version only handles bank statements.
2. **Every bank layout.** CSV files work when their columns use one of the names listed in the README. PDFs work when they have one table with Date, Description and Debit/Credit (or Amount) columns. Anything else fails with a message that says what was missing.
3. **Perfect OCR.** Scanned pages can be misread. The app checks every row against the running balance and flags rows the OCR engine wasn't confident about.
4. **Guessing.** An unclear row goes to review with a reason. It is never forced into a category.
5. **Tax advice.** A category is a bookkeeping label. It does not say whether something is deductible.
6. **Silent learning.** Fixes do not change future decisions unless the user makes a rule.
7. **Currency conversion.**
8. **Real data.** The repository holds only invented statements, made by `backend/scripts/make_samples.py`.

## 6. How careful the rules are

- A row is decided only when a rule clearly applies.
- Unknown merchants, rules that disagree, cash withdrawals, unclear transfers, unclear refunds and anything the reader wasn't sure about go to review.
- A refund is never income. It reduces the category of the purchase it belongs to.
- A transfer between your own accounts is never income or spending.
- A merchant name alone doesn't prove business use. Each merchant rule says how sure it is (always, usually, sometimes, never business), and the account type decides what "usually" means.
- Every row gets a reason the user can read.

A clear "please check this" is better than a confident wrong answer.

## 7. Data and privacy

- SQLite file in `backend/data/`, which is ignored by Git.
- Uploaded files are read in memory and not saved. Only the extracted rows are stored.
- No secrets are needed to run the app, and none are committed.
- Logs record counts only, never descriptions or amounts.
- The user can delete one import or all imported data from the page.

## 8. Technology

- Backend: Python, FastAPI, SQLite (standard library `sqlite3`).
- PDF text: pdfplumber. OCR: Tesseract through pytesseract.
- Rules: `backend/app/categorizer/rules.yaml`, read by `engine.py`.
- Frontend: one page in React with Tailwind CSS, built with Vite.
- Tests: pytest, with synthetic statements and expected results.
- Checks: ruff and ESLint, run in GitHub Actions on every pull request.

## 9. Definition of done

- [x] A CSV bank statement can be uploaded and processed.
- [x] A text PDF bank statement can be uploaded and processed.
- [x] A scanned PDF goes through OCR, and uncertain rows are sent to review.
- [x] Every row is either categorised or marked Needs review, and every row has a reason.
- [x] PKR and USD totals stay separate.
- [x] Users can fix a row, undo a fix, and choose to create a rule from it.
- [x] Refunds and transfers are handled apart from income and spending.
- [x] Category totals and a CSV export are available.
- [x] Tests cover normal cases, unclear cases, refunds, transfers, unreadable rows and currencies.
- [x] README.md, DESIGN.md, AI_USAGE.md and this Scope.md are in the repository.
- [x] No real financial data or secrets in the repository.
- [ ] AI_USAGE.md has my token numbers and usage screenshots.
- [ ] The work is submitted as a pull request.
