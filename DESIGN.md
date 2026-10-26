# Design

## Use case

A small landlord who needs their bank statement sorted for tax time. They want
rent, repairs, insurance, property tax and mortgage interest totals to hand to
an accountant.

Categories: Rental Income, Security Deposit, Transfer, Mortgage Payment (split
into Mortgage Interest and Mortgage Principal), Property Tax, Insurance,
Repairs & Maintenance, Utilities, HOA Fees, Bank Fees, Needs Review.

## The one rule

The brain is my own deterministic code. No GPT, Claude or Gemini decides a
category. Same input always gives the same output, and every row carries a
plain-English explanation.

## Messy cases handled

| Case | What the app does |
|---|---|
| Refund (e.g. ACE PLUMBING REFUND, +$120) | Reduces the expense; it is not income |
| Security deposit received or returned | Own category, so it is neither income nor expense. Received and returned nets to $0.00 |
| Transfer to savings | Category "Transfer", excluded from spending |
| Unknown merchant (JOES CAFE) | Needs Review, confidence 0 |
| Ambiguous merchant (HOME DEPOT, AMAZON) | Needs Review, because repair vs improvement or business vs personal can't be known from the text |
| Money coming IN from an expense merchant | Needs Review (possible refund or credit) |
| Typos (PLUMBNG) | Fuzzy match, slightly discounted |
| Duplicate rows | Flagged "possible duplicate of row N", not deleted (two real payments can look identical) |
| Partial rent (two $750 payments) | Both counted as Rental Income |
| Different bank layouts | Parser detects columns; both sample banks give identical totals |
| Bad rows in a file | Reported as parse errors; the valid rows still load |
| Mortgage payment | Split into interest and principal from the loan details (see below) |

## How a row is decided

Checks run in this order, and the first one that applies wins:

1. A correction the user made before (learned rule), confidence 1.0.
2. Transfer phrases.
3. Security deposit phrases.
4. Mortgage phrases (split if loan details exist, otherwise Needs Review).
5. Known ambiguous merchants (Needs Review).
6. Keyword scoring: every rule has a category and weight. Several hints for
   the same category combine as `1 - (1-w1)(1-w2)...`, capped at 0.99.
   Matching is whole-word, so RENT does not match CURRENT.

Then confidence decides:

- Best score below **0.75**: Needs Review.
- Two categories both above 0.75 and within **0.10** of each other: Needs
  Review ("conflicting evidence").
- Otherwise the category is accepted.

Special checks come first because "ZELLE FROM NEW TENANT SEC DEPOSIT" contains
the word TENANT. Without the order, a deposit would be counted as rent.

The principle: a wrong guess is worse than asking, so any uncertainty goes to
the user.

## Corrections become rules

When the user fixes a row, the normalized description is remembered. Fixing
`JOES CAFE 9921` also fixes `JOES CAFE 1234`, because normalization removes
store numbers. A manual choice always beats automatic logic. Needs Review and
the mortgage categories cannot be picked by hand, because they only make sense
from real loan math.

## Mortgage split

- **Decimal, not float.** Money must be exact. Cents are rounded half-up.
- **Standard amortization.** Payment = P·r / (1 − (1+r)^−n). Each month's
  interest is the balance times the monthly rate; the rest is principal.
- **Payment matching by calendar month.** A payment on the 3rd or the 28th
  lands on the right installment number.
- **Nothing is guessed.** If the paid amount differs from the schedule by more
  than one cent (escrow, extra principal), if the date is outside the loan, or
  if an installment was already matched, the row goes to Needs Review with the
  reason.
- **Rounding drift.** The last payment absorbs accumulated rounding so the
  balance ends at exactly $0.00.
- **Summary counts parts, not the whole.** A split payment contributes its
  interest and principal, never the full amount, so nothing is double counted.

## Architecture

- `brain/` has no web or file code, so it is easy to test.
- `parsing/` turns bytes into validated transactions and reports bad rows.
- `api.py` is thin: validation, limits (2 MB, 10,000 rows) and routing.
- The frontend never computes totals. The backend is the single source of
  truth. Amounts travel as strings so cents stay exact.

## Limitations

- Fixed-rate loans only. No adjustable rates.
- Payments that include escrow go to Needs Review rather than being split.
- Storage is in memory: data is lost on restart, with no login and a single
  process. `StatementStore` can be swapped for a database.
- Learned corrections last for one statement session.
- The rules are hand-written for landlords. Other use cases need new rules.
- Duplicate detection matches exact date + description + amount only.