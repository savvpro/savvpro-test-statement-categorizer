# AI_USAGE.md

This document records how AI tools were used while building the Statement Categorizer.

## Tools Used

| Tool              | Purpose                                      |
|-------------------|----------------------------------------------|
| Grok (xAI)        | Primary coding assistant for scaffolding, rule design, frontend components, tests, and documentation |

No other AI coding tools (Cursor, Copilot, Claude, ChatGPT, etc.) were used for this submission.

## How AI Helped

1. **Architecture & Design**
   - Helped define a clear, tax-relevant set of categories for freelance software engineers.
   - Suggested the priority order of rules (refunds / income first, then strong merchant matches, then broad keywords, then Needs Review).

2. **Rule Engine (`categorizer.py`)**
   - Generated the initial list of high-signal merchant patterns (Adobe, GitHub, Vercel, AWS, Uber, etc.).
   - Wrote the normalization logic and confidence / reason fields.
   - Added explicit handling for refunds vs debits and income vs expenses.

3. **CSV Parser**
   - Helped design flexible column detection (date / description / amount under common header names).

4. **FastAPI Backend**
   - Scaffolded the endpoints and Pydantic models quickly.

5. **React Frontend**
   - Generated a clean, dark-themed UI with upload, summary cards, filterable table, and inline category editing.

6. **Tests**
   - Wrote comprehensive unit tests covering happy paths and important edge cases (refunds, unknown merchants, empty descriptions).

7. **Documentation**
   - Drafted `README.md`, `DESIGN.md`, and this file.

## Where AI Got Things Wrong / Needed Correction

- Early versions of the rule lists contained a few overly broad patterns (e.g. just AMAZON) that would have incorrectly categorized shopping. These were tightened to more specific patterns.
- Initial refund logic did not check the sign of the amount. This was corrected so that a REFUND keyword on a debit is treated as suspicious and sent to Needs Review.
- Some frontend TypeScript types were incomplete in the first draft and needed manual fixing.

## Token / Usage Notes

Because this work was done in an interactive session with Grok, exact token counts per message are not available in a single exportable log.

Approximate session scale:
- Multiple long coding turns covering backend, frontend, tests, and docs.
- Total estimated tokens exchanged: in the range of tens of thousands (typical for a full-feature coding session of this size).

No API keys or paid third-party AI services were used beyond the interactive Grok session itself.

## Important Constraint Respected

**The categorization brain never calls any large language model at runtime.**

All category decisions are made by deterministic Python rules in `backend/app/categorizer.py`. AI was used only as a coding assistant to help write that code.
