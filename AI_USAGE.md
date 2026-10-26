# AI Usage & Collaboration Log

This document provides transparent reporting on the AI tools, models, prompts, tasks, and manual verifications conducted during the development and iterative refinement of the **Statement Categorizer**.

---

## 1. Tools & Models Used

- **Antigravity (for coding):** Used for scaffolding, backend and frontend implementation, Pydantic modeling, FastAPI endpoints, Next.js dashboard, and refactoring.
- **Claude (for testing):** Used for test suite generation, adversarial edge-case analysis, financial calculation verification, and code auditing.
- **Operating Environment:** Windows PowerShell, Local Python 3.11 virtual environment, Node.js v20+

---

## 2. Tasks Assisted by AI & Iterative Refinements

| Phase | Task Description | AI Contribution | Developer Verification & Critical Fixes |
| :--- | :--- | :--- | :--- |
| **Phase 1: Architecture** | Defining models and rule hierarchy | Proposed two-axis Pydantic models (`transaction_type` and `business_category`). | Added `Decimal.is_finite()` validation to reject `NaN` and `Infinity`. |
| **Phase 2: Rules Engine** | Scaffolding rule definitions | Generated initial vendor regex patterns. | **Critical Fix 1:** Removed broad `"invoice"` from income rule `R030`; added directional check so vendor invoices (`-$50.00`) are not classified as income.<br>**Critical Fix 2:** Resolved priority conflict between Payment Processing (moved to Priority 28) and Bank Fees (Priority 32), ensuring `STRIPE PROCESSING FEE` maps to `Payment Processing`.<br>**Critical Fix 3:** Added word boundaries (`\baws\b`) to prevent false positives with `lawson` or `flaws`. |
| **Phase 3: Transfers & P2P** | Internal transfer classifications | Initially classified all P2P payments as internal transfers. | **Critical Fix 4:** Differentiated verified own-account transfers from P2P payments (`Venmo payment to contractor` $\to$ `CONTRACTOR_EXPENSE`; generic Venmo payments $\to$ `Needs Review`). |
| **Phase 4: Refund Safety** | Refund validation & deduction | Initially subtracted all refund keywords from expenses. | **Critical Fix 5:** Implemented safe refund validation: only matched refunds reduce expenses; unmatched refunds and negative refunds are held in `Needs Review` and do not reduce expenses until confirmed. |
| **Phase 5: Parser & Encoding** | CSV parser robustness | Standard DictReader implementation. | Added ambiguous date detection (`MM/DD` vs `DD/MM`), Latin-1 fallback for non-UTF-8 bytes, and malformed row recovery. |
| **Phase 6: Summary & Impact** | Financial calculations & provisional results | Initially treated unclassified rows as having zero financial impact. | **Critical Fix 6:** Added unclassified dollar tracking (`unclassified_amount`) and explicitly labeled operating results as **Provisional** whenever unresolved items remain. |
| **Phase 7: Frontend UI** | Next.js 16 dashboard | Scaffolded React 19 / Tailwind components. | Enhanced Refund card with matched vs. unmatched breakdown; added provisional status alerts and linked purchase badges. |

---

## 3. Where Things Got Worse: Critical Issues Identified & How They Were Fixed

During adversarial testing and manual review, several severe logic errors emerged from early AI-generated code. Below is a detailed breakdown of each issue and how it was resolved:

### 1. Vendor Invoices Incorrectly Classified as Income
- **Where things went wrong:** Early AI rule generation created rule `R030` with the keyword `"invoice"` for Client Income. When a transaction like `"Invoice from Vendor"` with amount `-$50.00` was tested, the model categorized it as `Client Income` and added `-$50.00` to total income.
- **How it was fixed:** Enforced strict direction validation (`expected_sign = "positive"` for income rules). Removed the generic `"invoice"` pattern from income rules and created rule `R028` for outgoing vendor invoices (`expected_sign = "negative"` $\to$ `General Expense`). Any transaction with contradictory sign and keywords (e.g. negative amount with "client payment") routes directly to `Needs Review`.

### 2. Refunds Reducing Expenses Without Safe Validation
- **Where things went wrong:** Early code treated any description containing `"refund"`, `"reversal"`, or `"chargeback won"` as an expense deduction, blindly subtracting `abs(amount)` from total expenses. This caused unmatched refunds from unknown vendors to reduce legitimate operating costs, and treated negative customer refund payouts as expense reductions.
- **How it was fixed:**
  1. If a refund has `amount <= 0`, it represents an outflow (payout to a client) and routes to `Needs Review`.
  2. If a refund is positive, the engine attempts to link it to an original purchase and category.
  3. If a refund cannot be matched (`BusinessCategory.UNKNOWN`), it is held in `Needs Review` and **excluded** from expense deductions (`unmatched_refunds`) until confirmed by the user.

