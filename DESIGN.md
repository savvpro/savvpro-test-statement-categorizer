# TaxSort – System Design & Architecture Document

## 1. Use Case & Problem Definition

### Target Customer
**US Freelancers, Sole Proprietors, and Single-Member LLCs** filing **IRS Form 1040 Schedule C** (Profit or Loss From Business).

### The Real-World Pain Point
At tax time, self-employed professionals face a chaotic mix of bank and credit card statements containing hundreds or thousands of transactions. Generic financial apps either:
1. Make users manually label every row in spreadsheets, or
2. Rely on non-deterministic cloud LLMs that hallucinate, guess without certainty, violate privacy by sending unredacted banking data to third-party APIs, or silently miscategorize tax-critical lines.

Under IRS audit standards, **a wrong guess is far worse than asking**. Miscategorizing a personal expense as a business deduction triggers penalties, while classifying an expense refund as business income causes double taxation.

TaxSort solves this with **TaxSort Brain**: a **100% deterministic, local, rule-and-dictionary-driven categorization engine** built into a high-performance Python/FastAPI backend paired with a clean, distraction-free Next.js dashboard.

---

## 2. The Brain Architecture (Rule: No Big AI Model in the Path)

The categorizer is engineered strictly around deterministic algorithms, lexical tokenizers, regex normalizers, curated IRS Schedule C taxonomies, and conservative fuzzy ratio heuristics.

```
Statement Upload (CSV / PDF)
             │
             ▼
   [1. Format & Sign Normalizer]
      - Detects Checking vs. Credit Card
      - Unifies Debit/Credit vs. Signed Amount columns
      - Resolves negative amount conventions
             │
             ▼
   [2. Merchant Cleaning & Extraction]
      - Strips POS prefix noise (SQ *, TST*, POS DEBIT)
      - Strips processor codes (AMZN MKTP US, PAYPAL *)
      - Strips phone numbers, store numbers, cities, states
             │
             ▼
   [3. Transfer & Non-Spending Netting]
      - Excludes credit card payments (autopay, check payments)
      - Excludes bank transfers (internal savings/checking)
      - Excludes owner draws & capital contributions
      - Flags refunds/reimbursements (nets against expenses, not income)
             │
             ▼
   [4. User-Defined Rule Matcher] (Highest Precedence)
      - Evaluates user-confirmed overrides (EXACT, PREFIX, REGEX)
      - Enables deterministic memory of user preferences
             │
             ▼
   [5. Curated Schedule C Merchant Dictionary]
      - ~300 curated SaaS, travel, meal, office, and hardware merchants
      - Exact normalized dictionary lookup (O(1))
      - Assigns IRS Schedule C line, deductibility percentage, and confidence
             │
             ▼
   [6. RapidFuzz Heuristic Matcher] (Conservative)
      - Token-set ratio comparison against curated dictionary
      - Strict threshold ≥ 85% required for "suggested" status
             │
             ▼
   [7. Disambiguation & "Needs Review" Safe Fallback]
      - Ambiguous vendors (e.g. Amazon general, Target, Walmart)
      - Ambiguous transactions with score < 85%
      - Routed to `needs_review` with human-readable rationale
```

---

## 3. IRS Schedule C Mapping & Tax Compliance Rules

TaxSort deterministically maps spending to the exact lines on IRS Form 1040 Schedule C:

