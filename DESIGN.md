# Studio Ledger design

## Use case

Studio Ledger is for independent designers who use one business card for client work. It reads a CSV export from their bank and sorts spending into common tax-preparation categories: software, travel, meals, office supplies, professional services, and advertising. It also distinguishes income, transfers, and refunds from spending.

## Decision engine

The categorizer is intentionally small, deterministic, and inspectable. It normalizes the merchant description, then checks an ordered set of keyword rules. Rules for transfers, refunds, and income run before expense rules so that money movement is not accidentally reported as a business expense. A matching rule produces a high-confidence result and names the matched keyword. No match produces **Needs review** with low confidence rather than a guess.

The order matters:

1. Transfers (not spending)
2. Refunds (money back, not income)
3. Income
4. Merchant expense categories
5. Needs review

Rows can be corrected in the table. Manual changes are marked as manual and immediately update the category totals. The app does not persist uploaded data.

## CSV contract

Uploads must be UTF-8 CSV files with `Date`, `Description`, and `Amount` headers. Amounts may include dollar signs, commas, or accounting-style parentheses.
