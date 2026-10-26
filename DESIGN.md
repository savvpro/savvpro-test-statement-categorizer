# Design

## Customer and workflow

The target customer is a freelance designer organizing business
transactions before tax preparation.

The workflow is:
upload a CSV, validate rows, classify transactions, review uncertain
results, save corrections, inspect totals, and export saved rows.

## Architecture

The React frontend sends CSV files to a Python FastAPI backend.

The backend separates:
- API handling and correction validation in main.py.
- Parsing and categorization in categorizer.py.
- Financial summaries in summary.py.

Uploaded statements receive UUID identifiers and are stored in a
process-local dictionary.

The browser exports the latest saved transaction data as CSV.

## Decision engine

The decision engine uses ordinary Python conditions, phrase matching,
and a merchant-to-category mapping. It makes no AI API calls.

Descriptions are converted to uppercase, punctuation is replaced with
spaces, and repeated whitespace is collapsed. Phrase matching uses
word boundaries to reduce accidental substring matches.

Decision order:

1. Zero amounts require review.
2. Conflicting transfer, refund, and income indicators require review.
3. Explicit transfer phrases are classified as transfers.
4. Matches across multiple merchant categories require review.
5. Explicit positive refunds use the matched expense category.
6. Refunds without a known category remain flagged for review.
7. Explicit client payments with positive amounts become income.
8. Other positive amounts require review.
9. Negative amounts with a single merchant category become expenses.
10. Unmatched transactions require review.

Each result includes a transaction type, category, reason, and
needs_review flag.

The engine does not invent numeric confidence scores. Uncertainty is
represented explicitly through Needs Review.

## Money and summaries

Money is parsed with Python Decimal.

Expenses contribute positive spending totals. Refunds reduce spending
in their assigned expense category.

Transfers do not contribute to income or expenses.

Unresolved incoming and outgoing amounts are reported separately and
excluded from categorized totals.

Amounts are returned as decimal strings to avoid floating-point
rounding during transport.

## Manual corrections

Users select a type and category and explicitly save the change.

The backend validates category/type compatibility and amount direction.
For example, a negative amount cannot become incoming client income.

Invalid corrections leave the existing statement unchanged.
Successful corrections replace the classification reason with a
user-confirmation message and recalculate the summary.

Users can also mark a transaction unknown again.

## Input validation

Validation includes:
- CSV filename extension and UTF-8 decoding.
- Required and duplicate column names.
- Row structure and nonempty descriptions.
- Valid ISO dates.
- Amount syntax, precision, and maximum magnitude.
- Supported currency and one currency per statement.
- Upload size and transaction-count limits.

An invalid row rejects the upload rather than silently dropping it.

## Frontend

The interface provides:
- Upload feedback and error messages.
- Income, net expense, refund, and review-count cards.
- Category breakdown.
- Separate transfer and unresolved totals.
- Needs Review filter.
- Editable transaction rows.
- Export of saved results.

CSV text fields are quoted and formula-like text is prefixed with an
apostrophe to reduce spreadsheet formula execution risk.

## Testing

Tests cover normal classification, uncertain descriptions, conflicting
merchant matches, refund direction, transfers, malformed inputs,
mixed currencies, summary calculations, retrieval, correction
validation, and missing resources.

Backend validation completed with 24 passing test cases.
Frontend production build and ESLint checks passed.

## Tradeoffs and future improvements

Temporary storage kept the assessment implementation small, but data
does not survive restarts and is not shared between worker processes.

Before production use, add persistent storage, authentication,
authorization, resource limits, audit history, and deployment configuration.

Further improvements include configurable merchant rules, duplicate
review, business/personal classification, more statement formats,
frontend automated tests, and better handling of unsaved edits.

The current rules cannot reliably determine business purpose or tax
deductibility from a merchant name alone.