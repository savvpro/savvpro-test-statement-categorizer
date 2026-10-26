# Design Document

## Use Case
**Small e-commerce seller** (handmade goods sold on Shopify + Etsy). 
They upload their monthly business bank statement (CSV) to automatically sort their expenses for tax time. 

## The Brain (Rule Engine)
The task strictly forbids using LLMs (GPT, Claude) for categorization. The brain is a deterministic, rule-based engine built in Python. 

### Money-Flow Priority
To handle messy statements, the brain processes rows in a strict priority order. This prevents critical errors, like counting a refund as income.
1. **Refunds (Priority 1):** Checked first. If a row contains "REFUND" or "RETURN", it is categorized as a Refund. It is excluded from income totals.
2. **Transfers (Priority 2):** "TRANSFER TO SAVINGS" or "AUTOPAY" is tagged as "Not Spending" so it doesn't skew expense totals.
3. **Income/Payouts (Priority 3):** Matches known marketplace payouts (Shopify, Etsy, Stripe).
4. **Expenses (Priority 4):** Uses regex to match known merchants (USPS = Shipping, Facebook Ads = Marketing, Alibaba = Inventory).
5. **Needs Review (Fallback):** If a row does not match any rule, or if the confidence score is below `0.80`, it is sent to "Needs Review". The UI highlights this for the user to fix manually.

## Tech Stack
- **Backend:** Python, FastAPI, Pytest
- **Frontend:** Next.js (React), TypeScript
- **Data format:** CSV (v1). The parser interface is abstracted so PDF parsing can be added easily later.

## Edge Cases Handled
- **Refund vs Income:** An inbound "AMAZON REFUND" is not tagged as income.
- **Cryptic supplier names:** "ALIBABA.COM*XYZ123" is cleaned via regex normalizer to match "ALIBABA".
- **Bad Data:** Missing columns or invalid dates in the CSV are caught by the backend and returned as a clean `400 Bad Request` error message in the UI.