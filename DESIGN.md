# System Architecture & Design Document

## 1. Selected Use Case & Persona

**Target Persona:** Freelance Web & Graphic Designer preparing annual schedule C income and expense categorizations for tax reporting.

**Domain Context:**
Freelancers typically use a single primary business checking account or credit card for business expenses (software subscriptions, cloud hosting, client payments, rideshares, office supplies). However, real statements are inherently messy:
- Software subscriptions frequently have duplicate bills or occasional prorated refunds.
- Personal transfers (e.g. transfers between own checking/savings, ATM cash withdrawals) show up in statements but must **not** be calculated as tax-deductible expenses or taxable income.
- Peer-to-peer payments (Venmo, Zelle) are ambiguous: a payment to a subcontractor is a tax-deductible expense, whereas a personal draw is an internal transfer.
- Outgoing vendor invoices (`Invoice from Vendor`) are expenses or require review, and must **never** be classified as client revenue just because they contain the word "invoice".
- Incoming refunds must not reduce business expenses unless safely validated and matched to a legitimate business expense category.
- Unknown coffee shops or lunch venues (`JOES CAFE 9921`) should not be silently converted to business expenses without client confirmation.

---

## 2. Architecture & Tech Stack Rationale

The system follows a clean client-server architecture with strict separation between data presentation and deterministic accounting logic:

```text
[User / Browser]
       │
       ▼
[Next.js 16 + React 19 Frontend]
  • Drag & Drop File Upload
  • Live Recalculations & State Management
  • Category & Treatment Editing
  • Filter & CSV Export
       │  REST API (JSON / Multipart)
       ▼
[FastAPI + Python 3.11 Backend]
  • In-Memory Parser (Validates CSV schema, dates, currency, finiteness)
  • The Deterministic Brain (Rule priority hierarchy with direction checks)
  • Audit Trail Annotator (Rule ID, confidence, rationale, prior purchase linking)
  • Decimal Summary Calculator (Operating P&L, validated refunds, transfers)
```

### Why FastAPI + Python?
1. **Financial Exactness (`Decimal`):** JavaScript's native IEEE-754 `Number` introduces precision errors when aggregating dollar values (e.g., `0.1 + 0.2 = 0.30000000000000004`). Python's native `decimal.Decimal` guarantees exact cent-level arithmetic across tax aggregates. The parser also verifies `amount.is_finite()` and rejects non-numbers (`NaN`, `Infinity`).
2. **Strict Schema Contracts (`Pydantic`):** Request and response validation ensures that invalid dates, non-numeric values, or corrupted structures fail loudly with descriptive, row-specific error messages.
3. **In-Memory Simplicity:** Avoiding a traditional database in V1 keeps the system lightweight, zero-configuration for reviewers, and removes migration overhead while focusing on core categorization logic.

### Why Next.js + TypeScript?
1. **Interactive Feedback:** Real-time updates as the user edits categories, changes financial treatments, or marks items as confirmed.
2. **Type Safety:** Shared model interfaces across backend Pydantic models and frontend TypeScript types prevent silent payload mismatches.

---

## 3. The Categorization Pipeline ("The Brain")

The pipeline executes in sequential stages:

