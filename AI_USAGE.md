# AI usage

## Tool

Cursor, with the Grok 4.7 coding agent, wrote this project in one working session on 26 October 2026. I used it to implement the app, not to categorize transactions. The running app never calls an AI model. Categories come from the rules in `backend/app/brain.py`.

## What it did

- Read the assessment task and turned it into a freelance-designer tax-prep use case.
- Drafted the Python parser, the rule brain, totals, saved-merchant storage, the FastAPI routes, the React screen, the fictional sample statement, and the tests.
- Chose the confidence threshold and the list of merchants the rules refuse to file: Amazon, PayPal, unknown cafes, phone bills, cash, streaming.

## Where it went wrong

These showed up while the code was being checked, and the code was changed afterward:

- A first pass treated any line containing "AUTO PAY" as a card payment. That would have filed `T-MOBILE*AUTO PAY` as a card payment instead of asking about a phone bill. Autopay wording now counts as a card payment only when the money is coming in, or when the line is the familiar "payment thank you" wording.
- A trailing `CR` stuck to an amount (`54.99CR`) was not stripped, so the amount would have been rejected. The parser now accepts `CR`, `DR`, parentheses, and a trailing minus.
- A semicolon-separated header was invisible to a comma-only header scan. Header detection now tries comma, semicolon, and tab.
- Month names such as `02-Jan-2026` were parsed with the machine locale. They are now matched against an English month list.
- Uber Eats would also have matched the generic Uber travel rule. The travel rule does not apply when the line is Uber Eats.
- Remembering a Toast `TST*` cafe used a fingerprint that started with `TST`, so it would not meet the same cafe next month. A leading `TST` token is dropped before the fingerprint is built.

## Tokens

Cursor did not show a session token total, a per-request log, or a usage export in this session. No token number is recorded here, because inventing one would be false. There is no screenshot of a counter that was not on screen.

The work was a single implementation session: task reading, the backend, the frontend, tests, and these notes. I did not use a second AI product, an API key, or a hosted model to label transactions.