| Category Key | Schedule C Line | Deductible % | Tax Rule / Legal Basis |
| :--- | :--- | :---: | :--- |
| `advertising` | **Line 8** (Advertising) | 100% | Google Ads, Meta Ads, LinkedIn Ads, promotional costs |
| `vehicle` | **Line 9** (Car and Truck) | 100% | Parking, tolls, rideshare for business travel |
| `contract_labor` | **Line 11** (Contract Labor) | 100% | Freelance subcontractors (Upwork, Fiverr, 1099 contractors) |
| `insurance` | **Line 15** (Insurance) | 100% | Professional liability, E&O, commercial property |
| `professional_services` | **Line 17** (Legal & Professional) | 100% | CPA, bookkeeper, legal counsel, tax prep fees |
| `office_supplies` | **Line 18** (Office Expense) | 100% | Stationary, shipping (USPS, FedEx, UPS), consumables |
| `software_subscriptions` | **Line 18** (Other Expenses) | 100% | Cloud infrastructure, SaaS tools (Figma, GitHub, AWS, Adobe) |
| `bank_processing_fees` | **Line 18** (Other Expenses) | 100% | Stripe fees, wire fees, bank service charges |
| `education` | **Line 18** (Other Expenses) | 100% | Professional books, courses, industry conferences |
| `rent_utilities` | **Lines 20b & 25** | 100% | Coworking spaces (WeWork), internet service providers |
| `travel` | **Line 24a** (Travel) | 100% | Airfare, hotels, long-distance transit away from tax home |
| `meals` | **Line 24b** (Deductible Meals) | **50%** | **IRC § 274(n) 50% statutory limitation automatically applied** |
| `business_income` | **Line 1** (Gross Receipts) | N/A | Client invoices, Stripe payouts, direct deposit revenue |
| `refund_reimbursement` | N/A | 0% | Nets against deductible spending; excluded from gross income |
| `transfer` / `personal` | N/A (Excluded) | 0% | Non-deductible personal spending, balance transfers |
| `needs_review` | Review Queue | 0% | Uncategorized items requiring explicit filer confirmation |

---

## 4. Handling Real-World Bank Statement "Messiness"

Real statements are notoriously inconsistent. TaxSort includes deterministic safeguards for edge cases:

### A. Word Boundary Isolation in Column Matching
Many banks label columns `Description`, `Debit`, `Credit`. Naive regex checks like `r"dr"` match inside `description`, causing bank transaction texts to be misread as debit amounts. TaxSort uses word boundary checks `\b(?:dr|debit)\b` and excludes previously assigned columns.

### B. Refunds vs. Income Disambiguation
When a freelancer receives a $45.00 refund from Delta Air Lines or Uber, naive systems flag positive amounts as `Business Income`. TaxSort inspects the description for refund tokens (`refund`, `reversal`, `credit adjustment`, `reimbursement`) and categorizes the line as a negative offset to the original expense category, preventing false taxable income inflation.

### C. Multi-Account Semantics (Checking vs. Credit Card)
- **Checking accounts:** Credits are deposits/income; debits are expenses/outflows.
- **Credit cards:** Debits/charges increase the balance (expenses); credits reduce the balance (payments or refunds).
TaxSort normalizes amounts to integer cents internally (`amount_cents`) with consistent sign semantics across both account types.

### D. The Amazon / Big-Box Store Ambiguity Dilemma
Vendors like `Amazon`, `Target`, and `Walmart` sell both business monitors and personal groceries. The brain identifies `AMZN` / `AMAZON.COM` and marks them as `needs_review` unless the user creates an explicit rule or the description specifies digital software/AWS services.

---

## 5. Persistence, State, and Audit Trails

- **Database:** SQLite with SQLModel (SQLAlchemy 2.0 core).
- **Audit Fields:** Every transaction record maintains:
  - `status`: `auto`, `suggested`, `needs_review`, or `user_confirmed`.
  - `confidence`: `1.0` (exact dictionary/rule match), `0.85-0.95` (fuzzy heuristic), or `0.0` (unassigned).
  - `reason`: Complete textual explanation (e.g. `Exact merchant dictionary match: adobe`, `Regex exclusion rule: credit_card_payment`).
  - `flags`: `["refund"]`, `["transfer"]`, `["50pct_limit"]`, `["fuzzy_match"]`.
  - `deductible_pct`: Integer percentage (100, 50, or 0) for instant tax reporting.
- **User Rules Engine:** When a user reviews and assigns a category with "Always categorize this way" checked, a persistent `UserRule` record is created. Subsequent uploads matching that merchant are categorized automatically with 100% confidence.

---

## 6. Frontend Design Philosophy

- **Mercury / Stripe Aesthetic:** Clean slate/charcoal palette (`#0f172a`, `#2563eb`, `#16a34a`, `#f59e0b`), Inter font typography, subtle borders (`#e2e8f0`), and solid card structures.
- **Zero AI Gimmicks:** No gradient text, purple sparkles, neon glassmorphism, or non-functional animations.
- **Vector SVGs Exclusively:** All indicators, trend markers, and status icons are rendered via lightweight, accessible SVG vectors.
- **Instant Auditability:** Freelancers can click "Review Now" or "Resolve", inspect filtered unconfirmed records, assign Schedule C lines via an accessible modal, and export IRS audit-ready CSV and Excel worksheets.
