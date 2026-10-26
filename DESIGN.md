
# Design Document — Statement Categorizer

## 1. Use Case

This application helps freelancers organize bank or credit card statement transactions for tax-time preparation. It reads a CSV statement, categorizes transactions using a custom Python rule-based engine, and allows users to review and correct the results before exporting them.

The tool supports organization and review of transaction records. It does not determine whether an expense is legally tax-deductible.

## 2. User Workflow

1. The user uploads a CSV file containing transaction descriptions and amounts.
2. The backend validates the file type, file size, required columns, and transaction amounts.
3. Each valid transaction is passed to the categorization engine.
4. The engine checks transaction descriptions against predefined rules.
5. Recognized transactions receive a category and an explanation.
6. Transactions that cannot be confidently categorized are marked `Needs Review`.
7. The frontend displays the results and allows the user to correct categories.
8. The user can export the reviewed transactions as a CSV file.

## 3. Architecture

### Frontend
- React and TypeScript
- Allows CSV upload and displays categorized transactions.
- Supports manual category changes.
- Exports the current reviewed results to CSV.

### Backend
- Python and FastAPI
- Validates uploaded CSV files.
- Parses transaction descriptions and amounts.
- Calls the custom categorization engine.
- Returns categorized transaction data as JSON.

### Categorization Engine
- Implemented in `backend/app/categorizer.py`.
- Uses explicit keyword-based rules rather than an external large language model.
- Returns a category, status, and reason for each transaction.

## 4. Decision Engine

The categorization engine applies rules in a deliberate order:

1. **Transfer detection:** Descriptions containing recognized transfer phrases are categorized as `Transfer`. Transfers are not treated as ordinary spending.
2. **Refund detection:** Descriptions containing recognized refund or reversal phrases are categorized as `Refund`, not income.
3. **Merchant keyword matching:** Known descriptions are matched to predefined categories:
   - Software & Subscriptions
   - Office Supplies
   - Travel
   - Meals
   - Utilities
4. **Fallback:** If no rule matches, the transaction is marked `Needs Review` instead of guessing.

### Example Decisions

| Transaction description | Expected category | Reason |
|---|---|---|
| GitHub subscription | Software & Subscriptions | Matches a known software merchant |
| Uber trip | Travel | Matches a known travel merchant |
| Account transfer | Transfer | Recognized transfer wording |
| Adobe refund | Refund | Recognized refund wording |
| Unknown merchant 123 | Needs Review | No matching rule |

The rules are intentionally simple and transparent so users can understand why a category was assigned.

## 5. Error Handling and Validation

The API rejects unsupported file types, files that exceed the configured size limit, missing required columns, empty descriptions, and invalid numeric amounts. CSV parsing and validation help prevent malformed input from being processed as valid transactions.

## 6. Limitations and Risks

- Categorization depends on transaction-description keywords. Unrecognized merchant names may require manual review.
- A refund keyword does not prove which original transaction was refunded.
- Bank statement amount signs and transaction descriptions can vary between banks.
- A transfer may be difficult to identify if its description does not contain a recognized phrase.
- The application does not verify tax deductibility or provide tax advice.
- The current version accepts CSV files with `description` and `amount` columns.
- Reviewed changes are available for export, but are not persisted in a database after the session.
- The rules are a starting point and should be expanded with additional test cases and realistic, anonymized examples.

## 7. Privacy and Security

Use only synthetic or properly anonymized transaction data during development and testing. Do not commit real bank statements, credentials, API keys, or other sensitive information to the repository.
