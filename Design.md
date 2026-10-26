# Design

## Use case

A small gaming PC and hardware shop in Pakistan. The owner uploads a bank statement (CSV, PKR) at tax time and the app sorts every transaction into a category. If it is not sure, the row goes to **Needs Review** instead of being guessed.

## How the brain works

The brain is plain Python rules and scoring. It uses no AI model. For each row it:

1. Cleans the text (`IBFT TO CZONE 8841` becomes `CZONE`).
2. Checks saved rules, transfers (not spending) and ambiguous merchants like Daraz or ATM (always review).
3. Adds up evidence points for each category:
   - exact merchant name: +5
   - keyword: +3
   - close typo match: +2 or +1
   - amount in the category's usual range: +2
   - known supplier or customer, or a recurring payment: +2 each
4. Confidence is points divided by 9. Below 0.5 goes to Needs Review.

Every row gets a plain-English reason, for example: *"Inventory / COGS (0.78): exact alias TELEMART, in typical range."*

## When it is not sure

- **Conflicts:** an unrealistic amount (like PKR 250,000 for software), the wrong money direction, or evidence pointing two ways sends the row to review.
- **Two reasons needed:** a category is only assigned if at least two kinds of evidence agree (name, amount, history).
- **Corrections:** when you fix a row, the app saves a rule and uses it for similar rows.

## Edge cases handled

Refunds, transfers, duplicate rows, ambiguous merchants, wrong direction, unrealistic amounts, recurring payments, and messy CSVs (three layouts; blank and pending rows are skipped).

## Limitations

CSV only, no foreign currency, no splitting one payment across categories, and memory of suppliers and customers lasts for one upload. The weights were set by hand and tuned on fake data.