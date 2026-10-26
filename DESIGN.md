# Design: Statement Categorizer

## 1. Problem and Use Case

People often receive bank statements with inconsistent descriptions, debit and credit columns, and merchant names that are difficult to interpret. Manually categorizing every transaction takes time and can lead to inconsistent financial reports.

The application imports a statement, normalizes its transaction data, assigns categories using explicit rules, and identifies transactions that need human review.

The primary goal is **useful categorization with explainable decisions**, rather than assigning a category to every transaction at any cost.

## 2. Main Workflow

1. **Upload:** The user submits a CSV, XLSX, or XLS statement.
2. **Validate:** The parser checks whether the file contains the required transaction information.
3. **Normalize:** Supported column names and amount formats are mapped to a consistent transaction structure.
4. **Categorize:** The categorization engine applies deterministic rules to transaction descriptions and amounts.
5. **Persist:** The statement and its transactions are stored in SQLite, linked through a statement ID.
6. **Review:** The user searches, filters, and manually corrects categories when needed.
7. **Report and export:** The dashboard displays financial summaries and allows categorized transactions to be exported as CSV.

## 3. Categorization Decision Process

The categorization engine uses explicit, explainable rules. The API's categorization path does not rely on a generative AI model to decide transaction categories.

### Decision priorities

- **Refunds:** Identify refund or reversal descriptions and assign the Refund category. Refunds are reported separately and are not counted as ordinary income.
- **Transfers:** Identify transfers, savings movements, and relevant payment transfers. Assign Transfer and exclude them from ordinary spending.
- **Known merchants and patterns:** Match recognizable transaction descriptions to categories.
- **Income:** Identify known income descriptions, such as salary payments.
- **Unknown descriptions:** Assign Needs Review when no reliable rule matches.

Examples of recognizable patterns include Adobe for Software and Uber for Transportation.

### Example decisions

| Input description | Decision | Reason |
|---|---|---|
| ADOBE CREATIVE CLOUD | Software | Matches a known software merchant pattern |
| UBER TRIP | Transportation | Matches a known transport pattern |
| SALARY PAYMENT | Income | Matches a known income pattern |
| TRANSFER TO SAVINGS | Transfer | Represents movement of funds, not ordinary spending |
| JOES CAFE 9921 | Needs Review | Merchant description is not sufficiently recognized |

These examples describe the intended rule behavior. Actual outcomes depend on the rules implemented in the current code.

## 4. Explainability and Confidence

Each categorized transaction stores fields such as category, status, reason, confidence, and source. These help explain whether the result came from an automatic rule or a manual correction.

A rule match should provide a reason that identifies the matching pattern. An unknown transaction should remain reviewable rather than receiving an unsupported category.

Confidence values should be interpreted according to how the application calculates them; they are not necessarily calibrated probabilities.

## 5. Human Review and Corrections

The user can change a transaction's category. The correction endpoint stores the selected category, marks the transaction as reviewed, and records a manual source and reason.

This creates a human-in-the-loop workflow: automatic rules handle familiar cases, while the user resolves ambiguous cases.

A manual correction changes the stored transaction. It should not be confused with the original automatic prediction.

## 6. Data Model

The application uses two principal database entities:

- **Statement:** Stores the uploaded filename, transaction count, and creation timestamp.
- **Transaction:** Stores the statement relationship, date, description, amount, currency, balance, category, review status, reason, confidence, source, and correction metadata.

A statement can have many transactions. Each transaction belongs to a statement through `statement_id`, allowing transactions from different uploads to be distinguished.

## 7. Financial Summary Logic

The summary service calculates income, spending, refunds, net spending, transaction count, and the number of transactions requiring review.

- Positive transactions categorized as Income contribute to total income.
- Negative transactions in ordinary spending categories contribute to spending.
- Refunds are tracked separately.
- Transfers and Needs Review transactions are excluded from ordinary spending totals.
- Net spending is calculated as the greater of zero and total spending minus total refunds.

The dashboard should calculate the summary from the same statement that it displays.

## 8. Limitations and Future Improvements

- Merchant descriptions can be ambiguous or abbreviated.
- Rule-based categorization depends on the coverage and quality of the patterns.
- Different banks may use different date, debit, credit, and currency conventions.
- Manually corrected categories are persisted, so the interface should distinguish them from automatic results.
- More tests are needed for unusual file formats, duplicate uploads, refunds, transfers, and ambiguous descriptions.

Possible future improvements include broader bank-format support, explicit duplicate detection, more extensive rule tests, and statement selection in the interface.
