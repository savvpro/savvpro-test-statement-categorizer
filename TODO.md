# simplke delivery outcomes

- [ ] **Import and validate statement CSVs.** The app lets a freelance designer upload a bank or business-card statement CSV, maps and validates date, description, amount, and transaction type columns, and flags malformed rows, missing values, and duplicate entries before categorization.
- [ ] **Categorize with an explainable deterministic brain.** Every valid row is normalized and categorized by code-owned merchant, direction, and amount rules; the result shows the category, confidence, and exact matching rule or condition. No large language model decides categories.
- [ ] **Make uncertainty actionable.** Unmatched, conflicting, malformed, duplicate, or low-confidence rows go to a dedicated Needs review queue. The user can assign a category to an individual row or approve several selected rows in one batch.
- [ ] **Show the tax-time picture.** The review view provides categorized, needs-review, and reviewed counts plus category totals and a concise spend breakdown for the freelance designer’s business statement.
- [ ] **Export the finished ledger.** The user can download a categorized CSV that preserves original transaction fields alongside category, status, confidence, rule, and review note details.
- [ ] **Provide Python backend coverage and documentation.** The repository includes a Python rule engine and HTTP API, tests, README setup/run instructions, DESIGN.md, AI_USAGE.md, and fake statement data only.
