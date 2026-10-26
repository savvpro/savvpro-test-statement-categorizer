# Design

## Use case

The user is a **UK freelancer or sole trader** (designer, developer or consultant) preparing their **Self Assessment (SA103)**. They export the account they use for business as a CSV and upload it.

The app produces four things:

1. **Business income**, separated from money in that isn't income (refunds, transfers, interest)
2. **Allowable expenses** by SA103 category, separated from **personal** spending and **tax payments**
3. A review list for anything uncertain. Export stays locked until every row on it is resolved.
4. A **tax estimate**: profit, income tax, Class 4 NIC and how much to set aside

When the user corrects a merchant, they can tell the app to remember it. Each statement then needs less review than the last.

**Categories:** Business Income, Phone/Internet & Software, Office Costs, Travel, Professional Fees, Advertising & Marketing, Training, Bank & Finance Charges, Tax Payments, Refund, Transfer (Not Spending), Personal (Not Allowable), Needs Review.

## Architecture

```
React UI ──HTTP──► API (routes, schemas)
                     │
                     ▼
                  Services ──► ReaderRegistry ──► CsvStatementReader   (ingestion)
                     │
                     ├──► CategorizationEngine                         (categorization)
                     │        classifier chain → ConfidencePolicy → post-processors
                     │        uses RuleBook (data/rules.json) + MerchantRuleRepository (learning)
                     │
                     └──► totals, tax estimate                         (reporting)
```

The backend is split into layers. Dependencies point inwards: the API knows about services, and services know about the domain. The domain knows nothing about HTTP, files or storage.

### Design principles applied

| Principle | Where it shows up |
|-----------|-------------------|
| **Single Responsibility** | Each classifier handles one concern: duplicates, learned rules, transfers, refunds, credits, mixed-use merchants, keywords. Parsing, categorizing, reporting and persistence are separate modules. |
| **Open/Closed** | To add a behaviour, write a new `Classifier` or `PostProcessor`. To add a file format, write a `StatementReader`. To add merchants, edit `rules.json`. The engine itself doesn't change. |
| **Liskov Substitution** | `InMemoryMerchantRuleRepository` and `JsonFileMerchantRuleRepository` are interchangeable. Tests use one and production uses the other. |
| **Interface Segregation** | Small `Protocol`s (`Classifier`, `PostProcessor`, `StatementReader`, `MerchantRuleRepository`), each with one or two methods. |
| **Dependency Inversion** | The engine and services depend on protocols. Concrete classes are wired in two composition roots, `categorization/factory.py` and `main.create_app`. |
| **Chain of Responsibility** | The classifier pipeline: the first classifier that can decide wins. |
| **Strategy / Policy** | `ConfidencePolicy` decides whether a verdict is trusted, separately from producing it. |
| **Repository** | Learned rules sit behind a storage-agnostic interface. File writes are atomic (temp file, then rename). |
| **Factory / DI** | `create_app(settings, rule_repository)` lets tests inject in-memory dependencies. No global state is mutated. |
| **Configuration as data** | Merchant knowledge is in JSON. Thresholds and limits come from environment variables (12-factor). |
| **Fail-safe errors** | Domain errors map to clear HTTP 4xx responses in one exception handler. Bad rows become per-row issues and don't fail the upload. |

The frontend follows the same idea. Components only render, the `useStatement` hook owns state and actions, and all HTTP calls go through one API client in `lib/api.js`.

## How the engine decides

### 1. Normalize the description

The normalizer strips bank prefixes (`CARD PAYMENT TO`, `DD`, `POS`), reference numbers, dates and punctuation. For example, `CARD PAYMENT TO UBER *TRIP 8812 ON 03 MAR` becomes `UBER TRIP`.

It also derives a stable **merchant key** by dropping words like `LTD`, `COM` and `REFUND`. That way `TRAINLINE.COM 77731` and `TRAINLINE.COM REFUND` are both recognised as `TRAINLINE`.

### 2. Run the classifier chain

Rows are processed in date order. The first classifier that can decide wins:

| # | Classifier | Decision |
|---|------------|----------|
| 1 | Duplicate | Same date, text and amount as an earlier row: Review, flagged `duplicate` |
| 2 | Learned rule | The user's saved rule for this merchant. It only applies if the direction fits: an expense rule never turns a refund into an expense. |
| 3 | Transfer | Own-account moves and card repayments: `Transfer (Not Spending)` |
| 4 | Refund | Credits only. If there is an earlier purchase from the same merchant that is at least as large, the refund takes that purchase's category so the expense nets off, and each purchase can only be refunded once. If the credit has refund wording but no matching purchase, it goes to `Refund`. **A refund is never income.** |
| 5 | Credit | Interest, salary, HMRC or loan credits go to Review. Client-payment wording means `Business Income`. Anything else goes to Review, with Income as a suggestion. |
| 6 | Mixed-use | Debits at Amazon, PayPal, Apple and similar shops always go to Review. |
| 7 | Keyword | Weighted, whole-word matching against `rules.json`. If the top two categories are less than 0.2 apart, the row goes to Review as a conflict. |
| 8 | Fallback | Review, as an unknown merchant |

### 3. Apply the confidence policy

Any verdict scoring below 0.7 becomes Needs Review. The engine's best guess is kept as a **suggestion**, so the user can accept it in one click.

### 4. Run the post-processors

These look across the whole statement:

- **Large amount:** expenses of £1,000 or more are flagged as possible capital assets.
- **Recurring:** the same merchant charging a similar amount (within 10%) in two or more months is flagged as a subscription.

### Why lean towards review?

The brief says a wrong guess is worse than asking, so every threshold favours Review. The UI keeps review cheap: one-click suggestions, "apply to all from this merchant", and learned rules. A user who corrects a merchant once never has to correct it again.

## Tax estimate

`reporting/tax.py` uses 2025/26 rates for England, Wales and Northern Ireland:

- **Personal allowance:** £12,570, tapered by £1 for every £2 of income over £100,000
- **Income tax:** 20%, 40% and 45% bands
- **Class 4 NIC:** 6% between £12,570 and £50,270, then 2% above that
- **Deduction:** whichever is larger of actual allowable expenses and the £1,000 trading allowance

It assumes self-employment is the only income. The UI labels the result as an estimate, not tax advice.

## Messy-data cases handled

- **Reading the file:**
  - header and column variants, including split money-in/money-out columns
  - currency symbols, thousands separators, `(x)`, `DR`/`CR`
  - UK and ISO dates
  - BOM and Latin-1 encodings
  - blank lines, zero-value rows and broken rows (reported per row, not fatal)
- **Money in and out:**
  - refunds: matched to the original purchase, never income; a refund dated before its purchase is not matched
  - transfers, card repayments and HMRC payments: excluded from income and expenses
- **Flags and reviews:**
  - duplicates
  - mixed-use merchants
  - conflicting keywords
  - large purchases
  - recurring subscriptions
- **Limits:** a 5 MB upload limit and a 10,000-row limit, both configurable

## Next steps

- More formats (OFX/QIF, then PDF) as new `StatementReader` implementations
- Multi-user accounts, with the JSON repository swapped for Postgres behind the same interface
- Per-user thresholds, and VAT tracking for VAT-registered freelancers
