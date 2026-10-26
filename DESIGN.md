# Design Document — E-commerce Statement Categorizer

## 1. Use Case

The application helps small e-commerce business owners organize transactions for bookkeeping and financial review. Users upload a CSV statement, review automatically assigned categories, and correct categories when necessary.

**Input:** CSV containing `date`, `description`, and `amount`.

**Output:** Categorized transactions with explanations, review flags, and category totals.

## 2. Architecture

- **Frontend:** React and Vite handle CSV uploads, display transactions, allow manual category changes, and calculate category totals.
- **Backend:** FastAPI validates uploaded files and transaction data, then calls the Python categorization function.
- **Categorization engine:** `categorizer.py` applies explicit rules without using an external AI model at runtime.

## 3. Categorization Logic

The categorizer normalizes transaction descriptions by converting them to uppercase and removing extra whitespace. It then applies rules in this order:

1. **Missing description:** Assign `Needs Review`.
2. **Transfer:** If the description contains `TRANSFER`, assign `Transfer - Not Spending`.
3. **Refund:** If the description contains `REFUND`, assign `Refund`.
4. **Known merchant:** Match predefined merchant keywords to categories such as Inventory and Supplies, Shipping and Delivery, Advertising and Marketing, Platform Fees, Software, and Utilities.
5. **Unrecognized positive amount:** Assign `Needs Review`, since it could represent income, a refund, or another transaction.
6. **Other unmatched transaction:** Assign `Needs Review`.

Each result includes a reason explaining the rule that matched or why review is required.

## 4. Validation and Error Handling

The API checks the file extension, file size (maximum 2 MB), UTF-8 encoding, required and duplicate headers, row structure, required dates and amounts, date validity (`YYYY-MM-DD`), and finite numeric amounts. Invalid files or rows produce clear error responses.

## 5. Design Decisions

- **Deterministic rules:** Results are predictable and easy to explain.
- **Conservative categorization:** Unknown transactions are flagged rather than assigned potentially misleading categories.
- **Manual review:** Users can correct categories in the frontend.
- **No persistent storage:** Uploaded transactions and manual changes are not saved to a database.

## 6. Limitations

- Only CSV input is supported.
- Merchant matching relies on predefined text rules and may miss unfamiliar descriptions.
- A description containing `TRANSFER` or `REFUND` may be classified incorrectly if the keyword is misleading.
- The application does not infer currency or determine tax deductibility.
- Category totals are for organization and review, not tax advice.