```text
CSV Bytes 
   │
   ▼
[1. CSV Parser & Sanitizer]
   • Validate required headers: Date, Description, Amount
   • Encoding fallback (UTF-8-SIG -> UTF-8 -> Latin-1)
   • Normalize date formats (YYYY-MM-DD, MM/DD/YYYY, DD/MM/YYYY)
   • Flag ambiguous date values (e.g. 03/04/2026 where day and month <= 12)
   • Strip currency symbols ($, commas) and validate finite Decimal values
   • Collect line-item warnings for malformed or empty rows
   │
   ▼
[2. Normalized Duplicate Detection Engine]
   • Normalize descriptions (strip punctuation, collapse whitespace, lowercase)
   • Group transactions by composite key: (Date, Normalized Description, Amount)
   • Flag identical rows with `is_possible_duplicate: true` and assign `duplicate_group_id`
   • Route duplicates to `Needs Review` rather than silently deleting data
   │
   ▼
[3. Priority Rule Matcher with Direction Awareness]
   • Priority 10: Verified Internal Transfers & Cash Withdrawals
   • Priority 15: P2P Contractor Payments (Venmo/Zelle to contractors -> Contractor Expense)
   • Priority 20: Incoming Refunds (Validated & linked to prior purchases; unmatched held in Needs Review)
   • Priority 28: Specific Payment Processing Fees (Stripe, PayPal, Square, Merchant fees)
   • Priority 32: General Bank Fees (Monthly maintenance, Overdraft, Interest, Late fees)
   • Priority 45: Outgoing Vendor Invoices (Negative amounts -> General Expense or Needs Review)
   • Priority 50: Verified Client Income (Positive amounts only)
   • Priority 60–69: Known Business Expenses (Software, Cloud Hosting, Ads, Travel, Supplies)
   • Priority 100: Fallback Engine (P2P ambiguities, negative revenue contradictions -> Needs Review)
   │
   ▼
[4. Financial Summary Engine]
   • Operating Income = Sum of verified INCOME (amount > 0)
   • Gross Expenses = Sum of |EXPENSE|
   • Matched Refunds = Sum of confirmed refunds linked to business expense categories
   • Unmatched Refunds = Reported in Needs Review, NOT deducted from expenses
   • Net Expenses = Gross Expenses - Matched Refunds
   • Bank & Processing Fees = Sum of |FEE|
   • Net Operating Result = Operating Income - Net Expenses - Fees
   • Transfers = Excluded from operating result
```

---

## 4. Rule Precedence & Conflict Resolution

A common flaw in rudimentary categorizers is relying on the arithmetic sign alone:
$$\text{Positive} \implies \text{Income}, \quad \text{Negative} \implies \text{Expense}$$

This leads to catastrophic tax errors (e.g. treating a vendor invoice of `-$50.00` as Client Income, or treating an unmatched refund as an automatic expense deduction).

### Priority Hierarchy:
1. **Priority 10: Verified Transfers (`transfer`)**
   - *Patterns:* `transfer to/from savings`, `transfer to/from checking`, `transfer between own accounts`, `atm withdrawal`
   - *Rationale:* Capital moving between verified personal and business accounts is not an operating event.
2. **Priority 15: P2P Contractor Payments (`expense`)**
   - *Patterns:* `venmo to contractor`, `zelle to freelancer`, `paypal to designer`
   - *Rationale:* P2P payments with explicit contractor context are recognized as deductible contractor expenses, preventing them from being wrongly excluded as transfers.
3. **Priority 20: Refunds (`refund`)**
   - *Patterns:* `refund`, `reversal`, `credit adjustment`
   - *Direction Check:* Must have positive amount. Negative amounts with "refund" are treated as customer payouts and routed to `Needs Review`.
   - *Expense Linking:* The engine attempts to link the refund to a prior purchase in the statement (e.g. `REFUND - ADOBE CREATIVE CLOUD` linked to prior Adobe expense). If matched, it reduces `Software` expenses. If unmatched (`Unknown` category), it stays in `Needs Review` and does **not** reduce expenses.
4. **Priority 28: Payment Processing Fees (`fee`)**
   - *Patterns:* `stripe fee`, `stripe processing fee`, `paypal fee`, `square fee`, `merchant fee`
   - *Resolution of Priority Conflict:* Evaluated **before** general bank fees (Priority 32), ensuring `STRIPE PROCESSING FEE` is properly categorized as `Payment Processing`.
5. **Priority 32: General Bank Fees (`fee`)**
   - *Patterns:* `monthly fee`, `overdraft fee`, `interest charge`, `late payment fee`, `wire fee`
   - *Category:* `Bank Fees`.
6. **Priority 45: Vendor Invoices (`expense`)**
   - *Patterns:* `invoice from vendor`, `invoice payment to`, `vendor invoice`, `supplier invoice`
   - *Direction Check:* Negative amounts only. Classified as `General Expense` or routed to review, preventing confusion with client revenue.
