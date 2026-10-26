# PRD: Statement Categorizer

## Use case
A **freelance software developer in Lahore** receiving foreign income (Payoneer) and paying local bills. At tax time they need every transaction on their PKR bank statement sorted into categories, with uncertain rows flagged for review.

Bank: fictional "Ravi Commerce Bank Ltd". Currency: PKR.

## Problem
Statements are messy: cryptic merchant strings, refunds, transfers between own accounts, bank taxes, duplicate charges. Manual sorting is slow and error-prone.

## Goal
Upload a CSV statement, get every row categorized by deterministic code, review only the uncertain rows, see totals per category.

## Stack
Python FastAPI backend (conda env `assigment`), React/Next.js frontend, Supabase only if a database is required.

## Hard constraint
The categorization "brain" is our own rule-based Python code. **No LLM or big AI model makes any decision.**

## In scope
- CSV upload (columns: Date `DD-MM-YYYY`, Description, Debit, Credit, Balance)
- Parsing and normalizing rows into one signed amount
- Rule-based categorization with a confidence score
- Needs Review bucket for low-confidence or unknown rows
- Duplicate-charge detection
- Refund and reversal handling
- Own-account transfer detection (not spending)
- Summary: total per category, income vs spending
- UI to upload, view rows, fix Needs Review rows
- Tests, README, DESIGN.md, AI_USAGE.md

## Out of scope
PDF parsing, multiple bank formats, auth, multi-user, production database, ML models.

PDF parsing, multiple bank formats, auth, multi-user, ML models. Persistence is optional: default is in-memory, and Supabase is used only if a database is truly required.
## Categories
Income, Transfer (not spending), Software & Tools, Utilities, Internet & Phone, Rent/Office, Travel & Transport, Entertainment, Food, Groceries, Shopping, Health, Education, Taxes, Bank Fees, Refund, Cash Withdrawal, Needs Review.

## Edge cases that must work
| Case | Expected result |
|---|---|
| Refund (credit from a merchant) | Category Refund, not Income |
| `IBFT TO SAVINGS A/C` | Transfer, excluded from spending |
| Failed ATM txn plus reversal | Both flagged, net effect shown, not counted as spending |
| Same merchant, same amount, same day twice | Flag second row as possible duplicate |
| `AMZN MKTP US*...`, `M/S ... TRADERS` | Needs Review (ambiguous) |
| Raast P2P to or from an individual | Needs Review |
| Lowercase or double-spaced descriptions | Normalized, still matched |
| Foreign SaaS with USD hint | Software & Tools |
| WHT, FED, SMS alert, card fee | Bank Fees |
| FBR advance tax | Taxes |
| Unknown merchant | Needs Review, never a guess |

## Acceptance criteria
1. Sample CSV (75 rows) processes with no crash.
2. Every row has a category, a confidence, and a short reason.
3. No unknown row is silently guessed.
4. User can change a category and totals update.
5. `pytest` passes; brain rules covered by unit tests.
6. No LLM call anywhere in the categorization path.
7. README lets a reviewer run it in a few minutes.
