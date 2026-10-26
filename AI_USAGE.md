# AI usage

I used Copilot SDK in VS Code to help scaffold the application, review the assessment requirements, and draft tests and documentation. The categorization brain was designed as application code: an ordered, keyword-based ruleset with explicit confidence and review behavior. No generative AI model is called by the application to make category decisions.

## What AI helped with

- Project structure and initial FastAPI/React scaffolding.
- Edge-case discussion for refunds, transfers, unknown merchants, malformed CSV rows, and accounting-style amounts.
- Test case drafting and UI copy.

## What was checked or changed by hand

- Verified that unknown merchants go to **Needs review**.
- Verified that refunds are evaluated before income.
- Added validation for file type, UTF-8 encoding, required headers, empty statements, and invalid rows.
- Added tests for the core decision rules and upload response.

## Token usage

This implementation was created in a Copilot SDK session. The session's tool usage metadata is the usage log for this assessment; no external model API or application secret was used.
