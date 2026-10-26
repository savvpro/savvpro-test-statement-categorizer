# Design — Statement Categorizer

## Use Case

The target customer is a freelance designer preparing bank and credit card statements for tax reporting.

The application helps classify business expenses, identify refunds and transfers, detect duplicates, and review uncertain transactions.

## Architecture

Frontend: React and Vite.

Backend: Python and FastAPI.

Processing flow:

CSV Upload -> Parse -> Validate -> Categorize -> Review -> Summarize -> Export

The frontend communicates with the backend through REST API endpoints.

## Categorization Brain

The categorization brain is implemented in Python using deterministic rules and merchant matching.

It does not use GPT, Claude, Gemini or any external large language model to classify transactions at runtime.

Recognized transactions are assigned categories such as Software, Travel, Meals, Office, Education and Contractors.

Unknown or ambiguous merchants are marked Needs Review.

Classification details include confidence, reason and matched rule information.

## Transaction Handling

Positive amounts represent money out.

Refunds and transfers are distinguished from ordinary spending.

Duplicate transactions are detected and excluded from spending totals by default. Users may override duplicate handling.

Invalid rows are retained with validation information for review.

## Manual Corrections

Users can change transaction categories.

Merchant corrections are stored in memory and reused for matching transactions.

## Money and Currency

Amounts are represented as strings in API responses.

Spending summaries are calculated separately for each currency to avoid mixing incompatible monetary units.

## Security

- No real bank data is required.
- Sample transactions are synthetic.
- CSV export protects against spreadsheet formula injection.
- The application uses no external AI classification API.
- CORS is restricted to local development frontend origins.

## Testing

Automated backend tests cover the implemented API and transaction behavior.

The React frontend was verified using ESLint and a Vite production build.

Manual integration testing covered upload, category correction, duplicate override and summary updates.

## Trade-offs and Limitations

The application uses in-memory storage for assessment simplicity.

Data and corrections are lost after backend restart.

There is no authentication, database persistence or multi-user isolation.

A production implementation should add PostgreSQL, authentication, audit logs, persistent correction rules and deployment monitoring.

## Future Improvements

- Persistent database
- User authentication
- Automated frontend tests
- Additional statement formats
- Expanded merchant rules
- Docker deployment and CI
