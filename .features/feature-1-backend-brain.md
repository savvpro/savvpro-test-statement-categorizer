# Feature 1: Backend Models & Brain Engine

## Goal
Build the entire deterministic classification brain — the core logic that reads a transaction description and returns a category, confidence score, and review status. No LLM calls. Pure algorithmic code.

## Use Case
**Freelance Software Engineer / Tech Consultant** who earns via Stripe/Upwork/client invoices and spends on cloud hosting, SaaS tools, travel, meals, and hardware. Needs transactions sorted into IRS Schedule C tax categories.

---

## Files to Create

### 1. `backend/requirements.txt`
```
fastapi>=0.110.0
uvicorn>=0.28.0
pydantic>=2.6.0
python-multipart>=0.0.9
pytest>=8.0.0
httpx>=0.27.0
```

### 2. `backend/app/__init__.py`
Empty file.

### 3. `backend/app/models/__init__.py`
Re-export all models from `transaction.py`.

### 4. `backend/app/models/transaction.py`
Pydantic models:

- **`TransactionDirection`** (str Enum): `OUTFLOW`, `INFLOW`, `REFUND`, `TRANSFER`
- **`ReviewStatus`** (str Enum): `AUTO_VERIFIED`, `NEEDS_REVIEW`, `MANUALLY_APPROVED`, `PERSONAL`
- **`TransactionRaw`**: Input model with fields: `id`, `date`, `raw_description`, `amount`, `raw_type` (optional), `account` (optional)
- **`TransactionCategorized`**: Output model with fields: `id`, `date`, `raw_description`, `clean_merchant`, `amount`, `direction`, `category`, `schedule_c_line`, `tax_deductible`, `deductible_percentage`, `deductible_amount`, `confidence` (0.0–1.0), `status`, `needs_review`, `review_reason`, `decision_rule`, `notes`
- **`CategorySummary`**: `category`, `schedule_c_line`, `transaction_count`, `gross_amount`, `deductible_amount`
- **`TaxSummary`**: `total_transactions`, `gross_income`, `total_expenses`, `total_deductible_expenses`, `net_taxable_profit`, `estimated_tax_savings`, `non_taxable_transfers`, `needs_review_count`, `needs_review_amount`, `categories` (list of CategorySummary)
- **`CategorizeResponse`**: `filename`, `parsed_count`, `warnings`, `transactions`, `summary`
- **`RecalculateRequest`**: `transactions` (list of TransactionCategorized)

### 5. `backend/app/brain/__init__.py`
Re-export all brain modules.

### 6. `backend/app/brain/categories.py`
Dictionary `TAX_CATEGORIES` mapping category name → metadata:

| Category | Schedule C Line | Deductible % | Example |
|----------|----------------|-------------|---------|
| Software & Subscriptions | Part V (Other - Software) | 100% | GitHub, AWS, Vercel |
| Hardware & Equipment | Line 13 (Depreciation) | 100% | Laptops, monitors |
| Meals & Client Entertainment | Line 24b | **50%** | Business meals (IRS 50% rule) |
| Travel & Transportation | Line 24a / Line 9 | 100% | Uber, flights, hotels |
| Internet & Utilities | Line 25 | 80% | Comcast, Verizon (home office ratio) |
| Professional & Legal Services | Line 17 | 100% | CPA, Stripe fees, LegalZoom |
| Advertising & Marketing | Line 8 | 100% | Google Ads, domain registration |
| Office Supplies & Books | Line 22 | 100% | Notebooks, tech books |
| Gross Business Income | Line 1 | 0% | Client payments, Stripe payouts |
| Refund / Expense Reduction | Adjustment | 100% (negative offset) | Vendor returns |
| Transfers & Non-Taxable | N/A | 0% | Credit card autopay, savings transfer |
| Personal / Non-Deductible | N/A | 0% | Personal expenses on business card |
| Needs Review | Pending | 0% | Ambiguous / unrecognized |

Each entry should also have a `color` hex value for the frontend chart and a `description` string.

### 7. `backend/app/brain/sanitizer.py`
Function `sanitize_merchant(raw_text: str) -> str`

Logic:
1. Strip common POS prefixes: `CHECKCARD`, `POS PURCHASE`, `DEBIT CARD PURCHASE`, `RECURRING TRANSACTION`, `SQ *`, `TST*`, `PAYPAL *`, `AMZN Mktp US*`, `APL*`
2. Remove noise: store numbers (`#1042`), phone numbers (`800-275-2273`), dates (`04/12`), US state/city codes (`CA USA`, `SAN FRANCISCO`), URLs, transaction IDs (`DES:`, `ID:`, `CO:`)
3. Expand abbreviations: `AMZN` → `AMAZON`, `APL` → `APPLE`, `MSFT` → `MICROSOFT`
4. Collapse whitespace, trim trailing punctuation
5. If cleaning produces empty string, fall back to raw input uppercased

### 8. `backend/app/brain/direction.py`
Function `analyze_direction_and_type(raw_desc, clean_merchant, amount, is_credit_statement=False) -> (TransactionDirection, normalized_amount, reason)`

Logic:
1. Check **transfer keywords** first: `TRANSFER TO SAVINGS`, `AUTOPAY PAYMENT`, `CREDIT CARD PAYMENT`, `E-PAYMENT`, `OWNER DRAW` → `TRANSFER`
2. Check **refund keywords**: `REFUND`, `RETURN`, `REVERSAL`, `CHARGEBACK`, `CREDIT ADJ` → `REFUND`
3. Determine inflow vs outflow based on amount sign:
   - Checking account: negative = expense, positive = deposit
   - Credit card: positive = charge, negative = credit/payment
