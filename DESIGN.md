# Design: Ledgerly Statement Categorizer

## Customer and job to be done
Ledgerly is designed for freelancers and independent consultants who need to organize business bank or card transactions before tax preparation. Their statements often contain recognizable software subscriptions, transport, meals, advertising, equipment, fees, refunds, transfers, and client payments. Unrecognized merchant strings and ambiguous deposits are common; confidently inventing a category can distort their records.

## Product flow
1. User uploads a bank-exported CSV.
2. The API validates the file type and size, parses rows, normalizes amounts, and validates required transaction descriptions.
3. The deterministic categorization engine applies ordered rules and returns category, confidence estimate, and human-readable rationale.
4. Transfers and refunds receive special treatment before general merchant rules.
5. Unknowns are assigned `Needs Review`, surfaced in the UI, and can be corrected by the user.
6. The user exports a CSV containing the chosen categories.

## Decision engine
The engine is ordinary Python code. It does not call a language model or external categorization service. Ordered regular-expression rules recognize common merchant descriptors. The order is intentional: transfer detection happens before generic matching; refund detection happens before positive amounts can be treated as income. Recognized payroll/client payment descriptors can be income. A positive amount without a recognized income signal remains in `Needs Review`. Negative transactions are matched against known merchant classes. A transaction not confidently matched falls back to `Needs Review`.

Confidence values are rule-level indicators to help prioritize review, not statistically calibrated probabilities. Rationale text makes the trigger inspectable. A production version should maintain a curated merchant dictionary, allow per-user overrides, record rule versions, and calibrate confidence against a labeled dataset.

## Edge cases addressed
- Transfers are not treated as income or expenses in the summary.
- Refunds are shown separately rather than counted as income.
- Unknown positive amounts are not automatically assumed to be revenue.
- Unknown merchants are not forced into a plausible-sounding category.
- CSV parse errors include row context where available.
- File size is limited and unsupported file types are rejected.
- Exported values are CSV-escaped to avoid broken columns.

## Deliberate limitations
This assessment version accepts CSV only, uses an illustrative category taxonomy, does not store data persistently, and does not provide tax advice. The sample interface displays USD; real deployments must detect or ask for account currency. Rules may misclassify a merchant whose descriptor is unusual, so users should inspect suggested categories before relying on the output.

## Next production steps
Add broader bank-format fixtures, idempotent import history, a database with user-scoped access controls, authentication, currency selection, robust date normalization, rule editing, audit trail, CSV formula-injection defenses, rate limiting, and accessibility testing. PDF extraction should be a separate opt-in parsing stage with clear validation rather than a silent fallback.
