# Design Document: Statement Categorizer

## 1. Target User

The target user is a freelance designer or independent freelancer who wants to organize business transactions from bank statements.

## 2. Technology Stack

- Backend: Python and FastAPI
- Data processing: pandas
- CSV parsing: pandas
- PDF table extraction: pdfplumber
- Data validation: Pydantic
- Frontend: React and Vite
- Categorization: Keyword-based rules
- Testing: pytest

## 3. Processing Workflow

1. The user uploads a CSV or PDF statement.
2. The backend extracts transaction dates, descriptions, and amounts.
3. CSV files must contain date, description, and amount columns.
4. Transaction descriptions are normalized to uppercase, and digits and special characters are removed.
5. The categorizer checks descriptions against predefined merchant keywords.
6. Direct keyword matches receive high confidence.
7. Partial matches receive low confidence.
8. Unknown transactions are assigned Needs Review.
9. Users can inspect transactions and edit their categories.

## 4. Categories

The application defines these categories:

- Software
- Travel
- Meals & Entertainment
- Office Supplies
- Utilities
- Advertising & Marketing
- Freelance Income
- Transfer
- Refund
- Needs Review

## 5. Categorization Logic

The application uses deterministic keyword matching rather than a large AI model for transaction categorization.

Examples include Adobe and Figma for software, Uber for travel, Starbucks for meals, Amazon for office supplies, and Upwork for freelance-related transactions.

Unknown descriptions are assigned Needs Review. Keyword matches may be incorrect, so users should review uncertain transactions.

## 6. Refunds and Transfers

Currently, every negative amount is categorized as a Refund. This is a simple heuristic and can incorrectly classify other negative transactions.

Transfers and freelance-related transactions are identified using predefined keywords. Merchant keywords alone cannot reliably determine whether a transaction represents income, spending, or an internal transfer.

## 7. File Parsing

CSV parsing requires date, description, and amount columns. Invalid numeric amounts are currently replaced with zero.

PDF parsing extracts tables and assumes the first three cells represent date, description, and amount. Different PDF layouts may require manual verification.

Only CSV and PDF files are supported by the parser.

## 8. Limitations and Future Improvements

- Unknown merchants may require manual categorization.
- Keyword matching can produce false positives.
- Negative amounts do not always represent refunds.
- Invalid CSV amounts should ideally be reported instead of replaced with zero.
- PDF table layouts may affect extraction accuracy.
- Financial summaries should distinguish income, expenses, refunds, and transfers correctly.
- More edge-case tests and stronger input validation would improve reliability.

## 9. Testing

Backend tests are located in backend/tests/.

Run tests from the backend directory:

python -m pytest -v

Test results should be reported only after running the final submitted version.