### 3. Internal Transfers Concealing Legitimate Contractor Expenses
- **Where things went wrong:** Early code classified all descriptions containing `"venmo payment"` or `"zelle"` under rule `R002` as `INTERNAL_TRANSFER`. When testing `"Venmo payment to contractor"`, the expense was categorized as an internal transfer and completely excluded from operating expenses.
- **How it was fixed:** Differentiated transfers between verified accounts owned by the business (`transfer to savings`, `checking`, etc.) from third-party P2P payments. Created rule `R005` to capture contractor keywords (`contractor`, `freelancer`, `supplier`) as `Contractor Expense`. Generic P2P payments without clear context route to `Needs Review` instead of being silently excluded from P&L.

### 4. Fee Rules Priority Conflict
- **Where things went wrong:** General bank fee rule `R020` was assigned Priority 30 with pattern `"processing fee"`, while payment processing rule `R046` was assigned Priority 64 with `"stripe fee"`. Since the first rule wins, `"STRIPE PROCESSING FEE"` was intercepted by `R020` and categorized as `Bank Fees` instead of `Payment Processing`.
- **How it was fixed:** Reordered the priority hierarchy so specific Payment Processing fees (`R025`) execute at Priority 28, before General Bank Fees (`R020`) at Priority 32.

### 5. Short Substring Collisions (`aws`)
- **Where things went wrong:** Rule `R041` checked substring `"aws"` for cloud hosting. This resulted in false positives: `"LAWSON STATIONERY"` and `"NO FLAWS DRY CLEANERS"` matched `"aws"` and were classified as Software/Cloud hosting.
- **How it was fixed:** Replaced naive substring matching with pre-compiled regular expressions using strict word boundaries `\baws\b`.

### 6. Parser Accepting Non-Finite Decimals & Silent Ambiguities
- **Where things went wrong:** The CSV parser accepted special Decimal values like `NaN`, `Infinity`, and `-Infinity`, causing downstream arithmetic failures. Additionally, ambiguous dates like `03/04/2026` were silently parsed without user notice.
- **How it was fixed:** Added explicit `val.is_finite() and not val.is_nan()` checks in both the parser and Pydantic field validators. Added date ambiguity detection that warns when both day and month are $\le 12$. Added Latin-1 decoding fallback for non-UTF-8 statements.

### 7. Summaries Treating Unclassified Transactions as Final Zero-Impact Results
- **Where things went wrong:** Transactions in `Needs Review` were excluded from income and expenses, but the summary presented the resulting net figure as final. A user could be misled into thinking their tax liability was settled while thousands of dollars sat unclassified.
- **How it was fixed:** Added `unclassified_amount`, `unclassified_count`, and `is_provisional` to `FinancialSummary`. The dashboard explicitly labels the operating result as **"Provisional Operating Result"** whenever unresolved transactions exist, displaying a clear notice that unresolved items may alter the final result.

---

## 4. Release Gate: 9-Point Financial Correctness Checklist

All nine criteria required by the assessment were written into a dedicated automated test suite (`tests/test_checklist.py`) and verified:

| Checklist Item | Test Name | Status |
| :--- | :--- | :--- |
| 1. Vendor invoice with a negative amount | `test_item_1_vendor_invoice_with_negative_amount_not_income` | **PASSED** |
| 2. Refund with no matching purchase | `test_item_2_refund_with_no_matching_purchase` | **PASSED** |
| 3. Payment to a contractor through Venmo | `test_item_3_payment_to_contractor_through_venmo` | **PASSED** |
| 4. Stripe processing fee | `test_item_4_stripe_processing_fee_matches_payment_processing` | **PASSED** |
| 5. Unrelated merchant containing "aws" | `test_item_5_unrelated_merchant_containing_aws` | **PASSED** |
| 6. NaN, infinity, malformed rows, and invalid UTF-8 | `test_item_6_nan_infinity_malformed_and_invalid_utf8` | **PASSED** |
| 7. Duplicate transaction | `test_item_7_duplicate_transaction_flagged_without_deleting` | **PASSED** |
| 8. User changes a transaction category | `test_item_8_user_changes_transaction_category` | **PASSED** |
| 9. Transfers between verified own accounts | `test_item_9_transfers_between_verified_own_accounts` | **PASSED** |

---

## 5. Token & Session Estimates

- **Total Interaction Steps:** ~25 interactive development, testing, and refinement turns
- **Estimated Input Tokens:** ~195,000 tokens (including repository context, task specifications, and file revisions)
- **Estimated Output Tokens:** ~29,500 tokens (code generation, test fixtures, and comprehensive documentation)
- **Runtime Inference:** Zero (0) AI tokens used at application runtime. The categorizer operates entirely via the deterministic Python rules engine.

---

## 6. Developer Attestation

I attest that all business logic, financial formulas, rule hierarchies, edge-case fixes, and test assertions were independently reviewed and verified against the assessment guidelines. No black-box LLM calls exist in the runtime categorization engine.