7. **Priority 50: Known Client Income (`income`)**
   - *Patterns:* `client payment`, `payment received`, `acme corp`, `paypal *freelande`, `webflow project`
   - *Direction Check:* Enforces positive amounts (`amount > 0`). Broad "invoice" pattern removed.
8. **Priority 60–69: Known Business Expenses (`expense`)**
   - *Patterns:* Strict regex word boundaries (`\baws\b`, `\badobe\b`, `\bgoogle ads\b`, `\buber\b`, `\bstaples\b`). Prevents false matches such as `aws` matching `flaws` or `lawson`.
9. **Priority 100: Fallback (`unknown`)**
   - Ambiguous P2P payments without contractor context (`Venmo payment`) route to `Needs Review`.
   - Contradictory records (e.g. negative income descriptions) route to `Needs Review`.

---

## 5. Confidence Ratings & "Needs Review" Strategy

- **`HIGH`:** Exact or unambiguous pattern match with verified direction (e.g., `ADOBE CREATIVE CLOUD`, `DELTA AIR LINES`, `STRIPE PROCESSING FEE`).
- **`MEDIUM`:** Recognized category with minor contextual variation (e.g., `VENDOR INVOICE`).
- **`LOW`:** Unrecognized merchants (`JOES CAFE 9921`), ambiguous P2P transfers, or unmatched refunds.

**Guiding Philosophy:** *"A wrong guess is worse than asking."*
Instead of guessing whether an unknown \$18.40 charge at Joe's Cafe was personal coffee or a business client meeting, the system flags it for the freelancer to review and confirm with one click.

---

## 6. Financial Summary Math & Treatment

| Transaction Type | Example | Impact on Operating Result |
| :--- | :--- | :--- |
| **`income`** | Client Invoice (\$5,000.00) | Added to `total_income` (only positive amounts) |
| **`expense`** | AWS Hosting (-\$149.00) | Added to `total_expenses` |
| **`refund` (matched)** | Adobe Refund (+\$54.99) | Deducted from `total_expenses` to form `net_expenses` |
| **`refund` (unmatched)** | Mystery Refund (+\$30.00) | Reported in Needs Review, **not** deducted from expenses |
| **`fee`** | Stripe Processing Fee (-\$45.00) | Deducted from operating result |
| **`transfer`** | Transfer to Savings (-\$500.00) | **Excluded** from operating result |

$$\text{Net Operating Result} = \text{Total Income} - (\text{Total Expenses} - \text{Matched Refunds}) - \text{Total Fees}$$

---

## 7. Why No Runtime LLM? ("The Big Rule")

The assessment instructions strictly required:
> *"The brain must be your own code. Do not use a big AI model (like GPT, Claude or Gemini) to decide a category."*

### Architectural Advantages of Deterministic Rules over LLMs in Financial Categorization:
1. **100% Deterministic & Auditable:** Tax authorities require consistent, explainable classifications. With rule IDs (`R001`, `R010`, `R025`, `R040`), every assigned category can be defended during an audit.
2. **Zero Latency & Cost:** Processing 10,000 statement lines takes milliseconds locally without API rate limits or recurring inference costs.
3. **No Hallucination Risk:** LLMs can hallucinate non-existent categories or misinterpret negative numbers depending on prompt phrasing.
4. **Air-Gapped Privacy:** Client financial statements remain strictly within the user's local runtime without transmitting sensitive banking data to third-party AI APIs.

---

## 8. Current Limitations & Planned Improvements

1. **Rule Learning:** Adding local SQLite storage to persist user-created rules so that when a user corrects `JOES CAFE 9921` to `Meals & Entertainment`, future statements remember this merchant.
2. **Fuzzy String Distance:** Incorporate Levenshtein distance for typos or varying merchant prefixes.
3. **Multi-Currency:** Support statements with currency columns or exchange rate conversions.
