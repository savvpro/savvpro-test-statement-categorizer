# Feature 2: CSV Parser & Sample Data

## Goal
Build a CSV parser that handles multiple bank/credit card statement formats, and create realistic fake sample data with all edge cases covered.

## Dependencies
- Feature 1 (backend models & brain) must be complete.

---

## Files to Create

### 1. `backend/app/services/__init__.py`
Empty file.

### 2. `backend/app/services/parser.py`
Function `parse_csv(file_content: bytes, filename: str) -> Tuple[List[TransactionRaw], List[str]]`

Returns a tuple of (parsed transactions, warnings list).

**Logic:**
1. Decode bytes to string (try UTF-8, then latin-1 fallback)
2. Use Python `csv` module with `csv.Sniffer` to auto-detect delimiter (comma, tab, semicolon)
3. Read header row and **normalize column names** (lowercase, strip whitespace)
4. Auto-detect column mapping using flexible matching:

| We need | Accept these column names |
|---------|--------------------------|
| `date` | `date`, `transaction date`, `posting date`, `trans date`, `posted` |
| `description` | `description`, `merchant`, `name`, `memo`, `transaction`, `payee`, `details` |
| `amount` | `amount`, `transaction amount`, `sum`, `value` |
| `debit` | `debit`, `withdrawal`, `money out` |
| `credit` | `credit`, `deposit`, `money in` |
| `type` | `type`, `transaction type`, `category` |

5. Handle **two amount formats**:
   - **Single column**: One `amount` column where negative = expense, positive = deposit (or vice versa for credit cards)
   - **Split columns**: Separate `debit` and `credit` columns — combine into single signed amount

6. Generate a unique `id` for each transaction (e.g., `TXN-001`, `TXN-002`, ...)
7. Skip empty rows, header-only files, or rows with no amount
8. Add warnings for: skipped rows, unrecognized columns, missing required columns, unparseable amounts
9. If no `date` or `description` column found → raise a clear `ValueError` with guidance

### 3. `backend/sample_data/sample_statement.csv`
A fake CSV file with **~30 transactions** covering every edge case. Use the format:
```
Date,Description,Amount
```

**Must include these scenarios:**

