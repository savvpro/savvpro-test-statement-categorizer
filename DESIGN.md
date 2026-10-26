# Statement Categorizer Design

## Use Case

The app is for an independent web designer who uses one business credit card for client work. At tax time, they upload a statement and review categorized transactions before exporting a clean expense report.

The app handles business spending, money that should not count as spending, and uncertain purchases that require the designer's decision.

## Scope

The first supported statement format will be CSV. Each row must provide a transaction date, description, and amount. The app will preserve the original row while adding a category, confidence, decision reason, and review status.

The categorizer is not tax advice. It organizes transactions for review; the user remains responsible for confirming categories and applying the result to their tax records.

## Categories

| Category | Meaning | Included examples |
| --- | --- | --- |
| Software | Digital tools used for design or client work | Adobe Creative Cloud, Figma, GitHub, web hosting |
| Office Supplies | Physical supplies and small equipment for work | Printer ink, stationery, cables |
| Travel | Business transportation and lodging | Uber for a client meeting, train fare, hotel |
| Meals | Business meals | Client lunch, meal during business travel |
| Advertising | Marketing and promotion for the business | Google Ads, portfolio promotion |
| Professional Services | Services supporting the business | Accountant, attorney, bookkeeping |
| Banking Fees | Fees charged for business banking or cards | Monthly fee, foreign transaction fee |
| Refund | Money returned for a previous purchase | Adobe refund, returned equipment credit |
| Transfer | Movement of money rather than a purchase | Transfer to savings, card payment |
| Personal | Clearly personal spending | Personal grocery or entertainment purchase |
| Needs Review | Unknown, ambiguous, or conflicting transaction | Unrecognized merchant, mixed-use purchase |

## Categorization Brain

The brain is ordinary application code. It does not call GPT, Claude, Gemini, or another large language model at runtime. Every decision is reproducible from the transaction fields and the versioned local rules.

Rules are evaluated in this order:

1. **Validate the row.** Missing descriptions, invalid dates, and unparseable amounts become `Needs Review` with a validation reason.
2. **Detect refunds or credits.** A credit that clearly refers to a returned or refunded purchase becomes `Refund`. A refund is not income and does not increase revenue totals.
3. **Detect transfers and payments.** Descriptions containing transfer, payment, card payment, autopay, or similar movement-of-money terms become `Transfer` when there is no stronger refund signal. Transfers are excluded from spending totals.
4. **Match exact merchants.** A curated merchant dictionary maps known merchants to categories, such as Adobe, Figma, GitHub, and Google Ads. Matching normalizes case, punctuation, and repeated whitespace.
5. **Match category keywords.** Trusted description keywords can map a transaction to a category, such as `HOTEL` to `Travel` or `ACCOUNTING` to `Professional Services`.
6. **Handle explicit personal signals.** Descriptions that clearly identify personal purchases become `Personal`.
7. **Resolve ambiguity conservatively.** If rules match multiple categories, the amount is unusual, or the merchant is unknown, the result becomes `Needs Review` instead of guessing.

Each categorized row records the matched rule and a confidence level (`high`, `medium`, or `low`). Only high-confidence results are automatically categorized as business expenses. `Needs Review` is always available for manual correction.

## Important Edge Cases

- A positive credit is not automatically income; it is a `Refund` only when the description supports that interpretation.
- A transfer or card payment is not an expense and must not be included in category spending totals.
- An unknown cafe or merchant is `Needs Review`, even if it might be a business meal.
- A merchant can serve multiple purposes. For example, a general online marketplace is never categorized from the merchant name alone.
- Duplicate rows are retained during parsing and flagged so the user can decide whether they are real duplicates.
- Missing descriptions, malformed amounts, unsupported currencies, and invalid dates are shown to the user rather than discarded.
- A manually selected category overrides the automatic result and is marked as user-reviewed.

## User Review Flow

1. Upload a fake or user-provided CSV statement.
2. Review the parsed transaction table.
3. Filter to `Needs Review`, inspect the reason, and choose a final category.
4. Confirm category totals, with refunds and transfers separated from spending.
5. Export the reviewed transactions as CSV.

The app must make uncertain decisions visible. A wrong automatic guess is more harmful than requiring one extra user decision.

## Stage 1 Acceptance Criteria

- The customer and statement type are explicit.
- Every initial category has a defined meaning.
- The rule precedence is deterministic and documented.
- Refunds and transfers are separated from spending.
- Unknown or ambiguous transactions go to `Needs Review`.
- The design uses fake data and does not require external AI at runtime.
- Later stages can implement and test the rules without inventing additional product behavior.
