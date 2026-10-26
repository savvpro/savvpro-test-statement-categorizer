# Design notes

## Architecture

The application is a local, single-user web application:

```text
React + TypeScript UI  →  FastAPI API  →  SQLite
                                   ↘  deterministic categorization engine
```

The React interface manages file selection, statement history, filters, review
forms and export. The FastAPI API owns CSV validation, import idempotency,
categorization, review validation and CSV export. SQLite persists imported rows,
their original decisions, current reviews and a revision history of reviews.

## Categorization approach

Categorization is deliberately deterministic and explainable. Rules are ordered
keyword and regular-expression matches with word boundaries. Each result contains:

- a transaction type and category;
- a confidence level;
- an explanation that names the matching rule; and
- a `needs_review` flag for unknown, ambiguous and suspicious transactions.

Transfers, refunds, income and duplicates have special handling. A duplicate is
flagged but never silently removed. User corrections always override the suggested
decision and remain after a refresh or re-import of the same file.

No generative AI model, third-party categorization API or secret is used at runtime.

## Import safety

CSV input is limited to 5 MiB and 10,000 rows. The importer accepts a documented
set of header aliases and either an `amount` column or `debit`/`credit` columns.
Dates, currencies and decimal precision are validated before an import is stored.
If any nonblank row is invalid, the whole upload is rejected with row-specific
feedback. The original uploaded bytes are not retained.

Money is converted through `Decimal` and stored as integer cents, avoiding
floating-point rounding errors. Exports escape spreadsheet formulas and include
the original decision, current review status and explanation.

## Trade-offs

SQLite and loopback-only hosting keep assessment setup simple and prevent the app
from implying production multi-user finance security. The rule engine is easy to
audit but intentionally conservative: unexplained merchants are sent to review
instead of guessed. PDF and XLSX parsing are excluded so validation is predictable
and safe within the assessment scope.

## Verification

The repository contains parser, engine and API tests, plus browser workflow tests.
The CI workflow runs backend tests and frontend build/tests on pushes and pull
requests.
