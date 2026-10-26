# simplke design

## Use case

simplke is for a freelance designer getting a business card statement ready for tax time.

It helps sort:

- Adobe and Figma into Software.
- Uber and hotels into Travel.
- Office purchases into Office supplies.
- Client payments into Income.
- Transfers and card payments into Transfer / non-spend.
- Refunds into Refund, not Income.

The demo statement is fake.

## How the brain works

The brain is our own code. It is in `backend/categorizer.py`. The browser has the same rules in `client/src/lib/categorizer.ts`.

No GPT, Claude, Gemini, embeddings, or other large model chooses a category.

Rules run from top to bottom:

1. Missing data goes to **Needs review**.
2. Exact duplicate rows go to **Needs review**.
3. Transfers and card payments become **Transfer / non-spend**.
4. Refunds and returns become **Refund**.
5. Known client payments and payouts become **Income**.
6. Fees become **Bank fees**.
7. Known merchant words map to Software, Travel, Meals, Office supplies, Equipment, or Advertising.
8. A generic or unknown row becomes **Needs review**.

Example: `JOES CAFE 9921` is not a strong enough match, so it stays in Needs review.

Every automatic result shows the rule that matched. The user can fix unsure rows and export the result.

## Money display

The app displays amounts as PKR. It does not invent a dollar-to-PKR exchange rate. The original amount stays in the exported CSV.
