# Design Document - Statement Categorizer

## Use Case

**Target User:** Freelance designers, developers, agencies, and solopreneurs who need to categorize business expenses for tax reporting.

**Problem:** Manually categorizing hundreds of transactions is time-consuming and error-prone. Users need an automated solution that:
1. Correctly identifies common business expenses
2. Flags uncertain transactions for manual review
3. Handles edge cases (refunds, income vs expenses)

**Solution:** A rule-based categorization system that uses keyword matching and amount logic to sort transactions into tax-relevant categories.

## Categories

### 1. Software & Tools
**Purpose:** Track software subscriptions and cloud service expenses

**Keywords:**
- `adobe`, `figma`, `github`, `convex`, `vercel`, `aws`, `openai`
- `microsoft`, `google cloud`, `digitalocean`, `heroku`
- `slack`, `notion`, `zoom`, `canva`, `dropbox`
- `subscription`, `creative cloud`

**Examples:**
- `ADOBE CREATIVE CLOUD` → Software & Tools
- `GITHUB PRO SUBSCRIPTION` → Software & Tools
- `AWS SERVICES` → Software & Tools

### 2. Travel & Transport
**Purpose:** Track travel expenses for client meetings and business trips

**Keywords:**
- `uber`, `careem`, `lyft`, `grab`, `taxi`
- `airblue`, `airline`, `flight`
- `petrol`, `shell`, `gas station`, `fuel`
- `hotel`, `airbnb`, `parking`, `toll`

**Examples:**
- `UBER *TRIP TO CLIENT` → Travel & Transport
- `SHELL PETROL STATION` → Travel & Transport
- `AIRBLUE FLIGHT TICKET` → Travel & Transport

### 3. Office & Supplies
**Purpose:** Track physical office expenses

**Keywords:**
- `staples`, `office depot`, `stationery`
- `printing`, `paper`, `printer`, `ink`, `toner`
- `supplies`, `furniture`, `desk`

**Examples:**
- `STAPLES STORE #123` → Office & Supplies
- `PRINTING BUSINESS CARDS` → Office & Supplies

### 4. Client Income
**Purpose:** Identify income from client payments

**Logic:** Positive amount AND income keywords

**Keywords:**
- `upwork`, `stripe`, `payoneer`, `transfer in`
- `payment received`, `freelance`, `client payment`
- `invoice payment`, `consulting fee`, `fiverr`, `toptal`

**Examples:**
- `UPWORK PAYMENT` (amount: +$2500) → Client Income
- `STRIPE TRANSFER IN` (amount: +$1200) → Client Income

**Important:** If amount is negative, even with income keywords, it won't be categorized as income (likely a fee or reversal).

### 5. Expense Refund
**Purpose:** Track refunds and reversals (money coming back)

**Keywords:**
- `refund`, `reversal`, `return`, `chargeback`
- `credit adjustment`, `reimbursement`, `cashback`

**Examples:**
- `AMAZON REFUND` → Expense Refund
- `TRANSACTION REVERSAL` → Expense Refund

**Note:** Refund detection has highest priority - even negative amounts with refund keywords are marked as refunds.

### 6. Needs Review
**Purpose:** Flag uncertain transactions for manual review

**Triggers:**
1. Description is too vague (e.g., "payment", "transfer")
2. Description is very short (< 3 characters)
3. Description is only numbers
4. No keyword match found

**Examples:**
- `JOES CAFE 9921` → Needs Review (unknown merchant)
- `PAYMENT` → Needs Review (too vague)
- `XY` → Needs Review (too short)

## The Brain: How Categorization Works

The categorization engine (`brain.py`) uses a **rule-based decision tree**:

```
Input: description, amount
│
├─ Step 1: Validate inputs
│   ├─ Empty description? → Needs Review
│   └─ Invalid amount? → Needs Review
│
├─ Step 2: Check for ambiguous patterns
│   ├─ Too short? → Needs Review
│   ├─ Only numbers? → Needs Review
│   └─ Generic words (payment, transfer)? → Needs Review
│
├─ Step 3: Check amount-based rules (HIGH PRIORITY)
│   ├─ Refund keywords? → Expense Refund (High confidence)
│   └─ Positive amount + income keywords? → Client Income (High confidence)
│
├─ Step 4: Check expense category rules
│   ├─ Software keywords? → Software & Tools (High confidence)
│   ├─ Travel keywords? → Travel & Transport (High confidence)
│   └─ Office keywords? → Office & Supplies (High confidence)
│
└─ Step 5: No match found
    └─ Default → Needs Review (Low confidence)
```

### Key Design Decisions

#### 1. Word Boundary Matching
We use regex word boundaries (`\b`) to avoid false positives:
- `UBER TRIP` matches keyword `uber`
- `SUPERUBER` does NOT match keyword `uber`

