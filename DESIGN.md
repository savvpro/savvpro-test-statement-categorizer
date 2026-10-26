# Design Document: Freelance Ledger — Statement Categorizer

## 1. Selected Use Case & Target User

### Target Customer
**Independent Freelance Designer / Creative Consultant** operating as a sole proprietor in the United States, organizing bank and business credit card statements for bookkeeping and **IRS Form 1040 Schedule C (Profit or Loss from Business)** tax preparation.

### Why This Use Case?
1. **Concrete, checkable tax structure:** Rather than arbitrary spending buckets, mapping directly to Schedule C line items gives transactions real-world tax significance (e.g. Software SaaS, Office Supplies, Travel, 50% deductible Meals).
2. **Messy, multi-channel transaction streams:** Freelance designers encounter diverse charges:
   - Recurring software subscriptions (Adobe Creative Cloud, Figma, GitHub, Canva, JetBrains)
   - Mangled payment processor descriptors (`SQ *ARTISAN BAKERY`, `ADBE*CREATIVECLOUD`, `TST* DOWNTOWN BISTRO`)
   - Rideshares and transit for client meetings (Uber, Lyft, Amtrak)
   - Business coffee and client meals (subject to strict IRS 50% business deduction limits)
   - Personal charges accidentally put on the business card (grocery stores, streaming services)
   - Client invoice payments and retainers
   - Returns, vendor credits, and chargebacks
   - Internal transfers between checking, savings, and credit card autopay settlements
   - Ambiguous vendor records (e.g. `JOES CAFE 9921` or `AMAZON.COM`)

---

## 2. Core Architecture & Data Pipeline

The application adheres strictly to the assessment's **big rule**:
> **The Brain must be your own deterministic code. No call to any large language model (GPT, Claude, Gemini, etc.) may decide a transaction category at runtime.**

```
┌─────────────────────────┐
│   Upload Statement CSV  │
└────────────┬────────────┘
             │
             ▼
┌────────────────────────────────────────────────────────┐
│  Normalization & Extraction (backend/app/parsing.py)   │
│  - Flexible header alias matching                      │
│  - Decimal financial parsing (DR/CR, parens, currency) │
│  - Multi-format date parsing (ISO YYYY-MM-DD)          │
│  - Row-level issue detection & duplicate charge audit  │
└────────────┬───────────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────────┐
│  The Categorization Brain (backend/app/categorizer.py) │
│  Deterministic Layered Rule Hierarchy                  │
│  Layer 1: Internal Transfers & Settlements             │
│  Layer 2: Returns & Refunds (never income)             │
│  Layer 3: Personal / Owner Draws                       │
│  Layer 4: Inbound Client Revenue Verification          │
│  Layer 5: Exact Merchant Lookups                       │
│  Layer 6: Mangled Processor Heuristics                 │
│  Layer 7: Domain Keyword Heuristics                    │
│  Layer 8: Conservative "Needs Review" Routing          │
└────────────┬───────────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────────┐
│  Financial Aggregator (backend/app/summaries.py)       │
│  - Strict Decimal arithmetic (no IEEE-754 drift)       │
│  - Deductible Operating Expenses vs. Gross Inflows     │
│  - Separate tracking for Transfers & Refunds           │
│  - Real-time recalculation upon user review/edit       │
└────────────┬───────────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────────┐
│  Interactive Review UI (React + Vite + TypeScript)     │
│  - Financial summary cards & category progress bars    │
│  - Search, category filter, and Needs Review toggle    │
│  - Inline category overrides & instant feedback        │
│  - Export reviewed statement to CSV                    │
└────────────────────────────────────────────────────────┘
```

---

## 3. The Categorization "Brain": Decision Hierarchy

Every row passes through an ordered decision sequence. The earliest confident rule match wins; any row with low confidence or ambiguity is routed to **Needs Review**.

### Decision Layers

