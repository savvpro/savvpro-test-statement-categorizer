# System Design & Architecture Document: TaxSort

## 1. Selected Use Case & Target Persona

### Persona: Freelance Creative Designer & Digital Consultant
- **Entity Type:** Sole Proprietor / Single-Member LLC filing US IRS Schedule C (Profit or Loss from Business) or local tax equivalents.
- **Financial Profile:**
  - High volume of recurring digital software subscriptions (Adobe Creative Cloud, Figma, GitHub, Notion, Vercel, OpenAI, AWS).
  - Business travel & client meetings (Delta Air Lines, Uber, Lyft, client dinners).
  - Multi-channel revenue streams (Client wire invoices, Stripe payouts, Upwork withdrawals).
  - Mixed bank activity: Personal card payoffs, savings transfers, hardware purchases (Apple Store, Best Buy), and refunds for cancelled services.

### The Problem
Real bank and credit card statements are notoriously messy:
- Transaction strings are cluttered with POS prefixes (`SQ *`, `TST*`, `AMZN Mktp US*`), phone numbers (`800-833-6687`), and location/store numbers (`#9921`, `STORE 1403`).
- Many transactions represent internal money transfers (`TRANSFER TO SAVINGS`), which are not deductible business expenses.
- Refunds (`REFUND: APPLE STORE RETURN`) are often misclassified by naive tools as taxable income instead of expense offsets.
- Ambiguous or unrecognized local merchants (`JOES CAFE 9921`) require manual confirmation for tax deductibility.

---

## 2. "The Brain" Architecture (Rule & Heuristic Engine)

> **Core Constraint:** In accordance with assessment instructions, **no external large language models (LLMs like GPT, Claude, or Gemini) are used for categorization decisions.** The engine is 100% deterministic, written in pure Python, highly auditable, and executes in sub-millisecond speeds.

```
┌─────────────────────────────────────────────────────────────┐
│                   Uploaded Raw Statement                    │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│           Stage 1: Merchant Normalization Pipeline          │
│   • Strip payment processor junk (SQ *, TST*, PAYPAL *)     │
│   • Strip phone numbers, store #s, zipcodes, URLs           │
│   • Extract clean canonical merchant display & lookup key   │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│          Stage 2: User Override Memory (Feedback Loop)      │
│   • Check if user previously assigned category to merchant  │
│   • If match: Assign with 1.0 confidence (User Verified)    │
└──────────────────────────────┬──────────────────────────────┘
                               │ (Not in memory)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│         Stage 3: Internal Transfer & Owner Draw Check       │
│   • Detect 'TRANSFER TO SAVINGS', 'AUTOPAY', 'PAYMENT-TY'   │
│   • If match: Category = INTERNAL_TRANSFER (Excluded)       │
└──────────────────────────────┬──────────────────────────────┘
                               │ (Not a transfer)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│         Stage 4: Refund Disambiguation vs Gross Income      │
│   • Refund detected (negative amount on expense merchant):   │
│     ➔ Category = REFUND_CREDIT (Expense Offset, NOT Income)  │
│   • Payout/Invoice detected:                                │
│     ➔ Category = GROSS_INCOME (Taxable Revenue)             │
└──────────────────────────────┬──────────────────────────────┘
                               │ (Standard Outflow)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│           Stage 5: Exact Verified Merchant Lookup           │
│   • Exact match in Schedule C Taxonomy (Adobe, Figma, Uber) │
│   • If match: Assign category with 0.99 Confidence          │
└──────────────────────────────┬──────────────────────────────┘
                               │ (Not in verified list)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│       Stage 6: Keyword Scoring & Ambiguity Detection        │
│   • Score regex token patterns across all categories        │
│   • If conflicting categories tie ➔ Flag NEEDS_REVIEW       │
│   • If Score >= 0.80 ➔ Assign Category                      │
└──────────────────────────────┬──────────────────────────────┘
                               │ (Score < 0.80)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│        Stage 7: Fuzzy Similarity Matching (Levenshtein)     │
│   • SequenceMatcher ratio >= 0.85 against canonical names   │
└──────────────────────────────┬──────────────────────────────┘
                               │ (No match)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│      Stage 8: Fallback Escalation ➔ "Needs Review"          │
│   • Confidence = 0.10, needs_review = True                  │
│   • "A wrong guess is worse than asking"                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Real-World Messiness & Edge Cases Handled

| Real-World Problem | Example Bank String | How The Brain Handles It | Tax Impact |
|---|---|---|---|
| **POS Merchant Clutter** | `SQ *JOES CAFE 9921 SAN FRANCISCO CA` | Strips `SQ *`, `9921`, and state code to extract clean merchant `Joes Cafe`. | Clean presentation & accurate matching. |
| **Payment Gateway Prefix** | `PAYPAL *GITHUB INC 402-935-7733 CA` | Strips `PAYPAL *` and phone number to yield `GitHub`. | Categorized as **Software & Subscriptions**. |
| **Non-Spending Transfers** | `TRANSFER TO SAVINGS ACC #4821` | Recognized by regex pattern `transfer to savings`. | Categorized as **Internal Transfer / Owner Draw**; excluded from expense total. |
| **Refunds vs Income** | `REFUND: APPLE STORE RETURN #9812` | Detected via `REFUND` keyword and credit sign on known merchant. | Categorized as **Refund / Expense Offset**; reduces deductible expenses, **NOT** counted as taxable income. |
| **Unrecognized Dining** | `JOES CAFE 9921` | Recognized as unknown dining venue without verified business context. | Flagged as **Needs Review** (Confidence: 10%); asks user to confirm business purpose. |
| **Meals Deduction Rule** | `STARBUCKS STORE #19821` | Categorized as **Meals & Entertainment**. | Net deductible expense calculation applies the **50% IRS deduction limit**. |
| **Category Ambiguity** | Generic stores or multi-purpose vendors | When two categories produce overlapping keyword scores. | Flagged as **Needs Review** with reason: *"Ambiguous category match"*. |
| **User Feedback Loop** | User re-assigns `Joes Cafe` to `Meals` | Brain records override in `UserRuleMemory` store. | Future and matching rows auto-update with 1.0 confidence. |

---

## 4. Confidence Scoring Formula

The Brain computes confidence between `0.0` and `1.0`:
- **1.0 (100%):** User verified override, explicit internal transfer pattern, or verified credit card autopay.
- **0.99 (99%):** Exact match against canonical merchant registry (e.g., `Adobe Creative Cloud`, `Figma`, `Uber`).
- **0.95 - 0.98:** Refund credit adjustment or platform revenue payout (`Stripe Payout`, `Upwork Withdrawal`).
- **0.85 - 0.94:** Distinct category keyword match without conflicts (e.g., airline tickets, web hosting).
- **0.70 - 0.84:** Fuzzy similarity match against known merchant names.
- **< 0.80:** Escalated to **Needs Review** with human-readable rationale.

---

## 5. Technical Stack

- **Backend:** Python 3.12, FastAPI, Pydantic v2, Pytest, Uvicorn.
- **Frontend:** React 19, Vite, Modern CSS Design System, Responsive Data Table.
- **Data Formats:** Universal Bank Statement CSV Parser (supports Chase, Bank of America, Amex, Stripe, and generic CSV layouts).