#### 2. Text Normalization
All text is normalized before matching:
- Convert to lowercase
- Remove special characters
- Collapse multiple spaces
- Strip whitespace

Example: `ADOBE *CREATIVE-CLOUD!!!` → `adobe creative cloud`

#### 3. Priority Order
The categorization follows strict priority:

1. **Ambiguity check** (prevents false positives)
2. **Refund detection** (highest priority for amounts)
3. **Income detection** (amount + keywords)
4. **Expense categories** (keyword matching)
5. **Fallback** (Needs Review)

#### 4. Confidence Scoring
- **High:** Rule matched with clear keywords
- **Medium:** (Reserved for future fuzzy matching)
- **Low:** No clear match, needs manual review

### Edge Cases Handled

#### Case 1: Refunds vs Income
**Problem:** Both refunds and income are positive amounts

**Solution:** Check for refund keywords first. If present, categorize as Expense Refund regardless of amount sign.

```python
# Refund (highest priority)
"AMAZON REFUND" + $45.00 → Expense Refund

# Income (second priority)
"UPWORK PAYMENT" + $2500.00 → Client Income
```

#### Case 2: Negative Amount with Income Keywords
**Problem:** `UPWORK FEE -$50.00` has income keyword but is an expense

**Solution:** Only categorize as income if amount is positive.

```python
"UPWORK PAYMENT" + $2500 → Client Income
"UPWORK FEE" - $50 → (falls through to other rules)
```

#### Case 3: Ambiguous Descriptions
**Problem:** Generic descriptions like "PAYMENT" could be anything

**Solution:** Pre-filter ambiguous patterns before applying rules.

```python
"PAYMENT" → Needs Review (too vague)
"PAYMENT FROM UPWORK" → Client Income (has context)
```

#### Case 4: Unknown Merchants
**Problem:** `JOES CAFE 9921` - no keywords match

**Solution:** Default to Needs Review with low confidence.

```python
"JOES CAFE 9921" → Needs Review (unknown merchant)
```

## Why No AI Models?

The task explicitly requires NO external LLM/AI models. Here's why rule-based logic is appropriate:

### Advantages
1. **Deterministic:** Same input always produces same output
2. **Explainable:** Users can see exactly why a transaction was categorized
3. **Fast:** No API calls or model inference
4. **Free:** No API costs
5. **Private:** Data never leaves the system
6. **Testable:** Easy to write unit tests for specific patterns

### Tradeoffs
1. **Limited flexibility:** Can't understand complex or novel patterns
2. **Manual maintenance:** New patterns require code updates
3. **No learning:** Doesn't improve from user corrections

### When to Use AI
For a production system at scale, you'd want:
- Fine-tuned model for better pattern recognition
- User feedback loop for learning
- Fuzzy matching for typos
- Entity recognition for merchant names

But for this assessment and use case (freelancer with recurring expenses), rule-based logic is appropriate and sufficient.

## Testing Strategy

### Unit Tests (`test_brain.py`)
- **Normal categorization:** Test each category with typical examples
- **Edge cases:** Refunds, income, ambiguous descriptions
- **Error handling:** Invalid inputs, empty strings, wrong types
- **Real-world scenarios:** Simulated freelancer monthly expenses

### Integration Tests (`test_api.py`)
- **API health checks:** Ensure endpoints respond
- **Valid uploads:** Test full CSV processing pipeline
- **Invalid uploads:** Test error handling (wrong format, missing columns)
- **Summary accuracy:** Verify category counts are correct

### Coverage
Run tests with coverage:
```bash
pytest --cov=. --cov-report=html
```

Target: >90% code coverage

## Future Enhancements

If this were to become a production product:

1. **Machine Learning Layer**
   - Train model on user corrections
   - Fuzzy string matching for typos
   - Merchant name standardization

2. **User Customization**
   - Custom categories per user
   - User-defined keyword rules
   - Learning from manual corrections

3. **Data Export**
   - Export to CSV with categories
   - Integration with accounting software (QuickBooks, Xero)
   - PDF tax reports

4. **Multi-Currency Support**
   - Currency conversion
   - Multi-country tax categories

5. **Batch Processing**
   - Process multiple statements at once
   - Historical data analysis
   - Spending trends visualization

6. **Audit Trail**
   - Track manual edits
   - Version history
   - Compliance reporting

## Security Considerations

1. **No data persistence:** Uploaded files are not stored
2. **No authentication:** Add OAuth for multi-user deployment
3. **Input validation:** CSV structure and content validated
4. **CORS:** Properly configured for frontend access
5. **No secrets in code:** Environment variables for config

## Conclusion

This design balances simplicity with functionality. The rule-based approach provides:
- High accuracy for common freelancer expenses
- Clear decision logic
- Easy testing and maintenance
- Fast, reliable categorization

The "Needs Review" category ensures we never make wrong guesses - when uncertain, we ask the user. This is more valuable than a wrong automatic categorization.