| Layer | Type | Target Patterns | Assigned Category | Confidence | Rationale / Behavior |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Transfers** | Regex | `TRANSFER TO SAVINGS`, `AUTOPAY CREDIT CARD`, `ONLINE XFER` | `Transfer (not spending)` | 0.98 | Excluded from spending and revenue to prevent double-counting. |
| **2. Refunds** | Regex | `REFUND`, `RETURN`, `REVERSAL`, `CHARGEBACK`, `RETURN/REFUND` | `Refund` | 0.95 | Money returned; offsets expenses, **never** treated as taxable income. |
| **3. Personal** | Regex | `PERSONAL`, `OWNER DRAW`, `GROCERY OUTLET`, `NETFLIX` | `Personal / Owner Draw` | 0.92 | Personal charge that slipped onto business card; non-deductible. |
| **4. Ambiguous** | Regex | `JOES CAFE 9921`, `AMAZON.COM`, `SQUARE *PAYMENT 4012` | `Needs Review` | 0.35–0.45 | Ambiguous context or generic merchant descriptor; asking is safer than guessing. |
| **5. Inflow Revenue** | Regex + Sign | Positive amount + `CLIENT PAYMENT`, `INVOICE #`, `RETAINER` | `Income` | 0.96 | Confirmed business revenue from client invoices. |
| **6. Exact SaaS** | Dictionary | `ADOBE`, `FIGMA`, `GITHUB`, `JETBRAINS`, `CANVA`, `NOTION` | `Software` | 0.95–0.98 | Verified creative and software engineering tooling. |
| **7. Exact Transit** | Dictionary | `UBER`, `LYFT`, `CAREEM`, `AMTRAK`, `DELTA AIR`, `UNITED` | `Travel & Transport` | 0.95 | Commercial transit and ridesharing services. |
| **8. Exact Dining** | Dictionary | `BLUE BOTTLE`, `STARBUCKS`, `PEETS COFFEE`, `DUNKIN` | `Meals & Coffee` | 0.92 | Labeled as subject to IRS 50% business meal deduction. |
| **9. Hardware** | Dictionary | `OFFICE DEPOT`, `STAPLES`, `BEST BUY`, `MICRO CENTER` | `Office Supplies & Equipment` | 0.92–0.95 | Workstation monitors, cables, stationery. |
| **10. Telecom** | Dictionary | `COMCAST`, `VERIZON`, `AT&T`, `T-MOBILE`, `SPECTRUM` | `Internet & Utilities` | 0.95 | Studio broadband and mobile phone bills. |
| **11. Ads** | Dictionary | `GOOGLE ADS`, `META ADS`, `FACEBOOK ADS`, `LINKEDIN ADS` | `Advertising & Marketing` | 0.98 | Paid search and social client acquisition channels. |
| **12. Advisory** | Dictionary | `H&R BLOCK`, `SMITH & ASSOC`, `LEGALZOOM`, `ACCOUNTANT` | `Professional Services` | 0.95 | Legal and accounting advisory. |
| **13. Bank Fees** | Regex | `MONTHLY ACCOUNT SERVICE FEE`, `OVERDRAFT FEE`, `WIRE FEE` | `Bank Fees` | 0.92 | Commercial banking maintenance charges. |
| **14. Mangled SQ/TST**| Heuristic | `SQ *ARTISAN BAKERY`, `TST* DOWNTOWN BISTRO` | `Meals & Coffee` | 0.86 | Strips processor prefix and checks merchant root. |
| **15. Broad Keywords** | Substring | `TAXI`, `FLIGHT`, `COFFEE`, `PRINTER`, `PROMOTION` | Various | 0.80–0.85 | Keyword fallback for non-exact vendors. |
| **16. Unmatched Deposit**| Sign | Positive amount without verified invoice keywords | `Needs Review` | 0.30 | Unverified inbound funds could be loan or capital; requires review. |
| **17. Fallback** | Default | Any remaining unclassified transaction | `Needs Review` | 0.20 | Safe conservative fallback. |

---

## 4. Edge Cases & Tax Semantics

### 1. Refunds & Credits
- **Problem:** When an office supply purchase is returned, bank statements show an inflow (e.g. `+$45.50`). A naive script would treat this as client revenue, inflating taxable gross income.
- **Solution:** Layer 2 catches refunds, labels them `Refund`, separates them from client revenue, and offsets net operating costs without corrupting gross 1099 revenue metrics.

### 2. Internal Transfers & Card Settlements
- **Problem:** Moving $1,000 to savings or paying a $750 credit card bill from checking appears as a withdrawal. Categorizing this as an expense results in catastrophic double-counting of expenses.
- **Solution:** Identified early in Layer 1 as `Transfer (not spending)` and strictly excluded from both operating expenses and operating revenue.

### 3. Genuinely Ambiguous Merchants (`JOES CAFE 9921`, `AMAZON.COM`)
- **Problem:** `JOES CAFE 9921` could be a business client meeting, personal coffee, or travel meal. `AMAZON.COM` could be computer cables, personal groceries, or books.
- **Solution:** In accordance with the assessment rule (*"A wrong guess is worse than asking"*), ambiguous descriptors are flagged `Needs Review` (confidence < 0.50), bringing them to the user's attention in the dedicated review queue.

### 4. IRS Schedule C 50% Business Meal Limitation
- **Problem:** Under IRC § 274(n), business meals are generally limited to a 50% tax deduction. Automatically halving the statement amount corrupts bank reconciliation.
- **Solution:** The app preserves the true financial transaction amount ($8.75) and explicitly attaches an IRS Schedule C Notice: `"Subject to 50% business deduction rule under IRS Schedule C (Line 24b)"`.

### 5. Mangled Processor Descriptors
- **Problem:** Square and Toast prepend merchant names with `SQ *` or `TST* ` (e.g. `SQ *ARTISAN BAKERY`).
- **Solution:** Normalization cleans prefix noise and parses the underlying vendor name.

### 6. Duplicate Charge Detection
- **Problem:** Double-swipes or recurring charge anomalies can occur.
- **Solution:** An audit pass flags identical amounts at identical normalized merchants within a 3-day window with an interactive warning chip (`is_duplicate: true`).

---

## 5. Monetary Arithmetic & Numerical Precision

To prevent IEEE-754 binary floating point representation issues (e.g. `0.1 + 0.2 = 0.30000000000000004`), all financial sums and calculations in the backend use Python's standard `decimal.Decimal` with fixed two-decimal precision. JSON responses serialize monetary values as exact strings, and the React frontend formats them safely using localized currency display.

---

## 6. Privacy & Security Architecture

1. **Zero External AI Calls:** All categorization is evaluated locally within the Python process. Financial descriptions and amounts are never transmitted to third-party AI APIs.
2. **Ephemeral Memory Processing:** Uploaded files are processed in-memory. No financial statement files are stored on disk permanently.
3. **Zero Secrets in Repository:** No credentials, tokens, or private data are committed.
4. **Input Sanitization:** Strict CSV size limits (10 MB / 10,000 rows) and column validation prevent resource exhaustion.