| # | Date | Description | Amount | Expected Category | Edge Case |
|---|------|-------------|--------|------------------|-----------|
| 1 | 2024-10-01 | GITHUB INC | -25.00 | Software & Subscriptions | Tier 1 known vendor |
| 2 | 2024-10-01 | AWS AMAZON WEB SERVICES | -149.99 | Software & Subscriptions | Tier 1 cloud hosting |
| 3 | 2024-10-02 | VERCEL INC | -20.00 | Software & Subscriptions | Tier 1 |
| 4 | 2024-10-02 | JETBRAINS S.R.O. | -24.90 | Software & Subscriptions | Tier 1 IDE |
| 5 | 2024-10-03 | OPENAI *CHATGPT PLUS | -20.00 | Software & Subscriptions | Tier 1 with POS prefix |
| 6 | 2024-10-03 | FIGMA INC | -15.00 | Software & Subscriptions | Tier 1 design tool |
| 7 | 2024-10-04 | UBER *TRIP HELP.UBER.COM | -32.50 | Travel & Transportation | Tier 1 rideshare with noise |
| 8 | 2024-10-04 | LYFT *RIDE 4829 | -18.75 | Travel & Transportation | Tier 1 with store number |
| 9 | 2024-10-05 | DELTA AIR 0062839201842 | -385.00 | Travel & Transportation | Tier 1 airline with ticket number |
| 10 | 2024-10-05 | MARRIOTT HOTELS SAN FRANCISCO CA | -225.00 | Travel & Transportation | Tier 1 hotel with city |
| 11 | 2024-10-06 | COMCAST CABLE COMM | -89.99 | Internet & Utilities | Tier 1 internet |
| 12 | 2024-10-06 | VERIZON WIRELESS | -85.00 | Internet & Utilities | Tier 1 cell phone |
| 13 | 2024-10-07 | GOOGLE *ADS 4838291 | -150.00 | Advertising & Marketing | Tier 1 ads with ID |
| 14 | 2024-10-07 | NAMECHEAP INC | -12.99 | Advertising & Marketing | Tier 1 domain registration |
| 15 | 2024-10-08 | STRIPE FEE | -4.35 | Professional & Legal | Tier 1 payment processing |
| 16 | 2024-10-08 | LEGALZOOM.COM | -149.00 | Professional & Legal | Tier 1 legal services |
| 17 | 2024-10-09 | SQ *AMZN MKTP US*2B71X99 | -89.99 | Office Supplies & Books | Tier 2: Amazon — **Needs Review** |
| 18 | 2024-10-09 | APPLE.COM/BILL | -1299.00 | Hardware & Equipment | Tier 2: Apple — **Needs Review** |
| 19 | 2024-10-10 | BEST BUY 00217 | -79.99 | Hardware & Equipment | Tier 2: Best Buy — **Needs Review** |
| 20 | 2024-10-10 | TARGET 02841 | -45.67 | Office Supplies? | Tier 2: Target — **Needs Review** (likely personal) |
| 21 | 2024-10-11 | STARBUCKS STORE 18294 | -6.45 | Meals & Client Entertainment | Tier 3: known chain, auto-verify |
| 22 | 2024-10-11 | SWEETGREEN FINANCIAL DIST | -14.50 | Meals & Client Entertainment | Tier 3: known chain |
| 23 | 2024-10-12 | JOES CAFE 9921 | -22.00 | Meals — **Needs Review** | Tier 3: unknown local cafe |
| 24 | 2024-10-12 | DOORDASH DASHPASS | -35.00 | Meals & Client Entertainment | Tier 3: food delivery |
| 25 | 2024-10-13 | REFUND AMAZON MKTP | 89.99 | Refund / Expense Reduction | Refund edge case |
| 26 | 2024-10-13 | RETURN CREDIT BEST BUY | 79.99 | Refund / Expense Reduction | Return edge case |
| 27 | 2024-10-14 | TRANSFER TO SAVINGS | -500.00 | Transfers & Non-Taxable | Internal transfer |
| 28 | 2024-10-14 | AUTOMATIC PAYMENT - THANK YOU | -2500.00 | Transfers & Non-Taxable | Credit card autopay |
| 29 | 2024-10-15 | STRIPE PAYOUT | 8500.00 | Gross Business Income | Revenue deposit |
| 30 | 2024-10-15 | UPWORK DIRECT DEPOSIT | 3200.00 | Gross Business Income | Revenue deposit |
| 31 | 2024-10-16 | ACH DEPOSIT CHECKING ACCT | 1500.00 | Gross Business Income — **Needs Review** | Ambiguous deposit |
| 32 | 2024-10-17 | RANDOM MERCHANT XYZ 88192 | -55.00 | Needs Review | Completely unknown |
| 33 | 2024-10-17 | POS PURCHASE THING #99281 | -12.34 | Needs Review | Very noisy, no identifiable merchant |

### 4. `backend/sample_data/sample_statement_split.csv`
An alternate format CSV with separate Debit/Credit columns:
```
Transaction Date,Details,Debit,Credit
```

Include ~10 rows from the same scenarios above to test split-column parsing.

---

## Acceptance Criteria

- [x] `parse_csv` successfully parses `sample_statement.csv` → returns 33 `TransactionRaw` objects
- [x] `parse_csv` successfully parses `sample_statement_split.csv` → returns correct transactions with proper sign
- [x] Warnings are generated for skipped/malformed rows
- [x] Column names are matched case-insensitively and with trimmed whitespace
- [x] Each transaction has a unique auto-generated `id`
- [x] Empty rows and header-only files don't crash the parser
- [x] `ValueError` raised for CSV files missing required columns (no date or no description)
- [x] All sample data uses **fake data only** — no real people, no real bank statements

## Git Commit
```bash
git add backend/app/services/ backend/sample_data/
git commit -m "feat(backend): add CSV parser with multi-format support and sample statement data"
git push origin candidate-sikandarhussain6858
```
