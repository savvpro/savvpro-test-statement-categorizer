# Product and categorization design

## Use case

Freelance independent designers who use a bank account or credit card for business purchases. The product helps prepare transactions for bookkeeping and tax review; it does not determine tax deductibility. Meals, travel, mixed personal/business purchases, and other context-dependent expenses still need a human's judgment.

## User flow

1. The dashboard opens with clearly labeled fictional sample data so the workflow can be explored without sharing a statement.
2. The user uploads a bank-exported CSV. The API validates the headers, encoding, and each row before returning any results.
3. Local Python rules assign a category only for a known phrase. Anything unmatched is marked **Needs review**, with a reason.
4. The user searches or filters uncertain rows, changes a category, and exports a CSV containing the reviewed result.

## Decision rules

The backend normalizes descriptions to lowercase alphanumeric words and checks an ordered, explicit phrase dictionary. Transfers and refunds are checked before common expense vendors, followed by client-income phrases and specific merchant groups (meals, software, travel, office supplies, advertising, professional services, utilities, and bank fees). Matching is deterministic and uses no model, classifier service, or network call.

The list is intentionally narrow: for example, `UBER TRIP` is a known travel match, while an unrecognized `JOES CAFE 9921` is not assumed to be a business meal. A known phrase produces a 0.96 rule-match confidence indicator; an unknown is assigned zero confidence and sent to review. This confidence describes a phrase match, not tax correctness.

For single-amount files, signed values are preserved; parentheses denote negatives, and `CR`/`DR` suffixes are accepted. In two-column files, debit values become negative and credit values positive. A transaction-type column can explicitly identify debit or credit direction. Categorization is phrase-based rather than based on the amount sign, since bank and card providers encode direction differently. A positive, unknown merchant is still **Needs review**, never automatically classified as income.

## Data and limitations

The API accepts only CSV files up to 5 MB and 5,000 transactions. It supports UTF-8/Windows-1252 and comma, semicolon, or tab delimiters. It does not parse PDFs, OCR, multi-currency statements, or bank-specific pre-header metadata. Rows must contain date, description, and amount data. Duplicate transactions are retained. The API keeps no statement database and does not persist uploaded data. The UI displays amounts as USD; do not use a file with multiple currencies.

Rules are a starting point, not tax advice. Phrase matches can be wrong, and even a correct merchant category does not prove that an expense is deductible. Users should verify categories and business purpose with their bookkeeper or tax professional.

## Future improvements

Add opt-in merchant-rule customization, provider-specific CSV adapters, and transaction reconciliation after gathering feedback. Any expansion should preserve the conservative review path and avoid sending financial data to a categorization model.
