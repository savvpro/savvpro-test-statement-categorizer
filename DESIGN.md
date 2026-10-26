# System Design: Deterministic Statement Categorizer

## 1. Use Case & Domain Context

### Target Persona
**Alex**, an independent freelance software engineer and boutique consultancy owner operating as a single-member LLC / sole proprietor.

### The Problem
At tax time (Schedule C / Form 1120-S preparation), Alex downloads messy PDF/CSV statements from business checking accounts and business credit cards. Key challenges:
1. Bank descriptions are filled with cryptic noise: POS prefixes (`CHECKCARD 0303`), payment aggregators (`PAYPAL *`, `SQ *`, `TST*`), store numbers (`#104`), terminal codes, transaction IDs, and trailing city/state codes.
2. Expense deductions must strictly map to IRS-aligned tax buckets:
   - Developer tooling and subscriptions (`Software & Subscriptions`)
   - Cloud servers and hosting (`Cloud & Infrastructure`)
   - Laptops, monitors, and adapters (`Hardware & Office Equipment`)
   - Home-office ISP and mobile tethering (`Internet & Utilities`)
   - Invoicing, tax prep, and subcontractor payroll (`Professional & Legal Services`)
   - Banking wire fees, foreign transaction fees (`Bank & Merchant Fees`)
   - Client on-site travel and rideshare (`Travel & Transportation`)
   - Client meals (`Meals & Client Entertainment`)
   - Customer acquisition ads (`Advertising & Marketing`)
   - Client invoice payments & payouts (`Client Income & Revenue`)
   - Internal transfers & credit card autopay (`Transfers & Card Payments` — non-spending / non-taxable)
   - Unverified items (`Needs Review`)
3. **Critical Rule:** If the system is not certain, it must flag the transaction for review. A wrong guess is significantly worse than asking the user.

---

## 2. End-to-End Processing Pipeline

```
[ Upload Statement CSV ]
           │
           ▼
[ Robust Statement Parser ]
  ├── Auto-detects encoding (UTF-8, Latin-1, CP1252)
  ├── Auto-detects delimiter (comma, semicolon, tab)
  ├── Skips preamble metadata headers & account summary footers
  └── Normalizes dates & parses single or split debit/credit columns
           │
           ▼
[ Preprocessing & Normalization Engine ]
  ├── Converts to uppercase
  ├── Strips POS prefixes (CHECKCARD, POS PURCHASE, DEBIT CARD)
  ├── Strips payment aggregator wrappers (SQ *, TST*, PAYPAL *, STRIPE *)
  ├── Strips phone numbers, URLs, store IDs (#104), and auth/ref codes
  └── Strips embedded dates and trailing city/state tokens
           │
           ▼
[ "The Brain" Deterministic Rule Hierarchy ]
  ├── Layer 1: User-Learned Custom Rules (Precedence: 1.0 confidence)
  ├── Layer 2: Transfers & Credit Card Autopay Gate
  ├── Layer 3: Refunds & Reversals Gate (Linked to expense debits)
  ├── Layer 4: Personal vs. Business Ambiguity Gate (Target, Amazon, Cafe)
  ├── Layer 5: Exact Merchant Dictionary Lookup ($O(1)$)
  ├── Layer 6: Regex & Domain Pattern Matchers
  ├── Layer 7: Fuzzy Matching (rapidfuzz WRatio / token_set_ratio)
  └── Layer 8: Confidence Threshold Gate (< 0.75 -> Needs Review)
           │
           ▼
[ User Review & Correction Dashboard ]
  ├── Instant inline category overrides
  ├── Optional "Save as persistent rule" for future statements
  ├── Real-time financial metrics & category tax totals
  └── One-click export to accountant-ready CSV
```

---

## 3. "The Brain" Decision Engine

The categorization engine is **100% deterministic Python code** with **zero AI/LLM API calls**. Decisions are transparent, explainable, and reproducible.

### Rule Hierarchy & Precedence

| Priority | Layer | Technique | Confidence | Reason Example |
| :--- | :--- | :--- | :--- | :--- |
| **1** | **User Custom Rules** | Exact pattern match from persistent store | `1.00` | `"User custom rule matched: 'BOB'S WORKSHOP'"` |
| **2** | **Transfers & Card Payments** | Regex pattern for non-spending transactions | `0.98` | `"Internal transfer or card payment (non-spending)"` |
| **3** | **Refunds & Reversals** | Credit transaction linked to expense merchant | `0.96` | `"Merchant refund/reversal offset (linked to charge #tx_1)"` |
| **4** | **Personal Ambiguity Gate** | Mixed-use retail patterns (Target, Amazon, Cafe) | `0.50` | `"Personal vs Business Ambiguity: Mixed-use retailer"` |
| **5** | **Exact Merchant Lookup** | Hash map dictionary lookup | `0.95 - 0.98` | `"Exact merchant rule: 'GITHUB'"` |
| **6** | **Regex & Pattern Rules** | Domain-specific compiled regular expressions | `0.90 - 0.95` | `"Pattern match: Developer tools and SaaS"` |
| **7** | **Fuzzy Matching** | Rapidfuzz `WRatio` against canonical merchants | `0.76 - 0.88` | `"Fuzzy match with 'JETBRAINS' (90% similarity)"` |
| **8** | **Needs Review Fallback** | Unmatched merchants or confidence $< 0.75$ | `0.30` | `"Unknown merchant. Requires manual tax classification"` |

