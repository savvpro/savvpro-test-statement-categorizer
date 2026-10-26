# Design

## Use case

Studio North is a one-person freelance design practice. At tax time the designer exports the business credit card and needs every row in a Schedule C style bucket: software, travel, meals, supplies, equipment, contract labor, marketing, professional services, utilities, education, and card fees.

Some rows are not expenses at all. A card payment and a transfer to savings are movements of money. A Stripe payout or a client payment is income. A refund is money back against an earlier expense. A Sephora charge on the business card is personal. Amazon, PayPal, Venmo, cash, a phone bill, and an unknown cafe are not safe to file automatically.

The product ends when the designer can see a deductible total, a category breakdown, and a short list of rows that still need a human.

## Amount model

Inside the app, positive means money out and negative means money in.

- Credit-card exports usually store charges as positive and payments or refunds as negative. That is the default.
- Bank exports usually store deposits as positive. Choosing "Bank account" flips that sign.
- If the file has debit and credit columns, those columns win.
- `CR`, `DR`, parentheses, and a trailing minus are honored.
- If the description itself says refund, return, or reversal, and the amount came through as positive, the row is treated as money in.

## How a row is decided

The brain in `backend/app/brain.py` is a fixed procedure. Nothing in that path calls a model.

1. **Empty description.** Needs review.
2. **Shape of the statement line**, which outranks merchant names:
   - "Payment thank you", "credit card payment", or an autopay line that is money in → Card payment.
   - "Transfer to/from", "xfer", "balance transfer" → Transfer.
   - Interest, annual fee, foreign transaction fee, finance charge → Interest and fees.
   - "Stripe payout" or "client payment" that is money in → Client income.
   - The same income words on money out stay in review, because the sign and the words disagree.
   - A phone bill that says "AUTO PAY" is not a card payment. Autopay language only counts as a card payment when money is coming in, or when the line also says thank-you / credit-card payment.
3. **Merchant rules.** A list of patterns for tools and vendors a designer actually buys from: Adobe, Figma, Uber, Uber Eats, B&H, Staples, Upwork, Google Ads, and so on. Uber Eats is matched before Uber, so a meal is not filed as travel.
4. **Saved merchants.** When the designer checks "Remember merchant", the fingerprint and the category are stored in SQLite. Next time that fingerprint is seen, the saved category is used at 0.99. A saved merchant does not override a card payment, transfer, fee, or income line.
5. **Refunds.** Refund, return, reversal, or chargeback language, or money in from a known merchant, becomes Refund. If the merchant is known, the refund records which expense it reduces. It is never called income. A refund whose merchant is unknown is still a refund, and the category it reduces stays blank.
6. **Ask.** If no rule clears the bar, the row is Needs review. A weak hint (a cafe word, a Toast `TST*` prefix, Amazon, PayPal) is stored as a suggestion and is not filed.

A rule files the row only when its weight is at least **0.78** and the next competing rule is at least **0.12** behind. A tie, such as a line that names both Adobe and Figma, stays in review. The threshold is the whole policy: a wrong guess is worse than a question.

Fingerprints are the rule id for a confident merchant (`adobe`, `staples`) and the first two meaningful tokens otherwise (`JOES CAFE`). Store numbers, "pending", and a leading `TST*` are stripped so the same cafe can be recognized later. Remembering is offered less eagerly for Amazon, PayPal, Venmo, Zelle, Apple, and ATM, because one confirmation would be a poor label for every future row.

## Messy statement cases

- **Duplicate export or a repeated charge.** The second row with the same date, fingerprint, and amount is held out and marked as a possible duplicate. Saving a category on it means the designer confirmed it, and then it counts.
- **Pending.** The row is still categorized, and the screen marks it pending, because the amount is already on the statement.
- **Zero amount.** Held out of every total.
- **Totals lines, broken dates, and amounts that are not numbers.** Skipped, with a warning. A preamble above the header is ignored.
- **Blank description.** Kept and sent to review.

## Totals

The deductible figure is the sum of filed expense categories after refunds have been subtracted from the category they offset. These stay outside that figure:

- rows still in review, including unconfirmed duplicates
- personal charges
- card payments and transfers
- client income
- a refund that has no category to reduce

Personal refunds reduce the personal total. Unassigned refunds are shown on their own so the deductible number is not quietly overstated.

## What this does not do

It does not read PDFs. Bank PDF layouts vary too much to guess responsibly. It does not decide tax law. Meals are filed as meals, not as a 50 percent deduction, and card interest is filed as a fee for the designer to review with whoever prepares the return. It does not keep uploaded statements after the API process stops. Saved merchants do persist in the local SQLite file.
