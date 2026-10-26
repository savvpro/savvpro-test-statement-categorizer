# System Design & Brain Architecture: LedgerLens

## 1. Selected Customer Use Case: The Freelance Creative & Digital Consultant

### Context & Persona
**Target Customer:** Independent Freelancers, UI/UX Designers, Software Developers, and Digital Consultants preparing their annual business tax filings (e.g., US IRS Form 1040 Schedule C / Profit or Loss From Business, or UK Self-Assessment).

### The Tax Time Challenge
Freelancers often run their client engagements and business operations on dedicated credit cards and checking accounts. However, real-world statements are noisy:
- **Software Subscriptions** renew automatically (Adobe Creative Cloud, Figma, GitHub, AWS, Vercel).
- **Travel & Rideshare** occur for client meetings (Uber, Lyft, airlines, trains).
- **Client Meals & Entertainment** are subject to special tax treatment (50% deductible under IRS rules).
- **Internal Transfers** (e.g., moving money to a savings reserve, paying credit card balances) appear in statements but represent asset transfers—not deductible business expenses.
- **Refunds & Charge reversals** appear as positive amounts, which naive systems erroneously classify as taxable client income.
- **Ambiguous Vendors** (e.g., local cafes like `JOES CAFE 9921`, random card processors like `SQ *MARK`) cannot be assumed to be 100% deductible business expenses without human verification.

### Core Philosophy: "A wrong guess is worse than asking"
Filing improper deductions on a tax return triggers audit penalties. Therefore, the brain is designed with a strict **conservative threshold**: it only assigns high-confidence tax categories when deterministic criteria are verified. Any ambiguous vendor, conflicting rule, or unverified deposit is routed directly to **Needs Review** with an actionable human-readable explanation.

---

## 2. The Decision Engine ("The Brain")

In strict adherence to the assessment rule, **the decision engine contains no large language models (no GPT, Claude, or Gemini)**. It is an entirely deterministic, multi-stage heuristic pipeline engineered in Python.

### Architectural Decision Pipeline

```
[Raw Statement CSV Row]
           │
           ▼
[Stage 1: Sanitization & Parsing]
  • Accounting format parser: `(49.99)` → `-49.99`
  • Currency/comma normalization: `$1,250.00 USD` → `1250.00`
  • Text cleanup: Uppercase, strip punctuation noise (`*`, `#`, `-`)
           │
           ▼
[Stage 2: Transfer & Debt Movement Engine]
  • Keywords: `TRANSFER TO SAVINGS`, `CREDIT CARD PAYMENT`, `AUTOPAY`
  • Result: Category = `Transfer`, Deductible = `False`, Confidence = `High`
           │ (If not transfer)
           ▼
[Stage 3: Refund & Reversal Engine]
  • Detect tokens: `REFUND`, `REVERSAL`, `RETURN`, `CREDIT ADJ`
  • Match parent expense rules (e.g., `REFUND ADOBE` → `Software & Subscriptions`)
  • Result: Offsets gross expenses; never categorized as taxable income
           │ (If not refund)
           ▼
[Stage 4: Positive Amount / Revenue Engine]
  • If amount > 0:
      - Known payout keywords (`CLIENT PAYMENT`, `STRIPE PAYOUT`, `INVOICE`, `UPWORK`):
        Category = `Client Revenue`, Type = `Income`, Confidence = `High`
      - Unknown deposit:
        Category = `Needs Review`, Type = `Deposit`, Confidence = `Low`
           │ (If expense / amount <= 0)
           ▼
[Stage 5: Tax Category Heuristic Rule Engine]
  • Word-boundary regex matching across Schedule C domain lexicons:
      - Software & Subscriptions
      - Travel & Transit
      - Meals (50% Deductible)
      - Office Supplies & Equipment
      - Advertising & Marketing
      - Utilities & Internet
      - Banking & Processing Fees
      - Contract Labor & Professional Services
           │
           ▼
[Stage 6: Confidence Resolution & Ambiguity Handling]
  • Exact 1 match: Assign category, Confidence = `High`
  • > 1 matches: Assign `Needs Review`, Reason = "Ambiguous multi-category match"
  • 0 matches: Assign `Needs Review`, Reason = "Unrecognized merchant rule"
```

---

## 3. Real-World Statement Edge Cases Handled

| Edge Case | Problem in Naive Parsers | LedgerLens Solution |
| :--- | :--- | :--- |
| **Vendor Refund** (e.g., `REFUND ADOBE CREATIVE CLOUD +$29.99`) | Categorized as taxable client income because the amount is positive. | Identified as a refund via indicator tokens, matched to `Software & Subscriptions`, and credited against gross expenses. |
| **Credit Card Repayment** (e.g., `AUTOPAY PAYMENT - THANK YOU -$300`) | Categorized as a deductible business expense. | Identified as a balance payoff/transfer. Excluded from tax write-offs (`include_in_expenses: False`). |
| **Accounting Parentheses** (e.g., `(45.00)`) | String conversion fails or parses as positive `45.00`. | Custom Decimal parser detects `(...)` wrapper and produces signed `Decimal("-45.00")`. |
| **Split Bank Columns** (`Debit` / `Credit` vs single `Amount`) | CSV fails if strict single column is expected. | Flexible header resolver automatically handles separate `Debit` and `Credit` columns (e.g., Chase, BofA formats). |
| **Ambiguous Local Dining** (e.g., `JOES CAFE 9921`) | Mistakenly tagged as a verified business expense. | Generic words like "cafe" or "bistro" are deliberately excluded from automatic high-confidence matching. Tagged as **Needs Review** so the freelancer can confirm whether it was a client meeting or personal lunch. |
| **Special Characters & Merchant IDs** (e.g., `UBER *TRIP #9921-X`) | Strict exact-string matching misses the merchant name. | Regex normalizer scrubs punctuation noise while preserving word boundaries (`UBER TRIP 9921 X`). |

---

## 4. Financial & Tax Accounting Metrics

The backend computes the following reconciled figures:
- **Gross Deductible Expenses:** Sum of verified business expense outflows.
- **Refunds & Reversals:** Sum of credits offsetting business expenses.
- **Net Tax Deductions:** `Gross Deductible Expenses - Refunds & Reversals`.
- **Client Revenue:** Sum of client invoices and merchant payouts.
- **Net Business Profit:** `Client Revenue - Net Tax Deductions`.
- **Category Breakdown:** Aggregated totals and item counts by tax line item.

When the user updates any row on the frontend, the API dynamically recalculates these metrics to guarantee mathematical integrity.