### Confidence Scoring & Gating Logic
- **High Confidence ($\ge 0.90$):** User rules, exact dictionary hits, and strong domain regex matches.
- **Medium Confidence ($0.75 - 0.89$):** Rapidfuzz fuzzy matches with score $\ge 82\%$.
- **Low Confidence ($< 0.75$):** Automatically routed to `"Needs Review"` (`needs_review = True`).
- **Threshold Gate:** If any rule fires with confidence lower than `settings.confidence_threshold` (default `0.75`), the transaction is placed into `"Needs Review"`.

---

## 4. Edge Cases Explicitly Handled

### 1. Refunds & Expense Reversals (Money Back is NOT Income)
- **The Pitfall:** In typical bookkeeping, incoming credits are mistakenly tallied as gross business revenue, artificially inflating taxable income.
- **The Solution:** Credits from known expense merchants (e.g. AWS, JetBrains, Apple) or entries containing `REFUND` / `REVERSAL` / `RETURN` are tagged as `is_refund = True`, categorized into `Refunds & Reversals`, and offset against business expenses. The engine scans prior debit transactions to locate matching amounts and merchants, linking the refund to its parent transaction ID.

### 2. Internal Transfers & Credit Card Payments
- **The Pitfall:** Moving \$2,000 from checking to savings or paying off a credit card balance looks like a \$2,000 expense, doubling deduction claims.
- **The Solution:** Regex patterns identify `TRANSFER TO SAVINGS`, `AUTOPAY`, `PAYMENT THANK YOU`, and `ONLINE BANKING TRANSFER`. These are flagged as `is_transfer = True` under `Transfers & Card Payments`, isolated from deductible spending totals and income.

### 3. Duplicate Transaction Detection
- **The Pitfall:** Accidental double-swipes or software subscription billing glitches.
- **The Solution:** The engine analyzes the entire statement batch. Rows sharing identical `(date, abs(amount), transaction_type, normalized_description)` are flagged with `is_duplicate = True`, highlighting the row with a red badge and duplicate warning.

### 4. Personal vs. Business Ambiguity
- **The Pitfall:** Tech freelancers frequently make personal purchases at Target, Costco, Walmart, Starbucks, or Amazon on their business cards.
- **The Solution:** A dedicated ambiguity filter traps mixed-use retailers, forcing them into `"Needs Review"` with a confidence of `0.50` and an explicit note: *"Personal vs Business Ambiguity: Mixed-use retailer. Verify business deductibility."*

### 5. Foreign Currency & Merchant Fees
- **The Pitfall:** International server hosting or contractor payments generate cross-border fees (e.g. `FOREIGN TRANSACTION FEE - EUR CONVERSION`).
- **The Solution:** Pattern rules recognize FX fees, wire transfer charges, and monthly maintenance costs, automatically filing them under `Bank & Merchant Fees`.

### 6. Messy File Formats & Encoding Variations
- **Encodings:** Seamlessly handles UTF-8, UTF-8-BOM (`utf-8-sig`), Windows-1252 (`cp1252`), and Latin-1.
- **Delimiters:** Auto-detects comma (`,`), semicolon (`;`), tab (`\t`), or pipe (`|`).
- **Headers & Preamble:** Skips bank metadata (account numbers, statement periods, empty lines) and summary footers (`Ending Balance`, `Total Debits`).
- **Amount Conventions:** Handles signed single amount columns (`-19.00`, `($45.00)`, `19.00 DR`), separate `Debit` / `Credit` columns, thousand separators (`$1,299.00`), and European decimal formats.

### 7. Active Learning / Persistent Corrections
- When the user modifies a category in the frontend dropdown, they can check **"Save as persistent rule"**. The pattern is stored in `backend/data/user_rules.json`. On subsequent statement uploads, Layer 1 immediately fires with `confidence = 1.00`.

---

## 5. Known Limitations & Future Enhancements

1. **Multi-Item Receipts:** Transactions at retailers like Amazon or Apple may include both business hardware and personal supplies on a single line item. Full receipt-level itemization would require integration with purchase order APIs or OCR receipt attachments.
2. **PDF Parsing:** While the parser excels on structured CSV/TXT files, complex multi-column bank PDFs often require specialized table layout models (e.g. `pdfplumber` or `camelot`) tailored per bank format.
3. **Multi-Currency Reconciliation:** While foreign transaction fees are extracted, multi-currency statements with live exchange rate gains/losses are outside the current scope.
