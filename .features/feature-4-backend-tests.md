# Feature 4: Backend Tests

## Goal
Write a comprehensive pytest test suite covering every brain module, the parser, and the API endpoints.

## Dependencies
- Features 1, 2, 3 must be complete.

---

## Files to Create

### 1. `backend/tests/__init__.py`
Empty file.

### 2. `backend/tests/test_sanitizer.py`
Test `sanitize_merchant()`:

```python
# Test cases to cover:
("CHECKCARD POS PURCHASE SQ *GITHUB #1042 SAN FRANCISCO CA", "GITHUB")
("TST*STARBUCKS STORE 18294 SEATTLE WA", "STARBUCKS STORE")
("AMZN Mktp US*2B71X99", "AMAZON MKTP US")
("APL*APPLE.COM/BILL", "APPLE.COM/BILL")
("UBER *TRIP HELP.UBER.COM", "UBER TRIP")
("DELTA AIR 0062839201842", "DELTA AIR")
("RECURRING TRANSACTION GITHUB INC", "GITHUB INC")
("", "UNKNOWN")  # Empty input
("X", "X")  # Single character (too short after clean)
```

### 3. `backend/tests/test_direction.py`
Test `analyze_direction_and_type()`:

```python
# Transfers
("TRANSFER TO SAVINGS", -500) → TransactionDirection.TRANSFER
("AUTOMATIC PAYMENT - THANK YOU", -2500) → TransactionDirection.TRANSFER
("CREDIT CARD PAYMENT", -1000) → TransactionDirection.TRANSFER

# Refunds (by keyword)
("REFUND AMAZON MKTP", 89.99) → TransactionDirection.REFUND
("RETURN CREDIT BEST BUY", 79.99) → TransactionDirection.REFUND

# Income
("STRIPE PAYOUT", 8500) → TransactionDirection.INFLOW
("UPWORK DIRECT DEPOSIT", 3200) → TransactionDirection.INFLOW

# Refund by vendor (inflow from expense vendor)
("AMAZON", 89.99, clean_merchant="AMAZON") → TransactionDirection.REFUND

# Regular expense
("GITHUB INC", -25) → TransactionDirection.OUTFLOW
```

### 4. `backend/tests/test_classifier.py`
Test `StatementBrain.categorize_transaction()`:

```python
brain = StatementBrain()

# Tier 1: High confidence, auto-verified
("GITHUB INC", -25.00) → category="Software & Subscriptions", confidence≥0.95, needs_review=False
("UBER *TRIP", -32.50) → category="Travel & Transportation", confidence≥0.95, needs_review=False
("COMCAST CABLE", -89.99) → category="Internet & Utilities", confidence≥0.95, needs_review=False

# Tier 2: Mixed-use, needs review
("AMAZON PURCHASE", -89.99) → category="Office Supplies & Books", needs_review=True
("APPLE.COM/BILL", -1299) → needs_review=True
("TARGET 02841", -45.67) → needs_review=True

# Tier 3: Meal keywords
("STARBUCKS STORE 18294", -6.45) → category="Meals & Client Entertainment", needs_review=False (known chain)
("JOES CAFE 9921", -22.00) → category="Meals & Client Entertainment", needs_review=True (unknown cafe)

# Direction cases
("TRANSFER TO SAVINGS", -500) → category="Transfers & Non-Taxable", needs_review=False
("STRIPE PAYOUT", 8500) → category="Gross Business Income", needs_review=False
("REFUND AMAZON", 89.99) → category="Refund / Expense Reduction", needs_review=False

# Fallback
("RANDOM MERCHANT XYZ", -55.00) → category="Needs Review", confidence≤0.30, needs_review=True

# Deductibility
Meals → deductible_percentage=0.50
Software → deductible_percentage=1.0
Transfers → deductible_percentage=0.0, tax_deductible=False
```

### 5. `backend/tests/test_tax_summary.py`
Test `calculate_tax_summary()`:

```python
# Create a list of known categorized transactions and verify:
# - gross_income sums only verified INFLOW transactions
# - total_expenses sums OUTFLOW amounts
# - total_deductible_expenses correctly applies per-category deductible_percentage
# - Meals apply 50% deductibility (e.g., $100 meal → $50 deductible)
# - Refunds reduce total expenses (not increase income)
# - Transfers are tracked separately in non_taxable_transfers
# - needs_review_count matches count of NEEDS_REVIEW items
# - net_taxable_profit = gross_income - total_deductible_expenses
# - estimated_tax_savings = total_deductible_expenses × 0.28
# - categories list has correct grouping and totals
```

### 6. `backend/tests/test_parser.py`
Test `parse_csv()`:

```python
# Test standard CSV
parse_csv(sample_statement_bytes, "statement.csv") → 33 transactions, 0 warnings

# Test split debit/credit format
parse_csv(sample_split_bytes, "split.csv") → correct transactions with right sign

# Test missing required columns
parse_csv(b"col1,col2\n1,2", "bad.csv") → raises ValueError

# Test empty file
parse_csv(b"", "empty.csv") → raises ValueError

# Test extra whitespace in headers
parse_csv(b" Date , Description , Amount \n2024-01-01,TEST,-10", "spaces.csv") → 1 transaction

# Test semicolon delimiter
parse_csv(b"Date;Description;Amount\n2024-01-01;TEST;-10", "semi.csv") → 1 transaction
```

### 7. `backend/tests/test_api.py`
Test FastAPI endpoints using `httpx.AsyncClient` with `TestClient`:

```python
from fastapi.testclient import TestClient
from app.main import app
client = TestClient(app)

# GET /api/categories → 200, returns dict with 13 categories
# GET /api/sample → 200, returns CategorizeResponse with transactions
# POST /api/upload with valid CSV → 200, returns categorized data
# POST /api/upload with .txt file → 400 error
# POST /api/upload with empty CSV → 400 error
# POST /api/recalculate with valid body → 200, returns updated TaxSummary
```

---

## Acceptance Criteria

- [x] `cd backend && python -m pytest tests/ -v` passes all tests
- [x] Minimum **25 test cases** across all test files
- [x] Every brain module (sanitizer, direction, classifier, tax_summary) has at least 5 test cases
- [x] Parser tests cover standard format, split format, edge cases, and error cases
- [x] API tests cover all 4 endpoints including error responses
- [x] No tests rely on external services or network calls

## Verification
```bash
cd backend
python -m pytest tests/ -v --tb=short
```

## Git Commit
```bash
git add backend/tests/
git commit -m "test(backend): add comprehensive test suite for brain, parser, and API endpoints"
git push origin candidate-sikandarhussain6858
```