4. If inflow, check **income keywords**: `STRIPE PAYOUT`, `UPWORK`, `CLIENT PAYMENT`, `INVOICE PAYMENT`, `DIRECT DEPOSIT` → `INFLOW`
5. If inflow from a known expense vendor (Amazon, Adobe, etc.) → treat as `REFUND` not income
6. Default outflow → `OUTFLOW`

### 9. `backend/app/brain/rules.py`
Three data structures:

**`HIGH_CONFIDENCE_VENDORS`** (dict, ~50 entries, confidence 0.95–0.99):
- Software: `AWS`, `GITHUB`, `VERCEL`, `HEROKU`, `DIGITALOCEAN`, `JETBRAINS`, `OPENAI`, `ADOBE`, `FIGMA`, `SLACK`, `NOTION`, `ZOOM`, `1PASSWORD`, `DATADOG`, `SENTRY`, `DOCKER`
- Travel: `UBER`, `LYFT`, `DELTA AIR`, `UNITED AIRLINES`, `AMTRAK`, `AIRBNB`, `MARRIOTT`, `HILTON`
- Utilities: `COMCAST`, `XFINITY`, `VERIZON`, `AT&T`, `T-MOBILE`
- Advertising: `GOOGLE ADS`, `META ADS`, `LINKEDIN ADS`, `NAMECHEAP`, `GODADDY`
- Professional: `STRIPE FEE`, `LEGALZOOM`, `GUSTO`, `DELAWARE CORP`

**`MIXED_USE_VENDORS`** (dict, ~7 entries, confidence 0.40–0.70):
- `AMAZON` → suggested "Office Supplies" but needs review
- `APPLE` → suggested "Hardware" but needs review
- `BEST BUY`, `TARGET`, `WALMART` → needs review
- `MICRO CENTER` → suggested "Hardware" (higher confidence 0.82)

**`MEAL_KEYWORDS`** (list of regex patterns):
- `\bCAFE\b`, `\bCOFFEE\b`, `\bSTARBUCKS\b`, `\bRESTAURANT\b`, `\bPIZZA\b`, `\bDOORDASH\b`, `\bUBER EATS\b`, `\bGRUBHUB\b`, `\bCHIPOTLE\b`, `\bSWEETGREEN\b`, `\bDELI\b`

### 10. `backend/app/brain/classifier.py`
Class `StatementBrain` with method `categorize_transaction(raw: TransactionRaw, is_credit_statement=False) -> TransactionCategorized`

Decision flow:
```
1. Sanitize raw description → clean_merchant
2. Analyze direction → (direction, amount, reason)
3. If TRANSFER → category="Transfers & Non-Taxable", confidence=0.98
4. If INFLOW with known income keyword → category="Gross Business Income", confidence=0.98
5. If INFLOW without keyword → category="Gross Business Income" but NEEDS_REVIEW (confidence=0.70)
6. If REFUND → category="Refund / Expense Reduction", confidence=0.95
7. If OUTFLOW:
   a. Check Tier 1 (HIGH_CONFIDENCE_VENDORS) → exact match → high confidence, auto-verified
   b. Check Tier 2 (MIXED_USE_VENDORS) → match but flag NEEDS_REVIEW if confidence < 0.85
   c. Check Tier 3 (MEAL_KEYWORDS) → match known chains (Starbucks) auto-verify; unknown cafes → NEEDS_REVIEW
   d. No match → category="Needs Review", confidence=0.25, NEEDS_REVIEW
8. Look up TAX_CATEGORIES for schedule_c_line, deductible_percentage, tax_deductible
9. Calculate deductible_amount = amount × deductible_percentage (only if verified and deductible)
```

Confidence threshold for auto-approval: **0.85**. Below that → `NEEDS_REVIEW`.

### 11. `backend/app/brain/tax_summary.py`
Function `calculate_tax_summary(transactions: List[TransactionCategorized]) -> TaxSummary`

Logic:
- Sum all `INFLOW` amounts (verified only) → `gross_income`
- Sum all `OUTFLOW` amounts → `total_expenses`
- Sum deductible amounts (verified + tax_deductible only) → `total_deductible_expenses`
- Subtract refund amounts from expenses and deductible totals
- Sum `TRANSFER` amounts → `non_taxable_transfers`
- Count/sum `NEEDS_REVIEW` items
- `net_taxable_profit` = gross_income − total_deductible_expenses
- `estimated_tax_savings` = total_deductible_expenses × 0.28 (estimated self-employed marginal rate)
- Group by category → list of `CategorySummary`

---

## Acceptance Criteria

- [x] All files created and importable: `from app.brain import StatementBrain`
- [x] `sanitize_merchant("CHECKCARD POS PURCHASE SQ *GITHUB #1042 SAN FRANCISCO CA")` returns `"GITHUB"`
- [x] A refund transaction with "REFUND" keyword returns `direction=REFUND`
- [x] `TRANSFER TO SAVINGS` returns `direction=TRANSFER`, category `Transfers & Non-Taxable`
- [x] `GITHUB` returns `category="Software & Subscriptions"`, `confidence≥0.95`, `needs_review=False`
- [x] `AMAZON` returns `category="Office Supplies & Books"`, `needs_review=True`
- [x] `JOES CAFE 9921` returns `category="Meals & Client Entertainment"`, `needs_review=True`
- [x] An unrecognized vendor returns `category="Needs Review"`, `confidence=0.25`
- [x] Tax summary correctly applies 50% deductibility to meals
- [x] Tax summary treats refunds as expense reductions (not income)

## Git Commit
```bash
git add backend/
git commit -m "feat(backend): add models, brain engine with 3-tier classifier, sanitizer, direction analyzer, and tax summary"
git push origin candidate-sikandarhussain6858
```
