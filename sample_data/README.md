# Sample Data Files

All data is **100% fictional**. Institutions, account numbers, and people are made up.

| File | Format | Account type | Special features |
|------|--------|-------------|-----------------|
| `northwind_bank_checking.csv` | CSV - single Amount column | Checking | Preamble rows, refund row, transfer row, IRS payment |
| `contoso_card.csv` | CSV - single Amount column (inverted: purchases positive) | Credit card | Sign-convention inversion, CC payment row, annual fee |
| `fabrikam_cu_debit_credit.csv` | CSV - split Debit/Credit columns | Checking | Debit+Credit split, ATM withdrawal (owner draw) |

## Uploading

1. Start the backend: `uvicorn app.main:app --reload` from `backend/`
2. Open the app at http://localhost:3000 and go to **Upload**
3. Drop one of these files, select or create an account, confirm the mapping, click **Import**

The files are designed to exercise every branch of the categorization brain:
- Mixed-use merchants (Amazon, Uber) → Needs Review
- Refund detection (Amazon refund in northwind file)
- Transfer detection (savings transfer)
- Tax payment (IRS)
- Sign inversion (Contoso card - all purchases are positive amounts)
- Debit/Credit split columns (Fabrikam)
- ATM / owner draw (Fabrikam)
- B&H equipment purchase (high-value, needs review)
